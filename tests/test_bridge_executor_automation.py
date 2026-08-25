from __future__ import annotations

import argparse
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

import bridge
from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.executor import ExecutionCapability, ExecutionOperation
from src.aios_bridge.continuity.executor_transport import InvocationReceipt, InvocationStatus
from src.aios_bridge.executor_transports import CodexTransportDiagnostic, CodexInvocationOutcome
from src.aios_bridge.continuity.lease import ExecutorLease
from src.aios_bridge.continuity.state import ArtifactRef
from src.aios_bridge.validation import ValidationProfile


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def init_publication_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "e4@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "E4 Test"], cwd=path, check=True)
    subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=path, check=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://example.invalid/repository.git"],
        cwd=path,
        check=True,
    )
    (path / "bridge.py").write_text("baseline\n", encoding="utf-8")
    subprocess.run(["git", "add", "bridge.py"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=path, check=True)


def init_control_repo(path: Path, policy: dict) -> dict:
    init_publication_repo(path)
    context_path = path / ".ai" / "decisions" / "ADR-032.md"
    context_path.parent.mkdir(parents=True, exist_ok=True)
    context_path.write_bytes(b"ADR\n")
    context_blob = git_blob(b"ADR\n")
    task_path = path / ".ai" / "tasks" / "TASK-043.md"
    task_path.parent.mkdir(parents=True, exist_ok=True)
    task_content = "\n".join(
        (
            "TASK",
            "EXECUTOR_CONTEXT_REFS_JSON: "
            + json.dumps([{"path": ".ai/decisions/ADR-032.md", "blob_sha": context_blob}], separators=(",", ":")),
            'EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py"]',
            "DISPATCH_EXECUTOR_POLICY_JSON: " + json.dumps(policy, separators=(",", ":")),
            "",
        )
    ).encode("utf-8")
    task_path.write_bytes(task_content)
    subprocess.run(["git", "add", ".ai"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "control"], cwd=path, check=True)
    subprocess.run(["git", "branch", "-M", "ai-control"], cwd=path, check=True)
    task_blob = subprocess.run(
        ["git", "rev-parse", "ai-control:.ai/tasks/TASK-043.md"],
        cwd=path,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    return {
        "action": "RUN",
        "artifact_path": ".ai/tasks/TASK-043.md",
        "artifact_blob_sha": task_blob,
        "executor_id": "codex",
    }


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


def test_publication_trust_snapshot_resolves_linked_worktree_gitdir(tmp_path, monkeypatch):
    main_repo = tmp_path / "main"
    linked_repo = tmp_path / "linked"
    init_publication_repo(main_repo)
    subprocess.run(
        ["git", "worktree", "add", "-qb", "linked-test", str(linked_repo)],
        cwd=main_repo,
        check=True,
    )
    monkeypatch.setattr(bridge, "PROJECT", linked_repo)
    snapshot = bridge.capture_e4_publication_trust_snapshot("origin")
    assert Path(snapshot.git_dir) != Path(snapshot.common_git_dir)
    assert (linked_repo / ".git").is_file()
    bridge.verify_e4_publication_trust_snapshot(snapshot)
    subprocess.run(
        ["git", "config", "remote.origin.url", "https://attacker.invalid/repository.git"],
        cwd=linked_repo,
        check=True,
    )
    with pytest.raises(ContinuityStateValidationError, match="drifted"):
        bridge.verify_e4_publication_trust_snapshot(snapshot)


def make_execute_environment(
    monkeypatch,
    tmp_path,
    *,
    status=InvocationStatus.EXITED_ZERO,
    on_invoke=None,
    real_publication_trust=False,
):
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
    calls = {
        "invoke": 0,
        "publish": [],
        "persist": [],
        "state": [],
        "published": False,
        "lease_released": [],
        "auth_saved": [],
    }

    class LeaseStore:
        def require_active(self, value):
            assert value == lease

        def acquire(self, value):
            raise AssertionError("execute must never acquire a lease")

        def release(self, value):
            calls["lease_released"].append(value)

    class FakeTransport:
        def __init__(self, workspace, *, codex_executable, timeout_seconds):
            assert workspace == bridge.PROJECT
            self.transport_id = "codex-local-v1"

        def invoke(self, invocation, payload):
            calls["invoke"] += 1
            if on_invoke is not None:
                on_invoke()
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

        def invoke_with_diagnostic(self, invocation, payload):
            receipt = self.invoke(invocation, payload)
            diagnostic = CodexTransportDiagnostic(
                code="JSON_EVENT_STREAM" if status is InvocationStatus.EXITED_ZERO else "JSON_ERROR_EVENT",
                stdout_total_bytes=128,
                stderr_total_bytes=0,
                stdout_scan_truncated=False,
                stderr_scan_truncated=False,
                stdout_json_line_count=2,
                stdout_non_json_line_count=0,
                stdout_event_types=("turn_started", "item_completed"),
                last_stdout_event_type="item_completed",
            )
            return CodexInvocationOutcome(receipt=receipt, diagnostic=diagnostic)

    def fake_git(*args, **kwargs):
        sha = "e" * 40 if calls["published"] else "b" * 40
        return SimpleNamespace(returncode=0, stdout=sha + "\n", stderr="")

    def fake_publish(namespace):
        calls["publish"].append(namespace)
        calls["published"] = True

    current_auth = dict(auth)

    def fake_save_auth(task_id, new_auth):
        calls["auth_saved"].append((task_id, dict(new_auth)))
        current_auth.clear()
        current_auth.update(new_auth)

    def fake_load_auth(task_id):
        if calls["published"]:
            return {
                **current_auth,
                "status": "CONSUMED",
                "published_sha": "e" * 40,
            }
        return dict(current_auth)

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
    monkeypatch.setattr(
        bridge,
        "observe_e4_head",
        lambda: "e" * 40 if calls["published"] else "b" * 40,
    )
    monkeypatch.setattr(bridge, "observe_e4_branch", lambda: "ai/task-043")
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
    monkeypatch.setattr(bridge, "save_authorization", fake_save_auth)
    monkeypatch.setattr(bridge, "load_authorization", fake_load_auth)
    monkeypatch.setattr(bridge, "resolve_git_blob_sha", lambda ref, path: "f" * 40)
    monkeypatch.setattr(
        bridge,
        "update_state",
        lambda task_id, state, message: calls["state"].append((state, message)),
    )
    if not real_publication_trust:
        monkeypatch.setattr(
            bridge, "capture_e4_publication_trust_snapshot", lambda remote: "trusted"
        )
        monkeypatch.setattr(
            bridge,
            "verify_e4_publication_trust_snapshot",
            lambda snapshot: None,
        )
    return auth, snapshot, calls


def execute_args():
    return argparse.Namespace(task_id=43, codex_executable="codex", timeout_seconds=1800)


@pytest.mark.parametrize("drift_kind", ["hook", "remote", "hooks_path", "attributes", "exclude"])
def test_git_admin_drift_after_one_fake_invoke_blocks_publication(
    monkeypatch, tmp_path, drift_kind
):
    repo = tmp_path / "repo"
    init_publication_repo(repo)
    hook = repo / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    monkeypatch.setattr(bridge, "PROJECT", repo)

    def mutate():
        (repo / "bridge.py").write_text("allowed mutation\n", encoding="utf-8")
        if drift_kind == "hook":
            hook.write_text("#!/bin/sh\necho attacker\n", encoding="utf-8")
        elif drift_kind == "remote":
            subprocess.run(
                ["git", "config", "remote.origin.url", "https://attacker.invalid/repository.git"],
                cwd=repo,
                check=True,
            )
        elif drift_kind == "hooks_path":
            subprocess.run(
                ["git", "config", "core.hooksPath", "attacker-hooks"], cwd=repo, check=True
            )
        elif drift_kind == "attributes":
            info = repo / ".git" / "info"
            info.mkdir(exist_ok=True)
            (info / "attributes").write_text("* filter=attacker\n", encoding="utf-8")
        else:
            (repo / ".git" / "info" / "exclude").write_text("bridge.py\n", encoding="utf-8")

    _, _, calls = make_execute_environment(
        monkeypatch,
        tmp_path,
        on_invoke=mutate,
        real_publication_trust=True,
    )
    dirty_probes = []
    monkeypatch.setattr(
        bridge,
        "collect_e4_dirty_paths",
        lambda: dirty_probes.append(True) or ("bridge.py",),
    )
    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 1
    assert calls["publish"] == []
    assert dirty_probes == []
    assert calls["state"][-1][0] == "RECOVERY_REQUIRED"


def test_unchanged_git_admin_and_allowed_mutation_preserve_happy_path(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    init_publication_repo(repo)
    monkeypatch.setattr(bridge, "PROJECT", repo)

    def mutate_allowed_file():
        (repo / "bridge.py").write_text("allowed mutation\n", encoding="utf-8")

    _, _, calls = make_execute_environment(
        monkeypatch,
        tmp_path,
        on_invoke=mutate_allowed_file,
        real_publication_trust=True,
    )
    bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 1
    assert len(calls["publish"]) == 1


def assert_custom_hook_drift_blocked(monkeypatch, tmp_path, repo, hook):
    monkeypatch.setattr(bridge, "PROJECT", repo)

    def mutate():
        (repo / "bridge.py").write_text("allowed mutation\n", encoding="utf-8")
        hook.write_text("#!/bin/sh\necho changed\n", encoding="utf-8")

    _, _, calls = make_execute_environment(
        monkeypatch,
        tmp_path,
        on_invoke=mutate,
        real_publication_trust=True,
    )
    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 1
    assert calls["publish"] == []
    assert calls["state"][-1][0] == "RECOVERY_REQUIRED"


def test_preexisting_absolute_core_hookspath_content_drift_blocks_publication(
    monkeypatch, tmp_path
):
    repo = tmp_path / "repo"
    custom_hooks = tmp_path / "external-custom-hooks"
    init_publication_repo(repo)
    custom_hooks.mkdir()
    hook = custom_hooks / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    hook.chmod(0o755)
    subprocess.run(
        ["git", "config", "core.hooksPath", str(custom_hooks.resolve())],
        cwd=repo,
        check=True,
    )
    monkeypatch.setattr(bridge, "PROJECT", repo)
    snapshot = bridge.capture_e4_publication_trust_snapshot("origin")
    assert Path(snapshot.hooks_path) == custom_hooks.resolve()
    assert Path(snapshot.hooks_path) != Path(snapshot.default_hooks_path)
    assert_custom_hook_drift_blocked(monkeypatch, tmp_path, repo, hook)


def test_custom_hooks_under_nondefault_git_admin_path_are_protected(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    init_publication_repo(repo)
    custom_hooks = repo / ".git" / "publication-hooks"
    custom_hooks.mkdir()
    hook = custom_hooks / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    hook.chmod(0o755)
    subprocess.run(
        ["git", "config", "core.hooksPath", str(custom_hooks.resolve())],
        cwd=repo,
        check=True,
    )
    assert_custom_hook_drift_blocked(monkeypatch, tmp_path, repo, hook)


def test_relative_core_hookspath_resolves_from_nonbare_worktree_root_and_is_protected(
    monkeypatch, tmp_path
):
    repo = tmp_path / "repo"
    init_publication_repo(repo)
    custom_hooks = repo / ".relative-hooks"
    custom_hooks.mkdir()
    hook = custom_hooks / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    hook.chmod(0o755)
    subprocess.run(
        ["git", "config", "core.hooksPath", ".relative-hooks"], cwd=repo, check=True
    )
    monkeypatch.setattr(bridge, "PROJECT", repo)
    snapshot = bridge.capture_e4_publication_trust_snapshot("origin")
    assert Path(snapshot.hooks_path) == custom_hooks.resolve()
    assert_custom_hook_drift_blocked(monkeypatch, tmp_path, repo, hook)


def test_preexisting_custom_hooks_unchanged_preserves_happy_path(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    custom_hooks = tmp_path / "stable-custom-hooks"
    init_publication_repo(repo)
    custom_hooks.mkdir()
    hook = custom_hooks / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    hook.chmod(0o755)
    subprocess.run(
        ["git", "config", "core.hooksPath", str(custom_hooks.resolve())],
        cwd=repo,
        check=True,
    )
    monkeypatch.setattr(bridge, "PROJECT", repo)

    def mutate_allowed_file_only():
        (repo / "bridge.py").write_text("allowed mutation\n", encoding="utf-8")

    _, _, calls = make_execute_environment(
        monkeypatch,
        tmp_path,
        on_invoke=mutate_allowed_file_only,
        real_publication_trust=True,
    )
    bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 1
    assert len(calls["publish"]) == 1


def test_linked_worktree_custom_hookspath_never_falls_back_to_default(monkeypatch, tmp_path):
    main_repo = tmp_path / "main"
    linked_repo = tmp_path / "linked"
    init_publication_repo(main_repo)
    subprocess.run(
        ["git", "worktree", "add", "-qb", "linked-custom-hooks", str(linked_repo)],
        cwd=main_repo,
        check=True,
    )
    custom_hooks = main_repo / ".git" / "linked-publication-hooks"
    custom_hooks.mkdir()
    hook = custom_hooks / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    hook.chmod(0o755)
    subprocess.run(
        ["git", "config", "core.hooksPath", str(custom_hooks.resolve())],
        cwd=linked_repo,
        check=True,
    )
    monkeypatch.setattr(bridge, "PROJECT", linked_repo)
    snapshot = bridge.capture_e4_publication_trust_snapshot("origin")
    assert Path(snapshot.git_dir) != Path(snapshot.common_git_dir)
    assert Path(snapshot.hooks_path) == custom_hooks.resolve()
    assert Path(snapshot.hooks_path) != Path(snapshot.default_hooks_path)
    assert_custom_hook_drift_blocked(monkeypatch, tmp_path, linked_repo, hook)


def test_exit_zero_invokes_once_and_reuses_publisher_with_fixed_suite(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(monkeypatch, tmp_path)
    result = bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 1
    assert len(calls["publish"]) == 1
    published = calls["publish"][0]
    assert published.action == "RUN"
    assert "-m pytest tests/ -q" in published.test
    assert "E4_TRANSPORT_STATUS: EXITED_ZERO" in published.notes
    assert "E4_PUBLICATION_TRUST_VERIFIED: PASS" in published.notes
    assert "TASK E4" not in published.notes
    assert "ADR E4" not in published.notes
    assert "AIOS_EXECUTOR_CONTEXT_PACK" not in published.notes
    assert len(published.notes.encode("utf-8")) <= bridge._E4_MAX_PUBLICATION_NOTES_BYTES
    assert len(calls["persist"]) == 2
    assert calls["persist"][0]["published_sha"] is None
    assert calls["persist"][1]["published_sha"] == "e" * 40
    assert result.implementation_sha == "e" * 40


def test_result_manifest_persists_scoped_validation_observability():
    evidence = bridge.ValidationEvidence(
        task_id="TASK-083",
        action="FIX",
        executor_id="codex",
        validation_profile=ValidationProfile.CONTROL_PLANE_STRICT_COMPAT,
        full_suite_execution_count=1,
        expected_full_suite_execution_count=1,
        targeted_test_execution_count=None,
        full_suite_duration_seconds=12.5,
        targeted_test_duration_seconds=None,
        executor_ad_hoc_t2_observability=(
            bridge.ExecutorAdHocT2Observability.UNAVAILABLE
        ),
        executor_ad_hoc_t2_execution_count=None,
    )

    manifest = bridge._validation_result_manifest(evidence)

    assert "FULL_CANONICAL_OWNER: CERTIFICATION_BOUNDARY" in manifest
    assert "EXPECTED_AIOS_MANAGED_T2_EXECUTION_COUNT: 1" in manifest
    assert "AIOS_MANAGED_T2_EXECUTION_COUNT: 1" in manifest
    assert "AIOS_MANAGED_T2_DUPLICATION_DETECTED: NO" in manifest
    assert "EXECUTOR_AD_HOC_T2_OBSERVABILITY: UNAVAILABLE" in manifest
    assert "EXECUTOR_AD_HOC_T2_EXECUTION_COUNT: UNKNOWN" in manifest
    assert "GLOBAL_T2_EXECUTION_COUNT: UNKNOWN" in manifest
    assert "TARGETED_TEST_EXECUTION_COUNT: UNKNOWN" in manifest
    assert "FULL_SUITE_DURATION_SECONDS: 12.5" in manifest
    assert "TARGETED_TEST_DURATION_SECONDS: UNKNOWN" in manifest
    assert "EXPECTED_FULL_SUITE_EXECUTION_COUNT" not in manifest
    assert "\nFULL_SUITE_EXECUTION_COUNT:" not in manifest


@pytest.mark.parametrize(
    "status",
    [
        InvocationStatus.FAILED_TO_START,
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


def test_wrong_workspace_blocks_before_transport(monkeypatch, tmp_path):
    auth, _, calls = make_execute_environment(monkeypatch, tmp_path)
    auth["workspace_id"] = "f" * 64
    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 0
    assert calls["publish"] == []


@pytest.mark.parametrize("lease_failure", ["missing", "wrong"])
def test_missing_or_wrong_active_lease_blocks_before_transport(
    monkeypatch, tmp_path, lease_failure
):
    _, _, calls = make_execute_environment(monkeypatch, tmp_path)

    class InvalidLeaseStore:
        def require_active(self, lease):
            raise ContinuityStateValidationError(f"{lease_failure} active lease")

    monkeypatch.setattr(bridge, "get_lease_store", lambda: InvalidLeaseStore())
    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 0
    assert calls["publish"] == []


@pytest.mark.parametrize("authorized_branch,current", [("main", "ai/task-043"), ("ai/task-043", "main")])
def test_wrong_authorized_or_current_branch_blocks_before_transport(
    monkeypatch, tmp_path, authorized_branch, current
):
    auth, _, calls = make_execute_environment(monkeypatch, tmp_path)
    auth["branch"] = authorized_branch
    monkeypatch.setattr(bridge, "current_branch", lambda: current)
    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 0
    assert calls["publish"] == []


def test_non_codex_authorization_blocks_before_transport(monkeypatch, tmp_path):
    auth, _, calls = make_execute_environment(monkeypatch, tmp_path)
    auth["executor_id"] = "antigravity"
    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 0
    assert calls["publish"] == []


def test_ineligible_selected_executor_blocks_before_transport(monkeypatch, tmp_path):
    _, snapshot, calls = make_execute_environment(monkeypatch, tmp_path)
    snapshot["candidate"] = SimpleNamespace(
        executor_id="codex",
        supported_operations=(ExecutionOperation.RUN,),
        supported_capabilities=(),
    )
    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 0
    assert calls["publish"] == []


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


@pytest.mark.parametrize(
    "reason",
    ["dispatch policy operation mismatch", "selected executor absent"],
)
def test_dispatch_policy_mismatch_or_absent_executor_has_zero_invoke(
    monkeypatch, tmp_path, reason
):
    _, _, calls = make_execute_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(
        bridge,
        "resolve_e4_control_snapshot",
        lambda cfg, auth: (_ for _ in ()).throw(ContinuityStateValidationError(reason)),
    )
    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 0
    assert calls["publish"] == []


def policy(candidate_id="codex", operation="RUN", supported_operations=None):
    return {
        "allow_paid_api": False,
        "candidates": [
            {
                "capacity_class": "SUBSCRIPTION",
                "executor_id": candidate_id,
                "preference_rank": 0,
                "supported_capabilities": ["FILESYSTEM_WRITE"],
                "supported_operations": supported_operations or ["RUN"],
            }
        ],
        "operation": operation,
        "required_capabilities": ["FILESYSTEM_WRITE"],
    }


@pytest.mark.parametrize(
    "policy_value,error",
    [
        (policy(operation="FIX", supported_operations=["FIX"]), "operation mismatches"),
        (policy(candidate_id="antigravity"), "appear exactly once"),
        (policy(supported_operations=["FIX"]), "does not support"),
    ],
)
def test_control_snapshot_rejects_policy_action_absence_and_operation_ineligibility(
    monkeypatch, tmp_path, policy_value, error
):
    repo = tmp_path / "control"
    auth = init_control_repo(repo, policy_value)
    monkeypatch.setattr(bridge, "PROJECT", repo)
    monkeypatch.setattr(bridge, "fetch_control", lambda cfg: None)
    monkeypatch.setattr(bridge, "remote_ref", lambda cfg: "ai-control")
    with pytest.raises(ContinuityStateValidationError, match=error):
        bridge.resolve_e4_control_snapshot({}, auth)


def test_out_of_scope_untracked_path_blocks_publication(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(bridge, "collect_e4_dirty_paths", lambda: ("secret.txt",))
    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 1
    assert calls["publish"] == []
    assert calls["state"][-1][0] == "RECOVERY_REQUIRED"


def test_executor_head_advance_blocks_publication_and_requires_recovery(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(monkeypatch, tmp_path)
    observations = iter(("b" * 40, "c" * 40))
    monkeypatch.setattr(bridge, "observe_e4_head", lambda: next(observations))
    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 1
    assert calls["publish"] == []
    assert calls["state"][-1][0] == "RECOVERY_REQUIRED"


def test_post_executor_branch_observation_failure_enters_recovery(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(
        bridge,
        "observe_e4_branch",
        lambda: (_ for _ in ()).throw(ContinuityStateValidationError("branch unavailable")),
    )
    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 1
    assert calls["publish"] == []
    assert calls["state"][-1][0] == "RECOVERY_REQUIRED"


def test_post_executor_head_observation_failure_enters_recovery(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(monkeypatch, tmp_path)
    count = {"head": 0}

    def observe_head():
        count["head"] += 1
        if count["head"] == 1:
            return "b" * 40
        raise ContinuityStateValidationError("HEAD unavailable")

    monkeypatch.setattr(bridge, "observe_e4_head", observe_head)
    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 1
    assert calls["publish"] == []
    assert calls["state"][-1][0] == "RECOVERY_REQUIRED"


def test_post_publish_head_observation_failure_enters_recovery_once(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(monkeypatch, tmp_path)
    count = {"head": 0}

    def observe_head():
        count["head"] += 1
        if count["head"] <= 2:
            return "b" * 40
        raise ContinuityStateValidationError("published HEAD unavailable")

    monkeypatch.setattr(bridge, "observe_e4_head", observe_head)
    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 1
    assert len(calls["publish"]) == 1
    assert calls["state"][-1][0] == "RECOVERY_REQUIRED"


def test_post_publish_integrity_mismatch_enters_recovery(monkeypatch, tmp_path):
    auth, _, calls = make_execute_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(
        bridge,
        "load_authorization",
        lambda task_id: {**auth, "status": "CONSUMED", "published_sha": "f" * 40},
    )
    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 1
    assert len(calls["publish"]) == 1
    assert calls["state"][-1][0] == "RECOVERY_REQUIRED"


def test_cmd_publish_full_test_failure_remains_fail_closed(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(monkeypatch, tmp_path)

    def failing_publish(namespace):
        calls["publish"].append(namespace)
        raise SystemExit(1)

    monkeypatch.setattr(bridge, "cmd_publish", failing_publish)
    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 1
    assert len(calls["publish"]) == 1
    assert len(calls["persist"]) == 1


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



def test_e4_persists_transport_diagnostic_metadata(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(monkeypatch, tmp_path)
    bridge.cmd_execute(execute_args())

    assert len(calls["persist"]) == 2
    rec = calls["persist"][0]
    assert "transport_diagnostic" in rec
    assert "transport_diagnostic_fingerprint" in rec
    assert rec["transport_diagnostic"]["code"] == "JSON_EVENT_STREAM"
    assert len(rec["transport_diagnostic_fingerprint"]) == 64
    assert "stdout" not in rec
    assert "stderr" not in rec


def test_e4_nonzero_failure_surfaces_stable_diagnostic_codes(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(
        monkeypatch, tmp_path, status=InvocationStatus.EXITED_NONZERO
    )
    monkeypatch.setattr(bridge, "collect_e4_dirty_paths", lambda: ())
    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())

    assert calls["invoke"] == 1
    assert calls["publish"] == []
    # Check failure state message contains stable codes
    last_state = calls["state"][-1]
    assert last_state[0] == "RECOVERY_REQUIRED"
    msg = last_state[1]
    assert "EXITED_NONZERO" in msg
    assert "error=CODEX_EXIT_NONZERO" in msg
    assert "diagnostic=JSON_ERROR_EVENT" in msg
    assert "no publication and no retry" in msg


def test_clean_noop_exited_zero_classified_blocked_and_releases_lease(monkeypatch, tmp_path):
    auth, _, calls = make_execute_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(bridge, "collect_e4_dirty_paths", lambda: ())

    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())

    assert calls["invoke"] == 1
    assert calls["publish"] == []
    assert len(calls["lease_released"]) == 1
    assert len(calls["auth_saved"]) == 1
    saved_task_id, saved_auth = calls["auth_saved"][0]
    assert saved_task_id == 43
    assert saved_auth["status"] == "EXECUTION_BLOCKED"
    assert saved_auth["lease_id"] == auth["lease_id"]

    last_state = calls["state"][-1]
    assert last_state[0] == "EXECUTION_BLOCKED"
    msg = last_state[1]
    assert "CLEAN_NO_WORKTREE_DELTA" in msg
    assert "executor_outcome=" in msg
    assert "final_agent_message_observed=" in msg
    assert "diagnostic=JSON_EVENT_STREAM" in msg
    assert "no publication, no retry, no reroute" in msg


def test_noop_with_branch_drift_enters_recovery(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(bridge, "collect_e4_dirty_paths", lambda: ())
    monkeypatch.setattr(bridge, "observe_e4_branch", lambda: "ai/task-drift")

    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())

    assert calls["invoke"] == 1
    assert calls["publish"] == []
    assert len(calls["lease_released"]) == 0
    assert calls["state"][-1][0] == "RECOVERY_REQUIRED"


def test_noop_with_head_drift_enters_recovery(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(bridge, "collect_e4_dirty_paths", lambda: ())
    observations = iter(("b" * 40, "c" * 40))
    monkeypatch.setattr(bridge, "observe_e4_head", lambda: next(observations))

    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())

    assert calls["invoke"] == 1
    assert calls["publish"] == []
    assert len(calls["lease_released"]) == 0
    assert calls["state"][-1][0] == "RECOVERY_REQUIRED"


def test_dirty_out_of_scope_enters_recovery(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(bridge, "collect_e4_dirty_paths", lambda: ("unauthorized.txt",))

    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())

    assert calls["invoke"] == 1
    assert calls["publish"] == []
    assert len(calls["lease_released"]) == 0
    assert calls["state"][-1][0] == "RECOVERY_REQUIRED"


def test_clean_noop_release_failure_enters_recovery(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(bridge, "collect_e4_dirty_paths", lambda: ())

    class FailingLeaseStore:
        def require_active(self, value):
            pass

        def acquire(self, value):
            raise AssertionError("must not acquire")

        def release(self, value):
            raise OSError("lease release disk lock error")

    monkeypatch.setattr(bridge, "get_lease_store", lambda: FailingLeaseStore())

    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())

    assert calls["invoke"] == 1
    assert calls["publish"] == []
    assert calls["state"][-1][0] == "RECOVERY_REQUIRED"
    assert "clean no-op cleanup failed" in calls["state"][-1][1]


def test_clean_noop_auth_persistence_failure_enters_recovery(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(bridge, "collect_e4_dirty_paths", lambda: ())

    def failing_save_auth(task_id, new_auth):
        raise OSError("auth write failed")

    monkeypatch.setattr(bridge, "save_authorization", failing_save_auth)

    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())

    assert calls["invoke"] == 1
    assert calls["publish"] == []
    assert len(calls["lease_released"]) == 1
    assert calls["state"][-1][0] == "RECOVERY_REQUIRED"
    assert "clean no-op cleanup failed" in calls["state"][-1][1]


def test_clean_noop_auth_readback_mismatch_enters_recovery(monkeypatch, tmp_path):
    auth, _, calls = make_execute_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(bridge, "collect_e4_dirty_paths", lambda: ())

    # Load returns status EXECUTION_BLOCKED but drifted lease_fingerprint
    drifted_auth = {
        **auth,
        "status": "EXECUTION_BLOCKED",
        "lease_fingerprint": "f" * 64,
    }
    monkeypatch.setattr(bridge, "load_authorization", lambda task_id: drifted_auth)

    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())

    assert calls["invoke"] == 1
    assert calls["publish"] == []
    assert len(calls["lease_released"]) == 1
    assert calls["state"][-1][0] == "RECOVERY_REQUIRED"
    assert "clean no-op cleanup failed" in calls["state"][-1][1]


def test_clean_noop_execution_blocked_state_write_fails_attempts_recovery_required(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(bridge, "collect_e4_dirty_paths", lambda: ())

    state_attempts = []

    def failing_first_update_state(task_id, state, message):
        state_attempts.append((state, message))
        if state == "EXECUTION_BLOCKED":
            raise OSError("blocked state disk error")
        calls["state"].append((state, message))

    monkeypatch.setattr(bridge, "update_state", failing_first_update_state)

    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())

    assert calls["invoke"] == 1
    assert calls["publish"] == []
    assert len(calls["lease_released"]) == 1
    assert [s[0] for s in state_attempts] == ["EXECUTION_BLOCKED", "RECOVERY_REQUIRED"]
    assert calls["state"][-1][0] == "RECOVERY_REQUIRED"
    assert "E4 clean no-op state persistence failed" in calls["state"][-1][1]


def test_clean_noop_both_state_writes_fail_enters_explicit_diagnostic(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(bridge, "collect_e4_dirty_paths", lambda: ())

    def always_failing_update_state(task_id, state, message):
        raise OSError("all state writes failed")

    monkeypatch.setattr(bridge, "update_state", always_failing_update_state)

    with pytest.raises(SystemExit) as excinfo:
        bridge.cmd_execute(execute_args())

    assert calls["invoke"] == 1
    assert calls["publish"] == []
    assert len(calls["lease_released"]) == 1
    assert excinfo.value.code != 0



def test_is_exact_clean_noop_unit_predicate():
    assert bridge.is_exact_clean_noop(
        receipt_status=InvocationStatus.EXITED_ZERO,
        pre_branch="ai/task-043",
        post_branch="ai/task-043",
        target_branch="ai/task-043",
        pre_head_sha="a" * 40,
        post_head_sha="a" * 40,
        dirty_paths=(),
    ) is True

    # Non-zero exit status -> False
    assert bridge.is_exact_clean_noop(
        receipt_status=InvocationStatus.EXITED_NONZERO,
        pre_branch="ai/task-043",
        post_branch="ai/task-043",
        target_branch="ai/task-043",
        pre_head_sha="a" * 40,
        post_head_sha="a" * 40,
        dirty_paths=(),
    ) is False

    # Branch drift -> False
    assert bridge.is_exact_clean_noop(
        receipt_status=InvocationStatus.EXITED_ZERO,
        pre_branch="ai/task-043",
        post_branch="ai/task-044",
        target_branch="ai/task-043",
        pre_head_sha="a" * 40,
        post_head_sha="a" * 40,
        dirty_paths=(),
    ) is False

    # Head drift -> False
    assert bridge.is_exact_clean_noop(
        receipt_status=InvocationStatus.EXITED_ZERO,
        pre_branch="ai/task-043",
        post_branch="ai/task-043",
        target_branch="ai/task-043",
        pre_head_sha="a" * 40,
        post_head_sha="b" * 40,
        dirty_paths=(),
    ) is False

    # Dirty paths present -> False
    assert bridge.is_exact_clean_noop(
        receipt_status=InvocationStatus.EXITED_ZERO,
        pre_branch="ai/task-043",
        post_branch="ai/task-043",
        target_branch="ai/task-043",
        pre_head_sha="a" * 40,
        post_head_sha="a" * 40,
        dirty_paths=("bridge.py",),
    ) is False


def test_is_productive_nonzero_recovery_candidate_predicate():
    assert bridge.is_productive_nonzero_recovery_candidate(
        receipt_status=InvocationStatus.EXITED_NONZERO,
        receipt_error_code="CODEX_EXIT_NONZERO",
        pre_branch="ai/task-043",
        post_branch="ai/task-043",
        target_branch="ai/task-043",
        pre_head_sha="a" * 40,
        post_head_sha="a" * 40,
        dirty_paths=("bridge.py",),
        allowed_paths=["bridge.py", "tests/test_bridge_executor_automation.py"],
        publication_trust_valid=True,
        authorization_binding_valid=True,
    ) is True

    # Out of scope dirty path -> False
    assert bridge.is_productive_nonzero_recovery_candidate(
        receipt_status=InvocationStatus.EXITED_NONZERO,
        receipt_error_code="CODEX_EXIT_NONZERO",
        pre_branch="ai/task-043",
        post_branch="ai/task-043",
        target_branch="ai/task-043",
        pre_head_sha="a" * 40,
        post_head_sha="a" * 40,
        dirty_paths=("unauthorized.py",),
        allowed_paths=["bridge.py"],
        publication_trust_valid=True,
        authorization_binding_valid=True,
    ) is False

    # Publication trust invalid -> False
    assert bridge.is_productive_nonzero_recovery_candidate(
        receipt_status=InvocationStatus.EXITED_NONZERO,
        receipt_error_code="CODEX_EXIT_NONZERO",
        pre_branch="ai/task-043",
        post_branch="ai/task-043",
        target_branch="ai/task-043",
        pre_head_sha="a" * 40,
        post_head_sha="a" * 40,
        dirty_paths=("bridge.py",),
        allowed_paths=["bridge.py"],
        publication_trust_valid=False,
        authorization_binding_valid=True,
    ) is False

    # Authorization binding invalid -> False
    assert bridge.is_productive_nonzero_recovery_candidate(
        receipt_status=InvocationStatus.EXITED_NONZERO,
        receipt_error_code="CODEX_EXIT_NONZERO",
        pre_branch="ai/task-043",
        post_branch="ai/task-043",
        target_branch="ai/task-043",
        pre_head_sha="a" * 40,
        post_head_sha="a" * 40,
        dirty_paths=("bridge.py",),
        allowed_paths=["bridge.py"],
        publication_trust_valid=True,
        authorization_binding_valid=False,
    ) is False

    # Empty allowed paths -> False
    assert bridge.is_productive_nonzero_recovery_candidate(
        receipt_status=InvocationStatus.EXITED_NONZERO,
        receipt_error_code="CODEX_EXIT_NONZERO",
        pre_branch="ai/task-043",
        post_branch="ai/task-043",
        target_branch="ai/task-043",
        pre_head_sha="a" * 40,
        post_head_sha="a" * 40,
        dirty_paths=("bridge.py",),
        allowed_paths=[],
        publication_trust_valid=True,
        authorization_binding_valid=True,
    ) is False

    # EXITED_ZERO -> False
    assert bridge.is_productive_nonzero_recovery_candidate(
        receipt_status=InvocationStatus.EXITED_ZERO,
        receipt_error_code=None,
        pre_branch="ai/task-043",
        post_branch="ai/task-043",
        target_branch="ai/task-043",
        pre_head_sha="a" * 40,
        post_head_sha="a" * 40,
        dirty_paths=("bridge.py",),
        allowed_paths=["bridge.py"],
        publication_trust_valid=True,
        authorization_binding_valid=True,
    ) is False

    # TIMED_OUT / INTERRUPTED / FAILED_TO_START -> False
    for st in (InvocationStatus.TIMED_OUT, InvocationStatus.INTERRUPTED, InvocationStatus.FAILED_TO_START):
        assert bridge.is_productive_nonzero_recovery_candidate(
            receipt_status=st,
            receipt_error_code="CODEX_TIMEOUT",
            pre_branch="ai/task-043",
            post_branch="ai/task-043",
            target_branch="ai/task-043",
            pre_head_sha="a" * 40,
            post_head_sha="a" * 40,
            dirty_paths=("bridge.py",),
            allowed_paths=["bridge.py"],
            publication_trust_valid=True,
            authorization_binding_valid=True,
        ) is False

    # Error code not CODEX_EXIT_NONZERO -> False
    assert bridge.is_productive_nonzero_recovery_candidate(
        receipt_status=InvocationStatus.EXITED_NONZERO,
        receipt_error_code="OTHER_ERROR",
        pre_branch="ai/task-043",
        post_branch="ai/task-043",
        target_branch="ai/task-043",
        pre_head_sha="a" * 40,
        post_head_sha="a" * 40,
        dirty_paths=("bridge.py",),
        allowed_paths=["bridge.py"],
        publication_trust_valid=True,
        authorization_binding_valid=True,
    ) is False

    # Branch drift -> False
    assert bridge.is_productive_nonzero_recovery_candidate(
        receipt_status=InvocationStatus.EXITED_NONZERO,
        receipt_error_code="CODEX_EXIT_NONZERO",
        pre_branch="ai/task-043",
        post_branch="ai/task-drift",
        target_branch="ai/task-043",
        pre_head_sha="a" * 40,
        post_head_sha="a" * 40,
        dirty_paths=("bridge.py",),
        allowed_paths=["bridge.py"],
        publication_trust_valid=True,
        authorization_binding_valid=True,
    ) is False

    # Head drift -> False
    assert bridge.is_productive_nonzero_recovery_candidate(
        receipt_status=InvocationStatus.EXITED_NONZERO,
        receipt_error_code="CODEX_EXIT_NONZERO",
        pre_branch="ai/task-043",
        post_branch="ai/task-043",
        target_branch="ai/task-043",
        pre_head_sha="a" * 40,
        post_head_sha="b" * 40,
        dirty_paths=("bridge.py",),
        allowed_paths=["bridge.py"],
        publication_trust_valid=True,
        authorization_binding_valid=True,
    ) is False

    # Empty dirty paths -> False
    assert bridge.is_productive_nonzero_recovery_candidate(
        receipt_status=InvocationStatus.EXITED_NONZERO,
        receipt_error_code="CODEX_EXIT_NONZERO",
        pre_branch="ai/task-043",
        post_branch="ai/task-043",
        target_branch="ai/task-043",
        pre_head_sha="a" * 40,
        post_head_sha="a" * 40,
        dirty_paths=(),
        allowed_paths=["bridge.py"],
        publication_trust_valid=True,
        authorization_binding_valid=True,
    ) is False

    # exact_scope_valid = True explicitly passed -> True
    assert bridge.is_productive_nonzero_recovery_candidate(
        receipt_status=InvocationStatus.EXITED_NONZERO,
        receipt_error_code="CODEX_EXIT_NONZERO",
        pre_branch="ai/task-043",
        post_branch="ai/task-043",
        target_branch="ai/task-043",
        pre_head_sha="a" * 40,
        post_head_sha="a" * 40,
        dirty_paths=("bridge.py",),
        exact_scope_valid=True,
        publication_trust_valid=True,
        authorization_binding_valid=True,
    ) is True

    # exact_scope_valid = False explicitly passed -> False
    assert bridge.is_productive_nonzero_recovery_candidate(
        receipt_status=InvocationStatus.EXITED_NONZERO,
        receipt_error_code="CODEX_EXIT_NONZERO",
        pre_branch="ai/task-043",
        post_branch="ai/task-043",
        target_branch="ai/task-043",
        pre_head_sha="a" * 40,
        post_head_sha="a" * 40,
        dirty_paths=("bridge.py",),
        exact_scope_valid=False,
        publication_trust_valid=True,
        authorization_binding_valid=True,
    ) is False



def test_productive_nonzero_exact_scope_and_green_suite_publishes_for_review(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(
        monkeypatch, tmp_path, status=InvocationStatus.EXITED_NONZERO
    )
    monkeypatch.setattr(bridge, "collect_e4_dirty_paths", lambda: ("bridge.py",))

    res = bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 1
    assert len(calls["publish"]) == 1
    pub_arg = calls["publish"][0]
    assert pub_arg.failure_state == "RECOVERY_REQUIRED"
    assert "E4_TRANSPORT_STATUS: EXITED_NONZERO" in pub_arg.notes
    assert "E4_TRANSPORT_ERROR: CODEX_EXIT_NONZERO" in pub_arg.notes
    assert "E4_TRANSPORT_DIAGNOSTIC: JSON_ERROR_EVENT" in pub_arg.notes
    assert "E4_PRODUCTIVE_NONZERO_RECOVERY: YES" in pub_arg.notes
    assert "EXECUTOR_RERUN: NO" in pub_arg.notes
    assert "E4_ALLOWED_SCOPE_VERIFIED: PASS" in pub_arg.notes
    assert "E4_PUBLICATION_TRUST_VERIFIED: PASS" in pub_arg.notes
    assert "productive non-zero recovery" in pub_arg.summary
    assert res.implementation_sha == "e" * 40


def test_normal_exited_zero_passes_changes_required_failure_state(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(
        monkeypatch, tmp_path, status=InvocationStatus.EXITED_ZERO
    )
    monkeypatch.setattr(bridge, "collect_e4_dirty_paths", lambda: ("bridge.py",))

    res = bridge.cmd_execute(execute_args())
    assert calls["invoke"] == 1
    assert len(calls["publish"]) == 1
    pub_arg = calls["publish"][0]
    assert pub_arg.failure_state == "CHANGES_REQUIRED"


def test_productive_nonzero_post_invocation_auth_mutation_blocks_and_enters_recovery(monkeypatch, tmp_path):
    auth, _, calls = make_execute_environment(
        monkeypatch, tmp_path, status=InvocationStatus.EXITED_NONZERO
    )
    monkeypatch.setattr(bridge, "collect_e4_dirty_paths", lambda: ("bridge.py",))

    # Simulate post-invocation auth modification
    calls_count = 0

    def get_auth_sequence(task_id):
        nonlocal calls_count
        calls_count += 1
        if calls_count == 1:
            return auth
        return {**auth, "executor_id": "codex_mutated"}

    monkeypatch.setattr(bridge, "get_active_authorization", get_auth_sequence)

    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())

    assert calls["invoke"] == 1
    assert calls["publish"] == []
    assert calls["state"][-1][0] == "RECOVERY_REQUIRED"


def test_productive_nonzero_out_of_scope_dirty_path_does_not_publish_and_enters_recovery(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(
        monkeypatch, tmp_path, status=InvocationStatus.EXITED_NONZERO
    )
    monkeypatch.setattr(bridge, "collect_e4_dirty_paths", lambda: ("unauthorized.txt",))

    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())

    assert calls["invoke"] == 1
    assert calls["publish"] == []
    assert calls["state"][-1][0] == "RECOVERY_REQUIRED"


def test_productive_nonzero_branch_drift_does_not_publish(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(
        monkeypatch, tmp_path, status=InvocationStatus.EXITED_NONZERO
    )
    monkeypatch.setattr(bridge, "collect_e4_dirty_paths", lambda: ("bridge.py",))
    monkeypatch.setattr(bridge, "observe_e4_branch", lambda: "ai/task-drift")

    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())

    assert calls["invoke"] == 1
    assert calls["publish"] == []
    assert calls["state"][-1][0] == "RECOVERY_REQUIRED"


def test_productive_nonzero_head_drift_does_not_publish(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(
        monkeypatch, tmp_path, status=InvocationStatus.EXITED_NONZERO
    )
    monkeypatch.setattr(bridge, "collect_e4_dirty_paths", lambda: ("bridge.py",))
    observations = iter(("b" * 40, "c" * 40))
    monkeypatch.setattr(bridge, "observe_e4_head", lambda: next(observations))

    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())

    assert calls["invoke"] == 1
    assert calls["publish"] == []
    assert calls["state"][-1][0] == "RECOVERY_REQUIRED"


def test_productive_nonzero_empty_delta_fails_closed_without_publish(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(
        monkeypatch, tmp_path, status=InvocationStatus.EXITED_NONZERO
    )
    monkeypatch.setattr(bridge, "collect_e4_dirty_paths", lambda: ())

    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())

    assert calls["invoke"] == 1
    assert calls["publish"] == []
    assert calls["state"][-1][0] == "RECOVERY_REQUIRED"


def test_productive_nonzero_contract_order_exact_scope_validator_runs_before_predicate(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(
        monkeypatch, tmp_path, status=InvocationStatus.EXITED_NONZERO
    )
    monkeypatch.setattr(bridge, "collect_e4_dirty_paths", lambda: ("bridge.py",))

    call_order = []

    orig_validate = bridge.validate_executor_worktree_delta
    def tracked_validate(*args, **kwargs):
        call_order.append("validate_executor_worktree_delta")
        return orig_validate(*args, **kwargs)

    orig_predicate = bridge.is_productive_nonzero_recovery_candidate
    def tracked_predicate(*args, **kwargs):
        call_order.append("is_productive_nonzero_recovery_candidate")
        assert "validate_executor_worktree_delta" in call_order
        return orig_predicate(*args, **kwargs)

    monkeypatch.setattr(bridge, "validate_executor_worktree_delta", tracked_validate)
    monkeypatch.setattr(bridge, "is_productive_nonzero_recovery_candidate", tracked_predicate)

    res = bridge.cmd_execute(execute_args())
    assert call_order == ["validate_executor_worktree_delta", "is_productive_nonzero_recovery_candidate"]
    assert calls["invoke"] == 1
    assert len(calls["publish"]) == 1


def test_productive_nonzero_exact_scope_failure_blocks_before_predicate(monkeypatch, tmp_path):
    _, _, calls = make_execute_environment(
        monkeypatch, tmp_path, status=InvocationStatus.EXITED_NONZERO
    )
    monkeypatch.setattr(bridge, "collect_e4_dirty_paths", lambda: ("unauthorized.txt",))

    predicate_called = []
    def tracked_predicate(*args, **kwargs):
        predicate_called.append(True)
        return True

    monkeypatch.setattr(bridge, "is_productive_nonzero_recovery_candidate", tracked_predicate)

    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())

    assert not predicate_called
    assert calls["invoke"] == 1
    assert calls["publish"] == []
    assert calls["state"][-1][0] == "RECOVERY_REQUIRED"



def _setup_real_publish_repo(monkeypatch, tmp_path, *, action="FIX", task_id=43):
    repo = tmp_path / "publish_repo"
    init_publication_repo(repo)
    monkeypatch.setattr(bridge, "PROJECT", repo)
    monkeypatch.setattr(bridge, "AI", repo / ".ai")

    runtime = tmp_path / "publish_runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(bridge, "get_runtime_dir", lambda repo_root=None: runtime)

    cfg = {
        "remote": "origin",
        "control_branch": "ai-control",
        "base_branch": "main",
        "task_branch_prefix": "ai/task-",
    }
    bridge.save_json(runtime / "config.json", cfg)

    task_branch = f"ai/task-{task_id:03d}"
    subprocess.run(["git", "checkout", "-qb", task_branch], cwd=repo, check=True)
    (repo / "bridge.py").write_text("# candidate change\n", encoding="utf-8")

    op = ExecutionOperation(action)
    art_path = f".ai/reviews/REVIEW-{task_id:03d}.md" if action == "FIX" else f".ai/tasks/TASK-{task_id:03d}.md"
    lease = bridge.build_executor_lease_candidate(
        task_id=f"TASK-{task_id:03d}",
        workspace_id=bridge.get_workspace_id(repo),
        operation=op,
        target_branch=task_branch,
        authorized_artifact_path=art_path,
        authorized_artifact_blob_sha="a" * 40,
        executor_id="antigravity",
    )
    store = bridge.get_lease_store(repo)
    store.acquire(lease)

    auth = {
        "task_id": f"TASK-{task_id:03d}",
        "action": action,
        "kind": "REVIEW" if action == "FIX" else "TASK",
        "artifact_path": art_path,
        "artifact_blob_sha": "a" * 40,
        "approved_at": bridge.now(),
        "branch": task_branch,
        "status": "ACTIVE",
        "executor_id": "antigravity",
        "lease_id": lease.lease_id,
        "lease_fingerprint": lease.fingerprint(),
        "workspace_id": bridge.get_workspace_id(repo),
        "execution_fingerprint": lease.execution_fingerprint,
    }
    bridge.save_authorization(task_id, auth)

    monkeypatch.setattr(bridge, "fetch_control", lambda c: None)
    monkeypatch.setattr(bridge, "get_remote_blob_sha", lambda c, path: "a" * 40)
    monkeypatch.setattr(
        bridge,
        "read_remote_file",
        lambda c, path: "STATUS: CHANGES_REQUIRED\n" if action == "FIX" else "STATUS: ACTIVE\n",
    )

    return repo, auth, lease, runtime


def test_real_cmd_publish_productive_nonzero_test_failure_updates_recovery_required(monkeypatch, tmp_path):
    repo, auth, lease, runtime = _setup_real_publish_repo(monkeypatch, tmp_path)

    publish_args = argparse.Namespace(
        task_id=43,
        action="FIX",
        test=f'"{sys.executable}" -c "import sys; sys.exit(1)"',
        summary="summary",
        notes="notes",
        message=None,
        failure_state="RECOVERY_REQUIRED",
    )

    with pytest.raises(SystemExit) as exc:
        bridge.cmd_publish(publish_args)
    assert exc.value.code == 1

    # Authorization must NOT be consumed; work preserved
    saved_auth = bridge.load_authorization(43)
    assert saved_auth["status"] == "ACTIVE"
    state = bridge.load_json(runtime / "state" / "CURRENT_STATE.json")
    assert state["status"] == "RECOVERY_REQUIRED"
    assert "Tests failed" in state["next_step"]


def test_real_cmd_publish_normal_exited_zero_test_failure_updates_changes_required(monkeypatch, tmp_path):
    repo, auth, lease, runtime = _setup_real_publish_repo(monkeypatch, tmp_path)

    publish_args = argparse.Namespace(
        task_id=43,
        action="FIX",
        test=f'"{sys.executable}" -c "import sys; sys.exit(1)"',
        summary="summary",
        notes="notes",
        message=None,
        failure_state="CHANGES_REQUIRED",
    )

    with pytest.raises(SystemExit) as exc:
        bridge.cmd_publish(publish_args)
    assert exc.value.code == 1

    saved_auth = bridge.load_authorization(43)
    assert saved_auth["status"] == "ACTIVE"
    state = bridge.load_json(runtime / "state" / "CURRENT_STATE.json")
    assert state["status"] == "CHANGES_REQUIRED"
    assert "Tests failed" in state["next_step"]


def test_real_cmd_publish_post_test_git_admin_drift_blocks_with_work_preserved(monkeypatch, tmp_path):
    repo, auth, lease, runtime = _setup_real_publish_repo(monkeypatch, tmp_path)
    snapshot = bridge.capture_e4_publication_trust_snapshot("origin")

    mutator = tmp_path / "mutate_git_admin.py"
    mutator.write_text(
        "import subprocess, sys\n"
        "subprocess.run(['git', 'config', 'core.hooksPath', 'injected_hooks'], check=True)\n"
        "sys.exit(0)\n",
        encoding="utf-8",
    )
    publish_args = argparse.Namespace(
        task_id=43,
        action="FIX",
        test=f'"{sys.executable}" "{mutator}"',
        summary="summary",
        notes="notes",
        message=None,
        failure_state="RECOVERY_REQUIRED",
        publication_trust_snapshot=snapshot,
        allowed_paths=["bridge.py"],
    )

    with pytest.raises(SystemExit) as exc:
        bridge.cmd_publish(publish_args)
    assert exc.value.code == 1

    saved_auth = bridge.load_authorization(43)
    assert saved_auth["status"] == "ACTIVE"
    state = bridge.load_json(runtime / "state" / "CURRENT_STATE.json")
    assert state["status"] == "RECOVERY_REQUIRED"
    assert "E4 protected Git administration drifted during test execution" in state["next_step"]


def test_real_cmd_publish_post_test_out_of_scope_dirty_path_blocks_with_work_preserved(monkeypatch, tmp_path):
    repo, auth, lease, runtime = _setup_real_publish_repo(monkeypatch, tmp_path)
    snapshot = bridge.capture_e4_publication_trust_snapshot("origin")

    mutator = tmp_path / "mutate_scope.py"
    mutator.write_text(
        "import pathlib, sys\n"
        "pathlib.Path('unauthorized_leak.py').write_text('leak\\n', encoding='utf-8')\n"
        "sys.exit(0)\n",
        encoding="utf-8",
    )
    publish_args = argparse.Namespace(
        task_id=43,
        action="FIX",
        test=f'"{sys.executable}" "{mutator}"',
        summary="summary",
        notes="notes",
        message=None,
        failure_state="RECOVERY_REQUIRED",
        publication_trust_snapshot=snapshot,
        allowed_paths=["bridge.py"],
    )

    with pytest.raises(SystemExit) as exc:
        bridge.cmd_publish(publish_args)
    assert exc.value.code == 1

    saved_auth = bridge.load_authorization(43)
    assert saved_auth["status"] == "ACTIVE"
    state = bridge.load_json(runtime / "state" / "CURRENT_STATE.json")
    assert state["status"] == "RECOVERY_REQUIRED"
    assert "Dirty paths violated allowed scope during test execution" in state["next_step"]


def test_real_cmd_publish_post_test_head_drift_blocks_with_work_preserved(monkeypatch, tmp_path):
    repo, auth, lease, runtime = _setup_real_publish_repo(monkeypatch, tmp_path)
    snapshot = bridge.capture_e4_publication_trust_snapshot("origin")
    pre_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, text=True, capture_output=True, check=True).stdout.strip()

    mutator = tmp_path / "mutate_head.py"
    mutator.write_text(
        "import subprocess, sys\n"
        "subprocess.run(['git', 'commit', '--allow-empty', '-m', 'illicit commit'], check=True)\n"
        "sys.exit(0)\n",
        encoding="utf-8",
    )
    publish_args = argparse.Namespace(
        task_id=43,
        action="FIX",
        test=f'"{sys.executable}" "{mutator}"',
        summary="summary",
        notes="notes",
        message=None,
        failure_state="RECOVERY_REQUIRED",
        publication_trust_snapshot=snapshot,
        allowed_paths=["bridge.py"],
        pre_head_sha=pre_sha,
    )

    with pytest.raises(SystemExit) as exc:
        bridge.cmd_publish(publish_args)
    assert exc.value.code == 1

    saved_auth = bridge.load_authorization(43)
    assert saved_auth["status"] == "ACTIVE"
    state = bridge.load_json(runtime / "state" / "CURRENT_STATE.json")
    assert state["status"] == "RECOVERY_REQUIRED"
    assert "Task branch HEAD drifted" in state["next_step"]


def test_real_cmd_publish_post_test_auth_mutation_blocks_with_work_preserved(monkeypatch, tmp_path):
    repo, auth, lease, runtime = _setup_real_publish_repo(monkeypatch, tmp_path)
    snapshot = bridge.capture_e4_publication_trust_snapshot("origin")
    pre_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, text=True, capture_output=True, check=True).stdout.strip()

    # Test mutates the runtime auth file directly
    auth_file = runtime / "auth" / "AUTH-TASK-043.json"
    mutator = tmp_path / "mutate_auth.py"
    mutator.write_text(
        f"import json, pathlib, sys\n"
        f"p = pathlib.Path(r'{auth_file}')\n"
        f"d = json.loads(p.read_text(encoding='utf-8'))\n"
        f"d['executor_id'] = 'attacker'\n"
        f"p.write_text(json.dumps(d), encoding='utf-8')\n"
        f"sys.exit(0)\n",
        encoding="utf-8",
    )
    publish_args = argparse.Namespace(
        task_id=43,
        action="FIX",
        test=f'"{sys.executable}" "{mutator}"',
        summary="summary",
        notes="notes",
        message=None,
        failure_state="RECOVERY_REQUIRED",
        publication_trust_snapshot=snapshot,
        allowed_paths=["bridge.py"],
        pre_head_sha=pre_sha,
    )

    with pytest.raises(SystemExit) as exc:
        bridge.cmd_publish(publish_args)
    assert exc.value.code == 1

    state = bridge.load_json(runtime / "state" / "CURRENT_STATE.json")
    assert state["status"] == "RECOVERY_REQUIRED"
    assert "E4 authorization or lease binding drifted during test execution" in state["next_step"]


def test_clean_timeout_persists_evidence_blocks_publication_and_sets_blocked_state(monkeypatch, tmp_path):
    """Integration proof: CLEAN_TIMEOUT_NO_RESULT_PUBLICATION & structured evidence persistence."""
    auth, _, calls = make_execute_environment(monkeypatch, tmp_path, status=InvocationStatus.TIMED_OUT)
    monkeypatch.setattr(bridge, "collect_e4_dirty_paths", lambda: ())

    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())

    assert calls["invoke"] == 1
    assert calls["publish"] == []
    last_state = calls["state"][-1]
    assert last_state[0] == "EXECUTION_BLOCKED"
    assert "CLEAN_TIMEOUT" in last_state[1]
    assert "HUMAN_DECISION_REQUIRED_CLEAN_TIMEOUT" in last_state[1]

    # Verify structured evidence persisted into authorization
    assert len(calls["auth_saved"]) >= 1
    _, saved_auth = calls["auth_saved"][-1]
    assert "worker_failure_evidence" in saved_auth
    ev = saved_auth["worker_failure_evidence"]
    assert ev["failure_class"] == "CLEAN_TIMEOUT"
    assert ev["next_action"] == "HUMAN_DECISION_REQUIRED_CLEAN_TIMEOUT"
    assert ev["zero_worktree_delta"] is True


def test_dirty_timeout_persists_evidence_and_preserves_worktree(monkeypatch, tmp_path):
    """Integration proof: DIRTY_TIMEOUT_BLOCKS_FRESH_EXECUTOR_START & DIRTY_TIMEOUT_DOES_NOT_AUTO_RESET_STASH_COMMIT."""
    auth, _, calls = make_execute_environment(monkeypatch, tmp_path, status=InvocationStatus.TIMED_OUT)
    monkeypatch.setattr(bridge, "collect_e4_dirty_paths", lambda: ("bridge.py",))

    with pytest.raises(SystemExit):
        bridge.cmd_execute(execute_args())

    assert calls["invoke"] == 1
    assert calls["publish"] == []
    # Lease is retained, state is RECOVERY_REQUIRED
    last_state = calls["state"][-1]
    assert last_state[0] == "RECOVERY_REQUIRED"
    assert "DIRTY_TIMEOUT_RECOVERY_REQUIRED" in last_state[1]
    assert "RECOVERY_REQUIRED_PRESERVED_DELTA" in last_state[1]

    # Verify structured evidence persisted into authorization
    assert len(calls["auth_saved"]) >= 1
    _, saved_auth = calls["auth_saved"][-1]
    assert "worker_failure_evidence" in saved_auth
    ev = saved_auth["worker_failure_evidence"]
    assert ev["failure_class"] == "DIRTY_TIMEOUT_RECOVERY_REQUIRED"
    assert ev["next_action"] == "RECOVERY_REQUIRED_PRESERVED_DELTA"
    assert ev["zero_worktree_delta"] is False
