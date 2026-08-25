"""Closed evidence and pure preconditions for explicit blocked-executor replacement."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.executor import ExecutionOperation


BLOCKED_REASON_CLEAN_NO_WORKTREE_DELTA = "CLEAN_NO_WORKTREE_DELTA"
_SHA_RE = re.compile(r"\A[0-9a-f]{40}\Z")
_ACTOR_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
_TOKEN_RE = re.compile(r"\A[A-Z][A-Z0-9_]{0,63}\Z")


class BlockedRecoveryError(ContinuityStateValidationError):
    """Malformed blocker evidence or unsafe replacement precondition."""


def _error(message: str) -> BlockedRecoveryError:
    return BlockedRecoveryError(message)


def _actor(value: object, name: str) -> str:
    if type(value) is not str or _ACTOR_RE.fullmatch(value) is None:
        raise _error(f"{name} must be a bounded canonical actor ID")
    return value


def _token(value: object, name: str) -> str:
    if type(value) is not str or _TOKEN_RE.fullmatch(value) is None:
        raise _error(f"{name} must be a canonical uppercase token")
    return value


@dataclass(frozen=True, slots=True)
class BlockedExecutionEvidence:
    blocked_reason_code: str
    blocked_executor_id: str
    blocked_operation: ExecutionOperation
    blocked_head_sha: str
    blocked_at: str
    executor_outcome: str
    final_agent_message_observed: str
    diagnostic_code: str
    zero_worktree_delta: bool

    def __post_init__(self) -> None:
        if self.blocked_reason_code != BLOCKED_REASON_CLEAN_NO_WORKTREE_DELTA:
            raise _error("unsupported blocked_reason_code")
        _actor(self.blocked_executor_id, "blocked_executor_id")
        if type(self.blocked_operation) is not ExecutionOperation:
            raise _error("blocked_operation must be an exact ExecutionOperation")
        if type(self.blocked_head_sha) is not str or _SHA_RE.fullmatch(self.blocked_head_sha) is None:
            raise _error("blocked_head_sha must be an exact lowercase 40-hex SHA")
        if type(self.blocked_at) is not str or not self.blocked_at or self.blocked_at != self.blocked_at.strip() or len(self.blocked_at) > 128:
            raise _error("blocked_at must be bounded exact text")
        _token(self.executor_outcome, "executor_outcome")
        _token(self.final_agent_message_observed, "final_agent_message_observed")
        _token(self.diagnostic_code, "diagnostic_code")
        if self.zero_worktree_delta is not True:
            raise _error("clean no-op blocker must prove zero_worktree_delta=true")

    def to_dict(self) -> dict[str, Any]:
        return {
            "blocked_at": self.blocked_at,
            "blocked_executor_id": self.blocked_executor_id,
            "blocked_head_sha": self.blocked_head_sha,
            "blocked_operation": self.blocked_operation.value,
            "blocked_reason_code": self.blocked_reason_code,
            "diagnostic_code": self.diagnostic_code,
            "executor_outcome": self.executor_outcome,
            "final_agent_message_observed": self.final_agent_message_observed,
            "zero_worktree_delta": self.zero_worktree_delta,
        }

    @classmethod
    def from_dict(cls, data: object) -> "BlockedExecutionEvidence":
        fields = {
            "blocked_at", "blocked_executor_id", "blocked_head_sha", "blocked_operation",
            "blocked_reason_code", "diagnostic_code", "executor_outcome",
            "final_agent_message_observed", "zero_worktree_delta",
        }
        if type(data) is not dict or set(data) != fields:
            raise _error("blocked execution evidence must contain the exact field set")
        try:
            return cls(
                blocked_reason_code=data["blocked_reason_code"],
                blocked_executor_id=data["blocked_executor_id"],
                blocked_operation=ExecutionOperation(data["blocked_operation"]),
                blocked_head_sha=data["blocked_head_sha"], blocked_at=data["blocked_at"],
                executor_outcome=data["executor_outcome"],
                final_agent_message_observed=data["final_agent_message_observed"],
                diagnostic_code=data["diagnostic_code"], zero_worktree_delta=data["zero_worktree_delta"],
            )
        except (TypeError, ValueError) as exc:
            raise _error(f"malformed blocked execution evidence: {exc}") from exc


@dataclass(frozen=True, slots=True)
class BlockedReplacementPreflight:
    prior_authorization_status: str
    blocker: BlockedExecutionEvidence
    replacement_executor_id: str
    explicit_human_selection: bool
    active_lease_present: bool
    expected_task_branch: str
    current_branch: str
    worktree_clean: bool
    current_head_sha: str
    remote_head_sha: str | None
    reviewed_task_head_sha: str | None = None

    def __post_init__(self) -> None:
        if type(self.blocker) is not BlockedExecutionEvidence:
            raise _error("blocker must be exact BlockedExecutionEvidence")
        _actor(self.replacement_executor_id, "replacement_executor_id")
        for name in ("explicit_human_selection", "active_lease_present", "worktree_clean"):
            if type(getattr(self, name)) is not bool:
                raise _error(f"{name} must be an exact bool")
        for name in ("expected_task_branch", "current_branch"):
            value = getattr(self, name)
            if type(value) is not str or not value or value != value.strip() or len(value) > 256:
                raise _error(f"{name} must be bounded exact text")
        for name in ("current_head_sha", "remote_head_sha", "reviewed_task_head_sha"):
            value = getattr(self, name)
            if value is not None and (type(value) is not str or _SHA_RE.fullmatch(value) is None):
                raise _error(f"{name} must be exact lowercase 40-hex or None")


def require_blocked_executor_replacement(preflight: BlockedReplacementPreflight) -> BlockedExecutionEvidence:
    """Fail closed unless an explicit Human replacement is anchored to a proven zero-mutation head."""
    if type(preflight) is not BlockedReplacementPreflight:
        raise _error("preflight must be exact BlockedReplacementPreflight")
    blocker = preflight.blocker
    if preflight.prior_authorization_status != "EXECUTION_BLOCKED":
        raise _error("blocked replacement requires prior EXECUTION_BLOCKED authorization")
    if not preflight.explicit_human_selection:
        raise _error("blocked replacement requires explicit Human executor selection")
    if preflight.replacement_executor_id == blocker.blocked_executor_id:
        raise _error("replacement executor must differ from the blocked executor")
    if preflight.active_lease_present:
        raise _error("blocked replacement requires no active lease")
    if preflight.current_branch != preflight.expected_task_branch:
        raise _error("current branch must be the exact task branch")
    if not preflight.worktree_clean:
        raise _error("blocked replacement requires a clean worktree")
    if preflight.current_head_sha != blocker.blocked_head_sha:
        raise _error("current HEAD must match the structured blocked head")
    if preflight.remote_head_sha is not None and preflight.remote_head_sha != blocker.blocked_head_sha:
        raise _error("remote task HEAD must match the structured blocked head")
    if blocker.blocked_operation is ExecutionOperation.FIX and preflight.reviewed_task_head_sha != blocker.blocked_head_sha:
        raise _error("FIX replacement review head must match the structured blocked head")
    return blocker


__all__ = [
    "BLOCKED_REASON_CLEAN_NO_WORKTREE_DELTA", "BlockedExecutionEvidence",
    "BlockedRecoveryError", "BlockedReplacementPreflight", "require_blocked_executor_replacement",
]
