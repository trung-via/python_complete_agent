from __future__ import annotations

import argparse
import hashlib
import inspect
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

import bridge
from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.executor import ExecutionCapability, ExecutionOperation
from src.aios_bridge.continuity.executor_transport import InvocationReceipt, InvocationStatus
from src.aios_bridge.continuity.lease import ExecutorLease
from src.aios_bridge.continuity.state import ArtifactRef


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def test_binary_git_helpers_preserve_bom_crlf_and_trailing_spaces(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "e4@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "E4 Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=tmp_path, check=True)
    raw = b"\xef\xbb\xbfline one  \r\nline two\r\n"
    artifact = tmp_path / "artifact.md"
    artifact.write_bytes(raw)
    subprocess.run(["git", "add", "artifact.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=tmp_path, check=True)
    monkeypatch.setattr(bridge, "PROJECT", tmp_path)
    assert bridge.read_git_blob_bytes("HEAD", "artifact.md") == raw
    assert bridge.resolve_git_blob_sha("HEAD", "artifact.md") == git_blob(raw)


def test_dirty_collector_includes_rename_ends_and_untracked(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "e4@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "E4 Test"], cwd=tmp_path, check=True)
    (tmp_path / "old.py").write_text("old\n", encoding="utf-8")
    subprocess.run(["git", "add", "old.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=tmp_path, check=True)
    subprocess.run(["git", "mv", "old.py", "new.py"], cwd=tmp_path, check=True)
    (tmp_path / "untracked.py").write_text("new\n", encoding="utf-8")
    monkeypatch.setattr(bridge, "PROJECT", tmp_path)
    assert bridge.collect_e4_dirty_paths() == ("new.py", "old.py", "untracked.py")


def make_execute_environment(monkeypatch, tmp_path, *, status=InvocationStatus.EXITED_ZERO):
    task_bytes = b"TASK E4\r\n"
    context_bytes = b"ADR E4\n"
    task_blob = git_blob(task_bytes)
    context_blob = git_blob(context_bytes)
    workspace_id = "c" * 64
    execution_fingerprint = "d" * 64
    lease = ExecutorLease(
        schema_version="1",
        lease_id="lease-task-043-abc123",
        task_id="TASK-043",
        workspace_id=workspace_id,
        executor_id="codex",
        operation=ExecutionOperation.RUN,
        execution_fingerprint=execution_fingerprint,
    )
    auth = {
        "task_id": "TASK-043",
        "action": "RUN",
        "kind": "TASK",
        "artifact_path": ".ai/tasks/TASK-043.md",
        "artifact_blob_sha": task_blob,
        "branch": "ai/task-043",
        "status": "ACTIVE",
        "executor_id": "codex",
        "lease_id": lease.lease_id,
        "lease_fingerprint": lease.fingerprint(),
        "workspace_id": workspace_id,
        "execution_fingerprint": execution_fingerprint,
    }
    candidate = SimpleNamespace(
        executor_id="codex",
        supported_operations=(ExecutionOperation.RUN,),
        supported_capabilities=(ExecutionCapability.FILESYSTEM_WRITE,),
    )
    policy = SimpleNamespace(required_capabilities=(ExecutionCapability.FILESYSTEM_WRITE,))
    snapshot = {
        "control_commit_sha": "9" * 40,
        "work_ref": ArtifactRef(
            path=auth["artifact_path"], ref="9" * 40, blob_sha=task_blob
        ),
        "context_refs": (
            ArtifactRef(
                path=".ai/decisions/ADR-032.md", ref="9" * 40, blob_sha=context_blob
            ),
        ),
        "allowed_paths": ("bridge.py",),
        "policy": policy,
        "candidate": candidate,
        "artifact_payloads": {
            auth["artifact_path"]: task_bytes,
            ".ai/decisions/ADR-032.md": context_bytes,
        },
    }
    calls = {"invoke": 0, "publish": [], "persist": [], "state": [], "published": False}

    class LeaseStore:
        def require_active(self, value):
            assert value == lease

        def acquire(self, value):
            raise AssertionError("execute must never acquire a lease")

    class FakeTransport:
        def __init__(self, workspace, *, codex_executable, timeout_seconds):
            assert workspace == bridge.PROJECT
            self.transport_id = "codex-local-v1"

        def invoke(self, invocation, payload):
            calls["invoke"] += 1
            if status is InvocationStatus.EXITED_ZERO:
                exit_code, error_code = 0, None
            elif status is InvocationStatus.EXITED_NONZERO:
                exit_code, error_code = 2, "CODEX_EXIT_NONZERO"
            else:
                exit_code, error_code = None, "CODEX_EXECUTION_STOPPED"
            return InvocationReceipt(
                schema_version=invocation.schema_version,
                invocation_id=invocation.invocation_id,
                task_id=invocation.task_id,
                request_id=invocation.request_id,
                executor_id=invocation.executor_id,
                transport_id=invocation.transport_id,
                operation=invocation.operation,
                execution_id=invocation.execution_id,
                invocation_fingerprint=invocation.fingerprint(),
                status=status,
                exit_code=exit_code,
                error_code=error_code,
            )

    def fake_git(*args, **kwargs):
        sha = "e" * 40 if calls["published"] else "b" * 40
        return SimpleNamespace(returncode=0, stdout=sha + "\n", stderr="")

    def fake_publish(namespace):
        calls["publish"].append(namespace)
        calls["published"] = True

    monkeypatch.setattr(bridge, "ensure_git", lambda: None)
    monkeypatch.setattr(
        bridge,
        "load_config",
        lambda: {
            "remote": "origin",
            "control_branch": "ai-control",
            "base_branch": "main",
            "task_branch_prefix": "ai/task-",
        },
    )
    monkeypatch.setattr(bridge, "get_active_authorization", lambda task_id: auth)
    monkeypatch.setattr(bridge, "current_branch", lambda: "ai/task-043")
    monkeypatch.setattr(bridge, "get_workspace_id", lambda: workspace_id)
    monkeypatch.setattr(bridge, "is_worktree_clean", lambda: True)
    monkeypatch.setattr(bridge, "get_lease_store", lambda: LeaseStore())
    monkeypatch.setattr(bridge, "git", fake_git)
    monkeypatch.setattr(bridge, "_resolve_e4_main_sha", lambda cfg: "a" * 40)
    monkeypatch.setattr(bridge, "resolve_e4_control_snapshot", lambda cfg, value: snapshot)
    monkeypatch.setattr(bridge, "CodexLocalTransport", FakeTransport)
    monkeypatch.setattr(bridge, "collect_e4_dirty_paths", lambda: ("bridge.py",))
    monkeypatch.setattr(
        bridge,
        "_persist_e4_receipt",
        lambda path, record: calls["persist"].append(dict(record)),
    )
    monkeypatch.setattr(
        bridge, "get_runtime_paths", lambda: {"executor_automation": tmp_path / "runtime"}
    )
    monkeypatch.setattr(bridge, "cmd_publish", fake_publish)
    monkeypatch.setattr(
        bridge,
        "load_authorization",
        lambda task_id: {
            **auth,
            "status": "CONSUMED",
            "published_sha": "e" * 40,
        },
    )
    monkeypatch.setattr(bridge, "resolve_git_blob_sha", lambda ref, path: "f" * 40)
    monkeypatch.setattr(
        bridge,
        "update_state",
        lambda task_id, state, message: calls["state"].append((state, message)),
    )
    return auth, snapshot, calls


def execute_args():
    return argparse.Namespace(task_id=43, codex_executable="codex", timeout_seconds=1800)


def test_exit_zero_invokes_once_and_reuses_publisher_with_fixed_suite(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(monkeypatch, tmp_path)
    result = bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 1
    assert len(calls["publish"]) == 1
    published = calls["publish"][0]
    assert published.action == "RUN"
    assert "-m pytest tests/ -q" in published.test
    assert "E4_TRANSPORT_STATUS: EXITED_ZERO" in published.notes
    assert "TASK E4" not in published.notes
    assert len(calls["persist"]) == 2
    assert calls["persist"][0]["published_sha"] is None
    assert calls["persist"][1]["published_sha"] == "e" * 40
    assert result.implementation_sha == "e" * 40


@pytest.mark.parametrize(
    "status",
    [
        InvocationStatus.FAILED_TO_START,
        InvocationStatus.EXITED_NONZERO,
        InvocationStatus.TIMED_OUT,
        InvocationStatus.INTERRUPTED,
    ],
)
def test_nonzero_transport_statuses_never_publish_or_retry(monkeypatch, tmp_path, status):
    _, _, calls = make_execute_environment(monkeypatch, tmp_path, status=status)
    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 1
    assert calls["publish"] == []


def test_no_active_authorization_blocks_before_transport(monkeypatch):
    monkeypatch.setattr(bridge, "ensure_git", lambda: None)
    monkeypatch.setattr(bridge, "load_config", lambda: {})
    monkeypatch.setattr(bridge, "get_active_authorization", lambda task_id: None)
    monkeypatch.setattr(
        bridge,
        "CodexLocalTransport",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not invoke")),
    )
    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())


def test_control_drift_blocks_before_transport(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(
        bridge,
        "resolve_e4_control_snapshot",
        lambda cfg, auth: (_ for _ in ()).throw(ContinuityStateValidationError("drift")),
    )
    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 0
    assert calls["publish"] == []


def test_out_of_scope_untracked_path_blocks_publication(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(bridge, "collect_e4_dirty_paths", lambda: ("secret.txt",))
    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 1
    assert calls["publish"] == []
    assert calls["state"][-1][0] == "RECOVERY_REQUIRED"


def test_receipt_persistence_failure_blocks_publication(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(
        bridge,
        "_persist_e4_receipt",
        lambda path, record: (_ for _ in ()).throw(OSError("disk unavailable")),
    )
    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 1
    assert calls["publish"] == []


def test_execute_source_contains_no_authority_or_merge_calls():
    source = inspect.getsource(bridge.cmd_execute)
    assert ".acquire(" not in source
    assert "cmd_approve(" not in source
    assert "merge" not in source.lower()


def test_cli_exposes_execute_without_approval_side_effects():
    args = bridge.build_parser().parse_args(["execute", "43"])
    assert args.func is bridge.cmd_execute
    assert args.codex_executable == "codex"
    assert args.timeout_seconds == bridge.DEFAULT_CODEX_TIMEOUT_SECONDS
