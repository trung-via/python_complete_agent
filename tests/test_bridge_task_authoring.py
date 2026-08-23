from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import bridge
from src.aios_bridge.continuity.executor import (
    ExecutionCapability,
    ExecutionOperation,
)
from src.aios_bridge.executor_automation import parse_executor_automation_markers
from src.aios_bridge.runtime_dispatch import parse_executor_dispatch_policy_marker
from src.aios_bridge.task_authoring import (
    CANONICAL_E4_PUBLISHER_PROFILE,
    ExecutableArtifactPreflight,
    ExecutableArtifactPreflightError,
    preflight_executable_artifact,
    validate_publisher_profile,
)


VALID_BLOB_SHA = "a" * 40


def _sample_dispatch_policy(
    operation: str = "RUN",
    selected_executor: str = "antigravity",
    supported_ops: list[str] | None = None,
    required_caps: list[str] | None = None,
    supported_caps: list[str] | None = None,
) -> dict:
    if supported_ops is None:
        supported_ops = [operation]
    if required_caps is None:
        required_caps = ["FILESYSTEM_WRITE", "LOCAL_GIT", "REPOSITORY_READ", "SHELL", "TEST_EXECUTION"]
    if supported_caps is None:
        supported_caps = ["FILESYSTEM_WRITE", "LOCAL_GIT", "REPOSITORY_READ", "SHELL", "TEST_EXECUTION"]

    return {
        "operation": operation,
        "required_capabilities": required_caps,
        "allow_paid_api": False,
        "candidates": [
            {
                "executor_id": selected_executor,
                "preference_rank": 0,
                "capacity_class": "SUBSCRIPTION",
                "supported_operations": supported_ops,
                "supported_capabilities": supported_caps,
            }
        ],
    }


def _sample_artifact_content(
    task_id: str = "TASK-071",
    operation: str = "RUN",
    selected_executor: str = "antigravity",
    context_refs: list[dict] | None = None,
    allowed_paths: list[str] | None = None,
    policy: dict | None = None,
    extra_lines: list[str] | None = None,
) -> str:
    if context_refs is None:
        context_refs = [{"path": ".ai/decisions/ADR-044.md", "blob_sha": VALID_BLOB_SHA}]
    if allowed_paths is None:
        allowed_paths = ["bridge.py", "src/aios_bridge/task_authoring.py"]
    if policy is None:
        policy = _sample_dispatch_policy(operation=operation, selected_executor=selected_executor)

    lines = [
        f"# {task_id} ? Sample Task",
        "",
        "STATUS: READY",
        "",
        f"EXECUTOR_CONTEXT_REFS_JSON: {json.dumps(context_refs)}",
        f"EXECUTOR_ALLOWED_PATHS_JSON: {json.dumps(allowed_paths)}",
        f"DISPATCH_EXECUTOR_POLICY_JSON: {json.dumps(policy)}",
    ]
    if extra_lines:
        lines.extend(extra_lines)
    return "\n".join(lines)


def test_valid_run_preflight_passes() -> None:
    content = _sample_artifact_content(operation="RUN", selected_executor="antigravity")
    res = preflight_executable_artifact(
        content,
        work_path=".ai/tasks/TASK-071.md",
        operation=ExecutionOperation.RUN,
        selected_executor="antigravity",
    )
    assert isinstance(res, ExecutableArtifactPreflight)
    assert res.operation is ExecutionOperation.RUN
    assert res.selected_executor == "antigravity"
    assert res.work_path == ".ai/tasks/TASK-071.md"
    assert len(res.markers.context_refs) == 1
    assert res.candidate.executor_id == "antigravity"


def test_valid_fix_preflight_passes() -> None:
    content = _sample_artifact_content(
        task_id="REVIEW-071",
        operation="FIX",
        selected_executor="codex",
    )
    res = preflight_executable_artifact(
        content,
        work_path=".ai/reviews/REVIEW-071.md",
        operation=ExecutionOperation.FIX,
        selected_executor="codex",
    )
    assert isinstance(res, ExecutableArtifactPreflight)
    assert res.operation is ExecutionOperation.FIX
    assert res.selected_executor == "codex"
    assert res.work_path == ".ai/reviews/REVIEW-071.md"


def test_existing_marker_parsers_reused() -> None:
    source = inspect.getsource(preflight_executable_artifact)
    assert "parse_executor_automation_markers(" in source
    assert "parse_executor_dispatch_policy_marker(" in source


