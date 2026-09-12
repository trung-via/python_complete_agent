"""Bounded, resumable Shopee live-capture composition.

This module owns only capture sequencing and checkpoint state. Browser lifecycle,
discovery/ranking, extraction, and source-pack serialization remain delegated to
their existing authorities.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable, Optional, Sequence

from src.browser.errors import (
    BrowserContextError,
    BrowserNotStartedError,
    BrowserSessionUnavailableError,
    PageClosedError,
)
from src.browser.models import BrowserState
from src.core.types import ToolCall, ToolResult, ToolStatus
from src.integrations.playwright.manager import PlaywrightBrowserManager
from src.product_intelligence.adapters.shopee import ShopeeDiscoveryAdapter
from src.product_intelligence.discovery import (
    DiscoveryBatch,
    DiscoveryBlockedError,
    DiscoveryRequest,
)
from src.product_intelligence.models import ProductCandidateSnapshot
from src.product_intelligence.orchestration import (
    PlatformDiscoveryPlan,
    orchestrate_discovery,
)
from src.tools.shopee_scrape_tool import ShopeeScrapeTool


PROFILE_P7_1_DISCOVERY_COHORT = "p7-1-discovery-cohort"
DISCOVERY_COHORT_QUERIES = (
    "bình giữ nhiệt inox",
    "bàn phím cơ",
    "chuột không dây",
)

_CHECKPOINT_NAME = "capture_checkpoint.json"
_BUNDLE_NAME = "capture_bundle.json"
_DISCOVERY_BUNDLE_NAME = "discovery_capture_bundle.json"
_CHECKPOINT_SCHEMA = "product_intelligence_live_capture_checkpoint"
_BUNDLE_SCHEMA = "product_intelligence_live_capture_bundle"
_DISCOVERY_BUNDLE_SCHEMA = "product_intelligence_discovery_capture_bundle"
_CHECKPOINT_VERSION = 2
_BUNDLE_VERSION = 1
_DISCOVERY_BUNDLE_VERSION = 1
_MAX_QUERIES = 100
_BINDING_RUN_ID = "live-capture-session-binding"
_LIVENESS_SCRIPT = "() => true"


class LiveCaptureError(Exception):
    """A terminal, non-resumable live-capture failure."""


class LiveCaptureStatus(str, Enum):
    NEW = "NEW"
    SESSION_READY = "SESSION_READY"
    RUNNING = "RUNNING"
    HUMAN_ACTION_REQUIRED = "HUMAN_ACTION_REQUIRED"
    VERIFY_SESSION = "VERIFY_SESSION"
    SESSION_LOST = "SESSION_LOST"
    READY = "READY"
    FAILED = "FAILED"


class LiveCapturePhase(str, Enum):
    DISCOVERY = "DISCOVERY"
    ACQUIRE_1 = "ACQUIRE_1"
    ACQUIRE_2 = "ACQUIRE_2"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True)
class LiveCaptureOutcome:
    status: LiveCaptureStatus
    phase: LiveCapturePhase
    query_position: int
    query_count: int
    checkpoint_filename: str = _CHECKPOINT_NAME
    bundle_filename: Optional[str] = None
    profile: Optional[str] = None

    def to_document(self) -> dict[str, object]:
        document: dict[str, object] = {
            "status": self.status.value,
            "phase": self.phase.value,
            "query_position": self.query_position,
            "query_count": self.query_count,
            "checkpoint": self.checkpoint_filename,
        }
        if self.profile is not None:
            document["profile"] = self.profile
        if self.bundle_filename is not None:
            document["bundle"] = self.bundle_filename
        return document


class _LocalDriveSink:
    """Synchronous zero-network publication sink required by ShopeeScrapeTool."""

    def get_or_create_folder(self, name, parent_id=None):
        del name, parent_id
        return "live-capture-local-folder"

    def upload_file(self, file_path, folder_id=None):
        del file_path, folder_id
        return "live-capture-local-upload"


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _validate_scalar(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\n" in value or "\r" in value:
        raise LiveCaptureError(f"{label} must be an exact nonblank single-line string")
    return value


def _prepare_job_root(job_root: object) -> Path:
    if not isinstance(job_root, (str, os.PathLike)):
        raise LiveCaptureError("Job root must be an explicit filesystem path")
    lexical = Path(job_root).absolute()
    repository = _repository_root()
    if _is_relative_to(lexical, repository):
        raise LiveCaptureError("Job root must be outside the Git repository")
    try:
        lexical.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise LiveCaptureError("Job root could not be created") from exc
    try:
        resolved = lexical.resolve(strict=True)
    except OSError as exc:
        raise LiveCaptureError("Job root could not be resolved") from exc
    if _is_relative_to(resolved, repository):
        raise LiveCaptureError("Job root must be outside the Git repository")
    if not resolved.is_dir():
        raise LiveCaptureError("Job root must be a directory")
    return resolved


def _safe_path(root: Path, relative: str, *, must_exist: bool = False) -> Path:
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise LiveCaptureError("Capture artifact path escapes the job root")
    candidate = root.joinpath(relative_path)
    try:
        resolved = candidate.resolve(strict=must_exist)
    except OSError as exc:
        raise LiveCaptureError("Capture artifact path is invalid") from exc
    if not _is_relative_to(resolved, root):
        raise LiveCaptureError("Capture artifact path escapes the job root")
    return candidate


def _json_bytes(document: dict[str, object]) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _atomic_checkpoint(root: Path, state: dict[str, object]) -> None:
    destination = _safe_path(root, _CHECKPOINT_NAME)
    temporary = _safe_path(root, ".capture_checkpoint.json.tmp")
    if temporary.exists() or temporary.is_symlink():
        raise LiveCaptureError("Checkpoint atomic-write staging path already exists")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor: Optional[int] = None
    staging_created = False
    try:
        descriptor = os.open(temporary, flags, 0o600)
        staging_created = True
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = None
            stream.write(_json_bytes(state))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except OSError as exc:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if staging_created:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
        raise LiveCaptureError("Capture checkpoint could not be updated") from exc
    except BaseException:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if staging_created:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
        raise


def _exclusive_bundle(
    root: Path, document: dict[str, object], bundle_name: str = _BUNDLE_NAME
) -> None:
    destination = _safe_path(root, bundle_name)
    if destination.exists() or destination.is_symlink():
        raise LiveCaptureError("Capture bundle already exists")
    temporary = _safe_path(root, f".{bundle_name}.tmp")
    if temporary.exists() or temporary.is_symlink():
        raise LiveCaptureError("Bundle atomic-write staging path already exists")
    descriptor: Optional[int] = None
    staging_created = False
    try:
        descriptor = os.open(
            temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
        )
        staging_created = True
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = None
            stream.write(_json_bytes(document))
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, destination)
    except FileExistsError as exc:
        raise LiveCaptureError("Capture bundle already exists") from exc
    except OSError as exc:
        raise LiveCaptureError("Capture bundle could not be created") from exc
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if staging_created:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def _initial_state(
    endpoint: str,
    queries: Sequence[str],
    profile: Optional[str] = None,
) -> dict[str, object]:
    state: dict[str, object] = {
        "schema": _CHECKPOINT_SCHEMA,
        "version": _CHECKPOINT_VERSION,
        "status": LiveCaptureStatus.NEW.value,
        "endpoint_digest": _digest_endpoint(endpoint),
        "browser_binding_digest": None,
        "queries": list(queries),
        "query_position": 0,
        "phase": LiveCapturePhase.DISCOVERY.value,
        "category": None,
    }
    if profile == PROFILE_P7_1_DISCOVERY_COHORT:
        state["profile"] = PROFILE_P7_1_DISCOVERY_COHORT
        state["completed_batches"] = []
    else:
        state["completed_cohorts"] = []
        state["selected_candidate"] = None
        state["completed_observations"] = []
    return state


_DISCOVERY_BATCH_KEYS = frozenset({
    "candidate_count",
    "candidates",
    "diagnostic_codes",
    "observed_at",
    "pages_examined",
    "platform",
    "query",
    "raw_items_seen",
})

_CANDIDATE_KEYS = frozenset({
    "candidate_id",
    "platform",
    "source_product_id",
    "url",
    "observed_at",
    "collector",
    "title",
    "shop_id",
    "shop_name",
    "category",
    "brand",
    "model",
    "price",
    "original_price",
    "discount_percent",
    "sold_count",
    "rating",
    "review_count",
    "affiliate_commission_rate",
    "estimated_commission_value",
    "creator_count",
    "video_count",
    "similar_listing_count",
    "sales_velocity",
    "review_velocity",
    "creator_velocity",
    "video_velocity",
})


def _validate_persisted_candidate(
    candidate: object,
    *,
    batch_platform: str,
) -> tuple[str, str, ProductCandidateSnapshot]:
    if not isinstance(candidate, dict):
        raise LiveCaptureError("Capture checkpoint candidate snapshot is invalid")
    if set(candidate) != _CANDIDATE_KEYS:
        raise LiveCaptureError("Capture checkpoint candidate snapshot is invalid")

    cid = candidate["candidate_id"]
    if not isinstance(cid, str) or not cid:
        raise LiveCaptureError("Capture checkpoint candidate_id is invalid")

    platform = candidate["platform"]
    if platform != "shopee" or platform != batch_platform:
        raise LiveCaptureError("Capture checkpoint candidate platform is invalid")

    url = candidate["url"]
    if not isinstance(url, str) or not url:
        raise LiveCaptureError("Capture checkpoint candidate url is invalid")

    title = candidate["title"]
    if not isinstance(title, str) or not title:
        raise LiveCaptureError("Capture checkpoint candidate title is invalid")

    collector = candidate["collector"]
    if not isinstance(collector, str) or not collector:
        raise LiveCaptureError("Capture checkpoint candidate collector is invalid")

    observed_at_raw = candidate["observed_at"]
    if not isinstance(observed_at_raw, str):
        raise LiveCaptureError("Capture checkpoint candidate observed_at is invalid")
    try:
        cand_observed_at = datetime.fromisoformat(observed_at_raw)
    except (ValueError, TypeError) as exc:
        raise LiveCaptureError("Capture checkpoint candidate observed_at is invalid") from exc

    if cand_observed_at.tzinfo is None or cand_observed_at.utcoffset() is None:
        raise LiveCaptureError("Capture checkpoint candidate observed_at is invalid")
    if cand_observed_at.isoformat() != observed_at_raw:
        raise LiveCaptureError("Capture checkpoint candidate observed_at is invalid")

    for str_key in ("source_product_id", "shop_id", "shop_name", "category", "brand", "model"):
        val = candidate[str_key]
        if val is not None and not isinstance(val, str):
            raise LiveCaptureError(f"Capture checkpoint candidate {str_key} is invalid")

    for num_key in (
        "price",
        "original_price",
        "estimated_commission_value",
        "sales_velocity",
        "review_velocity",
        "creator_velocity",
        "video_velocity",
    ):
        val = candidate[num_key]
        if val is not None and (
            isinstance(val, bool)
            or not isinstance(val, (int, float))
            or val < 0
        ):
            raise LiveCaptureError(f"Capture checkpoint candidate {num_key} is invalid")

    for int_key in (
        "sold_count",
        "review_count",
        "creator_count",
        "video_count",
        "similar_listing_count",
    ):
        val = candidate[int_key]
        if val is not None and (
            isinstance(val, bool)
            or not isinstance(val, int)
            or val < 0
        ):
            raise LiveCaptureError(f"Capture checkpoint candidate {int_key} is invalid")

    for pct_key in ("discount_percent", "affiliate_commission_rate"):
        val = candidate[pct_key]
        if val is not None and (
            isinstance(val, bool)
            or not isinstance(val, (int, float))
            or not (0.0 <= val <= 100.0)
        ):
            raise LiveCaptureError(f"Capture checkpoint candidate {pct_key} is invalid")

    rating = candidate["rating"]
    if rating is not None and (
        isinstance(rating, bool)
        or not isinstance(rating, (int, float))
        or not (0.0 <= rating <= 5.0)
    ):
        raise LiveCaptureError("Capture checkpoint candidate rating is invalid")

    try:
        snapshot = ProductCandidateSnapshot(
            candidate_id=cid,
            platform=platform,
            url=url,
            observed_at=cand_observed_at,
            title=title,
            source_product_id=candidate["source_product_id"],
            collector=collector,
            shop_id=candidate["shop_id"],
            shop_name=candidate["shop_name"],
            category=candidate["category"],
            brand=candidate["brand"],
            model=candidate["model"],
            price=candidate["price"],
            original_price=candidate["original_price"],
            discount_percent=candidate["discount_percent"],
            sold_count=candidate["sold_count"],
            rating=candidate["rating"],
            review_count=candidate["review_count"],
            affiliate_commission_rate=candidate["affiliate_commission_rate"],
            estimated_commission_value=candidate["estimated_commission_value"],
            creator_count=candidate["creator_count"],
            video_count=candidate["video_count"],
            similar_listing_count=candidate["similar_listing_count"],
            sales_velocity=candidate["sales_velocity"],
            review_velocity=candidate["review_velocity"],
            creator_velocity=candidate["creator_velocity"],
            video_velocity=candidate["video_velocity"],
        )
    except (ValueError, TypeError) as exc:
        raise LiveCaptureError(f"Capture checkpoint candidate snapshot is invalid: {exc}") from exc

    if snapshot.to_dict() != candidate:
        raise LiveCaptureError("Capture checkpoint candidate snapshot is invalid")

    return cid, url, snapshot


def _validate_persisted_discovery_batch(
    batch: object,
    *,
    expected_query: str,
    seen_ids: set[str],
    seen_urls: set[str],
) -> None:
    if not isinstance(batch, dict):
        raise LiveCaptureError("Capture checkpoint discovery batch is invalid")
    if set(batch) != _DISCOVERY_BATCH_KEYS:
        raise LiveCaptureError("Capture checkpoint discovery batch is invalid")
    if batch["platform"] != "shopee":
        raise LiveCaptureError("Capture checkpoint discovery batch platform is invalid")
    if batch["query"] != expected_query:
        raise LiveCaptureError("Capture checkpoint discovery batch query mismatch")

    observed_at_raw = batch["observed_at"]
    if not isinstance(observed_at_raw, str):
        raise LiveCaptureError("Capture checkpoint discovery batch observed_at is invalid")
    try:
        batch_observed_at = datetime.fromisoformat(observed_at_raw)
    except (ValueError, TypeError) as exc:
        raise LiveCaptureError("Capture checkpoint discovery batch observed_at is invalid") from exc

    if batch_observed_at.tzinfo is None or batch_observed_at.utcoffset() is None:
        raise LiveCaptureError("Capture checkpoint discovery batch observed_at is invalid")
    if batch_observed_at.isoformat() != observed_at_raw:
        raise LiveCaptureError("Capture checkpoint discovery batch observed_at is invalid")

    pages_examined = batch["pages_examined"]
    if isinstance(pages_examined, bool) or not isinstance(pages_examined, int) or pages_examined != 1:
        raise LiveCaptureError("Capture checkpoint discovery batch pages_examined is invalid")

    raw_items_seen = batch["raw_items_seen"]
    if isinstance(raw_items_seen, bool) or not isinstance(raw_items_seen, int) or raw_items_seen < 0:
        raise LiveCaptureError("Capture checkpoint discovery batch raw_items_seen is invalid")

    candidate_count = batch["candidate_count"]
    if isinstance(candidate_count, bool) or not isinstance(candidate_count, int) or candidate_count != 5:
        raise LiveCaptureError("Capture checkpoint discovery batch candidate_count is invalid")

    diagnostic_codes = batch["diagnostic_codes"]
    if not isinstance(diagnostic_codes, list) or any(not isinstance(c, str) for c in diagnostic_codes):
        raise LiveCaptureError("Capture checkpoint discovery batch diagnostic_codes is invalid")

    candidates = batch["candidates"]
    if not isinstance(candidates, list) or len(candidates) != 5:
        raise LiveCaptureError("Capture checkpoint discovery batch candidates are invalid")

    batch_candidates: list[ProductCandidateSnapshot] = []
    batch_ids: set[str] = set()
    batch_urls: set[str] = set()
    for candidate in candidates:
        cid, url, snapshot = _validate_persisted_candidate(candidate, batch_platform=batch["platform"])
        if cid in batch_ids:
            raise LiveCaptureError("Capture checkpoint discovery batch has duplicate candidate ID")
        if url in batch_urls:
            raise LiveCaptureError("Capture checkpoint discovery batch has duplicate candidate URL")
        if cid in seen_ids:
            raise LiveCaptureError(
                "Capture checkpoint discovery batches have duplicate candidate ID across queries"
            )
        if url in seen_urls:
            raise LiveCaptureError(
                "Capture checkpoint discovery batches have duplicate candidate URL across queries"
            )
        batch_ids.add(cid)
        batch_urls.add(url)
        batch_candidates.append(snapshot)
    seen_ids.update(batch_ids)
    seen_urls.update(batch_urls)

    try:
        reconstructed_batch = DiscoveryBatch(
            platform=batch["platform"],
            query=batch["query"],
            observed_at=batch_observed_at,
            candidates=tuple(batch_candidates),
            pages_examined=pages_examined,
            raw_items_seen=raw_items_seen,
            diagnostic_codes=tuple(diagnostic_codes),
        )
    except (ValueError, TypeError) as exc:
        raise LiveCaptureError(f"Capture checkpoint discovery batch is invalid: {exc}") from exc

    if reconstructed_batch.to_dict() != batch:
        raise LiveCaptureError("Capture checkpoint discovery batch is invalid")


def _validate_live_discovery_batch(
    batch: object,
    *,
    expected_query: str,
    completed_batches: list[dict[str, object]],
) -> dict[str, object]:
    if not isinstance(batch, DiscoveryBatch):
        raise LiveCaptureError("Discovery returned an invalid batch")
    if batch.platform != "shopee":
        raise LiveCaptureError(f"Discovery returned unexpected platform: {batch.platform!r}")
    if batch.query != expected_query:
        raise LiveCaptureError(
            f"Discovery query mismatch: expected {expected_query!r}, got {batch.query!r}"
        )
    if not isinstance(batch.observed_at, datetime) or batch.observed_at.tzinfo is None or batch.observed_at.utcoffset() is None:
        raise LiveCaptureError("Discovery batch observed_at is invalid or naive")
    if batch.pages_examined != 1:
        raise LiveCaptureError(
            f"Discovery pages_examined mismatch: expected 1, got {batch.pages_examined}"
        )
    if len(batch.candidates) != 5:
        raise LiveCaptureError(
            f"Discovery candidate count mismatch: expected 5, got {len(batch.candidates)}"
        )

    candidate_ids: list[str] = []
    candidate_urls: list[str] = []
    for candidate in batch.candidates:
        if not isinstance(candidate, ProductCandidateSnapshot):
            raise LiveCaptureError("Discovery candidate is invalid")
        if candidate.platform != "shopee":
            raise LiveCaptureError(f"Discovery candidate platform is invalid: {candidate.platform!r}")
        if not isinstance(candidate.observed_at, datetime) or candidate.observed_at.tzinfo is None or candidate.observed_at.utcoffset() is None:
            raise LiveCaptureError("Discovery candidate observed_at is invalid or naive")
        cid = candidate.candidate_id
        url = candidate.url
        if not isinstance(cid, str) or not cid:
            raise LiveCaptureError("Discovery candidate_id is invalid")
        if not isinstance(url, str) or not url:
            raise LiveCaptureError("Discovery candidate url is invalid")
        candidate_ids.append(cid)
        candidate_urls.append(url)

    if len(set(candidate_ids)) != 5:
        raise LiveCaptureError("Discovery batch contains duplicate candidate IDs within batch")
    if len(set(candidate_urls)) != 5:
        raise LiveCaptureError("Discovery batch contains duplicate candidate URLs within batch")

    prior_ids = {
        cand["candidate_id"]
        for b in completed_batches
        for cand in b["candidates"]
    }
    prior_urls = {
        cand["url"]
        for b in completed_batches
        for cand in b["candidates"]
    }
    if any(cid in prior_ids for cid in candidate_ids):
        raise LiveCaptureError("Discovery batch contains duplicate candidate ID across queries")
    if any(curl in prior_urls for curl in candidate_urls):
        raise LiveCaptureError("Discovery batch contains duplicate candidate URL across queries")

    return batch.to_dict()


def _digest_endpoint(endpoint: str) -> str:
    return hashlib.sha256(endpoint.encode("utf-8")).hexdigest()


def _validate_digest(value: object, label: str, *, allow_none: bool = False) -> Optional[str]:
    if value is None and allow_none:
        return None
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise LiveCaptureError(f"{label} is invalid")
    return value


def _validate_observation(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {"manifest_path", "sha256"}:
        raise LiveCaptureError("Checkpoint observation record is invalid")
    path = value.get("manifest_path")
    digest = value.get("sha256")
    if not isinstance(path, str) or not path or Path(path).is_absolute() or ".." in Path(path).parts:
        raise LiveCaptureError("Checkpoint observation path is invalid")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise LiveCaptureError("Checkpoint observation digest is invalid")
    return {"manifest_path": path, "sha256": digest}


def _validate_candidate(value: object, *, allow_none: bool) -> Optional[dict[str, str]]:
    if value is None and allow_none:
        return None
    if not isinstance(value, dict) or set(value) != {"candidate_id", "product_url", "title"}:
        raise LiveCaptureError("Checkpoint selected candidate is invalid")
    result = {}
    for key in ("candidate_id", "product_url", "title"):
        item = value.get(key)
        if not isinstance(item, str) or not item:
            raise LiveCaptureError("Checkpoint selected candidate is invalid")
        result[key] = item
    return result


def _validate_checkpoint(root: Path, document: object) -> dict[str, object]:
    if not isinstance(document, dict):
        raise LiveCaptureError("Capture checkpoint is corrupt")
    version = document.get("version")
    profile = document.get("profile")

    if profile is not None and profile != PROFILE_P7_1_DISCOVERY_COHORT:
        raise LiveCaptureError("Capture checkpoint profile is unsupported")

    if profile == PROFILE_P7_1_DISCOVERY_COHORT:
        if version != _CHECKPOINT_VERSION:
            raise LiveCaptureError("Capture checkpoint schema is unsupported")
        discovery_required = {
            "schema",
            "version",
            "status",
            "queries",
            "query_position",
            "phase",
            "category",
            "endpoint_digest",
            "browser_binding_digest",
            "profile",
            "completed_batches",
        }
        if set(document) != discovery_required:
            raise LiveCaptureError("Capture checkpoint is corrupt")
    else:
        common = {
            "schema",
            "version",
            "status",
            "queries",
            "query_position",
            "phase",
            "completed_cohorts",
            "selected_candidate",
            "completed_observations",
            "category",
        }
        v1_required = common | {"cdp_endpoint"}
        v2_required = common | {"endpoint_digest", "browser_binding_digest"}
        if version == 1:
            required = v1_required
        elif version == _CHECKPOINT_VERSION:
            required = v2_required
        else:
            raise LiveCaptureError("Capture checkpoint schema is unsupported")
        if set(document) != required:
            raise LiveCaptureError("Capture checkpoint is corrupt")

    if document["schema"] != _CHECKPOINT_SCHEMA:
        raise LiveCaptureError("Capture checkpoint schema is unsupported")
    try:
        phase = LiveCapturePhase(document["phase"])
    except (ValueError, TypeError) as exc:
        raise LiveCaptureError("Capture checkpoint state is invalid") from exc

    if profile == PROFILE_P7_1_DISCOVERY_COHORT and phase not in (
        LiveCapturePhase.DISCOVERY,
        LiveCapturePhase.COMPLETE,
    ):
        raise LiveCaptureError(
            "Capture checkpoint phase is invalid for discovery profile"
        )

    if version == 1:
        status_value = document["status"]
        if status_value not in {"RUNNING", "CHALLENGE_REQUIRED", "READY", "FAILED"}:
            raise LiveCaptureError("Capture checkpoint state is invalid")
        endpoint = _validate_scalar(document["cdp_endpoint"], "Checkpoint CDP endpoint")
        endpoint_digest = _digest_endpoint(endpoint)
        browser_binding_digest = None
    else:
        try:
            status_value = LiveCaptureStatus(document["status"]).value
        except (ValueError, TypeError) as exc:
            raise LiveCaptureError("Capture checkpoint state is invalid") from exc
        endpoint = None
        endpoint_digest = _validate_digest(document["endpoint_digest"], "Checkpoint endpoint digest")
        browser_binding_digest = _validate_digest(
            document["browser_binding_digest"],
            "Checkpoint browser binding digest",
            allow_none=status_value in {
                LiveCaptureStatus.NEW.value,
                LiveCaptureStatus.SESSION_LOST.value,
                LiveCaptureStatus.FAILED.value,
            },
        )

    queries = document["queries"]
    if profile == PROFILE_P7_1_DISCOVERY_COHORT:
        if queries != list(DISCOVERY_COHORT_QUERIES):
            raise LiveCaptureError("Capture checkpoint query sequence is invalid")
    else:
        if not isinstance(queries, list) or not (1 <= len(queries) <= _MAX_QUERIES):
            raise LiveCaptureError("Capture checkpoint query sequence is invalid")
        for query in queries:
            _validate_scalar(query, "Checkpoint query")

    position = document["query_position"]
    if isinstance(position, bool) or not isinstance(position, int) or not (0 <= position <= len(queries)):
        raise LiveCaptureError("Capture checkpoint query position is invalid")

    if phase is LiveCapturePhase.COMPLETE and position != len(queries):
        raise LiveCaptureError("Capture checkpoint completion position is inconsistent")
    if position == len(queries) and phase is not LiveCapturePhase.COMPLETE:
        raise LiveCaptureError("Capture checkpoint terminal position is inconsistent")

    human_required = status_value in {"CHALLENGE_REQUIRED", LiveCaptureStatus.HUMAN_ACTION_REQUIRED.value}
    if profile == PROFILE_P7_1_DISCOVERY_COHORT:
        if human_required and document["category"] != "DISCOVERY_BLOCKED":
            raise LiveCaptureError("Capture checkpoint access-gate category is invalid")
    else:
        if human_required and document["category"] not in ("DISCOVERY_BLOCKED", "EXTRACTION_BLOCKED"):
            raise LiveCaptureError("Capture checkpoint access-gate category is invalid")
    if human_required and phase is LiveCapturePhase.COMPLETE:
        raise LiveCaptureError("Capture checkpoint access-gate phase is invalid")
    if status_value in {
        "RUNNING", LiveCaptureStatus.NEW.value, LiveCaptureStatus.SESSION_READY.value,
        LiveCaptureStatus.VERIFY_SESSION.value,
    } and document["category"] is not None:
        raise LiveCaptureError("Capture checkpoint operational category is invalid")
    if status_value == LiveCaptureStatus.SESSION_LOST.value and document["category"] not in {
        "ENDPOINT_MISMATCH", "BINDING_MISMATCH", "RESOURCE_LOST",
    }:
        raise LiveCaptureError("Capture checkpoint session-loss category is invalid")
    if (
        status_value == LiveCaptureStatus.SESSION_LOST.value
        and phase is LiveCapturePhase.COMPLETE
    ):
        raise LiveCaptureError("Capture checkpoint session-loss phase is invalid")
    if status_value == "FAILED" and document["category"] != "TERMINAL_FAILURE":
        raise LiveCaptureError("Capture checkpoint failure category is invalid")
    if status_value == "READY" and (phase is not LiveCapturePhase.COMPLETE or document["category"] is not None):
        raise LiveCaptureError("Capture checkpoint ready state is invalid")

    if status_value == "READY":
        bundle_file = _DISCOVERY_BUNDLE_NAME if profile == PROFILE_P7_1_DISCOVERY_COHORT else _BUNDLE_NAME
        bundle = _safe_path(root, bundle_file, must_exist=True)
        if bundle.is_symlink() or not bundle.is_file():
            raise LiveCaptureError("Ready capture bundle is invalid")

    if profile == PROFILE_P7_1_DISCOVERY_COHORT:
        batches_value = document["completed_batches"]
        if not isinstance(batches_value, list) or len(batches_value) != position:
            raise LiveCaptureError("Capture checkpoint discovery batches are inconsistent")
        all_candidate_ids: set[str] = set()
        all_urls: set[str] = set()
        for index, batch in enumerate(batches_value):
            _validate_persisted_discovery_batch(
                batch,
                expected_query=queries[index],
                seen_ids=all_candidate_ids,
                seen_urls=all_urls,
            )
        document["status"] = status_value
        document["endpoint_digest"] = endpoint_digest
        document["browser_binding_digest"] = browser_binding_digest
        document["profile"] = profile
        document["completed_batches"] = batches_value
        return document

    candidate = _validate_candidate(document["selected_candidate"], allow_none=True)
    observations_value = document["completed_observations"]
    if not isinstance(observations_value, list) or len(observations_value) > 2:
        raise LiveCaptureError("Capture checkpoint observations are invalid")
    observations = [_validate_observation(value) for value in observations_value]
    cohorts_value = document["completed_cohorts"]
    if not isinstance(cohorts_value, list) or len(cohorts_value) != position:
        raise LiveCaptureError("Capture checkpoint cohorts are inconsistent")
    cohorts = []
    for index, value in enumerate(cohorts_value):
        if not isinstance(value, dict) or set(value) != {"query", "candidate_id", "product_url", "title", "observations"}:
            raise LiveCaptureError("Capture checkpoint cohort is invalid")
        if value["query"] != queries[index]:
            raise LiveCaptureError("Capture checkpoint cohort order is invalid")
        cohort_candidate = _validate_candidate(
            {key: value[key] for key in ("candidate_id", "product_url", "title")},
            allow_none=False,
        )
        cohort_observations = value["observations"]
        if not isinstance(cohort_observations, list) or len(cohort_observations) != 2:
            raise LiveCaptureError("Capture checkpoint cohort observations are invalid")
        cohorts.append({
            "query": value["query"],
            **cohort_candidate,
            "observations": [_validate_observation(item) for item in cohort_observations],
        })
    expected_observations = {
        LiveCapturePhase.DISCOVERY: 0,
        LiveCapturePhase.ACQUIRE_1: 0,
        LiveCapturePhase.ACQUIRE_2: 1,
        LiveCapturePhase.COMPLETE: 0,
    }[phase]
    if phase is LiveCapturePhase.DISCOVERY and candidate is not None:
        raise LiveCaptureError("Capture checkpoint phase and candidate are inconsistent")
    if phase in (LiveCapturePhase.ACQUIRE_1, LiveCapturePhase.ACQUIRE_2) and candidate is None:
        raise LiveCaptureError("Capture checkpoint phase is missing its selected candidate")
    if len(observations) != expected_observations:
        raise LiveCaptureError("Capture checkpoint phase and observations are inconsistent")

    for record in [*observations, *(item for cohort in cohorts for item in cohort["observations"])]:
        manifest = _safe_path(root, record["manifest_path"], must_exist=True)
        if manifest.is_symlink() or not manifest.is_file():
            raise LiveCaptureError("Checkpoint manifest reference is invalid")
        try:
            manifest_bytes = manifest.read_bytes()
        except OSError as exc:
            raise LiveCaptureError("Checkpoint manifest could not be read") from exc
        if hashlib.sha256(manifest_bytes).hexdigest() != record["sha256"]:
            raise LiveCaptureError("Checkpoint manifest digest mismatch")
    document["status"] = status_value
    if version == 1:
        document["_legacy_endpoint"] = endpoint
    else:
        document["endpoint_digest"] = endpoint_digest
        document["browser_binding_digest"] = browser_binding_digest
    document["selected_candidate"] = candidate
    document["completed_observations"] = observations
    document["completed_cohorts"] = cohorts
    return document


def _load_resume_state(root: Path) -> dict[str, object]:
    checkpoint = _safe_path(root, _CHECKPOINT_NAME, must_exist=True)
    if checkpoint.is_symlink() or not checkpoint.is_file():
        raise LiveCaptureError("Capture checkpoint is missing")
    try:
        raw = checkpoint.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            raise ValueError("BOM")
        document = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise LiveCaptureError("Capture checkpoint is corrupt") from exc
    return _validate_checkpoint(root, document)


def _mark(state: dict[str, object], root: Path, status: LiveCaptureStatus, category: Optional[str]) -> None:
    state["status"] = status.value
    state["category"] = category
    _atomic_checkpoint(root, state)


def _outcome(state: dict[str, object], *, bundle: bool = False) -> LiveCaptureOutcome:
    profile = state.get("profile")
    bundle_filename = None
    if bundle:
        bundle_filename = (
            _DISCOVERY_BUNDLE_NAME
            if profile == PROFILE_P7_1_DISCOVERY_COHORT
            else _BUNDLE_NAME
        )
    return LiveCaptureOutcome(
        status=LiveCaptureStatus(state["status"]),
        phase=LiveCapturePhase(state["phase"]),
        query_position=state["query_position"],
        query_count=len(state["queries"]),
        checkpoint_filename=_CHECKPOINT_NAME,
        bundle_filename=bundle_filename,
        profile=profile,
    )


def _v2_from_legacy(
    state: dict[str, object], endpoint: str, binding_digest: Optional[str]
) -> dict[str, object]:
    return {
        "schema": _CHECKPOINT_SCHEMA,
        "version": _CHECKPOINT_VERSION,
        "status": LiveCaptureStatus.VERIFY_SESSION.value,
        "endpoint_digest": _digest_endpoint(endpoint),
        "browser_binding_digest": binding_digest,
        "queries": state["queries"],
        "query_position": state["query_position"],
        "phase": state["phase"],
        "completed_cohorts": state["completed_cohorts"],
        "selected_candidate": state["selected_candidate"],
        "completed_observations": state["completed_observations"],
        "category": None,
    }


def _session_resource_lost(error: BaseException, session: object = None) -> bool:
    if isinstance(
        error,
        (BrowserNotStartedError, BrowserSessionUnavailableError, PageClosedError),
    ):
        return True
    return (
        isinstance(error, BrowserContextError)
        and session is not None
        and getattr(session, "state", None) in {BrowserState.CLOSED, BrowserState.CRASHED}
    )


def _tool_resource_lost(result: object) -> bool:
    return (
        isinstance(result, ToolResult)
        and result.status is ToolStatus.FAILURE
        and result.error is not None
        and result.error.code in {
            "BROWSER_NOT_STARTED", "BROWSER_SESSION_UNAVAILABLE", "PAGE_CLOSED",
        }
    )


async def _binding_session(manager: object) -> tuple[object, str]:
    session = await manager.get_or_create_session(_BINDING_RUN_ID)
    digest = await session.browser_binding_digest()
    validated = _validate_digest(digest, "Browser binding digest")
    assert validated is not None
    return session, validated


async def _verify_session(session: object) -> None:
    await session.evaluate(_LIVENESS_SCRIPT)


async def run_live_capture(
    *,
    job_root: str | os.PathLike[str],
    cdp_endpoint: str,
    queries: Optional[Sequence[str]] = None,
    profile: Optional[str] = None,
    resume: bool = False,
    rebind_session: bool = False,
    manager_factory: Optional[Callable[..., object]] = None,
    tool_factory: Optional[Callable[[], object]] = None,
    orchestration: Optional[Callable[..., object]] = None,
    adapter_factory: Optional[Callable[..., object]] = None,
    now_factory: Optional[Callable[[], datetime]] = None,
) -> LiveCaptureOutcome:
    """Start or explicitly resume one external-root Shopee capture job."""

    endpoint = _validate_scalar(cdp_endpoint, "CDP endpoint")
    if profile is not None and profile != PROFILE_P7_1_DISCOVERY_COHORT:
        raise LiveCaptureError(f"Unsupported capture profile: {profile}")
    try:
        root = _prepare_job_root(job_root)
    except OSError as exc:
        raise LiveCaptureError("Job root could not be prepared") from exc
    manager_factory = manager_factory or PlaywrightBrowserManager
    tool_factory = tool_factory or ShopeeScrapeTool
    orchestration = orchestration or orchestrate_discovery
    now_factory = now_factory or (lambda: datetime.now(timezone.utc))
    initialized = False
    state: Optional[dict[str, object]] = None
    manager = None
    session = None
    operation_error: Optional[BaseException] = None
    outcome: Optional[LiveCaptureOutcome] = None
    try:
        if rebind_session and not resume:
            raise LiveCaptureError("Session rebind requires resume")
        if resume:
            if queries is not None:
                raise LiveCaptureError("Resume does not accept replacement queries")
            state = _load_resume_state(root)
            checkpoint_profile = state.get("profile")
            if profile is not None and profile != checkpoint_profile:
                raise LiveCaptureError("Resume cannot switch capture profiles")
            active_profile = checkpoint_profile
            if state["version"] == 1:
                if active_profile == PROFILE_P7_1_DISCOVERY_COHORT:
                    raise LiveCaptureError(
                        "Legacy capture does not support discovery profile"
                    )
                if state["status"] != "CHALLENGE_REQUIRED":
                    raise LiveCaptureError(
                        "Only a legacy CHALLENGE_REQUIRED capture may be upgraded"
                    )
                if rebind_session:
                    raise LiveCaptureError("Legacy capture does not permit session rebind")
                if endpoint != state["_legacy_endpoint"]:
                    raise LiveCaptureError(
                        "CDP endpoint does not match the legacy capture endpoint"
                    )
                initialized = True
                existing_bundle = _safe_path(root, _BUNDLE_NAME)
                if existing_bundle.exists() or existing_bundle.is_symlink():
                    state = _v2_from_legacy(state, endpoint, None)
                    raise LiveCaptureError("Capture bundle already exists")
                manager = manager_factory(cdp_endpoint=endpoint)
                try:
                    session, binding_digest = await _binding_session(manager)
                except (
                    BrowserContextError,
                    BrowserNotStartedError,
                    BrowserSessionUnavailableError,
                    PageClosedError,
                ):
                    state = _v2_from_legacy(state, endpoint, None)
                    _mark(state, root, LiveCaptureStatus.SESSION_LOST, "RESOURCE_LOST")
                    outcome = _outcome(state)
                except BaseException:
                    state = _v2_from_legacy(state, endpoint, None)
                    _mark(state, root, LiveCaptureStatus.FAILED, "TERMINAL_FAILURE")
                    raise
                else:
                    state = _v2_from_legacy(state, endpoint, binding_digest)
                    _atomic_checkpoint(root, state)
            else:
                resumable = state["status"] in {
                    LiveCaptureStatus.HUMAN_ACTION_REQUIRED.value,
                    LiveCaptureStatus.SESSION_LOST.value,
                }
                if not resumable:
                    raise LiveCaptureError(
                        "Only HUMAN_ACTION_REQUIRED or SESSION_LOST may be resumed"
                    )
                if state["status"] == LiveCaptureStatus.SESSION_LOST.value:
                    if not rebind_session:
                        raise LiveCaptureError(
                            "SESSION_LOST requires explicit session rebind"
                        )
                elif rebind_session:
                    raise LiveCaptureError(
                        "Session rebind is valid only for SESSION_LOST"
                    )
                initialized = True
                expected_bundle_name = (
                    _DISCOVERY_BUNDLE_NAME
                    if active_profile == PROFILE_P7_1_DISCOVERY_COHORT
                    else _BUNDLE_NAME
                )
                existing_bundle = _safe_path(root, expected_bundle_name)
                if existing_bundle.exists() or existing_bundle.is_symlink():
                    raise LiveCaptureError("Capture bundle already exists")
                supplied_endpoint_digest = _digest_endpoint(endpoint)
                if (
                    not rebind_session
                    and supplied_endpoint_digest != state["endpoint_digest"]
                ):
                    _mark(
                        state, root, LiveCaptureStatus.SESSION_LOST,
                        "ENDPOINT_MISMATCH",
                    )
                    outcome = _outcome(state)
                else:
                    manager = manager_factory(cdp_endpoint=endpoint)
                    try:
                        session, binding_digest = await _binding_session(manager)
                    except (
                        BrowserContextError,
                        BrowserNotStartedError,
                        BrowserSessionUnavailableError,
                        PageClosedError,
                    ):
                        _mark(
                            state, root, LiveCaptureStatus.SESSION_LOST,
                            "RESOURCE_LOST",
                        )
                        outcome = _outcome(state)
                    else:
                        if (
                            not rebind_session
                            and binding_digest != state["browser_binding_digest"]
                        ):
                            _mark(
                                state, root, LiveCaptureStatus.SESSION_LOST,
                                "BINDING_MISMATCH",
                            )
                            outcome = _outcome(state)
                        else:
                            if rebind_session:
                                state["endpoint_digest"] = supplied_endpoint_digest
                                state["browser_binding_digest"] = binding_digest
                            _mark(
                                state, root, LiveCaptureStatus.VERIFY_SESSION, None
                            )

            if outcome is None:
                try:
                    await _verify_session(session)
                except BaseException as error:
                    if _session_resource_lost(error, session):
                        _mark(
                            state, root, LiveCaptureStatus.SESSION_LOST,
                            "RESOURCE_LOST",
                        )
                        outcome = _outcome(state)
                    else:
                        raise
                if outcome is None:
                    _mark(state, root, LiveCaptureStatus.SESSION_READY, None)
                    _mark(state, root, LiveCaptureStatus.RUNNING, None)
        else:
            active_profile = profile
            if active_profile == PROFILE_P7_1_DISCOVERY_COHORT:
                if (
                    queries is None
                    or isinstance(queries, (str, bytes))
                    or list(queries) != list(DISCOVERY_COHORT_QUERIES)
                ):
                    raise LiveCaptureError(
                        "Discovery cohort profile requires exactly the 3 benchmark queries in order"
                    )
                frozen_queries = [_validate_scalar(query, "Query") for query in queries]
                checkpoint = _safe_path(root, _CHECKPOINT_NAME)
                bundle = _safe_path(root, _BUNDLE_NAME)
                discovery_bundle = _safe_path(root, _DISCOVERY_BUNDLE_NAME)
                if (
                    checkpoint.exists()
                    or checkpoint.is_symlink()
                    or bundle.exists()
                    or bundle.is_symlink()
                    or discovery_bundle.exists()
                    or discovery_bundle.is_symlink()
                ):
                    raise LiveCaptureError(
                        "Fresh capture job root already contains capture state"
                    )
                state = _initial_state(endpoint, frozen_queries, profile=active_profile)
                _atomic_checkpoint(root, state)
                initialized = True
                manager = manager_factory(cdp_endpoint=endpoint)
                try:
                    session, binding_digest = await _binding_session(manager)
                except (
                    BrowserContextError,
                    BrowserNotStartedError,
                    BrowserSessionUnavailableError,
                    PageClosedError,
                ):
                    _mark(state, root, LiveCaptureStatus.SESSION_LOST, "RESOURCE_LOST")
                    outcome = _outcome(state)
                else:
                    state["browser_binding_digest"] = binding_digest
                    _mark(state, root, LiveCaptureStatus.SESSION_READY, None)
                    _mark(state, root, LiveCaptureStatus.RUNNING, None)
            else:
                if (
                    queries is None
                    or isinstance(queries, (str, bytes))
                    or not (1 <= len(queries) <= _MAX_QUERIES)
                ):
                    raise LiveCaptureError("Fresh capture requires one or more queries")
                frozen_queries = [_validate_scalar(query, "Query") for query in queries]
                checkpoint = _safe_path(root, _CHECKPOINT_NAME)
                bundle = _safe_path(root, _BUNDLE_NAME)
                discovery_bundle = _safe_path(root, _DISCOVERY_BUNDLE_NAME)
                if (
                    checkpoint.exists()
                    or checkpoint.is_symlink()
                    or bundle.exists()
                    or bundle.is_symlink()
                    or discovery_bundle.exists()
                    or discovery_bundle.is_symlink()
                ):
                    raise LiveCaptureError(
                        "Fresh capture job root already contains capture state"
                    )
                state = _initial_state(endpoint, frozen_queries, profile=None)
                _atomic_checkpoint(root, state)
                initialized = True
                manager = manager_factory(cdp_endpoint=endpoint)
                try:
                    session, binding_digest = await _binding_session(manager)
                except (
                    BrowserContextError,
                    BrowserNotStartedError,
                    BrowserSessionUnavailableError,
                    PageClosedError,
                ):
                    _mark(state, root, LiveCaptureStatus.SESSION_LOST, "RESOURCE_LOST")
                    outcome = _outcome(state)
                else:
                    state["browser_binding_digest"] = binding_digest
                    _mark(state, root, LiveCaptureStatus.SESSION_READY, None)
                    _mark(state, root, LiveCaptureStatus.RUNNING, None)

        if active_profile == PROFILE_P7_1_DISCOVERY_COHORT:
            while outcome is None and state["query_position"] < len(state["queries"]):
                position = state["query_position"]
                query = state["queries"][position]
                request = DiscoveryRequest(
                    query=query,
                    max_candidates=5,
                    max_pages=1,
                    locale="vi-VN",
                )
                observed_at = now_factory()
                adapter = (
                    adapter_factory(session)
                    if adapter_factory is not None
                    else ShopeeDiscoveryAdapter(browser=session)
                )
                try:
                    batch = await adapter.discover(request, observed_at=observed_at)
                except DiscoveryBlockedError:
                    _mark(
                        state, root, LiveCaptureStatus.HUMAN_ACTION_REQUIRED, "DISCOVERY_BLOCKED"
                    )
                    outcome = _outcome(state)
                    break
                except BaseException as error:
                    if _session_resource_lost(error, session):
                        _mark(
                            state, root, LiveCaptureStatus.SESSION_LOST, "RESOURCE_LOST"
                        )
                        outcome = _outcome(state)
                        break
                    raise

                batch_dict = _validate_live_discovery_batch(
                    batch,
                    expected_query=query,
                    completed_batches=state["completed_batches"],
                )
                state["completed_batches"].append(batch_dict)
                state["query_position"] += 1
                state["phase"] = (
                    LiveCapturePhase.COMPLETE.value
                    if state["query_position"] == len(state["queries"])
                    else LiveCapturePhase.DISCOVERY.value
                )
                _atomic_checkpoint(root, state)

            if outcome is None:
                bundle_document = {
                    "batches": list(state["completed_batches"]),
                    "queries": list(state["queries"]),
                    "schema": _DISCOVERY_BUNDLE_SCHEMA,
                    "version": _DISCOVERY_BUNDLE_VERSION,
                }
                _exclusive_bundle(root, bundle_document, _DISCOVERY_BUNDLE_NAME)
                _mark(state, root, LiveCaptureStatus.READY, None)
                outcome = _outcome(state, bundle=True)
        else:
            tool = tool_factory() if outcome is None else None
            while outcome is None and state["query_position"] < len(state["queries"]):
                position = state["query_position"]
                query = state["queries"][position]
                phase = LiveCapturePhase(state["phase"])
                if phase is LiveCapturePhase.DISCOVERY:
                    request = DiscoveryRequest(query=query, max_pages=1, max_candidates=20)
                    adapter = ShopeeDiscoveryAdapter(browser=session)
                    plan = PlatformDiscoveryPlan(platform="shopee", adapter=adapter, request=request)
                    observed_at = now_factory()
                    try:
                        result = await orchestration(
                            (plan,), observed_at=observed_at, evaluated_at=observed_at, shortlist_size=3
                        )
                    except DiscoveryBlockedError:
                        _mark(state, root, LiveCaptureStatus.HUMAN_ACTION_REQUIRED, "DISCOVERY_BLOCKED")
                        outcome = _outcome(state)
                        break
                    prior_urls = {cohort["product_url"] for cohort in state["completed_cohorts"]}
                    selected = next(
                        (ranked.candidate for ranked in result.shortlist if ranked.candidate.url not in prior_urls),
                        None,
                    )
                    if selected is None:
                        raise LiveCaptureError("Discovery returned no distinct shortlisted candidate")
                    state["selected_candidate"] = {
                        "candidate_id": selected.candidate_id,
                        "product_url": selected.url,
                        "title": selected.title,
                    }
                    state["phase"] = LiveCapturePhase.ACQUIRE_1.value
                    _atomic_checkpoint(root, state)
                    phase = LiveCapturePhase.ACQUIRE_1

                observation_number = 1 if phase is LiveCapturePhase.ACQUIRE_1 else 2
                output_relative = f"cohorts/query-{position + 1:04d}/observation-{observation_number:04d}"
                output_directory = _safe_path(root, output_relative)
                output_directory.mkdir(parents=True, exist_ok=True)
                if not _is_relative_to(output_directory.resolve(strict=True), root):
                    raise LiveCaptureError("Observation output path escapes the job root")
                identifier = f"live-capture-q{position + 1:04d}-o{observation_number:04d}"
                result = await tool.execute(
                    ToolCall(
                        name="shopee_scrape",
                        arguments={"url": state["selected_candidate"]["product_url"]},
                        call_id=identifier,
                        run_id=identifier,
                    ),
                    {
                        "browser": session,
                        "browser_manager": manager,
                        "gdrive": _LocalDriveSink(),
                        "output_dir": str(output_directory),
                    },
                )
                if (
                    isinstance(result, ToolResult)
                    and result.status is ToolStatus.FAILURE
                    and result.error is not None
                    and result.error.code == "EXTRACTION_BLOCKED"
                ):
                    _mark(state, root, LiveCaptureStatus.HUMAN_ACTION_REQUIRED, "EXTRACTION_BLOCKED")
                    outcome = _outcome(state)
                    break
                if _tool_resource_lost(result):
                    _mark(state, root, LiveCaptureStatus.SESSION_LOST, "RESOURCE_LOST")
                    outcome = _outcome(state)
                    break
                if not isinstance(result, ToolResult):
                    raise LiveCaptureError("Acquisition returned an invalid result")
                if result.status is not ToolStatus.SUCCESS or result.error is not None:
                    raise LiveCaptureError("Acquisition failed")
                manifests = list(output_directory.rglob("source_pack.json"))
                if len(manifests) != 1:
                    raise LiveCaptureError("Acquisition did not persist exactly one source manifest")
                manifest = manifests[0]
                if manifest.is_symlink() or not manifest.is_file():
                    raise LiveCaptureError("Acquisition manifest is invalid")
                resolved_manifest = manifest.resolve(strict=True)
                if not _is_relative_to(resolved_manifest, root):
                    raise LiveCaptureError("Acquisition manifest escapes the job root")
                relative_manifest = resolved_manifest.relative_to(root).as_posix()
                observation = {
                    "manifest_path": relative_manifest,
                    "sha256": hashlib.sha256(resolved_manifest.read_bytes()).hexdigest(),
                }
                state["completed_observations"].append(observation)
                if observation_number == 1:
                    state["phase"] = LiveCapturePhase.ACQUIRE_2.value
                    _atomic_checkpoint(root, state)
                    continue

                candidate = state["selected_candidate"]
                state["completed_cohorts"].append({
                    "query": query,
                    "candidate_id": candidate["candidate_id"],
                    "product_url": candidate["product_url"],
                    "title": candidate["title"],
                    "observations": list(state["completed_observations"]),
                })
                state["query_position"] += 1
                state["selected_candidate"] = None
                state["completed_observations"] = []
                state["phase"] = (
                    LiveCapturePhase.COMPLETE.value
                    if state["query_position"] == len(state["queries"])
                    else LiveCapturePhase.DISCOVERY.value
                )
                _atomic_checkpoint(root, state)

            if outcome is None:
                bundle_document = {
                    "schema": _BUNDLE_SCHEMA,
                    "version": _BUNDLE_VERSION,
                    "cohorts": state["completed_cohorts"],
                }
                _exclusive_bundle(root, bundle_document)
                _mark(state, root, LiveCaptureStatus.READY, None)
                outcome = _outcome(state, bundle=True)
    except BaseException as error:
        operation_error = error
    finally:
        if manager is not None:
            try:
                await manager.close_all()
            except BaseException as close_error:
                if operation_error is None:
                    operation_error = close_error

    if operation_error is not None:
        if (
            initialized
            and state is not None
            and state.get("version") == _CHECKPOINT_VERSION
            and state.get("status") == LiveCaptureStatus.RUNNING.value
            and _session_resource_lost(operation_error, session)
        ):
            try:
                _mark(
                    state, root, LiveCaptureStatus.SESSION_LOST,
                    "RESOURCE_LOST",
                )
            except BaseException:
                pass
            else:
                return _outcome(state)
        if (
            initialized
            and state is not None
            and state.get("status") != LiveCaptureStatus.FAILED.value
        ):
            try:
                _mark(state, root, LiveCaptureStatus.FAILED, "TERMINAL_FAILURE")
            except BaseException:
                pass
        if isinstance(operation_error, LiveCaptureError):
            raise operation_error
        raise LiveCaptureError("Live capture failed") from operation_error
    assert outcome is not None
    return outcome


__all__ = [
    "DISCOVERY_COHORT_QUERIES",
    "LiveCaptureError",
    "LiveCaptureOutcome",
    "LiveCapturePhase",
    "LiveCaptureStatus",
    "PROFILE_P7_1_DISCOVERY_COHORT",
    "run_live_capture",
]
