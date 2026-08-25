import pytest

from src.aios_bridge.blocked_recovery import (
    BLOCKED_REASON_CLEAN_NO_WORKTREE_DELTA,
    BlockedExecutionEvidence,
    BlockedRecoveryError,
    BlockedReplacementPreflight,
    require_blocked_executor_replacement,
)
from src.aios_bridge.continuity.executor import ExecutionOperation


def blocker(operation=ExecutionOperation.RUN):
    return BlockedExecutionEvidence(
        blocked_reason_code=BLOCKED_REASON_CLEAN_NO_WORKTREE_DELTA,
        blocked_executor_id="codex",
        blocked_operation=operation,
        blocked_head_sha="a" * 40,
        blocked_at="2026-08-25T12:00:00+07:00",
        executor_outcome="BLOCKED",
        final_agent_message_observed="YES",
        diagnostic_code="JSON_EVENT_STREAM",
        zero_worktree_delta=True,
    )


def preflight(**overrides):
    values = {
        "prior_authorization_status": "EXECUTION_BLOCKED",
        "blocker": blocker(),
        "replacement_executor_id": "antigravity",
        "explicit_human_selection": True,
        "active_lease_present": False,
        "expected_task_branch": "ai/task-092",
        "current_branch": "ai/task-092",
        "worktree_clean": True,
        "current_head_sha": "a" * 40,
        "remote_head_sha": "a" * 40,
    }
    values.update(overrides)
    return BlockedReplacementPreflight(**values)


def test_clean_noop_blocker_closed_round_trip_has_no_raw_prose():
    evidence = blocker()
    data = evidence.to_dict()
    assert BlockedExecutionEvidence.from_dict(data) == evidence
    assert "final_agent_prose" not in data
    assert "reasoning" not in data


def test_blocked_replacement_requires_explicit_human_zero_delta_exact_head_and_no_lease():
    assert require_blocked_executor_replacement(preflight()) == blocker()
    for change in (
        {"explicit_human_selection": False},
        {"active_lease_present": True},
        {"current_head_sha": "b" * 40},
        {"replacement_executor_id": "codex"},
    ):
        with pytest.raises(BlockedRecoveryError):
            require_blocked_executor_replacement(preflight(**change))


def test_blocked_replacement_fix_review_head_must_match_blocked_head():
    fix_blocker = blocker(ExecutionOperation.FIX)
    with pytest.raises(BlockedRecoveryError):
        require_blocked_executor_replacement(
            preflight(blocker=fix_blocker, reviewed_task_head_sha="b" * 40)
        )
    assert require_blocked_executor_replacement(
        preflight(blocker=fix_blocker, reviewed_task_head_sha="a" * 40)
    ) == fix_blocker

