"""Read-only Human-facing presentation for persisted Product Intelligence."""

from __future__ import annotations

import argparse as _argparse
import asyncio as _asyncio
import json as _json
import sys as _sys

from src.core.errors import AgentException as _AgentException
from src.product_intelligence.canonical_catalog_sqlite import (
    CanonicalCatalogStorageError as _CanonicalCatalogStorageError,
    load_sqlite_canonical_catalog as _load_sqlite_canonical_catalog,
)
from src.product_intelligence.persistent_grounded_qa import (
    PersistentGroundedQaError as _PersistentGroundedQaError,
    answer_persisted_grounded_question as _answer_persisted_grounded_question,
)
from src.product_intelligence.grounded_invocation import (
    GroundedInvocationError as _GroundedInvocationError,
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
    _AgentException,
    OSError,
    ValueError,
)
_MAX_ERROR_MESSAGE_UTF8_BYTES = 2048


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
        else:
            document = _asyncio.run(_ask_document(arguments))
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
