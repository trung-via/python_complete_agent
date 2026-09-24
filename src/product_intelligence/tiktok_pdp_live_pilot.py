"""Human-operated one-shot carrier for the authorized TikTok PDP pilot.

This module owns only operation-specific orchestration. Browser/session lifecycle,
PDP semantics, parsing, and snapshot meaning remain with their existing owners.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Callable, Mapping, Protocol

from src.integrations.playwright.manager import PlaywrightBrowserManager
from src.product_intelligence.adapters.tiktok_pdp import (
    TikTokPdpCollectionError,
    TikTokPdpCollectionResult,
    TikTokPdpCollector,
)


PILOT_CONTEXT_ID = "p8-pilot-001-led-motion-tiktok-vn"
AUTHORIZED_SOURCE_ID = "1731381331718341815"
AUTHORIZED_PDP_URL = (
    "https://shop.tiktok.com/vn/pdp/"
    "den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815"
)
CONTRACT_IDENTIFIER = "POST_TASK248_LIVE_PUBLIC_PDP_COLLECTOR_VALIDATION"
COLLECTOR_BASELINE_TASK_ID = "TASK-248"
COLLECTOR_BASELINE_SOURCE_SHA = "39979020a10b78e1f86c30cf2b704f2f975daec9"

ATTEMPT_MARKER_FILENAME = "tiktok-pdp-live-validation-attempt-v2.json"
RESULT_FILENAME = "tiktok-pdp-live-validation-result-v2.json"
LEGACY_ARTIFACT_FILENAME = "tiktok-pdp-live-pilot-result-v1.json"
ARTIFACT_FILENAME = RESULT_FILENAME

_SESSION_RUN_ID = f"human-one-shot:{PILOT_CONTEXT_ID}"
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class TikTokPdpLivePilotError(RuntimeError):
    """Bounded carrier failure that never includes operator CDP input."""


class TikTokPdpLivePilotJobRootError(TikTokPdpLivePilotError):
    """The requested artifact boundary is unsafe or unavailable."""


class TikTokPdpLivePilotArtifactExistsError(TikTokPdpLivePilotError):
    """The one-shot artifact already exists and must not be overwritten."""


class _SessionManager(Protocol):
    async def get_or_create_session(self, run_id: str): ...

    async def close_session(self, run_id: str) -> None: ...


class _Collector(Protocol):
    async def collect(
        self, requested_url: str, *, observed_at: datetime
    ) -> TikTokPdpCollectionResult: ...


@dataclass(frozen=True)
class TikTokPdpLivePilotOutcome:
    artifact_path: Path
    document: Mapping[str, object]

    def to_document(self) -> dict[str, object]:
        return dict(self.document)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_external_job_root(job_root: str | Path) -> Path:
    if not isinstance(job_root, (str, Path)) or not str(job_root).strip():
        raise TikTokPdpLivePilotJobRootError("an explicit external job root is required")
    try:
        resolved = Path(job_root).expanduser().resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        raise TikTokPdpLivePilotJobRootError(
            "the external job root could not be resolved"
        ) from exc
    if resolved == _REPOSITORY_ROOT or _REPOSITORY_ROOT in resolved.parents:
        raise TikTokPdpLivePilotJobRootError(
            "the live-pilot job root must be outside the Git repository"
        )
    return resolved


def _write_json_exclusive(path: Path, document: Mapping[str, object]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(document, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def _attempt_marker_document(started_at: datetime) -> dict[str, object]:
    return {
        "schema_version": 2,
        "record_type": "VALIDATION_ATTEMPT_MARKER",
        "contract_identifier": CONTRACT_IDENTIFIER,
        "context_id": PILOT_CONTEXT_ID,
        "source_product_id": AUTHORIZED_SOURCE_ID,
        "requested_url": AUTHORIZED_PDP_URL,
        "started_at": started_at.isoformat(),
        "execution_owner": "HUMAN_OPERATOR",
        "review_status": "HUMAN_REVIEW_REQUIRED",
        "collector_baseline_task_id": COLLECTOR_BASELINE_TASK_ID,
        "collector_baseline_source_sha": COLLECTOR_BASELINE_SOURCE_SHA,
    }


def _snapshot_document(result: TikTokPdpCollectionResult) -> dict[str, object]:
    snapshot = result.snapshot
    return {
        "candidate_id": snapshot.candidate_id,
        "platform": snapshot.platform,
        "source_product_id": snapshot.source_product_id,
        "url": snapshot.url,
        "observed_at": snapshot.observed_at.isoformat(),
        "collector": snapshot.collector,
        "title": snapshot.title,
        "shop_name": snapshot.shop_name,
        "price": snapshot.price,
        "original_price": snapshot.original_price,
        "discount_percent": snapshot.discount_percent,
        "sold_count": snapshot.sold_count,
        "rating": snapshot.rating,
        "review_count": snapshot.review_count,
    }


def _terminal_result_document(
    *,
    operation_status: str,
    observation_status: str,
    session_release_status: str,
    failure_reason: str | None,
    started_at: datetime,
    observed_at: datetime,
    result: TikTokPdpCollectionResult | None = None,
) -> dict[str, object]:
    operation: dict[str, object] = {
        "operation_status": operation_status,
        "observation_status": observation_status,
        "session_release_status": session_release_status,
    }
    if failure_reason is not None:
        operation["failure_reason"] = failure_reason
    operation.update(
        {
            "contract_identifier": CONTRACT_IDENTIFIER,
            "context_id": PILOT_CONTEXT_ID,
            "source_product_id": AUTHORIZED_SOURCE_ID,
            "requested_url": AUTHORIZED_PDP_URL,
            "started_at": started_at.isoformat(),
            "observed_at": observed_at.isoformat(),
            "execution_owner": "HUMAN_OPERATOR",
            "review_status": "HUMAN_REVIEW_REQUIRED",
            "collector_baseline_task_id": COLLECTOR_BASELINE_TASK_ID,
            "collector_baseline_source_sha": COLLECTOR_BASELINE_SOURCE_SHA,
        }
    )
    doc: dict[str, object] = {
        "schema_version": 2,
        "operation": operation,
    }
    if observation_status == "OBSERVED" and result is not None:
        doc["binding"] = {
            "requested_url": result.binding.requested_url,
            "observed_url": result.binding.observed_url,
            "identity_bases": [
                {
                    "basis": basis.basis,
                    "source_product_id": basis.source_product_id,
                }
                for basis in result.binding.identity_bases
            ],
        }
        doc["snapshot"] = _snapshot_document(result)
    return doc


async def run_tiktok_pdp_live_pilot(
    *,
    job_root: str | Path,
    cdp_endpoint: str,
    clock: Callable[[], datetime] = _utc_now,
    manager_factory: Callable[..., _SessionManager] = PlaywrightBrowserManager,
    collector_factory: Callable[..., _Collector] = TikTokPdpCollector,
) -> TikTokPdpLivePilotOutcome:
    """Attempt the authorized exact listing once and never own browser shutdown."""

    # 1. Non-consuming local gates
    root = _resolve_external_job_root(job_root)
    legacy_path = root / LEGACY_ARTIFACT_FILENAME
    marker_path = root / ATTEMPT_MARKER_FILENAME
    result_path = root / RESULT_FILENAME

    if legacy_path.exists() or marker_path.exists() or result_path.exists():
        raise TikTokPdpLivePilotArtifactExistsError(
            "the one-shot live-pilot artifact already exists"
        )
    if not isinstance(cdp_endpoint, str) or not cdp_endpoint.strip():
        raise TikTokPdpLivePilotError("an explicit operator-owned CDP endpoint is required")

    started_at = clock()
    if (
        not isinstance(started_at, datetime)
        or started_at.tzinfo is None
        or started_at.utcoffset() is None
    ):
        raise TikTokPdpLivePilotError("the operation timestamp must be timezone-aware")
    observed_at = started_at

    # 2. Durable Attempt Marker creation
    marker_doc = _attempt_marker_document(started_at)
    try:
        root.mkdir(parents=True, exist_ok=True)
        _write_json_exclusive(marker_path, marker_doc)
    except FileExistsError as exc:
        raise TikTokPdpLivePilotArtifactExistsError(
            "the live-pilot attempt marker already exists"
        ) from exc
    except OSError as exc:
        raise TikTokPdpLivePilotJobRootError(
            "the live-pilot attempt marker could not be created"
        ) from exc

    # 3. Post-marker consuming execution
    session_acquired = False
    manager = None
    collector_result: TikTokPdpCollectionResult | None = None
    failure_reason: str | None = None

    try:
        try:
            manager = manager_factory(cdp_endpoint=cdp_endpoint)
            session = await manager.get_or_create_session(_SESSION_RUN_ID)
            session_acquired = True
        except Exception:
            failure_reason = "BROWSER_SESSION_UNAVAILABLE"

        if session_acquired:
            try:
                collector = collector_factory(session)
                collector_result = await collector.collect(
                    AUTHORIZED_PDP_URL, observed_at=observed_at
                )
            except TikTokPdpCollectionError as exc:
                failure_reason = exc.code.value
            except Exception:
                failure_reason = "UNCLASSIFIED_OPERATION_FAILURE"

            if collector_result is not None and failure_reason is None:
                if (
                    collector_result.snapshot.platform != "tiktok"
                    or collector_result.snapshot.source_product_id != AUTHORIZED_SOURCE_ID
                    or collector_result.snapshot.observed_at != observed_at
                    or collector_result.binding.requested_url != AUTHORIZED_PDP_URL
                    or collector_result.binding.observed_url != collector_result.snapshot.url
                    or not collector_result.binding.identity_bases
                    or any(
                        basis.source_product_id != AUTHORIZED_SOURCE_ID
                        for basis in collector_result.binding.identity_bases
                    )
                ):
                    failure_reason = "RESULT_BINDING_MISMATCH"
                    collector_result = None
    finally:
        cleanup_failed = False
        if session_acquired and manager is not None:
            try:
                await manager.close_session(_SESSION_RUN_ID)
            except Exception:
                cleanup_failed = True

    # 4. Derive statuses
    if session_acquired:
        if cleanup_failed:
            session_release_status = "FAILED"
        else:
            session_release_status = "SUCCESS"
    else:
        session_release_status = "NOT_APPLICABLE"

    if cleanup_failed:
        if failure_reason is None:
            failure_reason = "SESSION_RELEASE_FAILED"
            operation_status = "FAIL_CLOSED"
            observation_status = "OBSERVED"
        else:
            operation_status = "FAIL_CLOSED"
            observation_status = "NOT_OBSERVED"
    elif failure_reason is not None:
        operation_status = "FAIL_CLOSED"
        observation_status = "NOT_OBSERVED"
    else:
        operation_status = "SUCCESS"
        observation_status = "OBSERVED"

    # 5. Build and persist terminal document
    terminal_doc = _terminal_result_document(
        operation_status=operation_status,
        observation_status=observation_status,
        session_release_status=session_release_status,
        failure_reason=failure_reason,
        started_at=started_at,
        observed_at=observed_at,
        result=collector_result if observation_status == "OBSERVED" else None,
    )

    try:
        _write_json_exclusive(result_path, terminal_doc)
    except Exception:
        raise TikTokPdpLivePilotError("TERMINAL_ARTIFACT_WRITE_FAILED") from None

    if operation_status == "FAIL_CLOSED":
        assert failure_reason is not None
        raise TikTokPdpLivePilotError(failure_reason)

    return TikTokPdpLivePilotOutcome(artifact_path=result_path, document=terminal_doc)


__all__ = [
    "ARTIFACT_FILENAME",
    "ATTEMPT_MARKER_FILENAME",
    "AUTHORIZED_PDP_URL",
    "AUTHORIZED_SOURCE_ID",
    "COLLECTOR_BASELINE_SOURCE_SHA",
    "COLLECTOR_BASELINE_TASK_ID",
    "CONTRACT_IDENTIFIER",
    "LEGACY_ARTIFACT_FILENAME",
    "PILOT_CONTEXT_ID",
    "RESULT_FILENAME",
    "TikTokPdpLivePilotArtifactExistsError",
    "TikTokPdpLivePilotError",
    "TikTokPdpLivePilotJobRootError",
    "TikTokPdpLivePilotOutcome",
    "run_tiktok_pdp_live_pilot",
]
