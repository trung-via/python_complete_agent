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

from src.core.types import ToolCall, ToolResult, ToolStatus
from src.integrations.playwright.manager import PlaywrightBrowserManager
from src.product_intelligence.adapters.shopee import ShopeeDiscoveryAdapter
from src.product_intelligence.discovery import DiscoveryBlockedError, DiscoveryRequest
from src.product_intelligence.orchestration import (
    PlatformDiscoveryPlan,
    orchestrate_discovery,
)
from src.tools.shopee_scrape_tool import ShopeeScrapeTool


_CHECKPOINT_NAME = "capture_checkpoint.json"
_BUNDLE_NAME = "capture_bundle.json"
_CHECKPOINT_SCHEMA = "product_intelligence_live_capture_checkpoint"
_BUNDLE_SCHEMA = "product_intelligence_live_capture_bundle"
_VERSION = 1
_MAX_QUERIES = 100


class LiveCaptureError(Exception):
    """A terminal, non-resumable live-capture failure."""


class LiveCaptureStatus(str, Enum):
    RUNNING = "RUNNING"
    CHALLENGE_REQUIRED = "CHALLENGE_REQUIRED"
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

    def to_document(self) -> dict[str, object]:
        document: dict[str, object] = {
            "status": self.status.value,
            "phase": self.phase.value,
            "query_position": self.query_position,
            "query_count": self.query_count,
            "checkpoint": self.checkpoint_filename,
        }
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
    descriptor = os.open(temporary, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(_json_bytes(state))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except BaseException:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _exclusive_bundle(root: Path, document: dict[str, object]) -> None:
    destination = _safe_path(root, _BUNDLE_NAME)
    if destination.exists() or destination.is_symlink():
        raise LiveCaptureError("Capture bundle already exists")
    temporary = _safe_path(root, ".capture_bundle.json.tmp")
    if temporary.exists() or temporary.is_symlink():
        raise LiveCaptureError("Bundle atomic-write staging path already exists")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    linked = False
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(_json_bytes(document))
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, destination)
        linked = True
    except FileExistsError as exc:
        raise LiveCaptureError("Capture bundle already exists") from exc
    except OSError as exc:
        raise LiveCaptureError("Capture bundle could not be created") from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            if not linked:
                raise LiveCaptureError("Bundle staging cleanup failed")


def _initial_state(endpoint: str, queries: Sequence[str]) -> dict[str, object]:
    return {
        "schema": _CHECKPOINT_SCHEMA,
        "version": _VERSION,
        "status": LiveCaptureStatus.RUNNING.value,
        "cdp_endpoint": endpoint,
        "queries": list(queries),
        "query_position": 0,
        "phase": LiveCapturePhase.DISCOVERY.value,
        "completed_cohorts": [],
        "selected_candidate": None,
        "completed_observations": [],
        "category": None,
    }


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
    required = {
        "schema", "version", "status", "cdp_endpoint", "queries", "query_position",
        "phase", "completed_cohorts", "selected_candidate", "completed_observations", "category",
    }
    if not isinstance(document, dict) or set(document) != required:
        raise LiveCaptureError("Capture checkpoint is corrupt")
    if document["schema"] != _CHECKPOINT_SCHEMA or document["version"] != _VERSION:
        raise LiveCaptureError("Capture checkpoint schema is unsupported")
    try:
        status = LiveCaptureStatus(document["status"])
        phase = LiveCapturePhase(document["phase"])
    except (ValueError, TypeError) as exc:
        raise LiveCaptureError("Capture checkpoint state is invalid") from exc
    endpoint = _validate_scalar(document["cdp_endpoint"], "Checkpoint CDP endpoint")
    queries = document["queries"]
    if not isinstance(queries, list) or not (1 <= len(queries) <= _MAX_QUERIES):
        raise LiveCaptureError("Capture checkpoint query sequence is invalid")
    for query in queries:
        _validate_scalar(query, "Checkpoint query")
    position = document["query_position"]
    if isinstance(position, bool) or not isinstance(position, int) or not (0 <= position <= len(queries)):
        raise LiveCaptureError("Capture checkpoint query position is invalid")
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
    if phase is LiveCapturePhase.COMPLETE and position != len(queries):
        raise LiveCaptureError("Capture checkpoint completion position is inconsistent")
    if position == len(queries) and phase is not LiveCapturePhase.COMPLETE:
        raise LiveCaptureError("Capture checkpoint terminal position is inconsistent")
    if status is LiveCaptureStatus.CHALLENGE_REQUIRED and document["category"] not in ("DISCOVERY_BLOCKED", "EXTRACTION_BLOCKED"):
        raise LiveCaptureError("Capture checkpoint challenge category is invalid")
    if status is LiveCaptureStatus.CHALLENGE_REQUIRED and phase is LiveCapturePhase.COMPLETE:
        raise LiveCaptureError("Capture checkpoint challenge phase is invalid")
    if status is LiveCaptureStatus.RUNNING and document["category"] is not None:
        raise LiveCaptureError("Capture checkpoint running category is invalid")
    if status is LiveCaptureStatus.FAILED and document["category"] != "TERMINAL_FAILURE":
        raise LiveCaptureError("Capture checkpoint failure category is invalid")
    if status is LiveCaptureStatus.READY and (phase is not LiveCapturePhase.COMPLETE or document["category"] is not None):
        raise LiveCaptureError("Capture checkpoint ready state is invalid")
    if status is LiveCaptureStatus.READY:
        bundle = _safe_path(root, _BUNDLE_NAME, must_exist=True)
        if bundle.is_symlink() or not bundle.is_file():
            raise LiveCaptureError("Ready capture bundle is invalid")
    for record in [*observations, *(item for cohort in cohorts for item in cohort["observations"])]:
        manifest = _safe_path(root, record["manifest_path"], must_exist=True)
        if manifest.is_symlink() or not manifest.is_file():
            raise LiveCaptureError("Checkpoint manifest reference is invalid")
        if hashlib.sha256(manifest.read_bytes()).hexdigest() != record["sha256"]:
            raise LiveCaptureError("Checkpoint manifest digest mismatch")
    document["cdp_endpoint"] = endpoint
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
    return LiveCaptureOutcome(
        status=LiveCaptureStatus(state["status"]),
        phase=LiveCapturePhase(state["phase"]),
        query_position=state["query_position"],
        query_count=len(state["queries"]),
        bundle_filename=_BUNDLE_NAME if bundle else None,
    )