def test_missing_context_refs_marker_fails_preflight() -> None:
    content = """# TASK-071
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"operation":"RUN","required_capabilities":["SHELL"],"allow_paid_api":false,"candidates":[{"executor_id":"antigravity","preference_rank":0,"capacity_class":"SUBSCRIPTION","supported_operations":["RUN"],"supported_capabilities":["SHELL"]}]}
"""
    with pytest.raises(ExecutableArtifactPreflightError, match="EXECUTOR_CONTEXT_REFS_JSON"):
        preflight_executable_artifact(
            content,
            work_path=".ai/tasks/TASK-071.md",
            operation=ExecutionOperation.RUN,
            selected_executor="antigravity",
        )


def test_missing_allowed_paths_marker_fails_preflight() -> None:
    content = f"""# TASK-071
EXECUTOR_CONTEXT_REFS_JSON: [{{"path":".ai/decisions/ADR-044.md","blob_sha":"{VALID_BLOB_SHA}"}}]
DISPATCH_EXECUTOR_POLICY_JSON: {{"operation":"RUN","required_capabilities":["SHELL"],"allow_paid_api":false,"candidates":[{{"executor_id":"antigravity","preference_rank":0,"capacity_class":"SUBSCRIPTION","supported_operations":["RUN"],"supported_capabilities":["SHELL"]}}]}}
"""
    with pytest.raises(ExecutableArtifactPreflightError, match="EXECUTOR_ALLOWED_PATHS_JSON"):
        preflight_executable_artifact(
            content,
            work_path=".ai/tasks/TASK-071.md",
            operation=ExecutionOperation.RUN,
            selected_executor="antigravity",
        )


def test_missing_dispatch_policy_marker_fails_preflight() -> None:
    content = f"""# TASK-071
EXECUTOR_CONTEXT_REFS_JSON: [{{"path":".ai/decisions/ADR-044.md","blob_sha":"{VALID_BLOB_SHA}"}}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py"]
"""
    with pytest.raises(ExecutableArtifactPreflightError, match="DISPATCH_EXECUTOR_POLICY_JSON"):
        preflight_executable_artifact(
            content,
            work_path=".ai/tasks/TASK-071.md",
            operation=ExecutionOperation.RUN,
            selected_executor="antigravity",
        )


def test_duplicate_marker_fails_preflight() -> None:
    content = _sample_artifact_content()
    # Add duplicate EXECUTOR_ALLOWED_PATHS_JSON
    content += '\nEXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py"]\n'
    with pytest.raises(ExecutableArtifactPreflightError, match="found 2"):
        preflight_executable_artifact(
            content,
            work_path=".ai/tasks/TASK-071.md",
            operation=ExecutionOperation.RUN,
            selected_executor="antigravity",
        )


def test_malformed_marker_json_fails_preflight() -> None:
    content = f"""# TASK-071
EXECUTOR_CONTEXT_REFS_JSON: [not_valid_json]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {{"operation":"RUN","required_capabilities":["SHELL"],"allow_paid_api":false,"candidates":[{{"executor_id":"antigravity","preference_rank":0,"capacity_class":"SUBSCRIPTION","supported_operations":["RUN"],"supported_capabilities":["SHELL"]}}]}}
"""
    with pytest.raises(ExecutableArtifactPreflightError, match="Malformed"):
        preflight_executable_artifact(
            content,
            work_path=".ai/tasks/TASK-071.md",
            operation=ExecutionOperation.RUN,
            selected_executor="antigravity",
        )


def test_operation_mismatch_fails_preflight() -> None:
    content = _sample_artifact_content(operation="RUN", selected_executor="antigravity")
    with pytest.raises(ExecutableArtifactPreflightError, match="mismatches requested operation"):
        preflight_executable_artifact(
            content,
            work_path=".ai/tasks/TASK-071.md",
            operation=ExecutionOperation.FIX,  # requested FIX but artifact declares RUN
            selected_executor="antigravity",
        )


def test_executor_not_declared_fails_preflight() -> None:
    content = _sample_artifact_content(operation="RUN", selected_executor="codex")
    with pytest.raises(ExecutableArtifactPreflightError, match="must appear exactly once in policy candidates"):
        preflight_executable_artifact(
            content,
            work_path=".ai/tasks/TASK-071.md",
            operation=ExecutionOperation.RUN,
            selected_executor="antigravity",  # requested antigravity but policy only lists codex
        )


def test_executor_lacks_supported_operation_fails_preflight() -> None:
    policy = {
        "operation": "RUN",
        "required_capabilities": ["SHELL"],
        "allow_paid_api": False,
        "candidates": [
            {
                "executor_id": "antigravity",
                "preference_rank": 0,
                "capacity_class": "SUBSCRIPTION",
                "supported_operations": ["FIX"],
                "supported_capabilities": ["SHELL"],
            }
        ],
    }
    content = _sample_artifact_content(policy=policy)
    with pytest.raises(ExecutableArtifactPreflightError, match="does not support requested operation"):
        preflight_executable_artifact(
            content,
            work_path=".ai/tasks/TASK-071.md",
            operation=ExecutionOperation.RUN,
            selected_executor="antigravity",
        )


