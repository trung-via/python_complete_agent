"""Deterministic reviewed-head merge gate and review contract parser (ADR-042 / TASK-069)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import re
from typing import Any

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.roadmap_governance import (
    CanonicalRoadmap,
    RoadmapStatus,
    RoadmapTaskBinding,
)


_SHA_RE = re.compile(r"\A[0-9a-f]{40}\Z")
_STATUS_TOKEN_RE = re.compile(r"\A[A-Z0-9_]+\Z")
_TASK_ID_RE = re.compile(r"\ATASK-\d+\Z")
_KEY_VALUE_LINE_RE = re.compile(r"\A([A-Z0-9_]+)\s*:\s*(.+)\Z")


class MergeGateReason(str, Enum):
    """Closed stable vocabulary of merge gate outcome reasons."""
    PASS_ELIGIBLE = "PASS_ELIGIBLE"
    REVIEW_MISSING = "REVIEW_MISSING"
    REVIEW_NOT_PASS = "REVIEW_NOT_PASS"
    REVIEW_NOT_APPROVED = "REVIEW_NOT_APPROVED"
    AUTO_MERGE_DISABLED = "AUTO_MERGE_DISABLED"
    REVIEW_HEAD_INVALID = "REVIEW_HEAD_INVALID"
    REVIEW_BASE_INVALID = "REVIEW_BASE_INVALID"
    TASK_HEAD_DRIFT = "TASK_HEAD_DRIFT"
    MAIN_DRIFT = "MAIN_DRIFT"
    NOT_FAST_FORWARD = "NOT_FAST_FORWARD"
    BRANCH_BEHIND_MAIN = "BRANCH_BEHIND_MAIN"
    NO_TASK_DELTA = "NO_TASK_DELTA"
    POST_MERGE_IDENTITY_FAILED = "POST_MERGE_IDENTITY_FAILED"
    GIT_OPERATION_FAILED = "GIT_OPERATION_FAILED"
    ROADMAP_AUDIT_MISSING = "ROADMAP_AUDIT_MISSING"
    ROADMAP_AUDIT_NOT_PASS = "ROADMAP_AUDIT_NOT_PASS"
    ROADMAP_IDENTITY_MISMATCH = "ROADMAP_IDENTITY_MISMATCH"
    ROADMAP_MILESTONE_MISMATCH = "ROADMAP_MILESTONE_MISMATCH"
    ROADMAP_CAPABILITY_MISMATCH = "ROADMAP_CAPABILITY_MISMATCH"
    ROADMAP_BINDING_FINGERPRINT_MISMATCH = "ROADMAP_BINDING_FINGERPRINT_MISMATCH"
    ROADMAP_CURRENT_DRIFT = "ROADMAP_CURRENT_DRIFT"
    ROADMAP_TASK_MISSING = "ROADMAP_TASK_MISSING"
    ROADMAP_TASK_INVALID = "ROADMAP_TASK_INVALID"


class ReviewHeaderParseError(ContinuityStateValidationError):
    """Review header parse failure bound to an exact closed MergeGateReason."""
    def __init__(self, message: str, reason: MergeGateReason) -> None:
        super().__init__(message)
        self.reason = reason


@dataclass(frozen=True)
class RoadmapReviewAudit:
    """Exact roadmap evidence independently asserted by a PASS review."""
    roadmap_audit: str
    roadmap_id: str
    roadmap_version: str
    roadmap_blob_sha: str
    roadmap_fingerprint: str
    milestone: str
    capability_id: str
    requirement_bindings_fingerprint: str

    def __post_init__(self) -> None:
        if not isinstance(self.roadmap_audit, str) or not _STATUS_TOKEN_RE.fullmatch(self.roadmap_audit):
            raise ContinuityStateValidationError("roadmap_audit must be exact uppercase token")
        for name, value in (
            ("roadmap_id", self.roadmap_id),
            ("roadmap_version", self.roadmap_version),
            ("milestone", self.milestone),
            ("capability_id", self.capability_id),
        ):
            if not isinstance(value, str) or not value or value != value.strip():
                raise ContinuityStateValidationError(f"{name} must be exact non-empty string")
        if not _SHA_RE.fullmatch(self.roadmap_blob_sha):
            raise ContinuityStateValidationError("roadmap_blob_sha must be exact lowercase 40-hex")
        for name, value in (
            ("roadmap_fingerprint", self.roadmap_fingerprint),
            ("requirement_bindings_fingerprint", self.requirement_bindings_fingerprint),
        ):
            if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise ContinuityStateValidationError(f"{name} must be exact lowercase 64-hex")


@dataclass(frozen=True)
class ReviewedMergeInput:
    """Immutable input parameters for the pure merge gate decision."""
    task_id: str
    review_status: str
    review_approved: bool
    auto_merge_eligible: bool
    reviewed_task_head_sha: str
    reviewed_base_main_sha: str
    current_task_head_sha: str
    current_main_sha: str
    merge_base_sha: str
    ahead_by: int
    behind_by: int
    roadmap_governed: bool = False
    roadmap_audit: RoadmapReviewAudit | None = None
    task_roadmap_binding: RoadmapTaskBinding | None = None
    current_roadmap: CanonicalRoadmap | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, str) or not _TASK_ID_RE.fullmatch(self.task_id):
            raise ContinuityStateValidationError(
                f"task_id must be canonical TASK-NNN: got {self.task_id!r}"
            )
        if not isinstance(self.review_status, str) or not _STATUS_TOKEN_RE.fullmatch(self.review_status):
            raise ContinuityStateValidationError(
                f"review_status must be exact uppercase token: got {self.review_status!r}"
            )
        if type(self.review_approved) is not bool:
            raise ContinuityStateValidationError(
                f"review_approved must be exact bool: got {self.review_approved!r}"
            )
        if type(self.auto_merge_eligible) is not bool:
            raise ContinuityStateValidationError(
                f"auto_merge_eligible must be exact bool: got {self.auto_merge_eligible!r}"
            )
        if type(self.roadmap_governed) is not bool:
            raise ContinuityStateValidationError("roadmap_governed must be exact bool")
        if self.roadmap_audit is not None and not isinstance(self.roadmap_audit, RoadmapReviewAudit):
            raise ContinuityStateValidationError("roadmap_audit must be RoadmapReviewAudit or None")
        if self.task_roadmap_binding is not None and not isinstance(
            self.task_roadmap_binding, RoadmapTaskBinding
        ):
            raise ContinuityStateValidationError(
                "task_roadmap_binding must be RoadmapTaskBinding or None"
            )
        if self.current_roadmap is not None and not isinstance(self.current_roadmap, CanonicalRoadmap):
            raise ContinuityStateValidationError("current_roadmap must be CanonicalRoadmap or None")

        for name, sha_val in [
            ("reviewed_task_head_sha", self.reviewed_task_head_sha),
            ("reviewed_base_main_sha", self.reviewed_base_main_sha),
            ("current_task_head_sha", self.current_task_head_sha),
            ("current_main_sha", self.current_main_sha),
            ("merge_base_sha", self.merge_base_sha),
        ]:
            if not isinstance(sha_val, str) or not _SHA_RE.fullmatch(sha_val):
                raise ContinuityStateValidationError(
                    f"{name} must be exact lowercase 40-hex SHA: got {sha_val!r}"
                )

        for name, count_val in [
            ("ahead_by", self.ahead_by),
            ("behind_by", self.behind_by),
        ]:
            if type(count_val) is not int:
                raise ContinuityStateValidationError(
                    f"{name} must be exact int (bool forbidden): got {count_val!r}"
                )
            if count_val < 0:
                raise ContinuityStateValidationError(
                    f"{name} must be non-negative int: got {count_val!r}"
                )


@dataclass(frozen=True)
class MergeGateDecision:
    """Immutable evaluation result returned by the pure merge gate."""
    eligible: bool
    reason: MergeGateReason
    message: str

    def __post_init__(self) -> None:
        if type(self.eligible) is not bool:
            raise ContinuityStateValidationError("eligible must be exact bool")
        if not isinstance(self.reason, MergeGateReason):
            raise ContinuityStateValidationError(f"reason must be MergeGateReason: got {self.reason!r}")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ContinuityStateValidationError("message must be non-empty string")


def evaluate_merge_gate(input_data: ReviewedMergeInput) -> MergeGateDecision:
    """Evaluate merge eligibility deterministically with fail-closed precedence."""
    if input_data.review_status != "PASS":
        return MergeGateDecision(
            eligible=False,
            reason=MergeGateReason.REVIEW_NOT_PASS,
            message=f"Review status is {input_data.review_status}, expected PASS",
        )

    if not input_data.review_approved:
        return MergeGateDecision(
            eligible=False,
            reason=MergeGateReason.REVIEW_NOT_APPROVED,
            message="Review is not approved (APPROVED != YES)",
        )

    if not input_data.auto_merge_eligible:
        return MergeGateDecision(
            eligible=False,
            reason=MergeGateReason.AUTO_MERGE_DISABLED,
            message="Auto-merge is disabled (AUTO_MERGE_ELIGIBLE != YES)",
        )

    if input_data.roadmap_governed:
        audit = input_data.roadmap_audit
        binding = input_data.task_roadmap_binding
        current = input_data.current_roadmap
        if audit is None:
            return MergeGateDecision(
                eligible=False,
                reason=MergeGateReason.ROADMAP_AUDIT_MISSING,
                message="PASS review for roadmap-governed task omits exact roadmap audit evidence",
            )
        if audit.roadmap_audit != "PASS":
            return MergeGateDecision(
                eligible=False,
                reason=MergeGateReason.ROADMAP_AUDIT_NOT_PASS,
                message=f"ROADMAP_AUDIT is {audit.roadmap_audit}, expected PASS",
            )
        if binding is None:
            return MergeGateDecision(
                eligible=False,
                reason=MergeGateReason.ROADMAP_IDENTITY_MISMATCH,
                message="Roadmap-governed task has no machine-bound task roadmap evidence",
            )
        if (audit.roadmap_id, audit.roadmap_version, audit.roadmap_blob_sha, audit.roadmap_fingerprint) != (
            binding.roadmap_id,
            binding.roadmap_version,
            binding.roadmap_blob_sha,
            binding.roadmap_fingerprint,
        ):
            return MergeGateDecision(
                eligible=False,
                reason=MergeGateReason.ROADMAP_IDENTITY_MISMATCH,
                message="Review roadmap identity differs from exact task-bound roadmap identity",
            )
        if audit.milestone != binding.milestone:
            return MergeGateDecision(
                eligible=False,
                reason=MergeGateReason.ROADMAP_MILESTONE_MISMATCH,
                message="Review milestone differs from task-bound milestone",
            )
        if audit.capability_id != binding.capability_id:
            return MergeGateDecision(
                eligible=False,
                reason=MergeGateReason.ROADMAP_CAPABILITY_MISMATCH,
                message="Review capability differs from task-bound capability",
            )
        if audit.requirement_bindings_fingerprint != binding.requirement_bindings_fingerprint():
            return MergeGateDecision(
                eligible=False,
                reason=MergeGateReason.ROADMAP_BINDING_FINGERPRINT_MISMATCH,
                message="Review requirement binding fingerprint differs from task binding",
            )
        if current is None or current.status is not RoadmapStatus.LOCKED or (
            current.roadmap_id,
            current.roadmap_version,
            current.roadmap_blob_sha,
            current.roadmap_fingerprint,
        ) != (
            binding.roadmap_id,
            binding.roadmap_version,
            binding.roadmap_blob_sha,
            binding.roadmap_fingerprint,
        ):
            return MergeGateDecision(
                eligible=False,
                reason=MergeGateReason.ROADMAP_CURRENT_DRIFT,
                message="Current locked roadmap drifted from the reviewed task binding",
            )

    if input_data.current_task_head_sha != input_data.reviewed_task_head_sha:
        return MergeGateDecision(
            eligible=False,
            reason=MergeGateReason.TASK_HEAD_DRIFT,
            message=(
                f"Task branch head ({input_data.current_task_head_sha}) drifted "
                f"from reviewed head ({input_data.reviewed_task_head_sha})"
            ),
        )

    if input_data.current_main_sha != input_data.reviewed_base_main_sha:
        return MergeGateDecision(
            eligible=False,
            reason=MergeGateReason.MAIN_DRIFT,
            message=(
                f"Main head ({input_data.current_main_sha}) drifted "
                f"from reviewed base main ({input_data.reviewed_base_main_sha})"
            ),
        )

    if input_data.behind_by > 0:
        return MergeGateDecision(
            eligible=False,
            reason=MergeGateReason.BRANCH_BEHIND_MAIN,
            message=f"Task branch is behind main by {input_data.behind_by} commit(s)",
        )

    if input_data.merge_base_sha != input_data.current_main_sha:
        return MergeGateDecision(
            eligible=False,
            reason=MergeGateReason.NOT_FAST_FORWARD,
            message=(
                f"Merge base ({input_data.merge_base_sha}) does not match "
                f"current main ({input_data.current_main_sha})"
            ),
        )

    if input_data.ahead_by < 1:
        return MergeGateDecision(
            eligible=False,
            reason=MergeGateReason.NO_TASK_DELTA,
            message="Task branch has zero commits ahead of main",
        )

    return MergeGateDecision(
        eligible=True,
        reason=MergeGateReason.PASS_ELIGIBLE,
        message="Merge gate criteria fully satisfied for fast-forward auto-merge",
    )


def parse_review_header(review_text: str) -> dict[str, Any]:
    """
    Parse strict machine-readable review header key-values anchored strictly to the top header region.
    Fails closed on missing required keys, duplicate keys, malformed YES/NO, non-canonical casing,
    alias conflicts, or keys present only in later body/fenced sections.
    """
    if not isinstance(review_text, str) or not review_text.strip():
        raise ReviewHeaderParseError("review_text must be non-empty string", MergeGateReason.REVIEW_MISSING)

    seen_raw_keys: set[str] = set()
    raw_kv: dict[str, str] = {}

    lines = review_text.splitlines()
    i = 0
    # Skip leading blank lines
    while i < len(lines) and not lines[i].strip():
        i += 1
    # Skip initial top-level title (e.g. '# REVIEW-069 ...')
    if i < len(lines) and lines[i].strip().startswith("# "):
        i += 1

    # Anchor exclusively to the top header region before any section heading (## ...) or code block (```)
    in_header = False
    for line_idx in range(i, len(lines)):
        line = lines[line_idx].strip()
        if not line:
            if in_header:
                # Blank line following parsed header keys terminates the top header region
                break
            continue

        if line.startswith("#") or line.startswith("```"):
            # Section header or code block delimiter terminates the top header region
            break

        match = _KEY_VALUE_LINE_RE.match(line)
        if not match:
            # Any non-key-value prose line terminates the header region
            break

        in_header = True
        key, val = match.group(1), match.group(2).strip()

        # Reject any markdown wrapper formatting around authority values (e.g. `PASS` or "YES")
        if (
            val.startswith("`")
            or val.endswith("`")
            or val.startswith('"')
            or val.endswith('"')
            or val.startswith("'")
            or val.endswith("'")
        ):
            raise ReviewHeaderParseError(
                f"Authority value for {key} contains forbidden markdown/quote formatting: {val!r}",
                MergeGateReason.REVIEW_HEAD_INVALID if "SHA" in key else MergeGateReason.REVIEW_NOT_PASS,
            )

        if key in seen_raw_keys:
            raise ReviewHeaderParseError(
                f"Duplicate required/header key rejected: {key}", MergeGateReason.REVIEW_MISSING
            )
        seen_raw_keys.add(key)
        raw_kv[key] = val

    # Resolve required STATUS (exact uppercase token, no normalization)
    if "STATUS" not in raw_kv:
        raise ReviewHeaderParseError("Missing required review key in header: STATUS", MergeGateReason.REVIEW_NOT_PASS)
    status = raw_kv["STATUS"]
    if not _STATUS_TOKEN_RE.fullmatch(status):
        raise ReviewHeaderParseError(
            f"STATUS must be exact uppercase token (lowercase/normalization rejected): got {status!r}",
            MergeGateReason.REVIEW_NOT_PASS,
        )

    # Resolve required APPROVED (exact YES or NO, no normalization)
    if "APPROVED" not in raw_kv:
        raise ReviewHeaderParseError("Missing required review key in header: APPROVED", MergeGateReason.REVIEW_NOT_APPROVED)
    approved_raw = raw_kv["APPROVED"]
    if approved_raw == "YES":
        approved = True
    elif approved_raw == "NO":
        approved = False
    else:
        raise ReviewHeaderParseError(
            f"APPROVED must be exact 'YES' or 'NO' (case-sensitive): got {approved_raw!r}",
            MergeGateReason.REVIEW_NOT_APPROVED,
        )

    # Resolve required AUTO_MERGE_ELIGIBLE (or alias AUTO_MERGE_ALLOWED) with conflict check
    has_eligible = "AUTO_MERGE_ELIGIBLE" in raw_kv
    has_allowed = "AUTO_MERGE_ALLOWED" in raw_kv
    if not has_eligible and not has_allowed:
        raise ReviewHeaderParseError(
            "Missing required review key in header: AUTO_MERGE_ELIGIBLE", MergeGateReason.AUTO_MERGE_DISABLED
        )
    if has_eligible and has_allowed:
        if raw_kv["AUTO_MERGE_ELIGIBLE"] != raw_kv["AUTO_MERGE_ALLOWED"]:
            raise ReviewHeaderParseError(
                f"Conflicting AUTO_MERGE_ELIGIBLE ({raw_kv['AUTO_MERGE_ELIGIBLE']!r}) "
                f"and AUTO_MERGE_ALLOWED ({raw_kv['AUTO_MERGE_ALLOWED']!r})",
                MergeGateReason.AUTO_MERGE_DISABLED,
            )
        auto_merge_raw = raw_kv["AUTO_MERGE_ELIGIBLE"]
    elif has_eligible:
        auto_merge_raw = raw_kv["AUTO_MERGE_ELIGIBLE"]
    else:
        auto_merge_raw = raw_kv["AUTO_MERGE_ALLOWED"]

    if auto_merge_raw == "YES":
        auto_merge_eligible = True
    elif auto_merge_raw == "NO":
        auto_merge_eligible = False
    else:
        raise ReviewHeaderParseError(
            f"AUTO_MERGE_ELIGIBLE must be exact 'YES' or 'NO' (case-sensitive): got {auto_merge_raw!r}",
            MergeGateReason.AUTO_MERGE_DISABLED,
        )

    # Resolve REVIEWED_TASK_HEAD_SHA (or alias REVIEWED_HEAD_SHA) with conflict check
    has_task_head = "REVIEWED_TASK_HEAD_SHA" in raw_kv
    has_head_alias = "REVIEWED_HEAD_SHA" in raw_kv
    if not has_task_head and not has_head_alias:
        raise ReviewHeaderParseError(
            "Missing required review key in header: REVIEWED_TASK_HEAD_SHA", MergeGateReason.REVIEW_HEAD_INVALID
        )
    if has_task_head and has_head_alias:
        if raw_kv["REVIEWED_TASK_HEAD_SHA"] != raw_kv["REVIEWED_HEAD_SHA"]:
            raise ReviewHeaderParseError(
                f"Conflicting REVIEWED_TASK_HEAD_SHA ({raw_kv['REVIEWED_TASK_HEAD_SHA']!r}) "
                f"and REVIEWED_HEAD_SHA ({raw_kv['REVIEWED_HEAD_SHA']!r})",
                MergeGateReason.REVIEW_HEAD_INVALID,
            )
        reviewed_task_head = raw_kv["REVIEWED_TASK_HEAD_SHA"]
    elif has_task_head:
        reviewed_task_head = raw_kv["REVIEWED_TASK_HEAD_SHA"]
    else:
        reviewed_task_head = raw_kv["REVIEWED_HEAD_SHA"]

    if not _SHA_RE.fullmatch(reviewed_task_head):
        raise ReviewHeaderParseError(
            f"REVIEWED_TASK_HEAD_SHA must be exact lowercase 40-hex SHA: got {reviewed_task_head!r}",
            MergeGateReason.REVIEW_HEAD_INVALID,
        )

    # Resolve REVIEWED_BASE_MAIN_SHA (or alias BASE_MAIN_SHA) with conflict check
    has_base_main = "REVIEWED_BASE_MAIN_SHA" in raw_kv
    has_base_alias = "BASE_MAIN_SHA" in raw_kv
    if not has_base_main and not has_base_alias:
        raise ReviewHeaderParseError(
            "Missing required review key in header: REVIEWED_BASE_MAIN_SHA", MergeGateReason.REVIEW_BASE_INVALID
        )
    if has_base_main and has_base_alias:
        if raw_kv["REVIEWED_BASE_MAIN_SHA"] != raw_kv["BASE_MAIN_SHA"]:
            raise ReviewHeaderParseError(
                f"Conflicting REVIEWED_BASE_MAIN_SHA ({raw_kv['REVIEWED_BASE_MAIN_SHA']!r}) "
                f"and BASE_MAIN_SHA ({raw_kv['BASE_MAIN_SHA']!r})",
                MergeGateReason.REVIEW_BASE_INVALID,
            )
        reviewed_base_main = raw_kv["REVIEWED_BASE_MAIN_SHA"]
    elif has_base_main:
        reviewed_base_main = raw_kv["REVIEWED_BASE_MAIN_SHA"]
    else:
        reviewed_base_main = raw_kv["BASE_MAIN_SHA"]

    if not _SHA_RE.fullmatch(reviewed_base_main):
        raise ReviewHeaderParseError(
            f"REVIEWED_BASE_MAIN_SHA must be exact lowercase 40-hex SHA: got {reviewed_base_main!r}",
            MergeGateReason.REVIEW_BASE_INVALID,
        )

    task_artifact_blob_sha = raw_kv.get("TASK_ARTIFACT_BLOB_SHA")
    if task_artifact_blob_sha is not None and not _SHA_RE.fullmatch(task_artifact_blob_sha):
        raise ReviewHeaderParseError(
            "TASK_ARTIFACT_BLOB_SHA must be exact lowercase 40-hex SHA",
            MergeGateReason.ROADMAP_TASK_INVALID,
        )

    roadmap_keys = (
        "ROADMAP_AUDIT", "ROADMAP_ID", "ROADMAP_VERSION", "ROADMAP_BLOB_SHA",
        "ROADMAP_FINGERPRINT", "MILESTONE", "CAPABILITY_ID",
        "REQUIREMENT_BINDINGS_FINGERPRINT",
    )
    roadmap_audit: RoadmapReviewAudit | None = None
    if any(key in raw_kv for key in roadmap_keys):
        missing = [key for key in roadmap_keys if key not in raw_kv]
        if missing:
            raise ReviewHeaderParseError(
                f"Incomplete roadmap audit evidence; missing {missing}",
                MergeGateReason.ROADMAP_AUDIT_MISSING,
            )
        try:
            roadmap_audit = RoadmapReviewAudit(
                roadmap_audit=raw_kv["ROADMAP_AUDIT"],
                roadmap_id=raw_kv["ROADMAP_ID"],
                roadmap_version=raw_kv["ROADMAP_VERSION"],
                roadmap_blob_sha=raw_kv["ROADMAP_BLOB_SHA"],
                roadmap_fingerprint=raw_kv["ROADMAP_FINGERPRINT"],
                milestone=raw_kv["MILESTONE"],
                capability_id=raw_kv["CAPABILITY_ID"],
                requirement_bindings_fingerprint=raw_kv["REQUIREMENT_BINDINGS_FINGERPRINT"],
            )
        except ContinuityStateValidationError as exc:
            raise ReviewHeaderParseError(
                f"Malformed roadmap audit evidence: {exc}",
                MergeGateReason.ROADMAP_IDENTITY_MISMATCH,
            ) from exc

    return {
        "status": status,
        "approved": approved,
        "auto_merge_eligible": auto_merge_eligible,
        "reviewed_task_head_sha": reviewed_task_head,
        "reviewed_base_main_sha": reviewed_base_main,
        "task_artifact_blob_sha": task_artifact_blob_sha,
        "roadmap_audit": roadmap_audit,
    }


@dataclass(frozen=True)
class MergeReceipt:
    """Immutable record of an executed or attempted reviewed-head merge."""
    task_id: str
    reviewed_task_head_sha: str
    reviewed_base_main_sha: str
    pre_merge_main_sha: str
    post_merge_main_sha: str
    merge_method: str = "FAST_FORWARD"
    force_update: bool = False
    auto_merge: bool = True
    gate_reason: str = "PASS_ELIGIBLE"
    post_merge_identity_verified: bool = True
    schema_version: str = "1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "reviewed_task_head_sha": self.reviewed_task_head_sha,
            "reviewed_base_main_sha": self.reviewed_base_main_sha,
            "pre_merge_main_sha": self.pre_merge_main_sha,
            "post_merge_main_sha": self.post_merge_main_sha,
            "merge_method": self.merge_method,
            "force_update": self.force_update,
            "auto_merge": self.auto_merge,
            "gate_reason": self.gate_reason,
            "post_merge_identity_verified": self.post_merge_identity_verified,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


__all__ = [
    "MergeGateReason",
    "RoadmapReviewAudit",
    "ReviewHeaderParseError",
    "ReviewedMergeInput",
    "MergeGateDecision",
    "MergeReceipt",
    "evaluate_merge_gate",
    "parse_review_header",
]
