"""Read-only Human-facing presentation for persisted Product Intelligence."""

from __future__ import annotations

import argparse as _argparse
import asyncio as _asyncio
from datetime import datetime as _datetime, timezone as _timezone
import json as _json
import sys as _sys
from typing import Optional as _Optional

from src.core.errors import AgentException as _AgentException
from src.integrations.playwright.manager import (
    PlaywrightBrowserManager as _PlaywrightBrowserManager,
)
from src.product_intelligence.adapters.shopee import (
    ShopeeDiscoveryAdapter as _ShopeeDiscoveryAdapter,
)
from src.product_intelligence.adapters.tiktok import (
    TikTokDiscoveryAdapter as _TikTokDiscoveryAdapter,
)
from src.product_intelligence.approval import (
    ApprovalDecision as _ApprovalDecision,
    ApprovalError as _ApprovalError,
    create_approval_record as _create_approval_record,
    enqueue_approval as _enqueue_approval,
)
from src.product_intelligence.canonical_catalog_sqlite import (
    CanonicalCatalogStorageError as _CanonicalCatalogStorageError,
    load_sqlite_canonical_catalog as _load_sqlite_canonical_catalog,
)
from src.product_intelligence.discovery import (
    DiscoveryError as _DiscoveryError,
    DiscoveryRequest as _DiscoveryRequest,
)
from src.product_intelligence.grounded_invocation import (
    GroundedInvocationError as _GroundedInvocationError,
)
from src.product_intelligence.orchestration import (
    OrchestrationError as _OrchestrationError,
    OrchestrationResult as _OrchestrationResult,
    PlatformDiscoveryPlan as _PlatformDiscoveryPlan,
    orchestrate_discovery as _orchestrate_discovery,
)
from src.product_intelligence.persistent_grounded_qa import (
    PersistentGroundedQaError as _PersistentGroundedQaError,
    answer_persisted_grounded_question as _answer_persisted_grounded_question,
)
from src.product_intelligence.source_evidence_intake import (
    SourceEvidenceIntakeError as _SourceEvidenceIntakeError,
    intake_product_source_evidence as _intake_product_source_evidence,
)
from src.providers.gemini import GeminiProvider as _GeminiProvider


_KNOWN_APPLICATION_ERRORS = (
    _SourceEvidenceIntakeError,
    _CanonicalCatalogStorageError,
    _PersistentGroundedQaError,
    _GroundedInvocationError,
    _DiscoveryError,
    _OrchestrationError,
    _ApprovalError,
    _AgentException,
    OSError,
    ValueError,
)
_MAX_ERROR_MESSAGE_UTF8_BYTES = 2048


class _UniqueStoreAction(_argparse.Action):
    """Store option value while rejecting repeated occurrences."""

    def __call__(self, parser, namespace, values, option_string=None):
        seen = getattr(namespace, "_seen_unique_actions", None)
        if seen is None:
            seen = set()
            setattr(namespace, "_seen_unique_actions", seen)
        if self.dest in seen:
            raise _argparse.ArgumentError(self, "cannot be repeated")
        seen.add(self.dest)
        setattr(namespace, self.dest, values)


def _parse_iso_datetime(value: str) -> _datetime:
    try:
        return _datetime.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise _argparse.ArgumentTypeError(
            f"Invalid ISO-8601 datetime: {value!r}"
        ) from exc