def test_executor_lacks_required_capability_fails_preflight() -> None:
    policy = {
        "operation": "RUN",
        "required_capabilities": ["SHELL", "TEST_EXECUTION"],
        "allow_paid_api": False,
        "candidates": [
            {
                "executor_id": "antigravity",
                "preference_rank": 0,
                "capacity_class": "SUBSCRIPTION",
                "supported_operations": ["RUN"],
                "supported_capabilities": ["SHELL"],
            }
        ],
    }
    content = _sample_artifact_content(policy=policy)
    with pytest.raises(ExecutableArtifactPreflightError, match="lacks required capabilities"):
        preflight_executable_artifact(
            content,
            work_path=".ai/tasks/TASK-071.md",
            operation=ExecutionOperation.RUN,
            selected_executor="antigravity",
        )


def test_unsupported_custom_result_marker_fails_preflight() -> None:
    content = _sample_artifact_content(
        extra_lines=['REQUIRED_RESULT_KEYS_JSON: ["CUSTOM_KEY_1", "CUSTOM_KEY_2"]']
    )
    with pytest.raises(ExecutableArtifactPreflightError, match="Unsupported custom RESULT requirement"):
        preflight_executable_artifact(
            content,
            work_path=".ai/tasks/TASK-071.md",
            operation=ExecutionOperation.RUN,
            selected_executor="antigravity",
        )


def test_unsupported_publisher_profile_fails_preflight() -> None:
    content = _sample_artifact_content(
        extra_lines=["PUBLISHER_PROFILE: NON_CANONICAL_PROFILE"]
    )
    with pytest.raises(ExecutableArtifactPreflightError, match="Unsupported publisher profile"):
        preflight_executable_artifact(
            content,
            work_path=".ai/tasks/TASK-071.md",
            operation=ExecutionOperation.RUN,
            selected_executor="antigravity",
        )


def test_canonical_e4_publisher_profile_accepted() -> None:
    content = _sample_artifact_content(
        extra_lines=[f"PUBLISHER_PROFILE: {CANONICAL_E4_PUBLISHER_PROFILE}"]
    )
    res = preflight_executable_artifact(
        content,
        work_path=".ai/tasks/TASK-071.md",
        operation=ExecutionOperation.RUN,
        selected_executor="antigravity",
    )
    assert res.operation is ExecutionOperation.RUN


# --- Integration Tests proving Handoff Preflight Ordering ---

def test_cmd_handoff_preflight_failure_does_not_mutate_reconcile_branch_lease_or_auth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mutations: dict[str, list[object]] = {
        "reconcile_called": [],
        "prepare_task_branch_called": [],
        "acquire_lease_called": [],
        "save_auth_called": [],
        "update_state_called": [],
        "artifact_written": [],
    }

    monkeypatch.setattr(bridge, "ensure_git", lambda: None)
    monkeypatch.setattr(bridge, "ensure_dirs", lambda: None)
    monkeypatch.setattr(bridge, "load_config", lambda: {
        "control_branch": "ai-control",
        "remote": "origin",
        "base_branch": "main",
        "task_branch_prefix": "ai/task-",
    })
    monkeypatch.setattr(bridge, "fetch_control", lambda cfg: None)
    monkeypatch.setattr(bridge, "get_remote_blob_sha", lambda cfg, path: VALID_BLOB_SHA)

    # Malformed task: missing DISPATCH_EXECUTOR_POLICY_JSON
    malformed_content = f"""# TASK-071 ? Malformed Task
STATUS: READY
EXECUTOR_CONTEXT_REFS_JSON: [{{"path":".ai/decisions/ADR-044.md","blob_sha":"{VALID_BLOB_SHA}"}}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py"]
"""
    monkeypatch.setattr(bridge, "read_remote_file", lambda cfg, path: malformed_content)

    def fake_reconcile(cfg: dict) -> str:
        mutations["reconcile_called"].append(cfg)
        return "main_sha_123"

    def fake_prepare_branch(cfg: dict, task_id: int, action: str) -> str:
        mutations["prepare_task_branch_called"].append((task_id, action))
        return "ai/task-071"

    def fake_acquire(candidate: object) -> object:
        mutations["acquire_lease_called"].append(candidate)
        return candidate

    def fake_save_auth(task_id: int, record: dict) -> None:
        mutations["save_auth_called"].append((task_id, record))

    def fake_update_state(task_id: int, status: str, msg: str) -> None:
        mutations["update_state_called"].append((task_id, status, msg))

    monkeypatch.setattr(bridge, "reconcile_local_main", fake_reconcile)
    monkeypatch.setattr(bridge, "prepare_task_branch", fake_prepare_branch)
    mock_store = SimpleNamespace(acquire=fake_acquire)
    monkeypatch.setattr(bridge, "get_lease_store", lambda: mock_store)
    monkeypatch.setattr(bridge, "save_authorization", fake_save_auth)
    monkeypatch.setattr(bridge, "update_state", fake_update_state)

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(bridge, "get_runtime_paths", lambda repo_root=None: {
        "root": runtime_dir,
        "seen": runtime_dir / "seen.json",
    })
    artifact_dest = tmp_path / "artifacts" / ".ai" / "tasks" / "TASK-071.md"
    monkeypatch.setattr(bridge, "get_artifact_path", lambda rel: artifact_dest)

    args = SimpleNamespace(task_id=71, action="run", executor=None)

    with pytest.raises(SystemExit) as excinfo:
        bridge.cmd_handoff(args)

    assert excinfo.value.code != 0

    # Verify zero mutations occurred
    assert len(mutations["reconcile_called"]) == 0
    assert len(mutations["prepare_task_branch_called"]) == 0
    assert len(mutations["acquire_lease_called"]) == 0
    assert len(mutations["save_auth_called"]) == 0
    assert len(mutations["update_state_called"]) == 0
    assert not artifact_dest.exists()


