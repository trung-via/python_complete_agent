"""Human-operated one-shot carrier for the authorized TikTok PDP pilot.

This module owns only operation-specific orchestration.  Browser/session lifecycle,
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
    TikTokPdpCollectionResult,
    TikTokPdpCollector,
)


PILOT_CONTEXT_ID = "p8-pilot-001-led-motion-tiktok-vn"
AUTHORIZED_SOURCE_ID = "1731381331718341815"
AUTHORIZED_PDP_URL = (
    "https://shop.tiktok.com/vn/pdp/"
    "den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815"
)
ARTIFACT_FILENAME = "tiktok-pdp-live-pilot-result-v1.json"
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


def _snapshot_v1_document(result: TikTokPdpCollectionResult) -> dict[str, object]:
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


def _success_document(
    result: TikTokPdpCollectionResult, *, observed_at: datetime
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "operation": {
            "status": "SUCCESS",
            "classification": (
                "ONE_SHOT_LIVE_PUBLIC_PDP_PILOT_ENABLEMENT_AND_AUTHORIZATION"
            ),
            "context_id": PILOT_CONTEXT_ID,
            "source_product_id": AUTHORIZED_SOURCE_ID,
            "requested_url": AUTHORIZED_PDP_URL,
            "observed_at": observed_at.isoformat(),
            "authorized_capture_attempts": 1,
            "capture_execution_owner": "HUMAN_OPERATOR",
            "review_status": "HUMAN_REVIEW_REQUIRED",
        },
        "binding": {
            "requested_url": result.binding.requested_url,
            "observed_url": result.binding.observed_url,
            "identity_bases": [
                {
                    "basis": basis.basis,
                    "source_product_id": basis.source_product_id,
                }
                for basis in result.binding.identity_bases
            ],
        },
        "snapshot": _snapshot_v1_document(result),
    }


async def run_tiktok_pdp_live_pilot(
    *,
    job_root: str | Path,
    cdp_endpoint: str,
    clock: Callable[[], datetime] = _utc_now,
    manager_factory: Callable[..., _SessionManager] = PlaywrightBrowserManager,
    collector_factory: Callable[..., _Collector] = TikTokPdpCollector,
) -> TikTokPdpLivePilotOutcome:
    """Attempt the authorized exact listing once and never own browser shutdown."""

    root = _resolve_external_job_root(job_root)
    artifact_path = root / ARTIFACT_FILENAME
    if artifact_path.exists():
        raise TikTokPdpLivePilotArtifactExistsError(
            "the one-shot live-pilot artifact already exists"
        )
    if not isinstance(cdp_endpoint, str) or not cdp_endpoint.strip():
        raise TikTokPdpLivePilotError("an explicit operator-owned CDP endpoint is required")

    observed_at = clock()
    if (
        not isinstance(observed_at, datetime)
        or observed_at.tzinfo is None
        or observed_at.utcoffset() is None
    ):
        raise TikTokPdpLivePilotError("the operation timestamp must be timezone-aware")

    try:
        manager = manager_factory(cdp_endpoint=cdp_endpoint)
        session = await manager.get_or_create_session(_SESSION_RUN_ID)
    except Exception as exc:
        raise TikTokPdpLivePilotError(
            "the operator-owned browser session could not be borrowed"
        ) from exc

    collector = collector_factory(session)
    result = await collector.collect(AUTHORIZED_PDP_URL, observed_at=observed_at)
    if (
        result.snapshot.platform != "tiktok"
        or result.snapshot.source_product_id != AUTHORIZED_SOURCE_ID
        or result.snapshot.observed_at != observed_at
        or result.binding.requested_url != AUTHORIZED_PDP_URL
        or result.binding.observed_url != result.snapshot.url
        or not result.binding.identity_bases
        or any(
            basis.source_product_id != AUTHORIZED_SOURCE_ID
            for basis in result.binding.identity_bases
        )
    ):
        raise TikTokPdpLivePilotError(
            "collector result did not preserve the authorized exact-listing binding"
        )

    document = _success_document(result, observed_at=observed_at)
    try:
        root.mkdir(parents=True, exist_ok=True)
        with artifact_path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(document, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    except FileExistsError as exc:
        raise TikTokPdpLivePilotArtifactExistsError(
            "the one-shot live-pilot artifact already exists"
        ) from exc
    except OSError as exc:
        raise TikTokPdpLivePilotJobRootError(
            "the live-pilot artifact could not be created"
        ) from exc

    return TikTokPdpLivePilotOutcome(artifact_path=artifact_path, document=document)


__all__ = [
    "ARTIFACT_FILENAME",
    "AUTHORIZED_PDP_URL",
    "AUTHORIZED_SOURCE_ID",
    "PILOT_CONTEXT_ID",
    "TikTokPdpLivePilotArtifactExistsError",
    "TikTokPdpLivePilotError",
    "TikTokPdpLivePilotJobRootError",
    "TikTokPdpLivePilotOutcome",
    "run_tiktok_pdp_live_pilot",
]