def _parser() -> _argparse.ArgumentParser:
    parser = _argparse.ArgumentParser(
        prog="python -m src.product_intelligence.cli",
        description="Read-only Product Intelligence presentation.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    evidence = commands.add_parser(
        "evidence", help="Inspect persisted source-evidence inventory."
    )
    evidence.add_argument(
        "--root",
        action="append",
        required=True,
        help="Explicit local evidence root (repeat for multiple roots).",
    )

    catalog = commands.add_parser(
        "catalog", help="Inspect one persisted canonical catalog."
    )
    catalog.add_argument("--database", required=True, help="Canonical catalog database.")

    ask = commands.add_parser(
        "ask", help="Ask one grounded question over persisted knowledge."
    )
    ask.add_argument("--database", required=True, help="Canonical catalog database.")
    ask.add_argument(
        "--root",
        action="append",
        required=True,
        help="Explicit local evidence root (repeat for multiple roots).",
    )
    ask.add_argument("--question", required=True, help="Grounded question text.")
    ask.add_argument(
        "--backend",
        required=True,
        choices=("developer_api", "vertex_ai"),
        help="Human-selected Gemini backend.",
    )
    discover = commands.add_parser(
        "discover", help="Discover and rank candidate products across marketplaces."
    )
    discover.add_argument(
        "--query",
        action=_UniqueStoreAction,
        required=True,
        help="Discovery search query.",
    )
    discover.add_argument(
        "--platform",
        action="append",
        required=True,
        choices=("shopee", "tiktok"),
        help="Marketplace platform (repeat for multiple platforms).",
    )
    discover.add_argument(
        "--cdp-endpoint",
        action=_UniqueStoreAction,
        required=True,
        help="Explicit CDP endpoint URL.",
    )
    discover.add_argument(
        "--shortlist-size",
        action=_UniqueStoreAction,
        type=int,
        default=None,
        help="Optional maximum shortlist count.",
    )
    decide = commands.add_parser(
        "decide",
        help="Discover, review shortlist candidates, and record one human decision.",
    )
    decide.add_argument(
        "--query",
        action=_UniqueStoreAction,
        required=True,
        help="Discovery search query.",
    )
    decide.add_argument(
        "--platform",
        action="append",
        required=True,
        choices=("shopee", "tiktok"),
        help="Marketplace platform (repeat for multiple platforms).",
    )
    decide.add_argument(
        "--cdp-endpoint",
        action=_UniqueStoreAction,
        required=True,
        help="Explicit CDP endpoint URL.",
    )
    decide.add_argument(
        "--shortlist-size",
        action=_UniqueStoreAction,
        type=int,
        default=None,
        help="Optional maximum shortlist count.",
    )
    decide.add_argument(
        "--actor",
        action=_UniqueStoreAction,
        required=True,
        help="Explicit human actor identifier.",
    )
    decide.add_argument(
        "--decided-at",
        action=_UniqueStoreAction,
        required=True,
        type=_parse_iso_datetime,
        help="Explicit ISO-8601 decided timestamp.",
    )
    return parser


def _evidence_document(roots: list[str]) -> dict[str, object]:
    inventory = _intake_product_source_evidence(roots)
    return {
        "manifest_paths": list(inventory.manifest_paths),
        "source_packs": [
            {
                "source_pack_id": pack.source_pack_id,
                "platform": pack.platform,
                "source_product_id": pack.source_product_id,
                "product_url": pack.product_url,
                "observed_at": pack.observed_at.isoformat(),
                "title": pack.title,
            }
            for pack in inventory.source_packs
        ],
    }


def _catalog_document(database: str) -> dict[str, object]:
    catalog = _load_sqlite_canonical_catalog(database)
    return {
        "family_count": len(catalog.families),
        "variant_count": len(catalog.variants),
        "families": [
            {
                "family_id": family.family_id,
                "member_source_pack_ids": [
                    member.source_pack_id for member in family.members
                ],
            }
            for family in catalog.families
        ],
        "variants": [
            {
                "variant_id": variant.variant_id,
                "family_id": variant.family_id,
                "member_source_pack_ids": [
                    member.source_pack_id for member in variant.members
                ],
            }
            for variant in catalog.variants
        ],
    }


async def _ask_document(arguments: _argparse.Namespace) -> dict[str, object]:
    inventory = _intake_product_source_evidence(arguments.root)
    provider = _GeminiProvider(backend=arguments.backend)
    answer = await _answer_persisted_grounded_question(
        arguments.database,
        inventory.manifest_paths,
        question=arguments.question,
        provider=provider,
    )
    return {
        "status": answer.status.value,
        "answer_text": answer.answer_text,
        "citation_ids": list(answer.citation_ids),
        "limitations": list(answer.limitations),
    }


async def _run_live_discovery(
    cdp_endpoint: str,
    query: str,
    platforms: list[str],
    shortlist_size: _Optional[int] = None,
) -> _OrchestrationResult:
    browser_manager = _PlaywrightBrowserManager(cdp_endpoint=cdp_endpoint)
    orchestration_error: _Optional[BaseException] = None
    try:
        plans = tuple(
            _PlatformDiscoveryPlan(
                platform=platform,
                adapter=(
                    _ShopeeDiscoveryAdapter(browser=browser_manager)
                    if platform == "shopee"
                    else _TikTokDiscoveryAdapter(browser=browser_manager)
                ),
                request=_DiscoveryRequest(query=query),
            )
            for platform in platforms
        )
        now = _datetime.now(_timezone.utc)
        return await _orchestrate_discovery(
            plans,
            observed_at=now,
            evaluated_at=now,
            shortlist_size=shortlist_size,
        )
    except BaseException as error:
        orchestration_error = error
        raise
    finally:
        try:
            await browser_manager.close_all()
        except Exception:
            if orchestration_error is None:
                raise