async def run_live_capture(
    *,
    job_root: str | os.PathLike[str],
    cdp_endpoint: str,
    queries: Optional[Sequence[str]] = None,
    resume: bool = False,
    manager_factory: Optional[Callable[..., object]] = None,
    tool_factory: Optional[Callable[[], object]] = None,
    orchestration: Optional[Callable[..., object]] = None,
    now_factory: Optional[Callable[[], datetime]] = None,
) -> LiveCaptureOutcome:
    """Start or explicitly resume one external-root Shopee capture job."""

    endpoint = _validate_scalar(cdp_endpoint, "CDP endpoint")
    root = _prepare_job_root(job_root)
    manager_factory = manager_factory or PlaywrightBrowserManager
    tool_factory = tool_factory or ShopeeScrapeTool
    orchestration = orchestration or orchestrate_discovery
    now_factory = now_factory or (lambda: datetime.now(timezone.utc))
    initialized = False
    if resume:
        if queries is not None:
            raise LiveCaptureError("Resume does not accept replacement queries")
        state = _load_resume_state(root)
        if state["status"] != LiveCaptureStatus.CHALLENGE_REQUIRED.value:
            raise LiveCaptureError("Only a CHALLENGE_REQUIRED capture may be resumed")
        initialized = True
        existing_bundle = root / _BUNDLE_NAME
        if existing_bundle.exists() or existing_bundle.is_symlink():
            _mark(state, root, LiveCaptureStatus.FAILED, "TERMINAL_FAILURE")
            raise LiveCaptureError("Capture bundle already exists")
        if endpoint != state["cdp_endpoint"]:
            _mark(state, root, LiveCaptureStatus.FAILED, "TERMINAL_FAILURE")
            raise LiveCaptureError("CDP endpoint does not match the frozen capture endpoint")
        state["status"] = LiveCaptureStatus.RUNNING.value
        state["category"] = None
        _atomic_checkpoint(root, state)
    else:
        if queries is None or isinstance(queries, (str, bytes)) or not (1 <= len(queries) <= _MAX_QUERIES):
            raise LiveCaptureError("Fresh capture requires one or more queries")
        frozen_queries = [_validate_scalar(query, "Query") for query in queries]
        checkpoint = _safe_path(root, _CHECKPOINT_NAME)
        bundle = _safe_path(root, _BUNDLE_NAME)
        if checkpoint.exists() or checkpoint.is_symlink() or bundle.exists() or bundle.is_symlink():
            raise LiveCaptureError("Fresh capture job root already contains capture state")
        state = _initial_state(endpoint, frozen_queries)
        _atomic_checkpoint(root, state)
        initialized = True

    manager = None
    operation_error: Optional[BaseException] = None
    outcome: Optional[LiveCaptureOutcome] = None
    try:
        manager = manager_factory(cdp_endpoint=endpoint)
        tool = tool_factory()
        while state["query_position"] < len(state["queries"]):
            position = state["query_position"]
            query = state["queries"][position]
            phase = LiveCapturePhase(state["phase"])
            if phase is LiveCapturePhase.DISCOVERY:
                request = DiscoveryRequest(query=query, max_pages=1, max_candidates=20)
                adapter = ShopeeDiscoveryAdapter(browser=manager)
                plan = PlatformDiscoveryPlan(platform="shopee", adapter=adapter, request=request)
                observed_at = now_factory()
                try:
                    result = await orchestration(
                        (plan,), observed_at=observed_at, evaluated_at=observed_at, shortlist_size=3
                    )
                except DiscoveryBlockedError:
                    _mark(state, root, LiveCaptureStatus.CHALLENGE_REQUIRED, "DISCOVERY_BLOCKED")
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
                _mark(state, root, LiveCaptureStatus.CHALLENGE_REQUIRED, "EXTRACTION_BLOCKED")
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
                "version": _VERSION,
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
        if initialized and state.get("status") != LiveCaptureStatus.FAILED.value:
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
    "LiveCaptureError",
    "LiveCaptureOutcome",
    "LiveCapturePhase",
    "LiveCaptureStatus",
    "run_live_capture",
]
