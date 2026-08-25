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
        _validate_sha(self.pre_head_sha, "pre_head_sha")
        _validate_sha(self.post_head_sha, "post_head_sha")
        _validate_token(self.terminal_status, "terminal_status")
        _validate_token(self.diagnostic_code, "diagnostic_code")
        if not isinstance(self.zero_worktree_delta, bool):
            raise WorkerFailureError("zero_worktree_delta must be a bool")
        if not isinstance(self.is_known_stopped, bool):
            raise WorkerFailureError("is_known_stopped must be a bool")

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
            raise WorkerFailureError("WorkerFailureEvidence data must be a dict")
        required_fields = {
            "failure_class",
            "next_action",
            "human_guidance",
            "pre_head_sha",
            "post_head_sha",
            "dirty_paths",
            "zero_worktree_delta",
            "terminal_status",
            "diagnostic_code",
        }
        if not required_fields.issubset(data.keys()):
            raise WorkerFailureError(
                f"Missing required fields in WorkerFailureEvidence dict: {required_fields - set(data.keys())}"
            )
        try:
            fc = WorkerFailureClass(data["failure_class"])
            na = WorkerNextAction(data["next_action"])
            dirty_paths = tuple(str(p) for p in data.get("dirty_paths", []))
            return cls(
                failure_class=fc,
                next_action=na,
                human_guidance=str(data["human_guidance"]),
                pre_head_sha=str(data["pre_head_sha"]),
                post_head_sha=str(data["post_head_sha"]),
                dirty_paths=dirty_paths,
                zero_worktree_delta=bool(data["zero_worktree_delta"]),
                terminal_status=str(data["terminal_status"]),
                diagnostic_code=str(data["diagnostic_code"]),
                is_known_stopped=bool(data.get("is_known_stopped", True)),
                executor_outcome=str(data.get("executor_outcome", "UNKNOWN")),
                final_agent_message_observed=str(
                    data.get("final_agent_message_observed", "UNKNOWN")
                ),
            )
        except (ValueError, KeyError, TypeError) as exc:
            raise WorkerFailureError(f"Malformed WorkerFailureEvidence dict: {exc}") from exc


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

    Rules (TASK-087):
      1. CLEAN_TIMEOUT:
         - terminal_status == 'TIMED_OUT', known stopped/terminal, post_head == pre_head, zero dirty paths.
         - next_action = HUMAN_DECISION_REQUIRED_CLEAN_TIMEOUT.
      2. DIRTY_TIMEOUT_RECOVERY_REQUIRED:
         - terminal_status == 'TIMED_OUT', known stopped/terminal, and (dirty paths exist OR post_head != pre_head).
         - next_action = RECOVERY_REQUIRED_PRESERVED_DELTA.
      3. CLEAN_NO_WORKTREE_DELTA:
         - terminal/stopped execution, post_head == pre_head, zero dirty paths.
         - next_action = HUMAN_SELECT_REPLACEMENT_EXECUTOR_IF_PROVEN_SAFE.
      4. PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE:
         - terminal_status == 'EXITED_NONZERO', preserved delta exists (dirty paths or head delta),
           and all changed paths pass allowed_paths bounds (if allowed_paths is given).
         - next_action = RECOVERY_REQUIRED_PRESERVED_DELTA.
         - If changed paths violate allowed_paths, fails closed to DIRTY_TIMEOUT_RECOVERY_REQUIRED.
    """
    pre_head = _validate_sha(pre_head_sha, "pre_head_sha")
    post_head = _validate_sha(post_head_sha, "post_head_sha")
    cleaned_dirty = tuple(str(p).replace("\\", "/") for p in dirty_paths)
    zero_delta = (pre_head == post_head) and (len(cleaned_dirty) == 0)

    term_status = _validate_token(terminal_status.strip().upper(), "terminal_status")
    diag_code = _validate_token(diagnostic_code.strip().upper(), "diagnostic_code")

    if term_status == "TIMED_OUT":
        if zero_delta:
            failure_class = WorkerFailureClass.CLEAN_TIMEOUT
        else:
            failure_class = WorkerFailureClass.DIRTY_TIMEOUT_RECOVERY_REQUIRED
    elif zero_delta:
        failure_class = WorkerFailureClass.CLEAN_NO_WORKTREE_DELTA
    elif term_status == "EXITED_NONZERO":
        # Check if changed paths are strictly within allowed paths
        if allowed_paths is not None:
            normalized_allowed = {str(p).replace("\\", "/") for p in allowed_paths}
            out_of_scope = [p for p in cleaned_dirty if p not in normalized_allowed]
            if out_of_scope:
                # Out-of-scope delta fails closed to recovery required
                failure_class = WorkerFailureClass.DIRTY_TIMEOUT_RECOVERY_REQUIRED
            else:
                failure_class = WorkerFailureClass.PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE
        else:
            failure_class = WorkerFailureClass.PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE
    else:
        # Non-timeout, non-zero-delta general failure
        failure_class = WorkerFailureClass.DIRTY_TIMEOUT_RECOVERY_REQUIRED

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
        is_known_stopped=is_known_stopped,
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
