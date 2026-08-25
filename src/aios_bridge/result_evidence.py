"""Closed, compact machine evidence for review-first RESULT artifacts."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import PurePosixPath
import re
from typing import Any, Mapping

from src.aios_bridge.continuity.errors import ContinuityStateValidationError


RESULT_EVIDENCE_MARKER = "RESULT_EVIDENCE_JSON:"
RESULT_EVIDENCE_SCHEMA_VERSION = "2"
_TASK_RE = re.compile(r"\ATASK-\d+\Z")
_SHA_RE = re.compile(r"\A[0-9a-f]{40}\Z")
_TOKEN_RE = re.compile(r"\A[A-Z][A-Z0-9_]{0,63}\Z")
_ACTOR_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
_FORBIDDEN_KEY_PARTS = ("stdout", "stderr", "reasoning", "chain_of_thought", "raw_log")
_MAX_PATHS = 128
_MAX_NESTED_ITEMS = 256


class ResultEvidenceError(ContinuityStateValidationError):
    """Malformed or contradictory review-first RESULT evidence."""


def _error(message: str) -> ResultEvidenceError:
    return ResultEvidenceError(message)


def _require_token(value: object, name: str) -> str:
    if type(value) is not str or _TOKEN_RE.fullmatch(value) is None:
        raise _error(f"{name} must be a canonical uppercase token")
    return value


def _validate_path(value: object) -> str:
    if type(value) is not str or not value or value != value.strip() or "\\" in value:
        raise _error("actual_changed_paths entries must be exact POSIX paths")
    pure = PurePosixPath(value)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise _error("actual_changed_paths entries must be canonical repository-relative paths")
    if str(pure) != value or len(value) > 512:
        raise _error("actual_changed_paths entry is non-canonical or unbounded")
    return value


def _bounded_machine_value(value: object, *, path: str = "evidence", count: list[int] | None = None) -> Any:
    """Validate JSON-shaped evidence without accepting logs or reasoning fields."""
    if count is None:
        count = [0]
    count[0] += 1
    if count[0] > _MAX_NESTED_ITEMS:
        raise _error(f"{path} exceeds the bounded nested item count")
    if value is None or type(value) in {bool, int}:
        return value
    if type(value) is float:
        raise _error(f"{path} must not contain floating-point values")
    if type(value) is str:
        if len(value) > 1024 or any(ord(ch) < 32 and ch not in "\t" for ch in value):
            raise _error(f"{path} contains unbounded or control-bearing text")
        return value
    if type(value) is list:
        if len(value) > 128:
            raise _error(f"{path} list exceeds the bounded maximum")
        return [_bounded_machine_value(item, path=f"{path}[]", count=count) for item in value]
    if type(value) is dict:
        if len(value) > 64:
            raise _error(f"{path} object exceeds the bounded maximum")
        out: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str or not key or len(key) > 128:
                raise _error(f"{path} contains an invalid key")
            lowered = key.lower()
            if any(part in lowered for part in _FORBIDDEN_KEY_PARTS):
                raise _error(f"{path} contains forbidden raw log/reasoning field {key!r}")
            out[key] = _bounded_machine_value(item, path=f"{path}.{key}", count=count)
        return out
    raise _error(f"{path} must contain only exact JSON value types")


@dataclass(frozen=True, slots=True)
class ResultEvidence:
    schema_version: str
    task_id: str
    action: str
    executor_id: str
    pipeline_mode: str
    candidate_head_sha: str
    base_main_sha: str
    validation_profile: str
    full_canonical_owner: str
    candidate_stage_aios_managed_t2_execution_count: int
    certification_deferred: bool
    semantic_review_required: bool
    targeted_test_status: str
    publication_trust_status: str
    transport_status: str
    actual_changed_paths: tuple[str, ...]
    candidate_head_role: str = "PRE_PUBLICATION_CONTENT_HEAD"
    published_head_binding: str = "EXTERNAL_GIT_COMMIT"
    slice_c_impact_evidence: Mapping[str, Any] | None = None
    review_risk_evidence: Mapping[str, Any] | None = None
    blocked_execution_evidence: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.schema_version not in {"1", "2"}:
            raise _error("unsupported RESULT evidence schema_version")
        if type(self.task_id) is not str or _TASK_RE.fullmatch(self.task_id) is None:
            raise _error("task_id must match exact TASK-<digits>")
        if self.action not in {"RUN", "FIX"}:
            raise _error("action must be RUN or FIX")
        if type(self.executor_id) is not str or _ACTOR_RE.fullmatch(self.executor_id) is None:
            raise _error("executor_id must be a bounded canonical actor ID")
        if self.pipeline_mode != "REVIEW_FIRST_CERTIFICATION":
            raise _error("compact RESULT evidence is authority-safe only for review-first mode")
        if type(self.candidate_head_sha) is not str or _SHA_RE.fullmatch(self.candidate_head_sha) is None:
            raise _error("candidate_head_sha must be an exact lowercase 40-hex SHA")
        if self.schema_version == "2":
            if self.candidate_head_role != "PRE_PUBLICATION_CONTENT_HEAD":
                raise _error("candidate_head_role must be PRE_PUBLICATION_CONTENT_HEAD")
            if self.published_head_binding != "EXTERNAL_GIT_COMMIT":
                raise _error("published_head_binding must be EXTERNAL_GIT_COMMIT")
        if self.base_main_sha != "UNKNOWN" and (
            type(self.base_main_sha) is not str or _SHA_RE.fullmatch(self.base_main_sha) is None
        ):
            raise _error("base_main_sha must be exact lowercase 40-hex or UNKNOWN")
        _require_token(self.validation_profile, "validation_profile")
        if self.full_canonical_owner != "CERTIFICATION_BOUNDARY":
            raise _error("full_canonical_owner must be CERTIFICATION_BOUNDARY")
        if self.candidate_stage_aios_managed_t2_execution_count != 0:
            raise _error("review-first candidate evidence must record zero AIOS-managed T2 executions")
        if self.certification_deferred is not True or self.semantic_review_required is not True:
            raise _error("zero-T2 review-first candidate must defer certification and require semantic review")
        _require_token(self.targeted_test_status, "targeted_test_status")
        _require_token(self.publication_trust_status, "publication_trust_status")
        _require_token(self.transport_status, "transport_status")
        if type(self.actual_changed_paths) is not tuple or len(self.actual_changed_paths) > _MAX_PATHS:
            raise _error("actual_changed_paths must be an exact bounded tuple")
        for item in self.actual_changed_paths:
            _validate_path(item)
        if len(set(self.actual_changed_paths)) != len(self.actual_changed_paths):
            raise _error("actual_changed_paths must be duplicate-free")
        if tuple(sorted(self.actual_changed_paths)) != self.actual_changed_paths:
            raise _error("actual_changed_paths must be canonically sorted")
        for name in (
            "slice_c_impact_evidence",
            "review_risk_evidence",
            "blocked_execution_evidence",
        ):
            value = getattr(self, name)
            if value is not None:
                if not isinstance(value, Mapping):
                    raise _error(f"{name} must be a mapping or None")
                object.__setattr__(self, name, _bounded_machine_value(dict(value), path=name))
        if self.blocked_execution_evidence is not None:
            raise _error("a published review candidate cannot also be a blocked execution")

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "action": self.action,
            "actual_changed_paths": list(self.actual_changed_paths),
            "base_main_sha": self.base_main_sha,
            "blocked_execution_evidence": self.blocked_execution_evidence,
            "candidate_head_sha": self.candidate_head_sha,
            "candidate_stage_aios_managed_t2_execution_count": self.candidate_stage_aios_managed_t2_execution_count,
            "certification_deferred": self.certification_deferred,
            "executor_id": self.executor_id,
            "full_canonical_owner": self.full_canonical_owner,
            "pipeline_mode": self.pipeline_mode,
            "publication_trust_status": self.publication_trust_status,
            "review_risk_evidence": self.review_risk_evidence,
            "schema_version": self.schema_version,
            "semantic_review_required": self.semantic_review_required,
            "slice_c_impact_evidence": self.slice_c_impact_evidence,
            "targeted_test_status": self.targeted_test_status,
            "task_id": self.task_id,
            "transport_status": self.transport_status,
            "validation_profile": self.validation_profile,
        }
        if self.schema_version == "2":
            data["candidate_head_role"] = self.candidate_head_role
            data["published_head_binding"] = self.published_head_binding
        return data

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def fingerprint(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def render_marker(self) -> str:
        return f"{RESULT_EVIDENCE_MARKER} {self.canonical_json()}"

    @classmethod
    def from_dict(cls, data: object) -> "ResultEvidence":
        if type(data) is not dict:
            raise _error("RESULT evidence must be a dictionary")
        schema_version = data.get("schema_version")
        if schema_version == "2":
            fields = {
                "action", "actual_changed_paths", "base_main_sha", "blocked_execution_evidence",
                "candidate_head_role", "candidate_head_sha",
                "candidate_stage_aios_managed_t2_execution_count", "certification_deferred",
                "executor_id", "full_canonical_owner", "pipeline_mode", "publication_trust_status",
                "published_head_binding", "review_risk_evidence", "schema_version",
                "semantic_review_required", "slice_c_impact_evidence", "targeted_test_status",
                "task_id", "transport_status", "validation_profile",
            }
            if set(data) != fields:
                raise _error("RESULT evidence must contain the exact schema-v2 field set")
            if type(data["actual_changed_paths"]) is not list:
                raise _error("actual_changed_paths must be an exact JSON list")
            return cls(
                schema_version=data["schema_version"], task_id=data["task_id"], action=data["action"],
                executor_id=data["executor_id"], pipeline_mode=data["pipeline_mode"],
                candidate_head_sha=data["candidate_head_sha"], base_main_sha=data["base_main_sha"],
                validation_profile=data["validation_profile"], full_canonical_owner=data["full_canonical_owner"],
                candidate_stage_aios_managed_t2_execution_count=data["candidate_stage_aios_managed_t2_execution_count"],
                certification_deferred=data["certification_deferred"],
                semantic_review_required=data["semantic_review_required"],
                targeted_test_status=data["targeted_test_status"],
                publication_trust_status=data["publication_trust_status"],
                transport_status=data["transport_status"], actual_changed_paths=tuple(data["actual_changed_paths"]),
                candidate_head_role=data["candidate_head_role"],
                published_head_binding=data["published_head_binding"],
                slice_c_impact_evidence=data["slice_c_impact_evidence"],
                review_risk_evidence=data["review_risk_evidence"],
                blocked_execution_evidence=data["blocked_execution_evidence"],
            )
        elif schema_version == "1":
            fields_v1 = {
                "action", "actual_changed_paths", "base_main_sha", "blocked_execution_evidence",
                "candidate_head_sha", "candidate_stage_aios_managed_t2_execution_count",
                "certification_deferred", "executor_id", "full_canonical_owner", "pipeline_mode",
                "publication_trust_status", "review_risk_evidence", "schema_version",
                "semantic_review_required", "slice_c_impact_evidence", "targeted_test_status",
                "task_id", "transport_status", "validation_profile",
            }
            if set(data) != fields_v1:
                raise _error("RESULT evidence must contain the exact schema-v1 field set")
            if type(data["actual_changed_paths"]) is not list:
                raise _error("actual_changed_paths must be an exact JSON list")
            return cls(
                schema_version=data["schema_version"], task_id=data["task_id"], action=data["action"],
                executor_id=data["executor_id"], pipeline_mode=data["pipeline_mode"],
                candidate_head_sha=data["candidate_head_sha"], base_main_sha=data["base_main_sha"],
                validation_profile=data["validation_profile"], full_canonical_owner=data["full_canonical_owner"],
                candidate_stage_aios_managed_t2_execution_count=data["candidate_stage_aios_managed_t2_execution_count"],
                certification_deferred=data["certification_deferred"],
                semantic_review_required=data["semantic_review_required"],
                targeted_test_status=data["targeted_test_status"],
                publication_trust_status=data["publication_trust_status"],
                transport_status=data["transport_status"], actual_changed_paths=tuple(data["actual_changed_paths"]),
                slice_c_impact_evidence=data["slice_c_impact_evidence"],
                review_risk_evidence=data["review_risk_evidence"],
                blocked_execution_evidence=data["blocked_execution_evidence"],
            )
        else:
            raise _error("unsupported RESULT evidence schema_version")


def _reject_duplicate_keys_dict(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, val in pairs:
        if key in out:
            raise _error(f"duplicate JSON key {key!r}")
        out[key] = val
    return out


def parse_result_evidence(result_text: str) -> ResultEvidence:
    """Parse exactly one authoritative top-level marker from a RESULT artifact."""
    if type(result_text) is not str:
        raise _error("result_text must be exact text")

    lines = result_text.splitlines()
    in_fence = False
    fence_char = ""
    fence_len = 0
    unfenced_payloads: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not in_fence:
            if stripped.startswith("```") or stripped.startswith("~~~"):
                fence_char = stripped[0]
                run = 0
                while run < len(stripped) and stripped[run] == fence_char:
                    run += 1
                in_fence = True
                fence_len = run
                continue
            if line.startswith(RESULT_EVIDENCE_MARKER):
                unfenced_payloads.append(line[len(RESULT_EVIDENCE_MARKER):].strip())
        else:
            if stripped.startswith(fence_char * fence_len):
                run = 0
                while run < len(stripped) and stripped[run] == fence_char:
                    run += 1
                if run >= fence_len and not stripped[run:].strip():
                    in_fence = False
                    fence_char = ""
                    fence_len = 0
                    continue

    if len(unfenced_payloads) != 1:
        raise _error(f"RESULT must contain exactly one unfenced {RESULT_EVIDENCE_MARKER} marker")

    try:
        data = json.loads(unfenced_payloads[0], object_pairs_hook=_reject_duplicate_keys_dict)
    except (TypeError, ValueError) as exc:
        raise _error(f"malformed RESULT_EVIDENCE_JSON: {exc}") from exc
    return ResultEvidence.from_dict(data)


__all__ = [
    "RESULT_EVIDENCE_MARKER", "RESULT_EVIDENCE_SCHEMA_VERSION", "ResultEvidence",
    "ResultEvidenceError", "parse_result_evidence",
]