# --- Zero-Touch Local Main Reconciliation Invariants ---

def test_reconcile_local_main_fast_forwards_clean_behind_remote(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_git(*args: str, check: bool = True) -> SimpleNamespace:
        calls.append(list(args))
        op = args[0]
        if op == "fetch":
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        elif op == "rev-parse":
            if args[1] == "refs/remotes/origin/main":
                return SimpleNamespace(returncode=0, stdout="remote_sha_2222\n", stderr="")
            elif args[1] == "refs/heads/main":
                return SimpleNamespace(returncode=0, stdout="local_sha_1111\n", stderr="")
        elif op == "merge-base":
            return SimpleNamespace(returncode=0, stdout="local_sha_1111\n", stderr="")
        elif op == "status":
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        elif op == "branch":
            return SimpleNamespace(returncode=0, stdout="main\n", stderr="")
        elif op == "merge":
            return SimpleNamespace(returncode=0, stdout="Fast-forward\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(bridge, "git", fake_git)
    monkeypatch.setattr(bridge, "local_branch_exists", lambda b: True)
    monkeypatch.setattr(bridge, "current_branch", lambda: "main")

    cfg = {"remote": "origin", "base_branch": "main"}
    res = bridge.reconcile_local_main(cfg)
    assert res == "remote_sha_2222"
    assert any("merge" in call and "--ff-only" in call for call in calls)


def test_reconcile_local_main_fails_closed_on_divergence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_git(*args: str, check: bool = True) -> SimpleNamespace:
        op = args[0]
        if op == "fetch":
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        elif op == "rev-parse":
            if args[1] == "refs/remotes/origin/main":
                return SimpleNamespace(returncode=0, stdout="remote_sha_2222\n", stderr="")
            elif args[1] == "refs/heads/main":
                return SimpleNamespace(returncode=0, stdout="local_sha_1111\n", stderr="")
        elif op == "merge-base":
            # Neither is ancestor of the other -> returncode 1
            return SimpleNamespace(returncode=1, stdout="", stderr="")
        elif op == "status":
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        elif op == "branch":
            return SimpleNamespace(returncode=0, stdout="main\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(bridge, "git", fake_git)
    monkeypatch.setattr(bridge, "local_branch_exists", lambda b: True)
    monkeypatch.setattr(bridge, "current_branch", lambda: "main")

    cfg = {"remote": "origin", "base_branch": "main"}
    with pytest.raises(SystemExit):
        bridge.reconcile_local_main(cfg)


def test_reconcile_local_main_fails_closed_on_dirty_worktree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_git(*args: str, check: bool = True) -> SimpleNamespace:
        op = args[0]
        if op == "fetch":
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        elif op == "rev-parse":
            return SimpleNamespace(returncode=0, stdout="remote_sha_2222\n", stderr="")
        elif op == "status":
            return SimpleNamespace(returncode=0, stdout=" M dirty_file.py\n", stderr="")
        elif op == "branch":
            return SimpleNamespace(returncode=0, stdout="main\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(bridge, "git", fake_git)
    monkeypatch.setattr(bridge, "local_branch_exists", lambda b: True)
    monkeypatch.setattr(bridge, "current_branch", lambda: "main")

    cfg = {"remote": "origin", "base_branch": "main"}
    with pytest.raises(SystemExit):
        bridge.reconcile_local_main(cfg)
