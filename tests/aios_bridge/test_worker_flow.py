"""Targeted unit and integration tests for AIOS Transactional Worker Flow (TASK-086 / ADR-061 / ADR-062)."""
from __future__ import annotations

from pathlib import Path
import pytest

from src.aios_bridge.worker_flow import (
    FixExecutionMode,
    WorkerAction,
    WorkerAdapter,
    WorkerFlowCoordinator,
    WorkerFlowResult,
    WorkerIntent,
    extract_fix_execution_mode,
)


def test_worker_flow_module_created_and_exports_expected_types() -> None:
    """Proof: WORKER_FLOW_MODULE_CREATED: PASS."""
    assert issubclass(FixExecutionMode, str)
    assert FixExecutionMode.IMPLEMENTATION.value == "IMPLEMENTATION"
    assert FixExecutionMode.EVIDENCE_REFRESH.value == "EVIDENCE_REFRESH"
    assert len(FixExecutionMode) == 2  # Closed FIX mode

    assert issubclass(WorkerAction, str)
    assert WorkerAction.RUN.value == "RUN"
    assert WorkerAction.FIX.value == "FIX"
    assert WorkerAction.STATUS.value == "STATUS"

    assert issubclass(WorkerAdapter, str)
    assert WorkerAdapter.CODEX.value == "codex"
    assert WorkerAdapter.ANTIGRAVITY.value == "antigravity"


def test_fix_execution_mode_closed_and_legacy_default() -> None:
    """Proof: FIX_MODE_CLOSED: PASS & LEGACY_FIX_DEFAULT_IMPLEMENTATION: PASS."""
    # Missing / None / empty string defaults to IMPLEMENTATION
    assert extract_fix_execution_mode(None) == FixExecutionMode.IMPLEMENTATION
    assert extract_fix_execution_mode("") == FixExecutionMode.IMPLEMENTATION
    assert extract_fix_execution_mode("Some review without fix execution mode marker.") == FixExecutionMode.IMPLEMENTATION

    # Explicit valid markers
    assert extract_fix_execution_mode("FIX_EXECUTION_MODE: IMPLEMENTATION") == FixExecutionMode.IMPLEMENTATION
    assert extract_fix_execution_mode("fix_execution_mode: implementation") == FixExecutionMode.IMPLEMENTATION
    assert extract_fix_execution_mode("FIX_EXECUTION_MODE: EVIDENCE_REFRESH") == FixExecutionMode.EVIDENCE_REFRESH
    assert extract_fix_execution_mode("fix_execution_mode: evidence_refresh") == FixExecutionMode.EVIDENCE_REFRESH


def test_unknown_fix_mode_fails_closed() -> None:
    """Proof: UNKNOWN_FIX_MODE_FAILS_CLOSED: PASS."""
    with pytest.raises(ValueError, match="Unknown or unsupported FIX_EXECUTION_MODE"):
        extract_fix_execution_mode("FIX_EXECUTION_MODE: UNKNOWN_MODE")

    with pytest.raises(ValueError, match="Unknown or unsupported FIX_EXECUTION_MODE"):
        extract_fix_execution_mode("FIX_EXECUTION_MODE: RETRY")


def test_conflicting_fix_mode_fails_closed() -> None:
    """Proof: CONFLICTING_FIX_MODE_FAILS_CLOSED: PASS."""
    review_with_conflicts = (
        "# REVIEW\n"
        "FIX_EXECUTION_MODE: IMPLEMENTATION\n"
        "FIX_EXECUTION_MODE: EVIDENCE_REFRESH\n"
    )
    with pytest.raises(ValueError, match="Conflicting FIX_EXECUTION_MODE markers"):
        extract_fix_execution_mode(review_with_conflicts)


