"""Deterministic reviewed-head merge gate and review contract parser (ADR-042 / TASK-069)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import re
from typing import Any

from src.aios_bridge.continuity.errors import ContinuityStateValidationError


_SHA_RE = re.compile(r"\A[0-9a-f]{40}\Z")
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

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, str) or not _TASK_ID_RE.fullmatch(self.task_id):
            raise ContinuityStateValidationError(
                f"task_id must be canonical TASK-NNN: got {self.task_id!r}"
            )
        if not isinstance(self.review_status, str) or not self.review_status.strip():
            raise ContinuityStateValidationError(
                f"review_status must be non-empty string: got {self.review_status!r}"
            )
        if type(self.review_approved) is not bool:
            raise ContinuityStateValidationError(
                f"review_approved must be exact bool: got {self.review_approved!r}"
            )
        if type(self.auto_merge_eligible) is not bool:
            raise ContinuityStateValidationError(
                f"auto_merge_eligible must be exact bool: got {self.auto_merge_eligible!r}"
            )

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
    Parse strict machine-readable review header key-values.
    Fails closed on missing required keys, duplicate keys, or malformed YES/NO values.
    """
    if not isinstance(review_text, str) or not review_text.strip():
        raise ContinuityStateValidationError("review_text must be non-empty string")

    seen_raw_keys: set[str] = set()
    raw_kv: dict[str, str] = {}

    for raw_line in review_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("```"):
            continue

        match = _KEY_VALUE_LINE_RE.match(line)
        if match:
            key, val = match.group(1), match.group(2).strip()
            # Remove any trailing inline comment or backticks if present
            if val.startswith("`") and val.endswith("`") and len(val) >= 2:
                val = val[1:-1].strip()
            if key in seen_raw_keys:
                raise ContinuityStateValidationError(
                    f"Duplicate required/header key rejected: {key}"
                )
            seen_raw_keys.add(key)
            raw_kv[key] = val

    # Resolve required STATUS
    if "STATUS" not in raw_kv:
        raise ContinuityStateValidationError("Missing required review key: STATUS")
    status = raw_kv["STATUS"].upper()

    # Resolve required APPROVED
    if "APPROVED" not in raw_kv:
        raise ContinuityStateValidationError("Missing required review key: APPROVED")
    approved_raw = raw_kv["APPROVED"].upper()
    if approved_raw == "YES":
        approved = True
    elif approved_raw == "NO":
        approved = False
    else:
        raise ContinuityStateValidationError(
            f"Malformed APPROVED value (must be exact YES/NO): got {raw_kv['APPROVED']!r}"
        )

    # Resolve required AUTO_MERGE_ELIGIBLE (or alias AUTO_MERGE_ALLOWED)
    if "AUTO_MERGE_ELIGIBLE" in raw_kv:
        auto_merge_raw = raw_kv["AUTO_MERGE_ELIGIBLE"].upper()
    elif "AUTO_MERGE_ALLOWED" in raw_kv:
        auto_merge_raw = raw_kv["AUTO_MERGE_ALLOWED"].upper()
    else:
        raise ContinuityStateValidationError("Missing required review key: AUTO_MERGE_ELIGIBLE")

    if auto_merge_raw == "YES":
        auto_merge_eligible = True
    elif auto_merge_raw == "NO":
        auto_merge_eligible = False
    else:
        raise ContinuityStateValidationError(
            f"Malformed AUTO_MERGE_ELIGIBLE value (must be exact YES/NO): got {auto_merge_raw!r}"
        )

    # Resolve REVIEWED_TASK_HEAD_SHA (or alias REVIEWED_HEAD_SHA)
    if "REVIEWED_TASK_HEAD_SHA" in raw_kv:
        reviewed_task_head = raw_kv["REVIEWED_TASK_HEAD_SHA"].lower()
    elif "REVIEWED_HEAD_SHA" in raw_kv:
        reviewed_task_head = raw_kv["REVIEWED_HEAD_SHA"].lower()
    else:
        raise ContinuityStateValidationError(
            "Missing required review key: REVIEWED_TASK_HEAD_SHA"
        )

    if not _SHA_RE.fullmatch(reviewed_task_head):
        raise ContinuityStateValidationError(
            f"REVIEWED_TASK_HEAD_SHA must be exact 40-hex lowercase SHA: got {reviewed_task_head!r}"
        )

    # Resolve REVIEWED_BASE_MAIN_SHA (or alias BASE_MAIN_SHA)
    if "REVIEWED_BASE_MAIN_SHA" in raw_kv:
        reviewed_base_main = raw_kv["REVIEWED_BASE_MAIN_SHA"].lower()
    elif "BASE_MAIN_SHA" in raw_kv:
        reviewed_base_main = raw_kv["BASE_MAIN_SHA"].lower()
    else:
        raise ContinuityStateValidationError(
            "Missing required review key: REVIEWED_BASE_MAIN_SHA"
        )

    if not _SHA_RE.fullmatch(reviewed_base_main):
        raise ContinuityStateValidationError(
            f"REVIEWED_BASE_MAIN_SHA must be exact 40-hex lowercase SHA: got {reviewed_base_main!r}"
        )

    return {
        "status": status,
        "approved": approved,
        "auto_merge_eligible": auto_merge_eligible,
        "reviewed_task_head_sha": reviewed_task_head,
        "reviewed_base_main_sha": reviewed_base_main,
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
    "ReviewedMergeInput",
    "MergeGateDecision",
    "MergeReceipt",
    "evaluate_merge_gate",
    "parse_review_header",
]
