"""Provider-neutral worker failure classification and next-action model (TASK-087 / ADR-065).

Defines closed failure classes, deterministic single-action mappings, and pure
classification over bounded execution evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Sequence

from src.aios_bridge.continuity.errors import ContinuityStateValidationError

_SHA_RE = re.compile(r"\A[0-9a-f]{40}\Z")
_TOKEN_RE = re.compile(r"\A[A-Z][A-Z0-9_]{0,63}\Z")

_REQUIRED_EVIDENCE_FIELDS = frozenset({
    "failure_class",
    "next_action",
    "human_guidance",
    "pre_head_sha",
    "post_head_sha",
    "dirty_paths",
    "zero_worktree_delta",
    "terminal_status",
    "diagnostic_code",
    "is_known_stopped",
    "executor_outcome",
    "final_agent_message_observed",
})

_VALID_TERMINAL_STATUSES = frozenset({
    "EXITED_ZERO",
    "EXITED_NONZERO",
    "TIMED_OUT",
    "FAILED_TO_START",
    "INTERRUPTED",
})


class WorkerFailureClass(str, Enum):
    """Closed vocabulary of worker failure classifications."""

    CLEAN_NO_WORKTREE_DELTA = "CLEAN_NO_WORKTREE_DELTA"
    CLEAN_TIMEOUT = "CLEAN_TIMEOUT"
    DIRTY_TIMEOUT_RECOVERY_REQUIRED = "DIRTY_TIMEOUT_RECOVERY_REQUIRED"
    PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE = "PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE"


class WorkerNextAction(str, Enum):
    """Closed, deterministic next-action machine authority for worker failures."""

    HUMAN_SELECT_REPLACEMENT_EXECUTOR_IF_PROVEN_SAFE = (
        "HUMAN_SELECT_REPLACEMENT_EXECUTOR_IF_PROVEN_SAFE"
    )
    HUMAN_DECISION_REQUIRED_CLEAN_TIMEOUT = (
        "HUMAN_DECISION_REQUIRED_CLEAN_TIMEOUT"
    )
    RECOVERY_REQUIRED_PRESERVED_DELTA = "RECOVERY_REQUIRED_PRESERVED_DELTA"


FAILURE_CLASS_TO_NEXT_ACTION: dict[WorkerFailureClass, WorkerNextAction] = {
    WorkerFailureClass.CLEAN_NO_WORKTREE_DELTA: (
        WorkerNextAction.HUMAN_SELECT_REPLACEMENT_EXECUTOR_IF_PROVEN_SAFE
    ),
    WorkerFailureClass.CLEAN_TIMEOUT: (
        WorkerNextAction.HUMAN_DECISION_REQUIRED_CLEAN_TIMEOUT
    ),
    WorkerFailureClass.DIRTY_TIMEOUT_RECOVERY_REQUIRED: (
        WorkerNextAction.RECOVERY_REQUIRED_PRESERVED_DELTA
    ),
    WorkerFailureClass.PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE: (
        WorkerNextAction.RECOVERY_REQUIRED_PRESERVED_DELTA
    ),
}

NEXT_ACTION_TO_HUMAN_TEXT: dict[WorkerNextAction, str] = {
    WorkerNextAction.HUMAN_SELECT_REPLACEMENT_EXECUTOR_IF_PROVEN_SAFE: (
        "Human select replacement executor if proven safe"
    ),
    WorkerNextAction.HUMAN_DECISION_REQUIRED_CLEAN_TIMEOUT: (
        "Human decision required: clean timeout observed without worktree modifications"
    ),
    WorkerNextAction.RECOVERY_REQUIRED_PRESERVED_DELTA: (
        "Recovery required: preserved worktree modifications or commit delta detected"
    ),
}


class WorkerFailureError(ContinuityStateValidationError):
    """Raised when evidence for worker failure classification is invalid or malformed."""


def _validate_sha(sha: object, name: str) -> str:
    if type(sha) is not str or _SHA_RE.fullmatch(sha) is None:
        raise WorkerFailureError(f"{name} must be an exact lowercase 40-hex SHA")
    return sha


def _validate_token(tok: object, name: str) -> str:
    if type(tok) is not str or _TOKEN_RE.fullmatch(tok) is None:
        raise WorkerFailureError(f"{name} must be a valid uppercase token")
    return tok


@dataclass(frozen=True, slots=True)
class WorkerFailureEvidence:
    """Structured, bounded evidence of an execution failure and its classified next action."""

    failure_class: WorkerFailureClass
    next_action: WorkerNextAction
    human_guidance: str
    pre_head_sha: str
    post_head_sha: str
    dirty_paths: tuple[str, ...]
    zero_worktree_delta: bool
    terminal_status: str
    diagnostic_code: str
    is_known_stopped: bool = True
    executor_outcome: str = "UNKNOWN"
    final_agent_message_observed: str = "UNKNOWN"

    def __post_init__(self) -> None:
        if not isinstance(self.failure_class, WorkerFailureClass):
            raise WorkerFailureError(f"Invalid failure_class: {self.failure_class!r}")
        if not isinstance(self.next_action, WorkerNextAction):
            raise WorkerFailureError(f"Invalid next_action: {self.next_action!r}")
        if self.next_action != FAILURE_CLASS_TO_NEXT_ACTION[self.failure_class]:
            raise WorkerFailureError(
                f"next_action {self.next_action} does not match expected single mapping for {self.failure_class}"
            )
        if self.human_guidance != NEXT_ACTION_TO_HUMAN_TEXT[self.next_action]:
            raise WorkerFailureError("human_guidance does not match deterministic text mapping")
        _validate_sha(self.pre_head_sha, "pre_head_sha")
        _validate_sha(self.post_head_sha, "post_head_sha")
        _validate_token(self.terminal_status, "terminal_status")
        _validate_token(self.diagnostic_code, "diagnostic_code")
        if type(self.zero_worktree_delta) is not bool:
            raise WorkerFailureError("zero_worktree_delta must be a bool")
        if type(self.is_known_stopped) is not bool or self.is_known_stopped is not True:
            raise WorkerFailureError("is_known_stopped must be exact True bool")

    def to_dict(self) -> dict[str, Any]:
        return {
            "failure_class": self.failure_class.value,
            "next_action": self.next_action.value,
            "human_guidance": self.human_guidance,
            "pre_head_sha": self.pre_head_sha,
            "post_head_sha": self.post_head_sha,
            "dirty_paths": list(self.dirty_paths),
            "zero_worktree_delta": self.zero_worktree_delta,
            "terminal_status": self.terminal_status,
            "diagnostic_code": self.diagnostic_code,
            "is_known_stopped": self.is_known_stopped,
            "executor_outcome": self.executor_outcome,
            "final_agent_message_observed": self.final_agent_message_observed,
        }

    @classmethod
    def from_dict(cls, data: object) -> WorkerFailureEvidence:
        if type(data) is not dict:
            raise WorkerFailureError("WorkerFailureEvidence data must be an exact dict")
        if set(data.keys()) != _REQUIRED_EVIDENCE_FIELDS:
            extra = set(data.keys()) - _REQUIRED_EVIDENCE_FIELDS
            missing = _REQUIRED_EVIDENCE_FIELDS - set(data.keys())
            raise WorkerFailureError(
                f"WorkerFailureEvidence keys mismatch: extra={extra}, missing={missing}"
            )

        for str_field in (
            "failure_class",
            "next_action",
            "human_guidance",
            "pre_head_sha",
            "post_head_sha",
            "terminal_status",
            "diagnostic_code",
            "executor_outcome",
            "final_agent_message_observed",
        ):
            if type(data[str_field]) is not str:
                raise WorkerFailureError(f"Field '{str_field}' must be an exact str")

        for bool_field in ("zero_worktree_delta", "is_known_stopped"):
            if type(data[bool_field]) is not bool:
                raise WorkerFailureError(f"Field '{bool_field}' must be an exact bool")

        if type(data["dirty_paths"]) is not list:
            raise WorkerFailureError("Field 'dirty_paths' must be an exact list")
        for p in data["dirty_paths"]:
            if type(p) is not str:
                raise WorkerFailureError("Each element in dirty_paths must be an exact str")

        if data["is_known_stopped"] is not True:
            raise WorkerFailureError("is_known_stopped must be exact True")

        try:
            fc = WorkerFailureClass(data["failure_class"])
        except ValueError:
            raise WorkerFailureError(f"Invalid failure_class: {data['failure_class']!r}")

        try:
            na = WorkerNextAction(data["next_action"])
        except ValueError:
            raise WorkerFailureError(f"Invalid next_action: {data['next_action']!r}")

        if na != FAILURE_CLASS_TO_NEXT_ACTION[fc]:
            raise WorkerFailureError(
                f"next_action {na} does not match expected single mapping for {fc}"
            )

        if data["human_guidance"] != NEXT_ACTION_TO_HUMAN_TEXT[na]:
            raise WorkerFailureError("human_guidance does not match deterministic text mapping")

        pre_head = _validate_sha(data["pre_head_sha"], "pre_head_sha")
        post_head = _validate_sha(data["post_head_sha"], "post_head_sha")
        term_status = _validate_token(data["terminal_status"], "terminal_status")
        diag_code = _validate_token(data["diagnostic_code"], "diagnostic_code")

        dirty_paths = tuple(data["dirty_paths"])
        zero_delta = data["zero_worktree_delta"]
        expected_zero = (pre_head == post_head and len(dirty_paths) == 0)
        if zero_delta != expected_zero:
            raise WorkerFailureError("zero_worktree_delta inconsistent with pre/post SHA and dirty paths")

        if fc == WorkerFailureClass.CLEAN_NO_WORKTREE_DELTA and not zero_delta:
            raise WorkerFailureError("CLEAN_NO_WORKTREE_DELTA requires zero_worktree_delta is True")
        if fc == WorkerFailureClass.CLEAN_TIMEOUT and (term_status != "TIMED_OUT" or not zero_delta):
            raise WorkerFailureError("CLEAN_TIMEOUT requires TIMED_OUT and zero_worktree_delta is True")
        if fc == WorkerFailureClass.DIRTY_TIMEOUT_RECOVERY_REQUIRED and (term_status != "TIMED_OUT" or zero_delta):
            raise WorkerFailureError("DIRTY_TIMEOUT_RECOVERY_REQUIRED requires TIMED_OUT and non-zero worktree delta")
        if fc == WorkerFailureClass.PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE and (term_status != "EXITED_NONZERO" or zero_delta):
            raise WorkerFailureError("PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE requires EXITED_NONZERO and non-zero worktree delta")

        return cls(
            failure_class=fc,
            next_action=na,
            human_guidance=data["human_guidance"],
            pre_head_sha=pre_head,
            post_head_sha=post_head,
            dirty_paths=dirty_paths,
            zero_worktree_delta=zero_delta,
            terminal_status=term_status,
            diagnostic_code=diag_code,
            is_known_stopped=True,
            executor_outcome=data["executor_outcome"],
            final_agent_message_observed=data["final_agent_message_observed"],
        )


def classify_worker_failure(
    *,
    terminal_status: str,
    pre_head_sha: str,
    post_head_sha: str,
    dirty_paths: Sequence[str] = (),
    allowed_paths: Sequence[str] | None = None,
    is_known_stopped: bool = True,
    executor_outcome: str = "UNKNOWN",
    final_agent_message_observed: str = "UNKNOWN",
    diagnostic_code: str = "JSON_EVENT_STREAM",
) -> WorkerFailureEvidence:
    """Pure classifier consuming only bounded deterministic evidence.

    Rules (TASK-087 / ADR-065):
      1. is_known_stopped must be True (cannot classify active or non-stopped execution).
      2. terminal_status must be a supported closed status.
      3. CLEAN_TIMEOUT:
         - terminal_status == 'TIMED_OUT', is_known_stopped is True, zero delta (post_head == pre_head and dirty_paths == ()).
         - next_action = HUMAN_DECISION_REQUIRED_CLEAN_TIMEOUT.
      4. DIRTY_TIMEOUT_RECOVERY_REQUIRED:
         - terminal_status == 'TIMED_OUT', is_known_stopped is True, and preserved delta exists (dirty paths exist OR post_head != pre_head).
         - next_action = RECOVERY_REQUIRED_PRESERVED_DELTA.
      5. CLEAN_NO_WORKTREE_DELTA:
         - known stopped/terminal execution, zero delta (post_head == pre_head and dirty_paths == ()).
         - next_action = HUMAN_SELECT_REPLACEMENT_EXECUTOR_IF_PROVEN_SAFE.
      6. PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE:
         - terminal_status == 'EXITED_NONZERO', is_known_stopped is True, dirty paths exist,
           allowed_paths is provided, and all changed paths pass allowed_paths bounds.
         - next_action = RECOVERY_REQUIRED_PRESERVED_DELTA.
      7. Unknown or invalid combinations fail closed by raising WorkerFailureError.
    """
    if type(is_known_stopped) is not bool or is_known_stopped is not True:
        raise WorkerFailureError("classify_worker_failure requires is_known_stopped is True")

    pre_head = _validate_sha(pre_head_sha, "pre_head_sha")
    post_head = _validate_sha(post_head_sha, "post_head_sha")

    if type(dirty_paths) not in (list, tuple):
        raise WorkerFailureError("dirty_paths must be a list or tuple")
    for p in dirty_paths:
        if type(p) is not str:
            raise WorkerFailureError("Each dirty path must be an exact str")

    cleaned_dirty = tuple(str(p).replace("\\", "/") for p in dirty_paths)
    zero_delta = (pre_head == post_head) and (len(cleaned_dirty) == 0)

    term_status = _validate_token(terminal_status.strip().upper(), "terminal_status")
    if term_status not in _VALID_TERMINAL_STATUSES:
        raise WorkerFailureError(f"Unsupported or unknown terminal_status '{terminal_status}'")
    diag_code = _validate_token(diagnostic_code.strip().upper(), "diagnostic_code")

    if term_status == "TIMED_OUT":
        if zero_delta:
            failure_class = WorkerFailureClass.CLEAN_TIMEOUT
        else:
            failure_class = WorkerFailureClass.DIRTY_TIMEOUT_RECOVERY_REQUIRED
    elif zero_delta:
        if term_status in ("EXITED_ZERO", "FAILED_TO_START", "INTERRUPTED", "EXITED_NONZERO"):
            failure_class = WorkerFailureClass.CLEAN_NO_WORKTREE_DELTA
        else:
            raise WorkerFailureError(f"Cannot classify zero delta for terminal status '{term_status}'")
    elif term_status == "EXITED_NONZERO":
        if allowed_paths is None:
            raise WorkerFailureError("allowed_paths is required to classify non-zero delta EXITED_NONZERO")
        if not bool(cleaned_dirty):
            raise WorkerFailureError("PRODUCTIVE_NONZERO requires dirty paths delta")
        normalized_allowed = {str(p).replace("\\", "/") for p in allowed_paths}
        out_of_scope = [p for p in cleaned_dirty if p not in normalized_allowed]
        if out_of_scope:
            raise WorkerFailureError(f"Out of scope dirty paths cannot be productive recovery candidate: {out_of_scope}")
        failure_class = WorkerFailureClass.PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE
    elif term_status == "EXITED_ZERO":
        raise WorkerFailureError("EXITED_ZERO with non-zero worktree delta is not a failure class")
    else:
        raise WorkerFailureError(f"Cannot classify non-zero delta for terminal status '{term_status}'")

    next_action = FAILURE_CLASS_TO_NEXT_ACTION[failure_class]
    human_guidance = NEXT_ACTION_TO_HUMAN_TEXT[next_action]

    return WorkerFailureEvidence(
        failure_class=failure_class,
        next_action=next_action,
        human_guidance=human_guidance,
        pre_head_sha=pre_head,
        post_head_sha=post_head,
        dirty_paths=cleaned_dirty,
        zero_worktree_delta=zero_delta,
        terminal_status=term_status,
        diagnostic_code=diag_code,
        is_known_stopped=True,
        executor_outcome=str(executor_outcome),
        final_agent_message_observed=str(final_agent_message_observed),
    )


__all__ = [
    "FAILURE_CLASS_TO_NEXT_ACTION",
    "NEXT_ACTION_TO_HUMAN_TEXT",
    "WorkerFailureClass",
    "WorkerFailureError",
    "WorkerFailureEvidence",
    "WorkerNextAction",
    "classify_worker_failure",
]