def test_status_transaction_syncs_and_checks_pending_non_authorizing(tmp_path: Path) -> None:
    """Proof: STATUS_REMAINS_NON_AUTHORIZING: PASS."""
    invoked_cmds: list[list[str]] = []

    def fake_run_bridge_cmd(args: list[str]) -> int:
        invoked_cmds.append(args)
        return 0

    coordinator = WorkerFlowCoordinator(
        repo_root=tmp_path,
        run_bridge_cmd_fn=fake_run_bridge_cmd,
    )
    intent = WorkerIntent(
        action=WorkerAction.STATUS,
        task_id="TASK-086",
        task_num=86,
        adapter=WorkerAdapter.CODEX,
    )
    result = coordinator.execute_transaction(intent)

    assert result.status == "SYNCED"
    assert result.returncode == 0
    assert invoked_cmds == [["sync"], ["pending"]]


def test_run_executes_handoff_without_redundant_pre_sync_codex(tmp_path: Path) -> None:
    """Proof: RUN_WITHOUT_STATUS_AUTO_SYNCS: PASS & RUN_NO_REDUNDANT_PRE_SYNC: PASS."""
    invoked_cmds: list[list[str]] = []

    def fake_run_bridge_cmd(args: list[str]) -> int:
        invoked_cmds.append(args)
        return 0

    coordinator = WorkerFlowCoordinator(
        repo_root=tmp_path,
        run_bridge_cmd_fn=fake_run_bridge_cmd,
    )
    intent = WorkerIntent(
        action=WorkerAction.RUN,
        task_id="TASK-086",
        task_num=86,
        adapter=WorkerAdapter.CODEX,
    )
    result = coordinator.execute_transaction(intent)

    assert result.status == "PUBLISHED"
    assert result.executor_invocations == 1
    assert result.returncode == 0
    # Handoff directly without redundant pre-sync!
    assert invoked_cmds == [
        ["handoff", "86", "--action", "run", "--executor", "codex"],
        ["execute", "86"],
    ]


def test_run_antigravity_stops_at_handoff(tmp_path: Path) -> None:
    """Proof: IMPLEMENTATION_MODE_ANTIGRAVITY_CONTINUATION_PRESERVED: PASS."""
    invoked_cmds: list[list[str]] = []

    def fake_run_bridge_cmd(args: list[str]) -> int:
        invoked_cmds.append(args)
        return 0

    coordinator = WorkerFlowCoordinator(
        repo_root=tmp_path,
        run_bridge_cmd_fn=fake_run_bridge_cmd,
    )
    intent = WorkerIntent(
        action=WorkerAction.RUN,
        task_id="TASK-086",
        task_num=86,
        adapter=WorkerAdapter.ANTIGRAVITY,
    )
    result = coordinator.execute_transaction(intent)

    assert result.status == "AUTHORIZED"
    assert result.executor_invocations == 0
    assert result.returncode == 0
    assert invoked_cmds == [
        ["handoff", "86", "--action", "run", "--executor", "antigravity"],
    ]


def test_fix_executes_handoff_without_redundant_pre_sync_implementation_codex(tmp_path: Path) -> None:
    """Proof: FIX_WITHOUT_STATUS_AUTO_SYNCS: PASS & FIX_NO_REDUNDANT_PRE_SYNC: PASS & LATEST_EXACT_REVIEW_IS_SINGLE_MODE_AUTHORITY: PASS."""
    invoked_cmds: list[list[str]] = []

    def fake_run_bridge_cmd(args: list[str]) -> int:
        invoked_cmds.append(args)
        return 0

    def fake_load_auth(task_num: int) -> dict | None:
        return {
            "status": "ACTIVE",
            "action": "FIX",
            "fix_execution_mode": "IMPLEMENTATION",
        }

    coordinator = WorkerFlowCoordinator(
        repo_root=tmp_path,
        run_bridge_cmd_fn=fake_run_bridge_cmd,
        load_auth_fn=fake_load_auth,
    )
    intent = WorkerIntent(
        action=WorkerAction.FIX,
        task_id="TASK-086",
        task_num=86,
        adapter=WorkerAdapter.CODEX,
    )
    result = coordinator.execute_transaction(intent)

    assert result.status == "PUBLISHED"
    assert result.fix_execution_mode == "IMPLEMENTATION"
    assert result.executor_invocations == 1
    assert result.returncode == 0
    assert invoked_cmds == [
        ["handoff", "86", "--action", "fix", "--executor", "codex"],
        ["execute", "86"],
    ]