async def _discover_document(arguments: _argparse.Namespace) -> dict[str, object]:
    result = await _run_live_discovery(
        cdp_endpoint=arguments.cdp_endpoint,
        query=arguments.query,
        platforms=arguments.platform,
        shortlist_size=arguments.shortlist_size,
    )
    return result.to_dict()


async def _decide_document(arguments: _argparse.Namespace) -> dict[str, object]:
    result = await _run_live_discovery(
        cdp_endpoint=arguments.cdp_endpoint,
        query=arguments.query,
        platforms=arguments.platform,
        shortlist_size=arguments.shortlist_size,
    )
    if not result.shortlist:
        raise ValueError("Discovery shortlist is empty")

    _write_json(result.to_dict(), _sys.stderr)

    raw_position = _sys.stdin.readline()
    if not raw_position:
        raise ValueError("Unexpected end of input: missing shortlist position")
    position_text = raw_position.rstrip("\r\n")
    if not position_text.isdigit():
        raise ValueError(f"Invalid shortlist position: {position_text!r}")
    position = int(position_text)
    if not (1 <= position <= len(result.shortlist)):
        raise ValueError(
            f"Shortlist position out of range: {position} (expected 1..{len(result.shortlist)})"
        )

    raw_decision = _sys.stdin.readline()
    if not raw_decision:
        raise ValueError("Unexpected end of input: missing decision token")
    decision_text = raw_decision.rstrip("\r\n")
    if decision_text not in ("APPROVE", "REJECT"):
        raise ValueError(f"Invalid decision token: {decision_text!r}")

    selected_candidate = result.shortlist[position - 1]
    decision = (
        _ApprovalDecision.APPROVE
        if decision_text == "APPROVE"
        else _ApprovalDecision.REJECT
    )
    record = _create_approval_record(
        selected_candidate,
        decision=decision,
        actor=arguments.actor,
        decided_at=arguments.decided_at,
    )

    if decision is _ApprovalDecision.APPROVE:
        enqueue_result = _enqueue_approval(record)
        queue_document: _Optional[dict[str, object]] = {
            "task": enqueue_result.task,
            "outcome": enqueue_result.outcome.value,
        }
    else:
        queue_document = None

    return {
        "approval": {
            "decision": record.decision.value,
            "actor": record.actor,
            "decided_at": record.decided_at.isoformat(),
            "ranked_candidate": {
                "candidate": record.ranked_candidate.candidate.to_dict(),
                "score": record.ranked_candidate.score.to_dict(),
            },
        },
        "queue": queue_document,
    }


def _write_json(document: dict[str, object], stream) -> None:
    _json.dump(document, stream, ensure_ascii=False, indent=2)
    stream.write("\n")


def _bounded_error_message(error: BaseException) -> str:
    message = str(error)
    encoded = message.encode("utf-8", errors="replace")
    if len(encoded) <= _MAX_ERROR_MESSAGE_UTF8_BYTES:
        return encoded.decode("utf-8")
    return encoded[:_MAX_ERROR_MESSAGE_UTF8_BYTES].decode(
        "utf-8", errors="ignore"
    )


def main(argv=None) -> int:
    """Parse one operation, execute it once, and render one JSON document."""

    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "evidence":
            document = _evidence_document(arguments.root)
        elif arguments.command == "catalog":
            document = _catalog_document(arguments.database)
        elif arguments.command == "ask":
            document = _asyncio.run(_ask_document(arguments))
        elif arguments.command == "discover":
            document = _asyncio.run(_discover_document(arguments))
        elif arguments.command == "decide":
            document = _asyncio.run(_decide_document(arguments))
        else:
            raise ValueError(f"Unknown command: {arguments.command}")
    except _KNOWN_APPLICATION_ERRORS as error:
        _write_json(
            {
                "error": {
                    "type": type(error).__name__,
                    "message": _bounded_error_message(error),
                }
            },
            _sys.stderr,
        )
        return 1
    except Exception:
        _write_json(
            {
                "error": {
                    "type": "UnexpectedError",
                    "message": "An unexpected error occurred.",
                }
            },
            _sys.stderr,
        )
        return 1

    _write_json(document, _sys.stdout)
    return 0


__all__ = ["main"]


if __name__ == "__main__":
    raise SystemExit(main())