def test_handoff_failure_blocks_continuation(tmp_path: Path) -> None:
    """Proof: SYNC_FAILURE_PREVENTS_AUTHORIZATION: PASS."""
    invoked_cmds: list[list[str]] = []

    def fake_run_bridge_cmd(args: list[str]) -> int:
        invoked_cmds.append(args)
        if args[:2] == ["handoff", "86"]:
            return 1  # Handoff (pre-authority sync) fails
        return 0

    coordinator = WorkerFlowCoordinator(
        repo_root=tmp_path,
        run_bridge_cmd_fn=fake_run_bridge_cmd,
    )
    intent = WorkerIntent(
        action=WorkerAction.RUN,
        task_id="TASK-086",
        task_num=86,
        adapter=WorkerAdapter.CODEX,
    )
    result = coordinator.execute_transaction(intent)

    assert result.status == "HANDOFF_FAILED"
    assert result.returncode == 1
    assert invoked_cmds == [["handoff", "86", "--action", "run", "--executor", "codex"]]


def test_evidence_refresh_skips_executor_and_publishes_directly(tmp_path: Path) -> None:
    """Proof: EVIDENCE_REFRESH_SKIPS_EXECUTOR: PASS & EVIDENCE_REFRESH_PUBLISHES_THROUGH_NORMAL_WORKER_SURFACE: PASS & COORDINATOR_MODE_EQUALS_AUTHORIZED_MODE: PASS."""
    invoked_cmds: list[list[str]] = []

    def fake_run_bridge_cmd(args: list[str]) -> int:
        invoked_cmds.append(args)
        return 0

    def fake_load_auth(task_num: int) -> dict | None:
        return {
            "status": "ACTIVE",
            "action": "FIX",
            "fix_execution_mode": "EVIDENCE_REFRESH",
        }

    coordinator = WorkerFlowCoordinator(
        repo_root=tmp_path,
        run_bridge_cmd_fn=fake_run_bridge_cmd,
        load_auth_fn=fake_load_auth,
    )
    intent = WorkerIntent(
        action=WorkerAction.FIX,
        task_id="TASK-086",
        task_num=86,
        adapter=WorkerAdapter.CODEX,
    )
    result = coordinator.execute_transaction(intent)

    assert result.status == "PUBLISHED"
    assert result.fix_execution_mode == "EVIDENCE_REFRESH"
    assert result.executor_invocations == 0  # EXECUTOR SKIPPED
    assert result.returncode == 0

    assert len(invoked_cmds) == 2
    assert invoked_cmds[0] == ["handoff", "86", "--action", "fix", "--executor", "codex"]
    # Publish command invoked directly instead of execute!
    assert invoked_cmds[1][0] == "publish"
    assert invoked_cmds[1][1] == "86"
    assert "--action" in invoked_cmds[1]
    assert "fix" in invoked_cmds[1]


def test_fix_mode_drift_or_invalid_auth_fails_closed(tmp_path: Path) -> None:
    """Proof: MODE_DRIFT_FAILS_CLOSED: PASS."""
    def fake_run_bridge_cmd(args: list[str]) -> int:
        return 0

    # Test case 1: auth missing
    coordinator = WorkerFlowCoordinator(
        repo_root=tmp_path,
        run_bridge_cmd_fn=fake_run_bridge_cmd,
        load_auth_fn=lambda t: None,
    )
    intent = WorkerIntent(
        action=WorkerAction.FIX,
        task_id="TASK-086",
        task_num=86,
        adapter=WorkerAdapter.CODEX,
    )
    res = coordinator.execute_transaction(intent)
    assert res.status == "AUTH_INVALID"
    assert res.returncode == 1

    # Test case 2: unknown fix execution mode in auth
    coordinator_bad_mode = WorkerFlowCoordinator(
        repo_root=tmp_path,
        run_bridge_cmd_fn=fake_run_bridge_cmd,
        load_auth_fn=lambda t: {"status": "ACTIVE", "action": "FIX", "fix_execution_mode": "CORRUPTED_MODE"},
    )
    res_bad = coordinator_bad_mode.execute_transaction(intent)
    assert res_bad.status == "INVALID_FIX_MODE"
    assert res_bad.returncode == 1
