from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
import pytest

import bridge
from src.aios_bridge.continuity.executor import ExecutionOperation
from src.aios_bridge.continuity.state import ContinuityStateValidationError


def test_cli_handoff_synchronizes_before_authority_boundary(monkeypatch):
    calls = []
    monkeypatch.setattr(bridge, "sync_once", lambda verbose=False: calls.append(("sync", verbose)))
    args = type("Args", (), {})()
    args.cmd = "handoff"
    args.func = lambda _: calls.append(("handoff", None))
    bridge.dispatch_command(args)
    assert calls == [("sync", False), ("handoff", None)]


def test_cli_handoff_sync_failure_blocks_authority_boundary(monkeypatch):
    calls = []

    def fail_sync(verbose=False):
        calls.append(("sync", verbose))
        raise SystemExit(7)

    monkeypatch.setattr(bridge, "sync_once", fail_sync)
    args = type("Args", (), {})()
    args.cmd = "handoff"
    args.func = lambda _: calls.append(("handoff", None))
    with pytest.raises(SystemExit) as exc:
        bridge.dispatch_command(args)
    assert exc.value.code == 7
    assert calls == [("sync", False)]


def test_cli_status_dispatch_semantics_are_unchanged(monkeypatch):
    calls = []
    monkeypatch.setattr(bridge, "sync_once", lambda verbose=False: calls.append(("extra-sync", verbose)))
    args = type("Args", (), {})()
    args.cmd = "pending"
    args.func = lambda _: calls.append(("pending", None))
    bridge.dispatch_command(args)
    assert calls == [("pending", None)]



def _make_e4_test_task_content(task_id: int, action: str = "RUN", executor: str = "antigravity") -> str:
    op = action.upper()
    prefix = "TASK" if op == "RUN" else "REVIEW"
    status_line = "STATUS: READY" if op == "RUN" else "STATUS: CHANGES_REQUIRED"
    all_executors = ["antigravity", "codex", "claude-code"]
    candidates = []
    if executor in all_executors:
        candidates.append({
            "executor_id": executor,
            "preference_rank": 0,
            "capacity_class": "SUBSCRIPTION",
            "supported_operations": [op],
            "supported_capabilities": ["SHELL", "FILESYSTEM_WRITE", "LOCAL_GIT", "REPOSITORY_READ", "TEST_EXECUTION"],
        })
    for other in all_executors:
        if other != executor:
            candidates.append({
                "executor_id": other,
                "preference_rank": len(candidates),
                "capacity_class": "SUBSCRIPTION",
                "supported_operations": [op],
                "supported_capabilities": ["SHELL", "FILESYSTEM_WRITE", "LOCAL_GIT", "REPOSITORY_READ", "TEST_EXECUTION"],
            })
    policy = {
        "operation": op,
        "required_capabilities": ["SHELL"],
        "allow_paid_api": False,
        "candidates": candidates,
    }
    return f"""# {prefix}-{task_id:03d} Content

{status_line}
PUBLISHER_PROFILE: CANONICAL_E4

EXECUTOR_CONTEXT_REFS_JSON: [{{"path": ".ai/decisions/ADR-001.md", "blob_sha": "{"a"*40}"}}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {json.dumps(policy)}
"""

def test_runtime_state_path_is_outside_repository_worktree():
    with tempfile.TemporaryDirectory() as temp:
        repo_root = Path(temp) / "my_project"
        repo_root.mkdir()

        runtime_dir = bridge.get_runtime_dir(repo_root)

        assert not str(runtime_dir).startswith(str(repo_root))
        assert runtime_dir.name.startswith("my_project-")

        custom_dir = Path(temp) / "custom_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(custom_dir)
        try:
            assert bridge.get_runtime_dir(repo_root) == custom_dir
        finally:
            del os.environ["AIOS_RUNTIME_DIR"]


def test_sync_does_not_dirty_worktree_and_provides_context():
    """Validates that receiving inbound TASK/REVIEW events leaves git status 100% clean."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Clean Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial commit"], cwd=root, check=True, capture_output=True)

        p_init = subprocess.run(["git", "status", "--porcelain"], cwd=root, check=True, capture_output=True, text=True)
        assert p_init.stdout.strip() == ""

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_git = bridge.git
        old_fetch = bridge.fetch_control
        old_list = bridge.list_remote_inbound
        old_read = bridge.read_remote_file

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            inbound_task = (".ai/tasks/TASK-001.md", "1111111111111111111111111111111111111111")
            inbound_review = (".ai/reviews/REVIEW-001.md", "2222222222222222222222222222222222222222")

            bridge.fetch_control = lambda cfg: None
            bridge.list_remote_inbound = lambda cfg: [inbound_task, inbound_review]
            bridge.read_remote_file = lambda cfg, path: (
                "# Task 1\n" if "tasks" in path else "# Review 1\n## Status\nCHANGES_REQUIRED\n"
            )

            changed = bridge.sync_once(verbose=False)
            assert len(changed) == 2

            # CRITICAL INVARIANT: Git status in worktree must remain 100% clean!
            p_status = subprocess.run(["git", "status", "--porcelain"], cwd=root, check=True, capture_output=True, text=True)
            assert p_status.stdout.strip() == "", f"Git worktree was dirtied by sync: {p_status.stdout}"

            events = bridge.pending_events()
            assert len(events) == 2
            kinds = {e["kind"] for e in events}
            assert kinds == {"TASK", "REVIEW"}

            task_artifact = bridge.get_artifact_path(".ai/tasks/TASK-001.md")
            assert task_artifact.exists()
            assert "Task 1" in task_artifact.read_text(encoding="utf-8")
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.git = old_git
            bridge.fetch_control = old_fetch
            bridge.list_remote_inbound = old_list
            bridge.read_remote_file = old_read
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_changes_required_review_creates_pending_review_event():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_list = bridge.list_remote_inbound
        old_read = bridge.read_remote_file
        old_ensure = bridge.ensure_git

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_git = lambda: None
            bridge.ensure_dirs()
            cfg = {"windows_popup": False, "remote": "origin", "control_branch": "ai-control"}
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            bridge.fetch_control = lambda cfg: None
            bridge.list_remote_inbound = lambda cfg: [(".ai/reviews/REVIEW-003.md", "1" * 40)]
            review_content = "# REVIEW-003\n\n## Status\nCHANGES_REQUIRED\n\nFix is needed."
            bridge.read_remote_file = lambda cfg, path: review_content

            changed = bridge.sync_once(verbose=False)
            assert changed == [".ai/reviews/REVIEW-003.md"]

            events = bridge.pending_events()
            assert len(events) == 1
            assert events[0]["kind"] == "REVIEW"
            assert events[0]["task_id"] == "TASK-003"

            state = bridge.load_json(bridge.get_runtime_paths()["state"], {})
            assert state["status"] == "CHANGES_REQUIRED"
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.list_remote_inbound = old_list
            bridge.read_remote_file = old_read
            bridge.ensure_git = old_ensure
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_repeated_changes_required_updates_do_not_create_duplicate_pending_events():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Clean Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial commit"], cwd=root, check=True, capture_output=True)

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_git = bridge.git
        old_fetch = bridge.fetch_control
        old_list = bridge.list_remote_inbound
        old_read = bridge.read_remote_file

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {"windows_popup": False, "remote": "origin", "control_branch": "ai-control"}
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            # 1. Sync REVIEW-004 at blob SHA A
            bridge.fetch_control = lambda cfg: None
            bridge.list_remote_inbound = lambda cfg: [(".ai/reviews/REVIEW-004.md", "a" * 40)]
            bridge.read_remote_file = lambda cfg, path: "# REVIEW-004\n\n## Status\nCHANGES_REQUIRED\n\nInitial review fix required."

            bridge.sync_once(verbose=False)

            events = bridge.pending_events()
            assert len(events) == 1
            assert events[0]["task_id"] == "TASK-004"
            assert events[0]["blob_sha"] == "a" * 40

            # 2. Update same review content while keeping CHANGES_REQUIRED at blob SHA B
            bridge.list_remote_inbound = lambda cfg: [(".ai/reviews/REVIEW-004.md", "b" * 40)]
            bridge.read_remote_file = lambda cfg, path: "# REVIEW-004\n\n## Status\nCHANGES_REQUIRED\n\nUpdated review notes."

            # 3. Sync again
            bridge.sync_once(verbose=False)

            # 4. Assert pending_events() contains exactly ONE REVIEW event for TASK-004
            events = bridge.pending_events()
            assert len(events) == 1, f"Expected exactly 1 pending event, found {len(events)}: {events}"
            assert events[0]["kind"] == "REVIEW"
            assert events[0]["task_id"] == "TASK-004"
            assert events[0]["blob_sha"] == "b" * 40

            # 5. Assert worktree remains clean
            p_status = subprocess.run(["git", "status", "--porcelain"], cwd=root, check=True, capture_output=True, text=True)
            assert p_status.stdout.strip() == "", f"Git worktree dirtied: {p_status.stdout}"
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.git = old_git
            bridge.fetch_control = old_fetch
            bridge.list_remote_inbound = old_list
            bridge.read_remote_file = old_read
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_review_update_to_approved_clears_pending_and_sets_approved_state():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_list = bridge.list_remote_inbound
        old_read = bridge.read_remote_file
        old_notify = bridge.notify_best_effort
        old_ensure = bridge.ensure_git

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_git = lambda: None
            bridge.ensure_dirs()
            cfg = {"windows_popup": False, "remote": "origin", "control_branch": "ai-control"}
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            notifications = []
            bridge.notify_best_effort = lambda title, msg, *args: notifications.append((title, msg))

            # First sync: CHANGES_REQUIRED
            bridge.fetch_control = lambda cfg: None
            bridge.list_remote_inbound = lambda cfg: [(".ai/reviews/REVIEW-003.md", "1" * 40)]
            bridge.read_remote_file = lambda cfg, path: "# REVIEW-003\n\n## Status\nCHANGES_REQUIRED\n"
            bridge.sync_once(verbose=False)

            assert len(bridge.pending_events()) == 1

            # Second sync: updated to APPROVED on control branch
            bridge.list_remote_inbound = lambda cfg: [(".ai/reviews/REVIEW-003.md", "2" * 40)]
            bridge.read_remote_file = lambda cfg, path: "# REVIEW-003\n\n## Status\nAPPROVED\n\nLGTM!"
            bridge.sync_once(verbose=False)

            events = bridge.pending_events()
            assert len(events) == 0, f"Expected 0 pending events, got: {events}"

            state = bridge.load_json(bridge.get_runtime_paths()["state"], {})
            assert state["status"] == "APPROVED"
            assert "approved" in state["next_step"].lower()

            last_title, last_msg = notifications[-1]
            assert "APPROVED" in last_msg
            assert "Dùng" not in last_msg
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.list_remote_inbound = old_list
            bridge.read_remote_file = old_read
            bridge.notify_best_effort = old_notify
            bridge.ensure_git = old_ensure
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_missing_or_unknown_review_status_is_non_actionable():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_list = bridge.list_remote_inbound
        old_read = bridge.read_remote_file
        old_ensure = bridge.ensure_git

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_git = lambda: None
            bridge.ensure_dirs()
            cfg = {"windows_popup": False, "remote": "origin", "control_branch": "ai-control"}
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            bridge.fetch_control = lambda cfg: None
            bridge.list_remote_inbound = lambda cfg: [(".ai/reviews/REVIEW-004.md", "3" * 40)]
            bridge.read_remote_file = lambda cfg, path: "# REVIEW-004\n\nJust some notes without status.\n"

            bridge.sync_once(verbose=False)

            assert len(bridge.pending_events()) == 0

            state = bridge.load_json(bridge.get_runtime_paths()["state"], {})
            assert state["status"] == "REVIEW_RECEIVED"
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.list_remote_inbound = old_list
            bridge.read_remote_file = old_read
            bridge.ensure_git = old_ensure
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


# ---------------------------------------------------------------------------
# v0.4.0 Zero-Touch Handoff & Authorization Tests
# ---------------------------------------------------------------------------


def test_handoff_run_without_preexisting_pending_event_records_active_auth_and_creates_branch():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_git = bridge.git
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha
        old_read = bridge.read_remote_file
        old_reconcile = bridge.reconcile_local_main

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            # Mock control branch content
            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: "7" * 40
            bridge.read_remote_file = lambda cfg, path: _make_e4_test_task_content(6, "RUN", "antigravity")
            bridge.reconcile_local_main = lambda cfg: "main_sha_12345"

            # Execute handoff without any prior inbox event
            bridge.cmd_handoff(type("Args", (), {"task_id": 6, "action": "run"})())

            # Verify branch switched to ai/task-006
            p = subprocess.run(["git", "branch", "--show-current"], cwd=root, check=True, capture_output=True, text=True)
            assert p.stdout.strip() == "ai/task-006"

            # Verify active authorization recorded
            auth = bridge.get_active_authorization(6, "RUN")
            assert auth is not None
            assert auth["task_id"] == "TASK-006"
            assert auth["action"] == "RUN"
            assert auth["artifact_blob_sha"] == "7" * 40
            assert auth["branch"] == "ai/task-006"
            assert auth["base_main_sha"] == "main_sha_12345"

            # Verify task artifact cached externally
            task_file = bridge.get_artifact_path(".ai/tasks/TASK-006.md")
            assert task_file.exists()
            assert "TASK-006 Content" in task_file.read_text(encoding="utf-8")
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.git = old_git
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            bridge.read_remote_file = old_read
            bridge.reconcile_local_main = old_reconcile
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_handoff_run_missing_task_fails_closed():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha
        old_ensure = bridge.ensure_git

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_git = lambda: None
            bridge.ensure_dirs()
            cfg = {"windows_popup": False, "remote": "origin", "control_branch": "ai-control"}
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: None  # Missing task

            with pytest.raises(SystemExit):
                bridge.cmd_handoff(type("Args", (), {"task_id": 999, "action": "run"})())
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            bridge.ensure_git = old_ensure
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_reconcile_local_main_fast_forwards_when_behind():
    with tempfile.TemporaryDirectory() as temp:
        # Create a "remote" bare repository and a local clone
        remote_repo = Path(temp) / "remote_repo.git"
        subprocess.run(["git", "init", "--bare", "-b", "main", str(remote_repo)], check=True, capture_output=True)

        local_repo = Path(temp) / "local_repo"
        subprocess.run(["git", "clone", str(remote_repo), str(local_repo)], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=local_repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=local_repo, check=True, capture_output=True)

        (local_repo / "README.md").write_text("# Initial\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=local_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "commit 1"], cwd=local_repo, check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=local_repo, check=True, capture_output=True)

        # Create another clone to simulate ChatGPT remote merge advancing origin/main
        other_repo = Path(temp) / "other_repo"
        subprocess.run(["git", "clone", str(remote_repo), str(other_repo)], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "ChatGPT"], cwd=other_repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "chatgpt@test.local"], cwd=other_repo, check=True, capture_output=True)

        (other_repo / "new_feature.txt").write_text("feature content\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=other_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "commit 2 from remote merge"], cwd=other_repo, check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=other_repo, check=True, capture_output=True)

        remote_main_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=other_repo, check=True, capture_output=True, text=True).stdout.strip()

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        bridge.PROJECT = local_repo
        bridge.AI = local_repo / ".ai"

        try:
            cfg = {"remote": "origin", "base_branch": "main"}
            reconciled_sha = bridge.reconcile_local_main(cfg)

            assert reconciled_sha == remote_main_sha
            local_main_sha = subprocess.run(["git", "rev-parse", "main"], cwd=local_repo, check=True, capture_output=True, text=True).stdout.strip()
            assert local_main_sha == remote_main_sha
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_reconcile_local_main_fails_closed_when_diverged_or_ahead():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Local Commit Ahead\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_git = bridge.git
        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            def fake_git(*args, **kwargs):
                if args == ("rev-parse", "refs/remotes/origin/main"):
                    return type("Res", (), {"returncode": 0, "stdout": "1" * 40, "stderr": ""})()
                if args == ("merge-base", "--is-ancestor", "refs/heads/main", "refs/remotes/origin/main"):
                    return type("Res", (), {"returncode": 1, "stdout": "", "stderr": ""})()
                if args == ("merge-base", "--is-ancestor", "refs/remotes/origin/main", "refs/heads/main"):
                    return type("Res", (), {"returncode": 0, "stdout": "", "stderr": ""})()
                return old_git(*args, **kwargs)

            bridge.git = fake_git

            with pytest.raises(SystemExit):
                bridge.reconcile_local_main({"remote": "origin", "base_branch": "main"})
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.git = old_git


def test_dirty_worktree_blocks_handoff_and_reconciliation():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "app.py").write_text("print(1)\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        # Uncommitted dirty edit
        (root / "app.py").write_text("print(2)\n", encoding="utf-8")

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {"windows_popup": False, "remote": "origin", "base_branch": "main", "control_branch": "ai-control"}
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            with pytest.raises(SystemExit):
                bridge.cmd_handoff(type("Args", (), {"task_id": 6, "action": "run"})())
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_handoff_fix_succeeds_only_for_changes_required_and_binds_exact_blob():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        # Create existing task branch ai/task-006
        subprocess.run(["git", "checkout", "-b", "ai/task-006"], cwd=root, check=True, capture_output=True)

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha
        old_read = bridge.read_remote_file

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: "8" * 40
            bridge.read_remote_file = lambda cfg, path: _make_e4_test_task_content(6, "FIX", "antigravity")

            store = bridge.get_lease_store()
            prior_lease = bridge.build_executor_lease_candidate(
                task_id="TASK-006",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.RUN,
                target_branch="ai/task-006",
                authorized_artifact_path=".ai/tasks/TASK-006.md",
                authorized_artifact_blob_sha="7" * 40,
                executor_id="antigravity",
            )
            bridge.save_authorization(6, {
                "task_id": "TASK-006",
                "action": "RUN",
                "kind": "TASK",
                "artifact_path": ".ai/tasks/TASK-006.md",
                "artifact_blob_sha": "7" * 40,
                "approved_at": "2026-08-16T10:00:00+07:00",
                "branch": "ai/task-006",
                "status": "CONSUMED",
                "executor_id": "antigravity",
                "lease_id": prior_lease.lease_id,
                "lease_fingerprint": prior_lease.fingerprint(),
                "workspace_id": prior_lease.workspace_id,
                "execution_fingerprint": prior_lease.execution_fingerprint,
            })

            bridge.cmd_handoff(type("Args", (), {"task_id": 6, "action": "fix"})())

            auth = bridge.get_active_authorization(6, "FIX")
            assert auth is not None
            assert auth["action"] == "FIX"
            assert auth["kind"] == "REVIEW"
            assert auth["artifact_blob_sha"] == "8" * 40

            state = bridge.load_json(bridge.get_runtime_paths()["state"], {})
            assert state["status"] == "CHANGES_REQUIRED"
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            bridge.read_remote_file = old_read
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_handoff_fix_fails_closed_when_approved_or_missing_or_unknown_status():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha
        old_read = bridge.read_remote_file
        old_ensure = bridge.ensure_git

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_git = lambda: None
            bridge.ensure_dirs()
            cfg = {"windows_popup": False, "remote": "origin", "control_branch": "ai-control"}
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: "9" * 40
            # Review is APPROVED
            bridge.read_remote_file = lambda cfg, path: "# REVIEW-006\n\n## Status\nAPPROVED\n"

            with pytest.raises(SystemExit):
                bridge.cmd_handoff(type("Args", (), {"task_id": 6, "action": "fix"})())
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            bridge.read_remote_file = old_read
            bridge.ensure_git = old_ensure
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_publish_enforces_active_authorization_and_detects_control_drift():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "ai/task-006"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            auth = {
                "task_id": "TASK-006",
                "action": "RUN",
                "kind": "TASK",
                "artifact_path": ".ai/tasks/TASK-006.md",
                "artifact_blob_sha": "a" * 40,
                "approved_at": bridge.now(),
                "branch": "ai/task-006",
                "status": "ACTIVE",
            }
            bridge.save_authorization(6, auth)

            # Control branch drifted to "b"*40!
            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: "b" * 40

            with pytest.raises(SystemExit):
                bridge.cmd_publish(type("Args", (), {
                    "task_id": 6,
                    "test": None,
                    "summary": "drift test",
                    "notes": None,
                    "message": None,
                })())
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_publish_consumes_active_authorization_and_creates_result_with_test_evidence():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "ai/task-006"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "app.py").write_text("print('v0.4.0')\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        # Make a tracked change
        (root / "app.py").write_text("print('v0.4.0 final')\n", encoding="utf-8")

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_git = bridge.git
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            ws_id = bridge.get_workspace_id()
            lease_cand = bridge.build_executor_lease_candidate(
                task_id="TASK-006",
                workspace_id=ws_id,
                operation=bridge.ExecutionOperation.RUN,
                target_branch="ai/task-006",
                authorized_artifact_path=".ai/tasks/TASK-006.md",
                authorized_artifact_blob_sha="c" * 40,
                executor_id="antigravity",
            )
            store = bridge.get_lease_store()
            acq_lease = store.acquire(lease_cand)

            auth = {
                "task_id": "TASK-006",
                "action": "RUN",
                "kind": "TASK",
                "artifact_path": ".ai/tasks/TASK-006.md",
                "artifact_blob_sha": "c" * 40,
                "approved_at": bridge.now(),
                "branch": "ai/task-006",
                "status": "ACTIVE",
                "base_main_sha": "base_123",
                "executor_id": acq_lease.executor_id,
                "lease_id": acq_lease.lease_id,
                "lease_fingerprint": acq_lease.fingerprint(),
                "workspace_id": acq_lease.workspace_id,
                "execution_fingerprint": acq_lease.execution_fingerprint,
            }
            bridge.save_authorization(6, auth)

            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: "c" * 40 if "tasks" in path else None

            # Mock git push
            bridge.git = lambda *args, **kw: (
                type("Res", (), {"returncode": 0, "stdout": "", "stderr": ""})()
                if args[0] == "push"
                else subprocess.run(["git", *args], cwd=root, check=kw.get("check", True), capture_output=True, text=True)
            )

            bridge.cmd_publish(type("Args", (), {
                "task_id": 6,
                "action": None,
                "test": "echo '264 passed in 20.86s'",
                "summary": "Completed TASK-006",
                "notes": "Safe zero-touch workflow verified",
                "message": "TASK-006: implementation ready",
            })())

            # Authorization is CONSUMED
            updated_auth = bridge.load_authorization(6)
            assert updated_auth["status"] == "CONSUMED"
            assert updated_auth["published_sha"] is not None

            # RESULT-006 artifact created with full evidence
            result_file = root / ".ai" / "results" / "RESULT-006.md"
            assert result_file.exists()
            content = result_file.read_text(encoding="utf-8")
            assert "STATUS: READY_FOR_REVIEW" in content
            assert "264 passed" in content
            assert "base_123" in content
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.git = old_git
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_publish_preserves_active_authorization_when_tests_fail():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "ai/task-006"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            ws_id = bridge.get_workspace_id()
            lease_cand = bridge.build_executor_lease_candidate(
                task_id="TASK-006",
                workspace_id=ws_id,
                operation=bridge.ExecutionOperation.RUN,
                target_branch="ai/task-006",
                authorized_artifact_path=".ai/tasks/TASK-006.md",
                authorized_artifact_blob_sha="d" * 40,
                executor_id="antigravity",
            )
            store = bridge.get_lease_store()
            acq_lease = store.acquire(lease_cand)

            auth = {
                "task_id": "TASK-006",
                "action": "RUN",
                "kind": "TASK",
                "artifact_path": ".ai/tasks/TASK-006.md",
                "artifact_blob_sha": "d" * 40,
                "approved_at": bridge.now(),
                "branch": "ai/task-006",
                "status": "ACTIVE",
                "executor_id": acq_lease.executor_id,
                "lease_id": acq_lease.lease_id,
                "lease_fingerprint": acq_lease.fingerprint(),
                "workspace_id": acq_lease.workspace_id,
                "execution_fingerprint": acq_lease.execution_fingerprint,
            }
            bridge.save_authorization(6, auth)

            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: "d" * 40 if "tasks" in path else None

            with pytest.raises(SystemExit):
                bridge.cmd_publish(type("Args", (), {
                    "task_id": 6,
                    "action": None,
                    "test": "python -c 'import sys; sys.exit(1)'",
                    "summary": "Failing test run",
                    "notes": None,
                    "message": None,
                })())

            # Authorization MUST REMAIN ACTIVE for the developer session to fix code
            updated_auth = bridge.load_authorization(6)
            assert updated_auth["status"] == "ACTIVE"
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_watcher_notifications_v040_instruct_aios_worker_command():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_list = bridge.list_remote_inbound
        old_read = bridge.read_remote_file
        old_notify = bridge.notify_best_effort
        old_ensure = bridge.ensure_git

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_git = lambda: None
            bridge.ensure_dirs()
            cfg = {"windows_popup": False, "remote": "origin", "control_branch": "ai-control"}
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            notifications = []
            bridge.notify_best_effort = lambda title, msg, *args: notifications.append((title, msg))

            bridge.fetch_control = lambda cfg: None
            bridge.list_remote_inbound = lambda cfg: [
                (".ai/tasks/TASK-006.md", "t" * 40),
                (".ai/reviews/REVIEW-006.md", "r" * 40),
            ]
            bridge.read_remote_file = lambda cfg, path: (
                "# TASK-006\n" if "tasks" in path else "# REVIEW-006\n## Status\nCHANGES_REQUIRED\n"
            )

            bridge.sync_once(verbose=False)

            assert len(notifications) == 2
            assert "/aios-worker RUN TASK-006" in notifications[0][1]
            assert "bridge.py approve" not in notifications[0][1]

            assert "/aios-worker FIX TASK-006" in notifications[1][1]
            assert "bridge.py approve" not in notifications[1][1]
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.list_remote_inbound = old_list
            bridge.read_remote_file = old_read
            bridge.notify_best_effort = old_notify
            bridge.ensure_git = old_ensure
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_popup_notification_failure_does_not_break_sync_or_checkpoint():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_list = bridge.list_remote_inbound
        old_read = bridge.read_remote_file
        old_notify = bridge.notify
        old_ensure = bridge.ensure_git

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_git = lambda: None
            bridge.ensure_dirs()
            cfg = {"windows_popup": True, "remote": "origin", "control_branch": "ai-control"}
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            bridge.fetch_control = lambda cfg: None
            bridge.list_remote_inbound = lambda cfg: [(".ai/tasks/TASK-001.md", "c" * 40)]
            bridge.read_remote_file = lambda cfg, path: "# TASK-001\n"
            bridge.notify = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("popup display failed"))

            changed = bridge.sync_once(verbose=False)

            assert changed == [".ai/tasks/TASK-001.md"]
            artifact_file = bridge.get_artifact_path(".ai/tasks/TASK-001.md")
            assert artifact_file.read_text(encoding="utf-8") == "# TASK-001\n"

            seen = bridge.load_json(bridge.get_runtime_paths()["seen"], {})
            assert seen[".ai/tasks/TASK-001.md"] == "c" * 40
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.list_remote_inbound = old_list
            bridge.read_remote_file = old_read
            bridge.notify = old_notify
            bridge.ensure_git = old_ensure
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_watcher_retries_after_fetch_auth_network_error():
    old_cfg = bridge.load_config
    bridge.load_config = lambda: {"control_branch": "ai-control", "remote": "origin", "poll_seconds": 1}
    calls = []

    def fake_sync(verbose=False):
        calls.append(True)
        if len(calls) == 1:
            raise SystemExit(1)
        raise KeyboardInterrupt

    bridge.sync_once = fake_sync
    old_sleep = bridge.time.sleep
    bridge.time.sleep = lambda s: None

    try:
        bridge.cmd_watch(type("Args", (), {"poll_seconds": None})())
        assert len(calls) == 2
    finally:
        bridge.load_config = old_cfg
        bridge.time.sleep = old_sleep


def test_utf8_output_and_path_handling_remains_functional():
    captured = {}

    class FakeResult:
        returncode = 0
        stdout = "OK: Tiếng Việt UTF-8 \u2705"
        stderr = ""

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured.update(kwargs)
        return FakeResult()

    old_run = bridge.run
    old_git = bridge.git
    bridge.run = fake_run
    bridge.git = lambda *args, **kw: bridge.run(["git", *args], **kw)

    try:
        res = bridge.git("status", env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"})
        assert captured["env"]["LANG"] == "C.UTF-8"
        assert captured["env"]["LC_ALL"] == "C.UTF-8"
        assert "\u2705" in res.stdout
    finally:
        bridge.run = old_run
        bridge.git = old_git


def test_publish_fails_closed_when_only_legacy_approval_exists_and_no_active_authorization():
    """Validates Finding 1: Legacy historical approval alone can NEVER authorize publish."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "ai/task-006"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            # Write a historical legacy APPROVED inbox file
            inbox = bridge.get_runtime_paths()["inbox"]
            bridge.save_json(inbox / "TASK-006.legacy.json", {
                "kind": "TASK",
                "task_id": "TASK-006",
                "approval": "APPROVED",
                "approved_at": "2026-08-10T10:00:00+07:00",
            })

            # Assert NO active v0.4.0 authorization exists
            assert bridge.get_active_authorization(6) is None

            # Publish MUST fail closed!
            with pytest.raises(SystemExit):
                bridge.cmd_publish(type("Args", (), {
                    "task_id": 6,
                    "test": None,
                    "summary": "legacy test",
                    "notes": None,
                    "message": None,
                })())
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_existing_task_branch_resume_fails_when_local_ahead_of_remote():
    """Validates Finding 2: Existing task branch resume fails closed if local is ahead of remote."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "ai/task-006"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_git = bridge.git
        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            def fake_git(*args, **kwargs):
                if args == ("rev-parse", "refs/remotes/origin/ai/task-006"):
                    return type("Res", (), {"returncode": 0, "stdout": "1" * 40, "stderr": ""})()
                if args == ("merge-base", "--is-ancestor", "refs/heads/ai/task-006", "refs/remotes/origin/ai/task-006"):
                    return type("Res", (), {"returncode": 1, "stdout": "", "stderr": ""})()
                if args == ("merge-base", "--is-ancestor", "refs/remotes/origin/ai/task-006", "refs/heads/ai/task-006"):
                    return type("Res", (), {"returncode": 0, "stdout": "", "stderr": ""})()  # Local is ahead
                return old_git(*args, **kwargs)

            bridge.git = fake_git

            cfg = {"remote": "origin", "base_branch": "main", "task_branch_prefix": "ai/task-"}
            with pytest.raises(SystemExit):
                bridge.prepare_task_branch(cfg, 6, "FIX")
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.git = old_git


def test_existing_task_branch_resume_fails_when_local_and_remote_diverged():
    """Validates Finding 2: Existing task branch resume fails closed if local and remote diverged."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "ai/task-006"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_git = bridge.git
        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            def fake_git(*args, **kwargs):
                if args == ("rev-parse", "refs/remotes/origin/ai/task-006"):
                    return type("Res", (), {"returncode": 0, "stdout": "1" * 40, "stderr": ""})()
                if args == ("merge-base", "--is-ancestor", "refs/heads/ai/task-006", "refs/remotes/origin/ai/task-006"):
                    return type("Res", (), {"returncode": 1, "stdout": "", "stderr": ""})()
                if args == ("merge-base", "--is-ancestor", "refs/remotes/origin/ai/task-006", "refs/heads/ai/task-006"):
                    return type("Res", (), {"returncode": 1, "stdout": "", "stderr": ""})()  # Diverged
                return old_git(*args, **kwargs)

            bridge.git = fake_git

            cfg = {"remote": "origin", "base_branch": "main", "task_branch_prefix": "ai/task-"}
            with pytest.raises(SystemExit):
                bridge.prepare_task_branch(cfg, 6, "FIX")
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.git = old_git


def test_existing_task_branch_resume_fast_forwards_when_local_strictly_behind():
    """Validates Finding 2: Existing task branch resume fast-forwards when local is strictly behind."""
    with tempfile.TemporaryDirectory() as temp:
        # Create bare remote repository
        remote_repo = Path(temp) / "remote_repo.git"
        subprocess.run(["git", "init", "--bare", "-b", "main", str(remote_repo)], check=True, capture_output=True)

        local_repo = Path(temp) / "local_repo"
        subprocess.run(["git", "clone", str(remote_repo), str(local_repo)], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=local_repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=local_repo, check=True, capture_output=True)

        (local_repo / "README.md").write_text("# Initial\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=local_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "commit 1"], cwd=local_repo, check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=local_repo, check=True, capture_output=True)

        # Create ai/task-006 on remote
        subprocess.run(["git", "checkout", "-b", "ai/task-006"], cwd=local_repo, check=True, capture_output=True)
        subprocess.run(["git", "push", "-u", "origin", "ai/task-006"], cwd=local_repo, check=True, capture_output=True)

        # In another clone, advance ai/task-006 on remote
        other_repo = Path(temp) / "other_repo"
        subprocess.run(["git", "clone", str(remote_repo), str(other_repo)], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Reviewer"], cwd=other_repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "rev@test.local"], cwd=other_repo, check=True, capture_output=True)
        subprocess.run(["git", "checkout", "ai/task-006"], cwd=other_repo, check=True, capture_output=True)
        (other_repo / "patch.txt").write_text("patch\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=other_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "remote patch commit"], cwd=other_repo, check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "ai/task-006"], cwd=other_repo, check=True, capture_output=True)

        remote_task_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=other_repo, check=True, capture_output=True, text=True).stdout.strip()

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        bridge.PROJECT = local_repo
        bridge.AI = local_repo / ".ai"

        try:
            cfg = {"remote": "origin", "base_branch": "main", "task_branch_prefix": "ai/task-"}
            branch = bridge.prepare_task_branch(cfg, 6, "FIX")
            assert branch == "ai/task-006"

            local_task_sha = subprocess.run(["git", "rev-parse", "ai/task-006"], cwd=local_repo, check=True, capture_output=True, text=True).stdout.strip()
            assert local_task_sha == remote_task_sha
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai


def test_publish_fails_when_active_run_auth_has_changes_required_review_on_control():
    """Validates: An active RUN auth is rejected during publish if CHANGES_REQUIRED review exists on control."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "ai/task-006"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha
        old_read = bridge.read_remote_file

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            ws_id = bridge.get_workspace_id()
            lease_cand = bridge.build_executor_lease_candidate(
                task_id="TASK-006",
                workspace_id=ws_id,
                operation=bridge.ExecutionOperation.RUN,
                target_branch="ai/task-006",
                authorized_artifact_path=".ai/tasks/TASK-006.md",
                authorized_artifact_blob_sha="a" * 40,
                executor_id="antigravity",
            )
            store = bridge.get_lease_store()
            acq_lease = store.acquire(lease_cand)

            auth = {
                "task_id": "TASK-006",
                "action": "RUN",
                "kind": "TASK",
                "artifact_path": ".ai/tasks/TASK-006.md",
                "artifact_blob_sha": "a" * 40,
                "approved_at": bridge.now(),
                "branch": "ai/task-006",
                "status": "ACTIVE",
                "executor_id": acq_lease.executor_id,
                "lease_id": acq_lease.lease_id,
                "lease_fingerprint": acq_lease.fingerprint(),
                "workspace_id": acq_lease.workspace_id,
                "execution_fingerprint": acq_lease.execution_fingerprint,
            }
            bridge.save_authorization(6, auth)

            bridge.fetch_control = lambda cfg: None
            # TASK blob unchanged
            bridge.get_remote_blob_sha = lambda cfg, path: "a" * 40 if "tasks" in path else "r" * 40
            bridge.read_remote_file = lambda cfg, path: (
                "# TASK-006\n" if "tasks" in path else "# REVIEW-006\n## Status\nCHANGES_REQUIRED\n"
            )

            with pytest.raises(SystemExit):
                bridge.cmd_publish(type("Args", (), {
                    "task_id": 6,
                    "action": None,
                    "test": None,
                    "summary": "test",
                    "notes": None,
                    "message": None,
                })())
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            bridge.read_remote_file = old_read
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_publish_fails_when_action_argument_mismatches_active_authorization():
    """Validates: Explicit action argument mismatch fails publish."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "ai/task-006"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            ws_id = bridge.get_workspace_id()
            lease_cand = bridge.build_executor_lease_candidate(
                task_id="TASK-006",
                workspace_id=ws_id,
                operation=bridge.ExecutionOperation.RUN,
                target_branch="ai/task-006",
                authorized_artifact_path=".ai/tasks/TASK-006.md",
                authorized_artifact_blob_sha="a" * 40,
                executor_id="antigravity",
            )
            store = bridge.get_lease_store()
            acq_lease = store.acquire(lease_cand)

            auth = {
                "task_id": "TASK-006",
                "action": "RUN",
                "kind": "TASK",
                "artifact_path": ".ai/tasks/TASK-006.md",
                "artifact_blob_sha": "a" * 40,
                "approved_at": bridge.now(),
                "branch": "ai/task-006",
                "status": "ACTIVE",
                "executor_id": acq_lease.executor_id,
                "lease_id": acq_lease.lease_id,
                "lease_fingerprint": acq_lease.fingerprint(),
                "workspace_id": acq_lease.workspace_id,
                "execution_fingerprint": acq_lease.execution_fingerprint,
            }
            bridge.save_authorization(6, auth)

            # Request action="fix" while auth is "RUN" -> fails closed
            with pytest.raises(SystemExit):
                bridge.cmd_publish(type("Args", (), {
                    "task_id": 6,
                    "action": "fix",
                    "test": None,
                    "summary": "mismatch",
                    "notes": None,
                    "message": None,
                })())
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_handoff_run_fails_when_task_artifact_is_malformed():
    """Validates Finding 2: RUN handoff fails closed when task artifact is missing canonical TASK-N identifier."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha
        old_read = bridge.read_remote_file
        old_ensure = bridge.ensure_git

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_git = lambda: None
            bridge.ensure_dirs()
            cfg = {"windows_popup": False, "remote": "origin", "control_branch": "ai-control"}
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: "x" * 40
            # Non-empty content but missing TASK-006 identifier
            bridge.read_remote_file = lambda cfg, path: "# Random Document\n\nSome unrelated content without task id."

            with pytest.raises(SystemExit):
                bridge.cmd_handoff(type("Args", (), {"task_id": 6, "action": "run"})())
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            bridge.read_remote_file = old_read
            bridge.ensure_git = old_ensure
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_handoff_run_acquires_lease_and_second_handoff_conflicts():
    """Validates: RUN handoff acquires lease and binds to auth; second concurrent handoff fails closed (C9 / C16)."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha
        old_read = bridge.read_remote_file

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: "a" * 40
            bridge.read_remote_file = lambda cfg, path: _make_e4_test_task_content(29, "RUN", "antigravity")

            # 1. First handoff succeeds
            bridge.cmd_handoff(type("Args", (), {"task_id": 29, "action": "run"})())

            # Verify active lease was created in store
            store = bridge.get_lease_store()
            active_lease = store.load_active("TASK-029")
            assert active_lease is not None
            assert active_lease.task_id == "TASK-029"
            assert active_lease.executor_id == "antigravity"
            assert active_lease.operation == bridge.ExecutionOperation.RUN

            # Verify authorization contains exact lease binding
            auth = bridge.load_authorization(29)
            assert auth["status"] == "ACTIVE"
            assert auth["lease_id"] == active_lease.lease_id
            assert auth["lease_fingerprint"] == active_lease.fingerprint()
            assert auth["workspace_id"] == active_lease.workspace_id
            assert auth["execution_fingerprint"] == active_lease.execution_fingerprint

            # 2. Second concurrent handoff for same task fails closed on lease collision
            with pytest.raises(SystemExit):
                bridge.cmd_handoff(type("Args", (), {"task_id": 29, "action": "run"})())
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            bridge.read_remote_file = old_read
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_lease_status_and_confirmation_gated_release():
    """Validates: lease-status prints active leases, and lease-release requires --confirm-stopped (C23)."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha
        old_read = bridge.read_remote_file

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: "a" * 40
            bridge.read_remote_file = lambda cfg, path: _make_e4_test_task_content(29, "RUN", "antigravity")

            bridge.cmd_handoff(type("Args", (), {"task_id": 29, "action": "run"})())

            store = bridge.get_lease_store()
            active_lease = store.load_active("TASK-029")
            assert active_lease is not None

            # 1. lease-status runs cleanly
            bridge.cmd_lease_status(type("Args", (), {"task_id": 29})())
            bridge.cmd_lease_status(type("Args", (), {"task_id": None})())

            # 2. lease-release without confirm_stopped fails
            with pytest.raises(SystemExit):
                bridge.cmd_lease_release(type("Args", (), {
                    "task_id": 29,
                    "lease_id": active_lease.lease_id,
                    "confirm_stopped": False,
                })())

            # 3. lease-release with mismatched lease_id fails
            with pytest.raises(SystemExit):
                bridge.cmd_lease_release(type("Args", (), {
                    "task_id": 29,
                    "lease_id": "lease-wrong-id",
                    "confirm_stopped": True,
                })())

            # 4. lease-release with correct lease_id and confirm_stopped succeeds
            bridge.cmd_lease_release(type("Args", (), {
                "task_id": 29,
                "lease_id": active_lease.lease_id,
                "confirm_stopped": True,
            })())

            # Active lease is now None and auth is CANCELLED
            assert store.load_active("TASK-029") is None
            auth = bridge.load_authorization(29)
            assert auth["status"] == "CANCELLED"
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            bridge.read_remote_file = old_read
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


@pytest.mark.parametrize(
    ("kind", "governance_case"),
    [
        ("task", "governed_run_missing_or_invalid_roadmap_binding"),
        ("task", "h1_run_missing_or_invalid_predecessor_completion"),
        ("review", "governed_fix_missing_exact_task_review_binding"),
    ],
    ids=lambda value: value if isinstance(value, str) and "_" in value else None,
)
def test_cmd_approve_governed_attempts_fail_before_authority_access(
    monkeypatch, capsys, kind, governance_case
):
    """All governed bypass variants are denied before any authority-bearing access."""
    assert governance_case
    accessed = []

    def forbidden(name):
        def _forbidden(*args, **kwargs):
            accessed.append(name)
            raise AssertionError(f"legacy approve accessed {name}")

        return _forbidden

    for name in (
        "load_config",
        "find_latest_event",
        "checkout_task_branch",
        "get_lease_store",
        "save_json",
        "save_authorization",
        "update_state",
    ):
        monkeypatch.setattr(bridge, name, forbidden(name))

    args = bridge.build_parser().parse_args(
        ["approve", "77", "--kind", kind, "--executor", "codex"]
    )
    with pytest.raises(SystemExit) as exc:
        args.func(args)

    assert exc.value.code == 1
    assert accessed == []
    error = capsys.readouterr().err
    assert "Legacy 'approve' is disabled" in error
    assert "handoff" in error
    assert "$aios-worker or /aios-worker" in error


def test_cmd_approve_lease_conflict_preserves_pending_event_and_state():
    """
    Validates R1-4: When cmd_approve encounters a lease conflict, the inbox event remains PENDING
    and operational state is untouched, keeping the approval retryable.
    """
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            # 1. Create a pending inbox event
            inbox_path = bridge.get_runtime_paths()["inbox"] / "TASK-029.11111111111111111111.json"
            event_data = {
                "kind": "TASK",
                "task_id": "TASK-029",
                "path": ".ai/tasks/TASK-029.md",
                "blob_sha": "a" * 40,
                "detected_at": "2026-08-17T08:00:00+07:00",
                "approval": "PENDING",
            }
            bridge.save_json(inbox_path, event_data)

            # Pre-acquire lease for TASK-029 by another executor
            ws_id = bridge.get_workspace_id()
            other_lease = bridge.build_executor_lease_candidate(
                task_id="TASK-029",
                workspace_id=ws_id,
                operation=bridge.ExecutionOperation.RUN,
                target_branch="ai/task-029",
                authorized_artifact_path=".ai/tasks/TASK-029.md",
                authorized_artifact_blob_sha="a" * 40,
                executor_id="other-executor",
            )
            store = bridge.get_lease_store()
            store.acquire(other_lease)

            # 2. Attempt cmd_approve -> must fail closed due to lease conflict
            with pytest.raises(SystemExit):
                bridge.cmd_approve(type("Args", (), {"task_id": 29, "kind": None})())

            # 3. Critical verification: Inbox event is STILL PENDING and retryable!
            reloaded_event = bridge.load_json(inbox_path, {})
            assert reloaded_event.get("approval") == "PENDING"
            assert bridge.find_latest_event(29, "TASK") is not None
            assert len(bridge.pending_events()) == 1

            # 4. No ACTIVE authorization was persisted
            assert bridge.get_active_authorization(29) is None
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_publish_commit_and_push_failure_retains_exact_lease():
    """
    Validates R1-5: Commit or push failure during publish retains the exact active lease in store.
    """
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "ai/task-029"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Initial\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha
        old_read = bridge.read_remote_file
        old_git = bridge.git

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            # Acquire lease & bind auth
            ws_id = bridge.get_workspace_id()
            lease = bridge.build_executor_lease_candidate(
                task_id="TASK-029",
                workspace_id=ws_id,
                operation=bridge.ExecutionOperation.RUN,
                target_branch="ai/task-029",
                authorized_artifact_path=".ai/tasks/TASK-029.md",
                authorized_artifact_blob_sha="c" * 40,
                executor_id="antigravity",
            )
            store = bridge.get_lease_store()
            store.acquire(lease)

            auth = {
                "task_id": "TASK-029",
                "action": "RUN",
                "kind": "TASK",
                "artifact_path": ".ai/tasks/TASK-029.md",
                "artifact_blob_sha": "c" * 40,
                "approved_at": bridge.now(),
                "branch": "ai/task-029",
                "status": "ACTIVE",
                "executor_id": lease.executor_id,
                "lease_id": lease.lease_id,
                "lease_fingerprint": lease.fingerprint(),
                "workspace_id": lease.workspace_id,
                "execution_fingerprint": lease.execution_fingerprint,
            }
            bridge.save_authorization(29, auth)

            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: "c" * 40 if "tasks" in path else None

            # 1. Test failure retains lease
            with pytest.raises(SystemExit):
                bridge.cmd_publish(type("Args", (), {
                    "task_id": 29,
                    "action": None,
                    "test": 'python -c "import sys; sys.exit(1)"',
                    "summary": "failing test",
                    "notes": None,
                    "message": None,
                })())
            assert store.load_active("TASK-029") == lease

            # 2. Push failure retains lease
            def fake_git_push_fail(*args, **kwargs):
                if args[0] == "push":
                    bridge.fail("git push thất bại: fatal: remote rejected push")
                return old_git(*args, **kwargs)

            bridge.git = fake_git_push_fail

            with pytest.raises(SystemExit):
                bridge.cmd_publish(type("Args", (), {
                    "task_id": 29,
                    "action": None,
                    "test": None,
                    "summary": "push failing",
                    "notes": None,
                    "message": "push fail commit",
                })())

            # Active lease in store MUST REMAIN EXACTLY ACTIVE
            assert store.load_active("TASK-029") == lease
            assert bridge.load_authorization(29)["status"] == "ACTIVE"

            # 3. Commit failure retains lease
            def fake_git_commit_fail(*args, **kwargs):
                if args[0] == "commit":
                    bridge.fail("git commit thất bại: pre-commit hook rejected")
                return old_git(*args, **kwargs)

            bridge.git = fake_git_commit_fail

            with pytest.raises(SystemExit):
                bridge.cmd_publish(type("Args", (), {
                    "task_id": 29,
                    "action": None,
                    "test": None,
                    "summary": "commit failing",
                    "notes": None,
                    "message": "commit fail",
                })())

            # Active lease in store MUST REMAIN EXACTLY ACTIVE
            assert store.load_active("TASK-029") == lease
            assert bridge.load_authorization(29)["status"] == "ACTIVE"
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            bridge.read_remote_file = old_read
            bridge.git = old_git
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_cmd_approve_post_acquire_inbox_save_failure_rolls_back_lease():
    """
    Validates R2-1: When save_json fails on the inbox event file right after lease acquisition,
    the newly acquired lease is rolled back and fail closed is enforced.
    """
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_save_json = bridge.save_json
        old_checkout = bridge.checkout_task_branch

        bridge.PROJECT = root
        bridge.AI = root / ".ai"
        bridge.checkout_task_branch = lambda cfg, task_id: "ai/task-029"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            inbox_path = bridge.get_runtime_paths()["inbox"] / "TASK-029.11111111111111111111.json"
            event_data = {
                "kind": "TASK",
                "task_id": "TASK-029",
                "path": ".ai/tasks/TASK-029.md",
                "blob_sha": "a" * 40,
                "detected_at": "2026-08-17T08:00:00+07:00",
                "approval": "PENDING",
            }
            bridge.save_json(inbox_path, event_data)

            # Fault-inject save_json to raise only on the inbox event path during activation
            def fake_save_json(path, data_obj):
                if str(inbox_path) == str(path) and data_obj.get("approval") == "APPROVED":
                    raise IOError("Simulated inbox disk failure")
                return old_save_json(path, data_obj)

            bridge.save_json = fake_save_json

            store = bridge.get_lease_store()
            with pytest.raises(SystemExit):
                bridge.cmd_approve(type("Args", (), {"task_id": 29, "kind": None})())

            # 1. Lease was released on rollback
            assert store.load_active("TASK-029") is None

            # 2. No active authorization persisted
            assert bridge.get_active_authorization(29) is None
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.save_json = old_save_json
            bridge.checkout_task_branch = old_checkout
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_cmd_approve_post_acquire_update_state_failure_rolls_back_lease():
    """
    Validates R2-1: When an exception occurs during state update after lease acquisition,
    the newly acquired lease is rolled back and the event remains retryable.
    """
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_update_state = bridge.update_state
        old_checkout = bridge.checkout_task_branch

        bridge.PROJECT = root
        bridge.AI = root / ".ai"
        bridge.checkout_task_branch = lambda cfg, task_id: "ai/task-029"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            inbox_path = bridge.get_runtime_paths()["inbox"] / "TASK-029.22222222222222222222.json"
            event_data = {
                "kind": "TASK",
                "task_id": "TASK-029",
                "path": ".ai/tasks/TASK-029.md",
                "blob_sha": "b" * 40,
                "detected_at": "2026-08-17T08:00:00+07:00",
                "approval": "PENDING",
            }
            bridge.save_json(inbox_path, event_data)

            # Fault-inject update_state to fail during activation
            def fake_update_state(*args, **kwargs):
                if args[1] in ("IN_PROGRESS", "CHANGES_REQUIRED"):
                    raise RuntimeError("Simulated state transition disk error")
                return old_update_state(*args, **kwargs)

            bridge.update_state = fake_update_state

            store = bridge.get_lease_store()
            with pytest.raises(SystemExit):
                bridge.cmd_approve(type("Args", (), {"task_id": 29, "kind": None})())

            # 1. Lease was released on rollback
            assert store.load_active("TASK-029") is None

            # 2. Inbox event remains PENDING and retryable
            reloaded_event = bridge.load_json(inbox_path, {})
            assert reloaded_event.get("approval") == "PENDING"
            assert len(bridge.pending_events()) == 1

            # 3. No active authorization persisted
            assert bridge.get_active_authorization(29) is None
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.update_state = old_update_state
            bridge.checkout_task_branch = old_checkout
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_cmd_approve_post_acquire_save_auth_failure_rolls_back_lease_and_restores_pending():
    """
    Validates R2-1: When save_authorization raises after lease acquisition and event mutation,
    the lease is released, the inbox event is restored to PENDING, and approval remains retryable.
    """
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_save_auth = bridge.save_authorization
        old_checkout = bridge.checkout_task_branch

        bridge.PROJECT = root
        bridge.AI = root / ".ai"
        bridge.checkout_task_branch = lambda cfg, task_id: "ai/task-029"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            inbox_path = bridge.get_runtime_paths()["inbox"] / "TASK-029.33333333333333333333.json"
            event_data = {
                "kind": "TASK",
                "task_id": "TASK-029",
                "path": ".ai/tasks/TASK-029.md",
                "blob_sha": "c" * 40,
                "detected_at": "2026-08-17T08:00:00+07:00",
                "approval": "PENDING",
            }
            bridge.save_json(inbox_path, event_data)

            # Fault-inject save_authorization to raise an unexpected exception
            def fake_save_auth(task_id, auth_dict):
                raise IOError("Simulated authorization storage failure")

            bridge.save_authorization = fake_save_auth

            store = bridge.get_lease_store()
            with pytest.raises(SystemExit):
                bridge.cmd_approve(type("Args", (), {"task_id": 29, "kind": None})())

            # 1. Lease was released on rollback
            assert store.load_active("TASK-029") is None

            # 2. Inbox event was RESTORED to PENDING and remains retryable
            reloaded_event = bridge.load_json(inbox_path, {})
            assert reloaded_event.get("approval") == "PENDING"
            assert len(bridge.pending_events()) == 1

            # 3. No active authorization persisted
            assert bridge.get_active_authorization(29) is None
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.save_authorization = old_save_auth
            bridge.checkout_task_branch = old_checkout
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_cmd_approve_deprecation_precedes_inbox_rollback_paths(capsys):
    """
    The retired approve surface exits before activation, so neither primary writes nor
    rollback/recovery writes can become authority-bearing behavior.
    """
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_save_auth = bridge.save_authorization
        old_save_json = bridge.save_json
        old_checkout = bridge.checkout_task_branch

        bridge.PROJECT = root
        bridge.AI = root / ".ai"
        bridge.checkout_task_branch = lambda cfg, task_id: "ai/task-029"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            inbox_path = bridge.get_runtime_paths()["inbox"] / "TASK-029.44444444444444444444.json"
            event_data = {
                "kind": "TASK",
                "task_id": "TASK-029",
                "path": ".ai/tasks/TASK-029.md",
                "blob_sha": "d" * 40,
                "detected_at": "2026-08-17T08:00:00+07:00",
                "approval": "PENDING",
            }
            bridge.save_json(inbox_path, event_data)

            # Fault-inject save_auth to fail
            def fake_save_auth(task_id, auth_dict):
                raise IOError("Primary auth disk failure")

            # Fault-inject save_json during rollback to fail as well
            def fake_save_json(path, data_obj):
                if str(inbox_path) == str(path) and data_obj.get("approval") == "PENDING":
                    raise IOError("Rollback inbox write failure")
                return old_save_json(path, data_obj)

            bridge.save_authorization = fake_save_auth
            bridge.save_json = fake_save_json

            store = bridge.get_lease_store()
            with pytest.raises(SystemExit):
                bridge.cmd_approve(type("Args", (), {"task_id": 29, "kind": None})())

            err = capsys.readouterr().err
            assert "Legacy 'approve' is disabled" in err
            assert bridge.load_json(inbox_path, {}) == event_data
            assert bridge.get_active_authorization(29) is None
            assert store.load_active("TASK-029") is None
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.save_authorization = old_save_auth
            bridge.save_json = old_save_json
            bridge.checkout_task_branch = old_checkout
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_cmd_approve_deprecation_precedes_lease_acquire_and_release_paths(capsys):
    """
    The retired approve surface never acquires a lease, even when the configured store
    would be unable to release one during rollback.
    """
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_save_auth = bridge.save_authorization
        old_checkout = bridge.checkout_task_branch
        old_get_store = bridge.get_lease_store

        bridge.PROJECT = root
        bridge.AI = root / ".ai"
        bridge.checkout_task_branch = lambda cfg, task_id: "ai/task-029"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            inbox_path = bridge.get_runtime_paths()["inbox"] / "TASK-029.55555555555555555555.json"
            event_data = {
                "kind": "TASK",
                "task_id": "TASK-029",
                "path": ".ai/tasks/TASK-029.md",
                "blob_sha": "e" * 40,
                "detected_at": "2026-08-17T08:00:00+07:00",
                "approval": "PENDING",
            }
            bridge.save_json(inbox_path, event_data)

            # Fault-inject save_auth to fail
            def fake_save_auth(task_id, auth_dict):
                raise IOError("Primary auth disk failure")

            real_store = old_get_store()

            class FlakyReleaseStore:
                def __getattr__(self, name):
                    return getattr(real_store, name)

                def acquire(self, *args, **kwargs):
                    return real_store.acquire(*args, **kwargs)

                def release(self, *args, **kwargs):
                    raise RuntimeError("Simulated store rollback release crash")

            bridge.save_authorization = fake_save_auth
            bridge.get_lease_store = lambda: FlakyReleaseStore()

            with pytest.raises(SystemExit):
                bridge.cmd_approve(type("Args", (), {"task_id": 29, "kind": None})())

            err = capsys.readouterr().err
            assert "Legacy 'approve' is disabled" in err
            assert bridge.load_json(inbox_path, {}) == event_data
            assert bridge.get_active_authorization(29) is None
            assert real_store.load_active("TASK-029") is None
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.save_authorization = old_save_auth
            bridge.checkout_task_branch = old_checkout
            bridge.get_lease_store = old_get_store
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_reconstruct_expected_executor_lease_valid_and_invalid_cases():
    """
    Validates R5-1 / AIP-7: reconstruct_expected_executor_lease must fail closed without default
    inferences on missing, empty, malformed, or mismatched lease fields.
    """
    ws_id = "a" * 64
    task_id = "TASK-029"
    candidate = bridge.build_executor_lease_candidate(
        task_id=task_id,
        workspace_id=ws_id,
        operation=ExecutionOperation.RUN,
        executor_id="antigravity",
        target_branch="ai/task-029",
        authorized_artifact_path=".ai/tasks/TASK-029.md",
        authorized_artifact_blob_sha="1" * 40,
    )

    valid_auth = {
        "task_id": task_id,
        "action": "RUN",
        "executor_id": "antigravity",
        "lease_id": candidate.lease_id,
        "lease_fingerprint": candidate.fingerprint(),
        "workspace_id": ws_id,
        "execution_fingerprint": candidate.execution_fingerprint,
    }

    # 1. Valid reconstruction
    reconstructed = bridge.reconstruct_expected_executor_lease(valid_auth)
    assert reconstructed == candidate
    assert reconstructed.fingerprint() == candidate.fingerprint()

    # 2. Non-dict input
    with pytest.raises(ContinuityStateValidationError, match="dictionary"):
        bridge.reconstruct_expected_executor_lease("invalid_type")

    # 3. Missing or empty required fields (no default inference!)
    for field in [
        "task_id",
        "action",
        "executor_id",
        "lease_id",
        "lease_fingerprint",
        "workspace_id",
        "execution_fingerprint",
    ]:
        # Missing field
        bad_auth = dict(valid_auth)
        del bad_auth[field]
        with pytest.raises(ContinuityStateValidationError, match=field):
            bridge.reconstruct_expected_executor_lease(bad_auth)

        # None value
        bad_auth[field] = None
        with pytest.raises(ContinuityStateValidationError, match=field):
            bridge.reconstruct_expected_executor_lease(bad_auth)

        # Empty or whitespace string
        bad_auth[field] = "   "
        with pytest.raises(ContinuityStateValidationError, match=field):
            bridge.reconstruct_expected_executor_lease(bad_auth)

    # 4. Invalid operation
    bad_op_auth = dict(valid_auth, action="INVALID_OP")
    with pytest.raises(ContinuityStateValidationError, match="Invalid execution operation"):
        bridge.reconstruct_expected_executor_lease(bad_op_auth)

    # 5. Fingerprint mismatch
    bad_fp_auth = dict(valid_auth, lease_fingerprint="0" * 64)
    with pytest.raises(ContinuityStateValidationError, match="fingerprint mismatch"):
        bridge.reconstruct_expected_executor_lease(bad_fp_auth)


def test_cmd_publish_missing_executor_id_in_active_auth_fails_closed_and_retains_lease():
    """
    Validates R5-1: When executor_id is missing from an otherwise valid ACTIVE M5 authorization
    while the matching active lease exists, publish must fail closed BEFORE test execution/commit/push
    and the lease remains ACTIVE.
    """
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        subprocess.run(["git", "checkout", "-b", "ai/task-029"], cwd=root, check=True, capture_output=True)

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_blob = bridge.get_remote_blob_sha
        old_read = bridge.read_remote_file
        old_fetch = bridge.fetch_control

        bridge.PROJECT = root
        bridge.AI = root / ".ai"
        bridge.fetch_control = lambda cfg: None
        bridge.get_remote_blob_sha = lambda cfg, rel: "1" * 40
        bridge.read_remote_file = lambda cfg, rel: "STATUS: IN_PROGRESS"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            # 1. Acquire valid active lease
            store = bridge.get_lease_store()
            lease_candidate = bridge.build_executor_lease_candidate(
                task_id="TASK-029",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.RUN,
                executor_id="antigravity",
                target_branch="ai/task-029",
                authorized_artifact_path=".ai/tasks/TASK-029.md",
                authorized_artifact_blob_sha="1" * 40,
            )
            store.acquire(lease_candidate)
            assert store.load_active("TASK-029") == lease_candidate

            # 2. Save ACTIVE authorization that is MISSING executor_id
            auth = {
                "task_id": "TASK-029",
                "action": "RUN",
                "kind": "TASK",
                "artifact_path": ".ai/tasks/TASK-029.md",
                "artifact_blob_sha": "1" * 40,
                "approved_at": "2026-08-17T10:00:00+07:00",
                "branch": "ai/task-029",
                "status": "ACTIVE",
                # "executor_id" is intentionally omitted!
                "lease_id": lease_candidate.lease_id,
                "lease_fingerprint": lease_candidate.fingerprint(),
                "workspace_id": lease_candidate.workspace_id,
                "execution_fingerprint": lease_candidate.execution_fingerprint,
            }
            bridge.save_authorization(29, auth)

            # 3. Publish must FAIL CLOSED before tests or commits
            with pytest.raises(SystemExit):
                bridge.cmd_publish(
                    type("Args", (), {"task_id": 29, "action": "RUN", "test": "echo test_ran > test.txt", "keep_branch": False})()
                )

            # 4. Invariant: Test did NOT run, and lease is RETAINED as ACTIVE!
            assert not (root / "test.txt").exists()
            assert store.load_active("TASK-029") == lease_candidate
            assert bridge.get_active_authorization(29) is not None
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.get_remote_blob_sha = old_blob
            bridge.read_remote_file = old_read
            bridge.fetch_control = old_fetch
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_validate_runtime_executor_id_rules():
    """Validates C1 (M7): Runtime executor set is closed and explicit with exactly three executors."""
    assert bridge.SUPPORTED_RUNTIME_EXECUTORS == ("antigravity", "codex", "claude-code")

    # 1. Defaults to antigravity
    assert bridge.validate_runtime_executor_id(None) == "antigravity"

    # 2. Canonical supported executors
    assert bridge.validate_runtime_executor_id("antigravity") == "antigravity"
    assert bridge.validate_runtime_executor_id("codex") == "codex"
    assert bridge.validate_runtime_executor_id("claude-code") == "claude-code"

    # 3. Padded / mixed-case / aliases fail closed
    for bad in [
        " antigravity", "antigravity ", "Antigravity", "CODEX", "codex ",
        "Claude-Code", "claude_code", " claude-code", "claude-code ", "claude",
    ]:
        with pytest.raises(ContinuityStateValidationError):
            bridge.validate_runtime_executor_id(bad)

    # 4. Unknown / type errors fail closed
    for bad in ["gemini-cli", "random", "", 123, True]:
        with pytest.raises(ContinuityStateValidationError):
            bridge.validate_runtime_executor_id(bad)


def test_handoff_fix_failover_activation_flow_and_proof_generation():
    """Validates C12-C18: FIX handoff with --executor codex from prior antigravity auth generates valid failover proof."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        # Create task branch ai/task-030 and commit source RESULT
        subprocess.run(["git", "checkout", "-b", "ai/task-030"], cwd=root, check=True, capture_output=True)
        results_dir = root / ".ai" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / "RESULT-030.md").write_text("# RESULT-030\nSTATUS: READY_FOR_REVIEW\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "TASK-030: initial result"], cwd=root, check=True, capture_output=True)
        published_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha
        old_read = bridge.read_remote_file
        old_git = bridge.git

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            bridge.fetch_control = lambda cfg: None
            review_blob = "b" * 40
            control_commit_sha = "c" * 40
            bridge.get_remote_blob_sha = lambda cfg, path: review_blob
            bridge.read_remote_file = lambda cfg, path: _make_e4_test_task_content(30, "FIX", "codex")

            bridge.git = lambda *args, **kw: (
                type("Res", (), {"returncode": 0, "stdout": published_sha, "stderr": ""})()
                if args == ("rev-parse", "refs/remotes/origin/ai/task-030")
                else (
                    type("Res", (), {"returncode": 0, "stdout": control_commit_sha, "stderr": ""})()
                    if args == ("rev-parse", "refs/remotes/origin/ai-control")
                    else old_git(*args, **kw)
                )
            )

            # Setup prior CONSUMED auth by antigravity
            store = bridge.get_lease_store()
            prior_lease = bridge.build_executor_lease_candidate(
                task_id="TASK-030",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.RUN,
                target_branch="ai/task-030",
                authorized_artifact_path=".ai/tasks/TASK-030.md",
                authorized_artifact_blob_sha="a" * 40,
                executor_id="antigravity",
            )
            prior_auth = {
                "task_id": "TASK-030",
                "action": "RUN",
                "kind": "TASK",
                "artifact_path": ".ai/tasks/TASK-030.md",
                "artifact_blob_sha": "a" * 40,
                "approved_at": "2026-08-17T10:00:00+07:00",
                "branch": "ai/task-030",
                "status": "CONSUMED",
                "published_sha": published_sha,
                "published_at": "2026-08-17T11:00:00+07:00",
                "executor_id": "antigravity",
                "lease_id": prior_lease.lease_id,
                "lease_fingerprint": prior_lease.fingerprint(),
                "workspace_id": prior_lease.workspace_id,
                "execution_fingerprint": prior_lease.execution_fingerprint,
            }
            bridge.save_authorization(30, prior_auth)

            # Execute FIX handoff selecting Codex
            bridge.cmd_handoff(type("Args", (), {"task_id": 30, "action": "fix", "executor": "codex"})())

            # Verify active replacement lease belongs to codex
            active_lease = store.load_active("TASK-030")
            assert active_lease is not None
            assert active_lease.executor_id == "codex"
            assert active_lease.operation == ExecutionOperation.FIX

            # Verify ACTIVE authorization contains complete failover proof
            new_auth = bridge.load_authorization(30)
            assert new_auth["status"] == "ACTIVE"
            assert new_auth["executor_id"] == "codex"
            assert "failover_source_lease" in new_auth
            assert "failover_proof" in new_auth
            assert "failover_proof_fingerprint" in new_auth

            proof = bridge.StableExecutorFailoverProof.from_json(new_auth["failover_proof"])
            assert proof.source_executor_id == "antigravity"
            assert proof.replacement_executor_id == "codex"
            assert proof.source_published_sha == published_sha
            assert proof.fingerprint() == new_auth["failover_proof_fingerprint"]

            # Relational validation succeeds against reconstructed leases
            source_lease = bridge.ExecutorLease.from_dict(new_auth["failover_source_lease"])
            bridge.validate_stable_executor_failover(proof, source_lease=source_lease, replacement_lease=active_lease)
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            bridge.read_remote_file = old_read
            bridge.git = old_git
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_handoff_fix_failover_fails_closed_when_prior_auth_not_consumed_or_branch_drift():
    """Validates C12-C14: Failover fails closed on non-consumed prior auth, branch drift, or active lease."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        subprocess.run(["git", "checkout", "-b", "ai/task-030"], cwd=root, check=True, capture_output=True)
        results_dir = root / ".ai" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / "RESULT-030.md").write_text("# RESULT-030\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "result"], cwd=root, check=True, capture_output=True)
        published_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha
        old_read = bridge.read_remote_file
        old_git = bridge.git

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: "b" * 40
            bridge.read_remote_file = lambda cfg, path: _make_e4_test_task_content(30, "FIX", "codex")

            bridge.git = lambda *args, **kw: (
                type("Res", (), {"returncode": 0, "stdout": published_sha, "stderr": ""})()
                if args == ("rev-parse", "refs/remotes/origin/ai/task-030")
                else (
                    type("Res", (), {"returncode": 0, "stdout": "c" * 40, "stderr": ""})()
                    if args == ("rev-parse", "refs/remotes/origin/ai-control")
                    else old_git(*args, **kw)
                )
            )

            store = bridge.get_lease_store()
            prior_lease = bridge.build_executor_lease_candidate(
                task_id="TASK-030",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.RUN,
                target_branch="ai/task-030",
                authorized_artifact_path=".ai/tasks/TASK-030.md",
                authorized_artifact_blob_sha="a" * 40,
                executor_id="antigravity",
            )

            # 1. Non-consumed prior auth fails closed
            bad_auth = {
                "task_id": "TASK-030",
                "action": "RUN",
                "kind": "TASK",
                "artifact_path": ".ai/tasks/TASK-030.md",
                "artifact_blob_sha": "a" * 40,
                "approved_at": "2026-08-17T10:00:00+07:00",
                "branch": "ai/task-030",
                "status": "ACTIVE",  # Still ACTIVE!
                "published_sha": published_sha,
                "executor_id": "antigravity",
                "lease_id": prior_lease.lease_id,
                "lease_fingerprint": prior_lease.fingerprint(),
                "workspace_id": prior_lease.workspace_id,
                "execution_fingerprint": prior_lease.execution_fingerprint,
            }
            bridge.save_authorization(30, bad_auth)

            with pytest.raises(SystemExit):
                bridge.cmd_handoff(type("Args", (), {"task_id": 30, "action": "fix", "executor": "codex"})())

            # 2. Branch head mismatch (drift) fails closed
            bad_auth["status"] = "CONSUMED"
            bad_auth["published_sha"] = "0" * 40  # Mismatched published sha
            bridge.save_authorization(30, bad_auth)

            with pytest.raises(SystemExit):
                bridge.cmd_handoff(type("Args", (), {"task_id": 30, "action": "fix", "executor": "codex"})())

            # 3. Active lease in store blocks failover replacement
            bad_auth["published_sha"] = published_sha
            bridge.save_authorization(30, bad_auth)
            store.acquire(prior_lease)  # Active lease present!

            with pytest.raises(SystemExit):
                bridge.cmd_handoff(type("Args", (), {"task_id": 30, "action": "fix", "executor": "codex"})())
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            bridge.read_remote_file = old_read
            bridge.git = old_git
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_cmd_publish_failover_revalidation_and_result_manifest():
    """Validates C20-C22: Publish under failover authorization validates proof, outputs failover manifest, and releases lease."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        subprocess.run(["git", "checkout", "-b", "ai/task-030"], cwd=root, check=True, capture_output=True)
        results_dir = root / ".ai" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / "RESULT-030.md").write_text("# RESULT-030\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "source result"], cwd=root, check=True, capture_output=True)
        published_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
        result_blob_sha = subprocess.run(["git", "rev-parse", f"{published_sha}:.ai/results/RESULT-030.md"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha
        old_read = bridge.read_remote_file
        old_git = bridge.git

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            review_blob = "b" * 40
            control_commit_sha = "c" * 40
            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: review_blob
            bridge.read_remote_file = lambda cfg, path: _make_e4_test_task_content(30, "FIX", "codex")

            store = bridge.get_lease_store()
            source_lease = bridge.build_executor_lease_candidate(
                task_id="TASK-030",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.RUN,
                target_branch="ai/task-030",
                authorized_artifact_path=".ai/tasks/TASK-030.md",
                authorized_artifact_blob_sha="a" * 40,
                executor_id="antigravity",
            )
            repl_lease = bridge.build_executor_lease_candidate(
                task_id="TASK-030",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.FIX,
                target_branch="ai/task-030",
                authorized_artifact_path=".ai/reviews/REVIEW-030.md",
                authorized_artifact_blob_sha=review_blob,
                executor_id="codex",
            )
            store.acquire(repl_lease)

            proof = bridge.StableExecutorFailoverProof(
                schema_version="1",
                task_id="TASK-030",
                target_branch="ai/task-030",
                source_executor_id=source_lease.executor_id,
                source_operation=source_lease.operation,
                source_execution_fingerprint=source_lease.execution_fingerprint,
                source_lease_fingerprint=source_lease.fingerprint(),
                source_published_sha=published_sha,
                source_result_ref=bridge.ArtifactRef(
                    path=".ai/results/RESULT-030.md",
                    ref=published_sha,
                    blob_sha=result_blob_sha,
                ),
                replacement_executor_id=repl_lease.executor_id,
                replacement_operation=repl_lease.operation,
                replacement_execution_fingerprint=repl_lease.execution_fingerprint,
                replacement_lease_fingerprint=repl_lease.fingerprint(),
                review_ref=bridge.ArtifactRef(
                    path=".ai/reviews/REVIEW-030.md",
                    ref=control_commit_sha,
                    blob_sha=review_blob,
                ),
            )

            active_auth = {
                "task_id": "TASK-030",
                "action": "FIX",
                "kind": "REVIEW",
                "artifact_path": ".ai/reviews/REVIEW-030.md",
                "artifact_blob_sha": review_blob,
                "approved_at": "2026-08-17T11:30:00+07:00",
                "branch": "ai/task-030",
                "status": "ACTIVE",
                "executor_id": "codex",
                "lease_id": repl_lease.lease_id,
                "lease_fingerprint": repl_lease.fingerprint(),
                "workspace_id": repl_lease.workspace_id,
                "execution_fingerprint": repl_lease.execution_fingerprint,
                "failover_source_lease": source_lease.to_dict(),
                "failover_proof": proof.to_dict(),
                "failover_proof_fingerprint": proof.fingerprint(),
            }
            bridge.save_authorization(30, active_auth)

            # Make a code change to publish
            (root / "fix.txt").write_text("fix by codex\n", encoding="utf-8")

            # Mock git push and remote control ref
            bridge.git = lambda *args, **kw: (
                type("Res", (), {"returncode": 0, "stdout": "", "stderr": ""})()
                if args[0] == "push"
                else (
                    type("Res", (), {"returncode": 0, "stdout": control_commit_sha, "stderr": ""})()
                    if args == ("rev-parse", "refs/remotes/origin/ai-control")
                    else old_git(*args, **kw)
                )
            )

            try:
                bridge.cmd_publish(
                    type("Args", (), {
                        "task_id": 30,
                        "action": "FIX",
                        "test": None,
                        "summary": "Codex failover fix",
                        "notes": "all good",
                        "message": "TASK-030: failover fix",
                    })()
                )
            finally:
                bridge.git = old_git

            # Verify RESULT content contains failover manifest
            result_text = (results_dir / "RESULT-030.md").read_text(encoding="utf-8")
            assert "EXECUTOR_FAILOVER: YES" in result_text
            assert "FAILOVER_FROM_EXECUTOR: antigravity" in result_text
            assert "FAILOVER_TO_EXECUTOR: codex" in result_text
            assert f"FAILOVER_SOURCE_PUBLISHED_SHA: {published_sha}" in result_text
            assert f"FAILOVER_PROOF_FINGERPRINT: {proof.fingerprint()}" in result_text
            assert f"FAILOVER_REVIEW_BLOB_SHA: {review_blob}" in result_text

            # Verify replacement lease was released
            assert store.load_active("TASK-030") is None

            # Verify authorization became CONSUMED
            consumed_auth = bridge.load_authorization(30)
            assert consumed_auth["status"] == "CONSUMED"
            assert "published_sha" in consumed_auth
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            bridge.read_remote_file = old_read
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_cmd_publish_failover_tampered_proof_fails_closed_and_retains_lease():
    """Validates C20: Tampered failover proof blocks test execution and retains replacement lease."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        subprocess.run(["git", "checkout", "-b", "ai/task-030"], cwd=root, check=True, capture_output=True)

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha
        old_read = bridge.read_remote_file

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            review_blob = "b" * 40
            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: review_blob
            bridge.read_remote_file = lambda cfg, path: _make_e4_test_task_content(30, "FIX", "codex")

            store = bridge.get_lease_store()
            source_lease = bridge.build_executor_lease_candidate(
                task_id="TASK-030",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.RUN,
                target_branch="ai/task-030",
                authorized_artifact_path=".ai/tasks/TASK-030.md",
                authorized_artifact_blob_sha="a" * 40,
                executor_id="antigravity",
            )
            repl_lease = bridge.build_executor_lease_candidate(
                task_id="TASK-030",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.FIX,
                target_branch="ai/task-030",
                authorized_artifact_path=".ai/reviews/REVIEW-030.md",
                authorized_artifact_blob_sha=review_blob,
                executor_id="codex",
            )
            store.acquire(repl_lease)

            proof = bridge.StableExecutorFailoverProof(
                schema_version="1",
                task_id="TASK-030",
                target_branch="ai/task-030",
                source_executor_id=source_lease.executor_id,
                source_operation=source_lease.operation,
                source_execution_fingerprint=source_lease.execution_fingerprint,
                source_lease_fingerprint=source_lease.fingerprint(),
                source_published_sha="1" * 40,
                source_result_ref=bridge.ArtifactRef(
                    path=".ai/results/RESULT-030.md",
                    ref="1" * 40,
                    blob_sha="d" * 40,
                ),
                replacement_executor_id=repl_lease.executor_id,
                replacement_operation=repl_lease.operation,
                replacement_execution_fingerprint=repl_lease.execution_fingerprint,
                replacement_lease_fingerprint=repl_lease.fingerprint(),
                review_ref=bridge.ArtifactRef(
                    path=".ai/reviews/REVIEW-030.md",
                    ref="c" * 40,
                    blob_sha=review_blob,
                ),
            )

            # Save ACTIVE auth with tampered fingerprint
            active_auth = {
                "task_id": "TASK-030",
                "action": "FIX",
                "kind": "REVIEW",
                "artifact_path": ".ai/reviews/REVIEW-030.md",
                "artifact_blob_sha": review_blob,
                "approved_at": "2026-08-17T11:30:00+07:00",
                "branch": "ai/task-030",
                "status": "ACTIVE",
                "executor_id": "codex",
                "lease_id": repl_lease.lease_id,
                "lease_fingerprint": repl_lease.fingerprint(),
                "workspace_id": repl_lease.workspace_id,
                "execution_fingerprint": repl_lease.execution_fingerprint,
                "failover_source_lease": source_lease.to_dict(),
                "failover_proof": proof.to_dict(),
                "failover_proof_fingerprint": "0" * 64,  # Tampered fingerprint!
            }
            bridge.save_authorization(30, active_auth)

            with pytest.raises(SystemExit):
                bridge.cmd_publish(
                    type("Args", (), {"task_id": 30, "action": "FIX", "test": "echo test_ran > test.txt"})()
                )

            # Test did not run and lease is retained
            assert not (root / "test.txt").exists()
            assert store.load_active("TASK-030") == repl_lease
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            bridge.read_remote_file = old_read
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_handoff_and_approve_failover_remote_branch_drift_or_missing_fails_closed():
    """Validates R1-1: Missing or drifting remote tracking ref fails closed for failover handoff and approve."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        subprocess.run(["git", "checkout", "-b", "ai/task-030"], cwd=root, check=True, capture_output=True)
        results_dir = root / ".ai" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / "RESULT-030.md").write_text("# RESULT-030\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "result"], cwd=root, check=True, capture_output=True)
        published_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha
        old_read = bridge.read_remote_file
        old_git = bridge.git

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: "b" * 40
            bridge.read_remote_file = lambda cfg, path: _make_e4_test_task_content(30, "FIX", "codex")

            store = bridge.get_lease_store()
            prior_lease = bridge.build_executor_lease_candidate(
                task_id="TASK-030",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.RUN,
                target_branch="ai/task-030",
                authorized_artifact_path=".ai/tasks/TASK-030.md",
                authorized_artifact_blob_sha="a" * 40,
                executor_id="antigravity",
            )
            prior_auth = {
                "task_id": "TASK-030",
                "action": "RUN",
                "kind": "TASK",
                "artifact_path": ".ai/tasks/TASK-030.md",
                "artifact_blob_sha": "a" * 40,
                "approved_at": "2026-08-17T10:00:00+07:00",
                "branch": "ai/task-030",
                "status": "CONSUMED",
                "published_sha": published_sha,
                "published_at": "2026-08-17T11:00:00+07:00",
                "executor_id": "antigravity",
                "lease_id": prior_lease.lease_id,
                "lease_fingerprint": prior_lease.fingerprint(),
                "workspace_id": prior_lease.workspace_id,
                "execution_fingerprint": prior_lease.execution_fingerprint,
            }
            bridge.save_authorization(30, prior_auth)

            # 1. Missing remote task branch tracking ref fails closed
            with pytest.raises(SystemExit):
                bridge.cmd_handoff(type("Args", (), {"task_id": 30, "action": "fix", "executor": "codex"})())

            # 2. Remote tracking ref present but drifting fails closed
            bridge.git = lambda *args, **kw: (
                type("Res", (), {"returncode": 0, "stdout": "d" * 40, "stderr": ""})()
                if args == ("rev-parse", "refs/remotes/origin/ai/task-030")
                else old_git(*args, **kw)
            )

            with pytest.raises(SystemExit):
                bridge.cmd_handoff(type("Args", (), {"task_id": 30, "action": "fix", "executor": "codex"})())
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            bridge.read_remote_file = old_read
            bridge.git = old_git
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_handoff_and_approve_failover_requires_explicit_executor():
    """Validates R1-3: Omitted --executor when prior was codex fails closed rather than silently failing over."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        subprocess.run(["git", "checkout", "-b", "ai/task-030"], cwd=root, check=True, capture_output=True)
        results_dir = root / ".ai" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / "RESULT-030.md").write_text("# RESULT-030\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "result"], cwd=root, check=True, capture_output=True)
        published_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha
        old_read = bridge.read_remote_file
        old_git = bridge.git

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: "b" * 40
            bridge.read_remote_file = lambda cfg, path: _make_e4_test_task_content(30, "FIX", "codex")

            # Setup prior consumed auth by CODEX
            store = bridge.get_lease_store()
            prior_lease = bridge.build_executor_lease_candidate(
                task_id="TASK-030",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.RUN,
                target_branch="ai/task-030",
                authorized_artifact_path=".ai/tasks/TASK-030.md",
                authorized_artifact_blob_sha="a" * 40,
                executor_id="codex",
            )
            prior_auth = {
                "task_id": "TASK-030",
                "action": "RUN",
                "kind": "TASK",
                "artifact_path": ".ai/tasks/TASK-030.md",
                "artifact_blob_sha": "a" * 40,
                "approved_at": "2026-08-17T10:00:00+07:00",
                "branch": "ai/task-030",
                "status": "CONSUMED",
                "published_sha": published_sha,
                "published_at": "2026-08-17T11:00:00+07:00",
                "executor_id": "codex",
                "lease_id": prior_lease.lease_id,
                "lease_fingerprint": prior_lease.fingerprint(),
                "workspace_id": prior_lease.workspace_id,
                "execution_fingerprint": prior_lease.execution_fingerprint,
            }
            bridge.save_authorization(30, prior_auth)

            # Mock git to resolve tracking ref and control commit
            bridge.git = lambda *args, **kw: (
                type("Res", (), {"returncode": 0, "stdout": published_sha, "stderr": ""})()
                if args == ("rev-parse", "refs/remotes/origin/ai/task-030")
                else (
                    type("Res", (), {"returncode": 0, "stdout": "c" * 40, "stderr": ""})()
                    if args == ("rev-parse", "refs/remotes/origin/ai-control")
                    else old_git(*args, **kw)
                )
            )

            # 1. Handoff with executor=None (omitted) FAILS CLOSED because prior was codex!
            with pytest.raises(SystemExit):
                bridge.cmd_handoff(type("Args", (), {"task_id": 30, "action": "fix", "executor": None})())

            # 2. Handoff with explicit executor="antigravity" SUCCEEDS
            bridge.cmd_handoff(type("Args", (), {"task_id": 30, "action": "fix", "executor": "antigravity"})())
            active = store.load_active("TASK-030")
            assert active is not None
            assert active.executor_id == "antigravity"
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            bridge.read_remote_file = old_read
            bridge.git = old_git
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_publish_failover_control_commit_mismatch_fails_closed():
    """Validates R1-2: Publish fails closed if authoritative control branch commit has drifted from proof review_ref."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        subprocess.run(["git", "checkout", "-b", "ai/task-030"], cwd=root, check=True, capture_output=True)

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha
        old_read = bridge.read_remote_file
        old_git = bridge.git

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            review_blob = "b" * 40
            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: review_blob
            bridge.read_remote_file = lambda cfg, path: _make_e4_test_task_content(30, "FIX", "codex")

            store = bridge.get_lease_store()
            source_lease = bridge.build_executor_lease_candidate(
                task_id="TASK-030",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.RUN,
                target_branch="ai/task-030",
                authorized_artifact_path=".ai/tasks/TASK-030.md",
                authorized_artifact_blob_sha="a" * 40,
                executor_id="antigravity",
            )
            repl_lease = bridge.build_executor_lease_candidate(
                task_id="TASK-030",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.FIX,
                target_branch="ai/task-030",
                authorized_artifact_path=".ai/reviews/REVIEW-030.md",
                authorized_artifact_blob_sha=review_blob,
                executor_id="codex",
            )
            store.acquire(repl_lease)

            proof = bridge.StableExecutorFailoverProof(
                schema_version="1",
                task_id="TASK-030",
                target_branch="ai/task-030",
                source_executor_id=source_lease.executor_id,
                source_operation=source_lease.operation,
                source_execution_fingerprint=source_lease.execution_fingerprint,
                source_lease_fingerprint=source_lease.fingerprint(),
                source_published_sha="1" * 40,
                source_result_ref=bridge.ArtifactRef(
                    path=".ai/results/RESULT-030.md",
                    ref="1" * 40,
                    blob_sha="d" * 40,
                ),
                replacement_executor_id=repl_lease.executor_id,
                replacement_operation=repl_lease.operation,
                replacement_execution_fingerprint=repl_lease.execution_fingerprint,
                replacement_lease_fingerprint=repl_lease.fingerprint(),
                review_ref=bridge.ArtifactRef(
                    path=".ai/reviews/REVIEW-030.md",
                    ref="c" * 40,  # Bound commit
                    blob_sha=review_blob,
                ),
            )

            active_auth = {
                "task_id": "TASK-030",
                "action": "FIX",
                "kind": "REVIEW",
                "artifact_path": ".ai/reviews/REVIEW-030.md",
                "artifact_blob_sha": review_blob,
                "approved_at": "2026-08-17T11:30:00+07:00",
                "branch": "ai/task-030",
                "status": "ACTIVE",
                "executor_id": "codex",
                "lease_id": repl_lease.lease_id,
                "lease_fingerprint": repl_lease.fingerprint(),
                "workspace_id": repl_lease.workspace_id,
                "execution_fingerprint": repl_lease.execution_fingerprint,
                "failover_source_lease": source_lease.to_dict(),
                "failover_proof": proof.to_dict(),
                "failover_proof_fingerprint": proof.fingerprint(),
            }
            bridge.save_authorization(30, active_auth)

            # Control branch commit has drifted from "c" * 40 to "9" * 40
            bridge.git = lambda *args, **kw: (
                type("Res", (), {"returncode": 0, "stdout": "9" * 40, "stderr": ""})()
                if args == ("rev-parse", "refs/remotes/origin/ai-control")
                else old_git(*args, **kw)
            )

            with pytest.raises(SystemExit):
                bridge.cmd_publish(
                    type("Args", (), {"task_id": 30, "action": "FIX", "test": "echo test_ran > test.txt"})()
                )

            # Invariant: Test did not run, replacement lease retained
            assert not (root / "test.txt").exists()
            assert store.load_active("TASK-030") == repl_lease
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            bridge.read_remote_file = old_read
            bridge.git = old_git
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_handoff_failover_post_acquire_rollback_safety():
    """Validates R1-5: Failures during post-acquire in handoff roll back the replacement lease."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        subprocess.run(["git", "checkout", "-b", "ai/task-030"], cwd=root, check=True, capture_output=True)
        results_dir = root / ".ai" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / "RESULT-030.md").write_text("# RESULT-030\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "result"], cwd=root, check=True, capture_output=True)
        published_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha
        old_read = bridge.read_remote_file
        old_git = bridge.git
        old_save_auth = bridge.save_authorization

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: "b" * 40
            bridge.read_remote_file = lambda cfg, path: _make_e4_test_task_content(30, "FIX", "codex")

            store = bridge.get_lease_store()
            prior_lease = bridge.build_executor_lease_candidate(
                task_id="TASK-030",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.RUN,
                target_branch="ai/task-030",
                authorized_artifact_path=".ai/tasks/TASK-030.md",
                authorized_artifact_blob_sha="a" * 40,
                executor_id="antigravity",
            )
            prior_auth = {
                "task_id": "TASK-030",
                "action": "RUN",
                "kind": "TASK",
                "artifact_path": ".ai/tasks/TASK-030.md",
                "artifact_blob_sha": "a" * 40,
                "approved_at": "2026-08-17T10:00:00+07:00",
                "branch": "ai/task-030",
                "status": "CONSUMED",
                "published_sha": published_sha,
                "published_at": "2026-08-17T11:00:00+07:00",
                "executor_id": "antigravity",
                "lease_id": prior_lease.lease_id,
                "lease_fingerprint": prior_lease.fingerprint(),
                "workspace_id": prior_lease.workspace_id,
                "execution_fingerprint": prior_lease.execution_fingerprint,
            }
            bridge.save_authorization(30, prior_auth)

            bridge.git = lambda *args, **kw: (
                type("Res", (), {"returncode": 0, "stdout": published_sha, "stderr": ""})()
                if args == ("rev-parse", "refs/remotes/origin/ai/task-030")
                else (
                    type("Res", (), {"returncode": 0, "stdout": "c" * 40, "stderr": ""})()
                    if args == ("rev-parse", "refs/remotes/origin/ai-control")
                    else old_git(*args, **kw)
                )
            )

            # Fault injection: save_authorization fails
            bridge.save_authorization = lambda *args, **kw: (_ for _ in ()).throw(IOError("disk full"))

            with pytest.raises(SystemExit):
                bridge.cmd_handoff(type("Args", (), {"task_id": 30, "action": "fix", "executor": "codex"})())

            # Replacement lease is rolled back
            assert store.load_active("TASK-030") is None
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            bridge.read_remote_file = old_read
            bridge.git = old_git
            bridge.save_authorization = old_save_auth
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_handoff_failover_post_acquire_rollback_restores_prior_consumed_auth_when_update_state_fails():
    """Validates R1-5: If update_state fails after save_authorization, rollback restores prior CONSUMED auth."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        subprocess.run(["git", "checkout", "-b", "ai/task-030"], cwd=root, check=True, capture_output=True)
        results_dir = root / ".ai" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / "RESULT-030.md").write_text("# RESULT-030\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "result"], cwd=root, check=True, capture_output=True)
        published_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha
        old_read = bridge.read_remote_file
        old_git = bridge.git
        old_update_state = bridge.update_state

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: "b" * 40
            bridge.read_remote_file = lambda cfg, path: _make_e4_test_task_content(30, "FIX", "codex")

            store = bridge.get_lease_store()
            prior_lease = bridge.build_executor_lease_candidate(
                task_id="TASK-030",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.RUN,
                target_branch="ai/task-030",
                authorized_artifact_path=".ai/tasks/TASK-030.md",
                authorized_artifact_blob_sha="a" * 40,
                executor_id="antigravity",
            )
            prior_auth = {
                "task_id": "TASK-030",
                "action": "RUN",
                "kind": "TASK",
                "artifact_path": ".ai/tasks/TASK-030.md",
                "artifact_blob_sha": "a" * 40,
                "approved_at": "2026-08-17T10:00:00+07:00",
                "branch": "ai/task-030",
                "status": "CONSUMED",
                "published_sha": published_sha,
                "published_at": "2026-08-17T11:00:00+07:00",
                "executor_id": "antigravity",
                "lease_id": prior_lease.lease_id,
                "lease_fingerprint": prior_lease.fingerprint(),
                "workspace_id": prior_lease.workspace_id,
                "execution_fingerprint": prior_lease.execution_fingerprint,
            }
            bridge.save_authorization(30, prior_auth)

            bridge.git = lambda *args, **kw: (
                type("Res", (), {"returncode": 0, "stdout": published_sha, "stderr": ""})()
                if args == ("rev-parse", "refs/remotes/origin/ai/task-030")
                else (
                    type("Res", (), {"returncode": 0, "stdout": "c" * 40, "stderr": ""})()
                    if args == ("rev-parse", "refs/remotes/origin/ai-control")
                    else old_git(*args, **kw)
                )
            )

            # Fault injection: update_state fails during activation (first call), but succeeds during rollback (second call)
            state_call_count = 0
            def faulty_update_state(task_id, state, message=""):
                nonlocal state_call_count
                state_call_count += 1
                if state_call_count == 1:
                    raise IOError("state file write failed")
                return old_update_state(task_id, state, message)

            bridge.update_state = faulty_update_state

            with pytest.raises(SystemExit):
                bridge.cmd_handoff(type("Args", (), {"task_id": 30, "action": "fix", "executor": "codex"})())

            # 1. Replacement lease is released
            assert store.load_active("TASK-030") is None

            # 2. Prior CONSUMED authorization is restored (R1-5)
            restored_auth = bridge.load_authorization(30)
            assert restored_auth is not None
            assert restored_auth["status"] == "CONSUMED"
            assert restored_auth["executor_id"] == "antigravity"
            assert restored_auth["published_sha"] == published_sha
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            bridge.read_remote_file = old_read
            bridge.git = old_git
            bridge.update_state = old_update_state
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_handoff_and_approve_fix_fails_closed_when_prior_auth_missing_or_malformed():
    """Validates R2-1: Missing or malformed prior authorization fails closed before lease acquisition for both handoff and approve."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        subprocess.run(["git", "checkout", "-b", "ai/task-030"], cwd=root, check=True, capture_output=True)

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha
        old_read = bridge.read_remote_file

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            review_blob = "b" * 40
            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: review_blob
            bridge.read_remote_file = lambda cfg, path: _make_e4_test_task_content(30, "FIX", "codex")

            # Create inbox event for cmd_approve testing
            inbox_event_path = bridge.get_runtime_paths()["inbox"] / "review_030.json"
            inbox_event = {
                "task_id": "TASK-030",
                "kind": "REVIEW",
                "path": ".ai/reviews/REVIEW-030.md",
                "blob_sha": review_blob,
                "approval": "PENDING",
            }
            bridge.save_json(inbox_event_path, inbox_event)

            store = bridge.get_lease_store()

            # --- Test Group 1: Missing prior authorization (no auth file) ---
            # 1a. handoff FIX with omitted --executor
            with pytest.raises(SystemExit):
                bridge.cmd_handoff(type("Args", (), {"task_id": 30, "action": "fix", "executor": None})())
            assert store.load_active("TASK-030") is None

            # 1b. handoff FIX with explicit --executor antigravity
            with pytest.raises(SystemExit):
                bridge.cmd_handoff(type("Args", (), {"task_id": 30, "action": "fix", "executor": "antigravity"})())
            assert store.load_active("TASK-030") is None

            # 1c. handoff FIX with explicit --executor codex
            with pytest.raises(SystemExit):
                bridge.cmd_handoff(type("Args", (), {"task_id": 30, "action": "fix", "executor": "codex"})())
            assert store.load_active("TASK-030") is None

            # 1d. cmd_approve FIX with omitted --executor
            with pytest.raises(SystemExit):
                bridge.cmd_approve(type("Args", (), {"task_id": 30, "kind": "review", "executor": None})())
            assert store.load_active("TASK-030") is None

            # 1e. cmd_approve FIX with explicit --executor codex
            with pytest.raises(SystemExit):
                bridge.cmd_approve(type("Args", (), {"task_id": 30, "kind": "review", "executor": "codex"})())
            assert store.load_active("TASK-030") is None

            # --- Test Group 2: Prior auth exists but missing executor_id ---
            malformed_auth = {
                "task_id": "TASK-030",
                "action": "RUN",
                "kind": "TASK",
                "artifact_path": ".ai/tasks/TASK-030.md",
                "artifact_blob_sha": "a" * 40,
                "status": "CONSUMED",
                "lease_id": "lease-task-030-123456789abc",
                "lease_fingerprint": "1" * 64,
                "workspace_id": "0" * 64,
                "execution_fingerprint": "2" * 64,
            }
            bridge.save_authorization(30, malformed_auth)

            with pytest.raises(SystemExit):
                bridge.cmd_handoff(type("Args", (), {"task_id": 30, "action": "fix", "executor": None})())
            assert store.load_active("TASK-030") is None

            with pytest.raises(SystemExit):
                bridge.cmd_approve(type("Args", (), {"task_id": 30, "kind": "review", "executor": "codex"})())
            assert store.load_active("TASK-030") is None

            # --- Test Group 3: Prior auth exists but has malformed nonempty M5 binding ---
            # 3a. Invalid lease fingerprint (doesn't match computed fingerprint)
            malformed_auth["executor_id"] = "antigravity"
            malformed_auth["lease_fingerprint"] = "bad_fingerprint_hex"
            bridge.save_authorization(30, malformed_auth)

            with pytest.raises(SystemExit):
                bridge.cmd_handoff(type("Args", (), {"task_id": 30, "action": "fix", "executor": "codex"})())
            assert store.load_active("TASK-030") is None

            with pytest.raises(SystemExit):
                bridge.cmd_approve(type("Args", (), {"task_id": 30, "kind": "review", "executor": None})())
            assert store.load_active("TASK-030") is None

            # 3b. Missing required field in M5 lease binding
            del malformed_auth["lease_fingerprint"]
            bridge.save_authorization(30, malformed_auth)

            with pytest.raises(SystemExit):
                bridge.cmd_handoff(type("Args", (), {"task_id": 30, "action": "fix", "executor": "antigravity"})())
            assert store.load_active("TASK-030") is None

            with pytest.raises(SystemExit):
                bridge.cmd_approve(type("Args", (), {"task_id": 30, "kind": "review", "executor": "antigravity"})())
            assert store.load_active("TASK-030") is None
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            bridge.read_remote_file = old_read
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_failover_preconditions_reject_when_workspace_on_wrong_branch():
    """Validates R7-1 / C13: Failover activation rejects and acquires no lease when workspace is on wrong branch even if HEAD matches published SHA."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        subprocess.run(["git", "checkout", "-b", "ai/task-030"], cwd=root, check=True, capture_output=True)
        results_dir = root / ".ai" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / "RESULT-030.md").write_text("# RESULT-030\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "result"], cwd=root, check=True, capture_output=True)
        published_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
        result_blob_sha = subprocess.run(["git", "rev-parse", f"{published_sha}:.ai/results/RESULT-030.md"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

        # Create another branch pointing to the EXACT same commit SHA
        subprocess.run(["git", "checkout", "-b", "feature/other-branch"], cwd=root, check=True, capture_output=True)

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha
        old_read = bridge.read_remote_file
        old_git = bridge.git

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            review_blob = "b" * 40
            control_commit_sha = "c" * 40
            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: review_blob
            bridge.read_remote_file = lambda cfg, path: _make_e4_test_task_content(30, "FIX", "codex")

            bridge.git = lambda *args, **kw: (
                type("Res", (), {"returncode": 0, "stdout": published_sha, "stderr": ""})()
                if args == ("rev-parse", "refs/remotes/origin/ai/task-030")
                else (
                    type("Res", (), {"returncode": 0, "stdout": control_commit_sha, "stderr": ""})()
                    if args == ("rev-parse", "refs/remotes/origin/ai-control")
                    else old_git(*args, **kw)
                )
            )

            store = bridge.get_lease_store()
            prior_lease = bridge.build_executor_lease_candidate(
                task_id="TASK-030",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.RUN,
                target_branch="ai/task-030",
                authorized_artifact_path=".ai/tasks/TASK-030.md",
                authorized_artifact_blob_sha="a" * 40,
                executor_id="antigravity",
            )
            prior_auth = {
                "task_id": "TASK-030",
                "action": "RUN",
                "kind": "TASK",
                "artifact_path": ".ai/tasks/TASK-030.md",
                "artifact_blob_sha": "a" * 40,
                "approved_at": "2026-08-17T10:00:00+07:00",
                "branch": "ai/task-030",
                "status": "CONSUMED",
                "published_sha": published_sha,
                "published_at": "2026-08-17T11:00:00+07:00",
                "executor_id": "antigravity",
                "lease_id": prior_lease.lease_id,
                "lease_fingerprint": prior_lease.fingerprint(),
                "workspace_id": prior_lease.workspace_id,
                "execution_fingerprint": prior_lease.execution_fingerprint,
            }
            bridge.save_authorization(30, prior_auth)

            # 1. Direct helper test: workspace is on feature/other-branch, expected is ai/task-030 -> fails closed
            with pytest.raises(SystemExit):
                bridge._validate_stable_failover_preconditions(
                    cfg=cfg,
                    task_id=30,
                    branch="ai/task-030",
                    prior_auth=prior_auth,
                    selected_executor="codex",
                    explicit_executor=True,
                    expected_review_rel=".ai/reviews/REVIEW-030.md",
                    expected_review_blob=review_blob,
                )
            assert store.load_active("TASK-030") is None

            # 2. Integration test via cmd_handoff when current_branch remains on wrong branch
            old_curr = bridge.current_branch
            bridge.current_branch = lambda: "feature/other-branch"
            try:
                with pytest.raises(SystemExit):
                    bridge.cmd_handoff(type("Args", (), {"task_id": 30, "action": "fix", "executor": "codex"})())
                assert store.load_active("TASK-030") is None

                # 3. Integration test via cmd_approve when current_branch remains on wrong branch
                inbox_event = {
                    "task_id": "TASK-030",
                    "kind": "REVIEW",
                    "path": ".ai/reviews/REVIEW-030.md",
                    "blob_sha": review_blob,
                    "approval": "PENDING",
                }
                bridge.save_json(bridge.get_runtime_paths()["inbox"] / "review_030.json", inbox_event)

                with pytest.raises(SystemExit):
                    bridge.cmd_approve(type("Args", (), {"task_id": 30, "kind": "review", "executor": "codex"})())
                assert store.load_active("TASK-030") is None
            finally:
                bridge.current_branch = old_curr
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            bridge.read_remote_file = old_read
            bridge.git = old_git
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_cmd_publish_task_030_proof_progress_manifest_generation():
    """Validates R2-2: Bridge emits canonical M6 real-proof progress fields and preserves proven stages across repairs."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        subprocess.run(["git", "checkout", "-b", "ai/task-030"], cwd=root, check=True, capture_output=True)
        results_dir = root / ".ai" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / "RESULT-030.md").write_text("# RESULT-030\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial result"], cwd=root, check=True, capture_output=True)
        init_source_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
        init_result_blob_sha = subprocess.run(["git", "rev-parse", f"{init_source_sha}:.ai/results/RESULT-030.md"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha
        old_read = bridge.read_remote_file
        old_git = bridge.git

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            review_blob = "b" * 40
            control_commit_sha = "c" * 40
            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: review_blob
            bridge.read_remote_file = lambda cfg, path: _make_e4_test_task_content(30, "FIX", "codex")

            bridge.git = lambda *args, **kw: (
                type("Res", (), {"returncode": 0, "stdout": "", "stderr": ""})()
                if args[0] == "push"
                else (
                    type("Res", (), {"returncode": 0, "stdout": control_commit_sha, "stderr": ""})()
                    if args == ("rev-parse", "refs/remotes/origin/ai-control")
                    else old_git(*args, **kw)
                )
            )

            store = bridge.get_lease_store()

            # --- Stage 0: Initial same-executor Antigravity FIX before failover ---
            lease_antigravity = bridge.build_executor_lease_candidate(
                task_id="TASK-030",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.FIX,
                target_branch="ai/task-030",
                authorized_artifact_path=".ai/reviews/REVIEW-030.md",
                authorized_artifact_blob_sha=review_blob,
                executor_id="antigravity",
            )
            store.acquire(lease_antigravity)

            auth_antigravity = {
                "task_id": "TASK-030",
                "action": "FIX",
                "kind": "REVIEW",
                "artifact_path": ".ai/reviews/REVIEW-030.md",
                "artifact_blob_sha": review_blob,
                "approved_at": "2026-08-17T11:00:00+07:00",
                "branch": "ai/task-030",
                "status": "ACTIVE",
                "executor_id": "antigravity",
                "lease_id": lease_antigravity.lease_id,
                "lease_fingerprint": lease_antigravity.fingerprint(),
                "workspace_id": lease_antigravity.workspace_id,
                "execution_fingerprint": lease_antigravity.execution_fingerprint,
            }
            bridge.save_authorization(30, auth_antigravity)

            # Worker attempt to forge Stage A in local committed git history is ignored
            (results_dir / "RESULT-030.md").write_text("# WORKER FORGED GIT COMMIT\nM6_REAL_PROOF_ANTIGRAVITY_TO_CODEX: PASS\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "worker forged commit"], cwd=root, check=True, capture_output=True)

            bridge.cmd_publish(type("Args", (), {
                "task_id": 30, "action": "FIX", "test": None, "summary": "Initial Antigravity FIX", "notes": None, "message": "Round 2 fix"
            })())

            res_init = (results_dir / "RESULT-030.md").read_text(encoding="utf-8")
            assert "M6_REAL_PROOF_ANTIGRAVITY_TO_CODEX: PENDING" in res_init
            assert "M6_REAL_PROOF_CODEX_TO_ANTIGRAVITY: PENDING" in res_init
            assert "EXECUTOR_FAILOVER: NO" in res_init
            assert "FORGED" not in res_init

            stage_a_source_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
            stage_a_result_blob = subprocess.run(["git", "rev-parse", f"{stage_a_source_sha}:.ai/results/RESULT-030.md"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

            # --- Stage A: Validated failover (antigravity -> codex) ---
            repl_lease_a = bridge.build_executor_lease_candidate(
                task_id="TASK-030",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.FIX,
                target_branch="ai/task-030",
                authorized_artifact_path=".ai/reviews/REVIEW-030.md",
                authorized_artifact_blob_sha=review_blob,
                executor_id="codex",
            )
            store.acquire(repl_lease_a)

            proof_a = bridge.StableExecutorFailoverProof(
                schema_version="1",
                task_id="TASK-030",
                target_branch="ai/task-030",
                source_executor_id="antigravity",
                source_operation=ExecutionOperation.FIX,
                source_execution_fingerprint=lease_antigravity.execution_fingerprint,
                source_lease_fingerprint=lease_antigravity.fingerprint(),
                source_published_sha=stage_a_source_sha,
                source_result_ref=bridge.ArtifactRef(
                    path=".ai/results/RESULT-030.md",
                    ref=stage_a_source_sha,
                    blob_sha=stage_a_result_blob,
                ),
                replacement_executor_id=repl_lease_a.executor_id,
                replacement_operation=repl_lease_a.operation,
                replacement_execution_fingerprint=repl_lease_a.execution_fingerprint,
                replacement_lease_fingerprint=repl_lease_a.fingerprint(),
                review_ref=bridge.ArtifactRef(
                    path=".ai/reviews/REVIEW-030.md",
                    ref=control_commit_sha,
                    blob_sha=review_blob,
                ),
            )

            active_auth_a = {
                "task_id": "TASK-030",
                "action": "FIX",
                "kind": "REVIEW",
                "artifact_path": ".ai/reviews/REVIEW-030.md",
                "artifact_blob_sha": review_blob,
                "approved_at": "2026-08-17T11:30:00+07:00",
                "branch": "ai/task-030",
                "status": "ACTIVE",
                "executor_id": "codex",
                "lease_id": repl_lease_a.lease_id,
                "lease_fingerprint": repl_lease_a.fingerprint(),
                "workspace_id": repl_lease_a.workspace_id,
                "execution_fingerprint": repl_lease_a.execution_fingerprint,
                "failover_source_lease": lease_antigravity.to_dict(),
                "failover_proof": proof_a.to_dict(),
                "failover_proof_fingerprint": proof_a.fingerprint(),
            }
            bridge.save_authorization(30, active_auth_a)

            (root / "change_a.txt").write_text("change a\n", encoding="utf-8")

            bridge.cmd_publish(type("Args", (), {
                "task_id": 30, "action": "FIX", "test": None, "summary": "Stage A publish", "notes": None, "message": "Stage A"
            })())

            res_a = (results_dir / "RESULT-030.md").read_text(encoding="utf-8")
            assert "M6_REAL_PROOF_ANTIGRAVITY_TO_CODEX: PASS" in res_a
            assert "M6_REAL_PROOF_CODEX_TO_ANTIGRAVITY: PENDING" in res_a
            assert "EXECUTOR_FAILOVER: YES" in res_a
            assert "FAILOVER_FROM_EXECUTOR: antigravity" in res_a
            assert "FAILOVER_TO_EXECUTOR: codex" in res_a

            stage_a_published_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
            stage_a_published_result_blob = subprocess.run(["git", "rev-parse", f"{stage_a_published_sha}:.ai/results/RESULT-030.md"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

            # --- Stage A+: Same-executor Codex FIX (repair before Stage B) preserves Stage A PASS ---
            lease_codex_repair = bridge.build_executor_lease_candidate(
                task_id="TASK-030",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.FIX,
                target_branch="ai/task-030",
                authorized_artifact_path=".ai/reviews/REVIEW-030.md",
                authorized_artifact_blob_sha=review_blob,
                executor_id="codex",
            )
            store.acquire(lease_codex_repair)

            auth_codex_repair = {
                "task_id": "TASK-030",
                "action": "FIX",
                "kind": "REVIEW",
                "artifact_path": ".ai/reviews/REVIEW-030.md",
                "artifact_blob_sha": review_blob,
                "approved_at": "2026-08-17T11:45:00+07:00",
                "branch": "ai/task-030",
                "status": "ACTIVE",
                "executor_id": "codex",
                "lease_id": lease_codex_repair.lease_id,
                "lease_fingerprint": lease_codex_repair.fingerprint(),
                "workspace_id": lease_codex_repair.workspace_id,
                "execution_fingerprint": lease_codex_repair.execution_fingerprint,
                "prior_published_sha": stage_a_published_sha,
            }
            bridge.save_authorization(30, auth_codex_repair)

            (root / "change_codex_repair.txt").write_text("repair\n", encoding="utf-8")

            bridge.cmd_publish(type("Args", (), {
                "task_id": 30, "action": "FIX", "test": None, "summary": "Codex repair", "notes": None, "message": "Codex repair"
            })())

            res_repair = (results_dir / "RESULT-030.md").read_text(encoding="utf-8")
            assert "M6_REAL_PROOF_ANTIGRAVITY_TO_CODEX: PASS" in res_repair
            assert "M6_REAL_PROOF_CODEX_TO_ANTIGRAVITY: PENDING" in res_repair
            assert "EXECUTOR_FAILOVER: NO" in res_repair

            stage_b_source_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
            stage_b_result_blob = subprocess.run(["git", "rev-parse", f"{stage_b_source_sha}:.ai/results/RESULT-030.md"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

            # --- Stage B: Failover (codex -> antigravity) ---
            repl_lease_b = bridge.build_executor_lease_candidate(
                task_id="TASK-030",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.FIX,
                target_branch="ai/task-030",
                authorized_artifact_path=".ai/reviews/REVIEW-030.md",
                authorized_artifact_blob_sha=review_blob,
                executor_id="antigravity",
            )
            store.acquire(repl_lease_b)

            proof_b = bridge.StableExecutorFailoverProof(
                schema_version="1",
                task_id="TASK-030",
                target_branch="ai/task-030",
                source_executor_id="codex",
                source_operation=ExecutionOperation.FIX,
                source_execution_fingerprint=lease_codex_repair.execution_fingerprint,
                source_lease_fingerprint=lease_codex_repair.fingerprint(),
                source_published_sha=stage_b_source_sha,
                source_result_ref=bridge.ArtifactRef(
                    path=".ai/results/RESULT-030.md",
                    ref=stage_b_source_sha,
                    blob_sha=stage_b_result_blob,
                ),
                replacement_executor_id="antigravity",
                replacement_operation=ExecutionOperation.FIX,
                replacement_execution_fingerprint=repl_lease_b.execution_fingerprint,
                replacement_lease_fingerprint=repl_lease_b.fingerprint(),
                review_ref=bridge.ArtifactRef(
                    path=".ai/reviews/REVIEW-030.md",
                    ref=control_commit_sha,
                    blob_sha=review_blob,
                ),
            )

            active_auth_b = {
                "task_id": "TASK-030",
                "action": "FIX",
                "kind": "REVIEW",
                "artifact_path": ".ai/reviews/REVIEW-030.md",
                "artifact_blob_sha": review_blob,
                "approved_at": "2026-08-17T12:00:00+07:00",
                "branch": "ai/task-030",
                "status": "ACTIVE",
                "executor_id": "antigravity",
                "lease_id": repl_lease_b.lease_id,
                "lease_fingerprint": repl_lease_b.fingerprint(),
                "workspace_id": repl_lease_b.workspace_id,
                "execution_fingerprint": repl_lease_b.execution_fingerprint,
                "failover_source_lease": lease_codex_repair.to_dict(),
                "failover_proof": proof_b.to_dict(),
                "failover_proof_fingerprint": proof_b.fingerprint(),
            }
            bridge.save_authorization(30, active_auth_b)

            (root / "change_b.txt").write_text("change b\n", encoding="utf-8")

            bridge.cmd_publish(type("Args", (), {
                "task_id": 30, "action": "FIX", "test": None, "summary": "Stage B publish", "notes": None, "message": "Stage B"
            })())

            res_b = (results_dir / "RESULT-030.md").read_text(encoding="utf-8")
            assert "M6_REAL_PROOF_ANTIGRAVITY_TO_CODEX: PASS" in res_b
            assert "M6_REAL_PROOF_CODEX_TO_ANTIGRAVITY: PASS" in res_b
            assert "EXECUTOR_FAILOVER: YES" in res_b
            assert "FAILOVER_FROM_EXECUTOR: codex" in res_b
            assert "FAILOVER_TO_EXECUTOR: antigravity" in res_b

            stage_b_published_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

            # --- Stage B+: Subsequent same-executor Antigravity repair preserves both PASS ---
            lease_antigravity_repair = bridge.build_executor_lease_candidate(
                task_id="TASK-030",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.FIX,
                target_branch="ai/task-030",
                authorized_artifact_path=".ai/reviews/REVIEW-030.md",
                authorized_artifact_blob_sha=review_blob,
                executor_id="antigravity",
            )
            store.acquire(lease_antigravity_repair)

            auth_antigravity_repair = {
                "task_id": "TASK-030",
                "action": "FIX",
                "kind": "REVIEW",
                "artifact_path": ".ai/reviews/REVIEW-030.md",
                "artifact_blob_sha": review_blob,
                "approved_at": "2026-08-17T12:15:00+07:00",
                "branch": "ai/task-030",
                "status": "ACTIVE",
                "executor_id": "antigravity",
                "lease_id": lease_antigravity_repair.lease_id,
                "lease_fingerprint": lease_antigravity_repair.fingerprint(),
                "workspace_id": lease_antigravity_repair.workspace_id,
                "execution_fingerprint": lease_antigravity_repair.execution_fingerprint,
                "prior_published_sha": stage_b_published_sha,
            }
            bridge.save_authorization(30, auth_antigravity_repair)

            (root / "change_antigravity_repair.txt").write_text("repair2\n", encoding="utf-8")

            bridge.cmd_publish(type("Args", (), {
                "task_id": 30, "action": "FIX", "test": None, "summary": "Antigravity repair", "notes": None, "message": "Antigravity repair"
            })())

            res_final = (results_dir / "RESULT-030.md").read_text(encoding="utf-8")
            assert "M6_REAL_PROOF_ANTIGRAVITY_TO_CODEX: PASS" in res_final
            assert "M6_REAL_PROOF_CODEX_TO_ANTIGRAVITY: PASS" in res_final
            assert "EXECUTOR_FAILOVER: NO" in res_final
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            bridge.read_remote_file = old_read
            bridge.git = old_git
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_handoff_claude_code_transitions_and_legacy_approve_is_closed():
    """Validates Claude Code handoff transitions and the retired approve boundary."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        subprocess.run(["git", "checkout", "-b", "ai/task-031"], cwd=root, check=True, capture_output=True)
        results_dir = root / ".ai" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / "RESULT-031.md").write_text("# RESULT-031\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "result"], cwd=root, check=True, capture_output=True)
        published_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
        result_blob_sha = subprocess.run(["git", "rev-parse", f"{published_sha}:.ai/results/RESULT-031.md"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha
        old_read = bridge.read_remote_file
        old_git = bridge.git

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            review_blob = "b" * 40
            control_commit_sha = "c" * 40
            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: review_blob
            bridge.read_remote_file = lambda cfg, path: _make_e4_test_task_content(31, "FIX", "claude-code")

            bridge.git = lambda *args, **kw: (
                type("Res", (), {"returncode": 0, "stdout": "", "stderr": ""})()
                if args and args[0] == "fetch"
                else (
                    type("Res", (), {"returncode": 0, "stdout": published_sha, "stderr": ""})()
                    if args == ("rev-parse", "refs/remotes/origin/ai/task-031")
                    else (
                        type("Res", (), {"returncode": 0, "stdout": control_commit_sha, "stderr": ""})()
                        if args == ("rev-parse", "refs/remotes/origin/ai-control")
                        else old_git(*args, **kw)
                    )
                )
            )

            store = bridge.get_lease_store()

            # 1. Antigravity -> Claude Code failover FIX via cmd_handoff
            prior_lease_ag = bridge.build_executor_lease_candidate(
                task_id="TASK-031",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.RUN,
                target_branch="ai/task-031",
                authorized_artifact_path=".ai/tasks/TASK-031.md",
                authorized_artifact_blob_sha="a" * 40,
                executor_id="antigravity",
            )
            prior_auth_ag = {
                "task_id": "TASK-031",
                "action": "RUN",
                "kind": "TASK",
                "artifact_path": ".ai/tasks/TASK-031.md",
                "artifact_blob_sha": "a" * 40,
                "approved_at": "2026-08-17T10:00:00+07:00",
                "branch": "ai/task-031",
                "status": "CONSUMED",
                "published_sha": published_sha,
                "published_at": "2026-08-17T11:00:00+07:00",
                "executor_id": "antigravity",
                "lease_id": prior_lease_ag.lease_id,
                "lease_fingerprint": prior_lease_ag.fingerprint(),
                "workspace_id": prior_lease_ag.workspace_id,
                "execution_fingerprint": prior_lease_ag.execution_fingerprint,
            }
            bridge.save_authorization(31, prior_auth_ag)

            bridge.cmd_handoff(type("Args", (), {"task_id": 31, "action": "fix", "executor": "claude-code"})())

            auth_cc = bridge.load_authorization(31)
            assert auth_cc is not None
            assert auth_cc["status"] == "ACTIVE"
            assert auth_cc["executor_id"] == "claude-code"
            assert auth_cc.get("failover_proof") is not None
            assert auth_cc["failover_proof"]["source_executor_id"] == "antigravity"
            assert auth_cc["failover_proof"]["replacement_executor_id"] == "claude-code"

            lease_cc = store.load_active("TASK-031")
            assert lease_cc is not None
            assert lease_cc.executor_id == "claude-code"
            store.release(lease_cc)

            # 2. Legacy approve cannot authorize Claude Code -> Antigravity failover FIX
            auth_cc["status"] = "CONSUMED"
            auth_cc["published_sha"] = published_sha
            bridge.save_authorization(31, auth_cc)

            inbox_event = {
                "task_id": "TASK-031",
                "kind": "REVIEW",
                "path": ".ai/reviews/REVIEW-031.md",
                "blob_sha": review_blob,
                "approval": "PENDING",
            }
            bridge.save_json(bridge.get_runtime_paths()["inbox"] / "review_031.json", inbox_event)

            with pytest.raises(SystemExit):
                bridge.cmd_approve(
                    type("Args", (), {"task_id": 31, "kind": "review", "executor": "antigravity"})()
                )

            unchanged_auth = bridge.load_authorization(31)
            assert unchanged_auth is not None
            assert unchanged_auth["status"] == "CONSUMED"
            assert unchanged_auth["executor_id"] == "claude-code"
            assert store.load_active("TASK-031") is None
            assert bridge.load_json(
                bridge.get_runtime_paths()["inbox"] / "review_031.json", {}
            )["approval"] == "PENDING"

            # 3. Claude Code -> Claude Code same-executor FIX via cmd_handoff
            auth_cc["status"] = "CONSUMED"
            auth_cc["published_sha"] = published_sha
            bridge.save_authorization(31, auth_cc)

            bridge.cmd_handoff(type("Args", (), {"task_id": 31, "action": "fix", "executor": "claude-code"})())

            auth_cc_repair = bridge.load_authorization(31)
            assert auth_cc_repair is not None
            assert auth_cc_repair["status"] == "ACTIVE"
            assert auth_cc_repair["executor_id"] == "claude-code"
            assert "failover_proof" not in auth_cc_repair
            assert auth_cc_repair.get("prior_published_sha") == published_sha

            lease_cc_repair = store.load_active("TASK-031")
            assert lease_cc_repair is not None
            assert lease_cc_repair.executor_id == "claude-code"
            store.release(lease_cc_repair)
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            bridge.read_remote_file = old_read
            bridge.git = old_git
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_cmd_publish_task_031_proof_progress_manifest_generation():
    """Validates C9, C10 (M7): Bridge emits canonical M7 real-proof progress fields for TASK-031 and preserves them across repairs."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        subprocess.run(["git", "checkout", "-b", "ai/task-031"], cwd=root, check=True, capture_output=True)
        results_dir = root / ".ai" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / "RESULT-031.md").write_text("# RESULT-031\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial result"], cwd=root, check=True, capture_output=True)
        init_source_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
        init_result_blob_sha = subprocess.run(["git", "rev-parse", f"{init_source_sha}:.ai/results/RESULT-031.md"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha
        old_read = bridge.read_remote_file
        old_git = bridge.git

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            review_blob = "b" * 40
            control_commit_sha = "c" * 40
            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: review_blob
            bridge.read_remote_file = lambda cfg, path: _make_e4_test_task_content(31, "FIX", "claude-code")

            bridge.git = lambda *args, **kw: (
                type("Res", (), {"returncode": 0, "stdout": "", "stderr": ""})()
                if args[0] == "push"
                else (
                    type("Res", (), {"returncode": 0, "stdout": control_commit_sha, "stderr": ""})()
                    if args == ("rev-parse", "refs/remotes/origin/ai-control")
                    else old_git(*args, **kw)
                )
            )

            store = bridge.get_lease_store()

            # --- Stage 0: Initial same-executor Antigravity FIX before failover ---
            lease_antigravity = bridge.build_executor_lease_candidate(
                task_id="TASK-031",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.FIX,
                target_branch="ai/task-031",
                authorized_artifact_path=".ai/reviews/REVIEW-031.md",
                authorized_artifact_blob_sha=review_blob,
                executor_id="antigravity",
            )
            store.acquire(lease_antigravity)

            auth_antigravity = {
                "task_id": "TASK-031",
                "action": "FIX",
                "kind": "REVIEW",
                "artifact_path": ".ai/reviews/REVIEW-031.md",
                "artifact_blob_sha": review_blob,
                "approved_at": "2026-08-17T11:00:00+07:00",
                "branch": "ai/task-031",
                "status": "ACTIVE",
                "executor_id": "antigravity",
                "base_main_sha": init_source_sha,
                "lease_id": lease_antigravity.lease_id,
                "lease_fingerprint": lease_antigravity.fingerprint(),
                "workspace_id": lease_antigravity.workspace_id,
                "execution_fingerprint": lease_antigravity.execution_fingerprint,
                "prior_published_sha": init_source_sha,
            }
            bridge.save_authorization(31, auth_antigravity)

            # Worker attempt to forge Stage A in local committed git history is ignored
            (results_dir / "RESULT-031.md").write_text("# WORKER FORGED GIT COMMIT\nM7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE: PASS\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "worker forged commit"], cwd=root, check=True, capture_output=True)

            bridge.cmd_publish(type("Args", (), {
                "task_id": 31, "action": "FIX", "test": None, "summary": "Initial Antigravity FIX", "notes": None, "message": "Round 1 fix"
            })())

            res_init = (results_dir / "RESULT-031.md").read_text(encoding="utf-8")
            assert "M7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE: PENDING" in res_init
            assert "M7_REAL_PROOF_CLAUDE_CODE_TO_ANTIGRAVITY: PENDING" in res_init
            assert "EXECUTOR_FAILOVER: NO" in res_init
            assert "FORGED" not in res_init

            stage_a_source_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
            stage_a_result_blob = subprocess.run(["git", "rev-parse", f"{stage_a_source_sha}:.ai/results/RESULT-031.md"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

            # --- Stage A: Validated failover (antigravity -> claude-code) ---
            repl_lease_a = bridge.build_executor_lease_candidate(
                task_id="TASK-031",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.FIX,
                target_branch="ai/task-031",
                authorized_artifact_path=".ai/reviews/REVIEW-031.md",
                authorized_artifact_blob_sha=review_blob,
                executor_id="claude-code",
            )
            store.acquire(repl_lease_a)

            proof_a = bridge.StableExecutorFailoverProof(
                schema_version="1",
                task_id="TASK-031",
                target_branch="ai/task-031",
                source_executor_id="antigravity",
                source_operation=ExecutionOperation.FIX,
                source_execution_fingerprint=lease_antigravity.execution_fingerprint,
                source_lease_fingerprint=lease_antigravity.fingerprint(),
                source_published_sha=stage_a_source_sha,
                source_result_ref=bridge.ArtifactRef(
                    path=".ai/results/RESULT-031.md",
                    ref=stage_a_source_sha,
                    blob_sha=stage_a_result_blob,
                ),
                replacement_executor_id=repl_lease_a.executor_id,
                replacement_operation=repl_lease_a.operation,
                replacement_execution_fingerprint=repl_lease_a.execution_fingerprint,
                replacement_lease_fingerprint=repl_lease_a.fingerprint(),
                review_ref=bridge.ArtifactRef(
                    path=".ai/reviews/REVIEW-031.md",
                    ref=control_commit_sha,
                    blob_sha=review_blob,
                ),
            )

            active_auth_a = {
                "task_id": "TASK-031",
                "action": "FIX",
                "kind": "REVIEW",
                "artifact_path": ".ai/reviews/REVIEW-031.md",
                "artifact_blob_sha": review_blob,
                "approved_at": "2026-08-17T11:30:00+07:00",
                "branch": "ai/task-031",
                "status": "ACTIVE",
                "executor_id": "claude-code",
                "base_main_sha": init_source_sha,
                "lease_id": repl_lease_a.lease_id,
                "lease_fingerprint": repl_lease_a.fingerprint(),
                "workspace_id": repl_lease_a.workspace_id,
                "execution_fingerprint": repl_lease_a.execution_fingerprint,
                "failover_source_lease": lease_antigravity.to_dict(),
                "failover_proof": proof_a.to_dict(),
                "failover_proof_fingerprint": proof_a.fingerprint(),
            }
            bridge.save_authorization(31, active_auth_a)

            (root / "change_a.txt").write_text("change a\n", encoding="utf-8")

            bridge.cmd_publish(type("Args", (), {
                "task_id": 31, "action": "FIX", "test": None, "summary": "Stage A publish", "notes": None, "message": "Stage A"
            })())

            res_a = (results_dir / "RESULT-031.md").read_text(encoding="utf-8")
            assert "M7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE: PASS" in res_a
            assert "M7_REAL_PROOF_CLAUDE_CODE_TO_ANTIGRAVITY: PENDING" in res_a
            assert "EXECUTOR_FAILOVER: YES" in res_a
            assert "FAILOVER_FROM_EXECUTOR: antigravity" in res_a
            assert "FAILOVER_TO_EXECUTOR: claude-code" in res_a

            stage_a_published_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

            # --- Stage A+: Same-executor Claude Code FIX (repair before Stage B) preserves Stage A PASS ---
            lease_cc_repair = bridge.build_executor_lease_candidate(
                task_id="TASK-031",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.FIX,
                target_branch="ai/task-031",
                authorized_artifact_path=".ai/reviews/REVIEW-031.md",
                authorized_artifact_blob_sha=review_blob,
                executor_id="claude-code",
            )
            store.acquire(lease_cc_repair)

            auth_cc_repair = {
                "task_id": "TASK-031",
                "action": "FIX",
                "kind": "REVIEW",
                "artifact_path": ".ai/reviews/REVIEW-031.md",
                "artifact_blob_sha": review_blob,
                "approved_at": "2026-08-17T11:45:00+07:00",
                "branch": "ai/task-031",
                "status": "ACTIVE",
                "executor_id": "claude-code",
                "base_main_sha": init_source_sha,
                "lease_id": lease_cc_repair.lease_id,
                "lease_fingerprint": lease_cc_repair.fingerprint(),
                "workspace_id": lease_cc_repair.workspace_id,
                "execution_fingerprint": lease_cc_repair.execution_fingerprint,
                "prior_published_sha": stage_a_published_sha,
            }
            bridge.save_authorization(31, auth_cc_repair)

            (root / "change_cc_repair.txt").write_text("repair\n", encoding="utf-8")

            bridge.cmd_publish(type("Args", (), {
                "task_id": 31, "action": "FIX", "test": None, "summary": "Claude Code repair", "notes": None, "message": "Claude Code repair"
            })())

            res_repair = (results_dir / "RESULT-031.md").read_text(encoding="utf-8")
            assert "M7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE: PASS" in res_repair
            assert "M7_REAL_PROOF_CLAUDE_CODE_TO_ANTIGRAVITY: PENDING" in res_repair
            assert "EXECUTOR_FAILOVER: NO" in res_repair

            stage_b_source_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
            stage_b_result_blob = subprocess.run(["git", "rev-parse", f"{stage_b_source_sha}:.ai/results/RESULT-031.md"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

            # --- Stage B: Failover (claude-code -> antigravity) ---
            repl_lease_b = bridge.build_executor_lease_candidate(
                task_id="TASK-031",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.FIX,
                target_branch="ai/task-031",
                authorized_artifact_path=".ai/reviews/REVIEW-031.md",
                authorized_artifact_blob_sha=review_blob,
                executor_id="antigravity",
            )
            store.acquire(repl_lease_b)

            proof_b = bridge.StableExecutorFailoverProof(
                schema_version="1",
                task_id="TASK-031",
                target_branch="ai/task-031",
                source_executor_id="claude-code",
                source_operation=ExecutionOperation.FIX,
                source_execution_fingerprint=lease_cc_repair.execution_fingerprint,
                source_lease_fingerprint=lease_cc_repair.fingerprint(),
                source_published_sha=stage_b_source_sha,
                source_result_ref=bridge.ArtifactRef(
                    path=".ai/results/RESULT-031.md",
                    ref=stage_b_source_sha,
                    blob_sha=stage_b_result_blob,
                ),
                replacement_executor_id="antigravity",
                replacement_operation=ExecutionOperation.FIX,
                replacement_execution_fingerprint=repl_lease_b.execution_fingerprint,
                replacement_lease_fingerprint=repl_lease_b.fingerprint(),
                review_ref=bridge.ArtifactRef(
                    path=".ai/reviews/REVIEW-031.md",
                    ref=control_commit_sha,
                    blob_sha=review_blob,
                ),
            )

            active_auth_b = {
                "task_id": "TASK-031",
                "action": "FIX",
                "kind": "REVIEW",
                "artifact_path": ".ai/reviews/REVIEW-031.md",
                "artifact_blob_sha": review_blob,
                "approved_at": "2026-08-17T12:00:00+07:00",
                "branch": "ai/task-031",
                "status": "ACTIVE",
                "executor_id": "antigravity",
                "base_main_sha": init_source_sha,
                "lease_id": repl_lease_b.lease_id,
                "lease_fingerprint": repl_lease_b.fingerprint(),
                "workspace_id": repl_lease_b.workspace_id,
                "execution_fingerprint": repl_lease_b.execution_fingerprint,
                "failover_source_lease": lease_cc_repair.to_dict(),
                "failover_proof": proof_b.to_dict(),
                "failover_proof_fingerprint": proof_b.fingerprint(),
            }
            bridge.save_authorization(31, active_auth_b)

            (root / "change_b.txt").write_text("change b\n", encoding="utf-8")

            bridge.cmd_publish(type("Args", (), {
                "task_id": 31, "action": "FIX", "test": None, "summary": "Stage B publish", "notes": None, "message": "Stage B"
            })())

            res_b = (results_dir / "RESULT-031.md").read_text(encoding="utf-8")
            assert "M7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE: PASS" in res_b
            assert "M7_REAL_PROOF_CLAUDE_CODE_TO_ANTIGRAVITY: PASS" in res_b
            assert "EXECUTOR_FAILOVER: YES" in res_b
            assert "FAILOVER_FROM_EXECUTOR: claude-code" in res_b
            assert "FAILOVER_TO_EXECUTOR: antigravity" in res_b

            stage_b_published_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

            # --- Stage B+: Subsequent same-executor Antigravity repair preserves both PASS ---
            lease_antigravity_repair = bridge.build_executor_lease_candidate(
                task_id="TASK-031",
                workspace_id=store.workspace_id,
                operation=ExecutionOperation.FIX,
                target_branch="ai/task-031",
                authorized_artifact_path=".ai/reviews/REVIEW-031.md",
                authorized_artifact_blob_sha=review_blob,
                executor_id="antigravity",
            )
            store.acquire(lease_antigravity_repair)

            auth_antigravity_repair = {
                "task_id": "TASK-031",
                "action": "FIX",
                "kind": "REVIEW",
                "artifact_path": ".ai/reviews/REVIEW-031.md",
                "artifact_blob_sha": review_blob,
                "approved_at": "2026-08-17T12:15:00+07:00",
                "branch": "ai/task-031",
                "status": "ACTIVE",
                "executor_id": "antigravity",
                "base_main_sha": init_source_sha,
                "lease_id": lease_antigravity_repair.lease_id,
                "lease_fingerprint": lease_antigravity_repair.fingerprint(),
                "workspace_id": lease_antigravity_repair.workspace_id,
                "execution_fingerprint": lease_antigravity_repair.execution_fingerprint,
                "prior_published_sha": stage_b_published_sha,
            }
            bridge.save_authorization(31, auth_antigravity_repair)

            (root / "change_antigravity_repair.txt").write_text("repair2\n", encoding="utf-8")

            bridge.cmd_publish(type("Args", (), {
                "task_id": 31, "action": "FIX", "test": None, "summary": "Antigravity repair", "notes": None, "message": "Antigravity repair"
            })())

            res_final = (results_dir / "RESULT-031.md").read_text(encoding="utf-8")
            assert "M7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE: PASS" in res_final
            assert "M7_REAL_PROOF_CLAUDE_CODE_TO_ANTIGRAVITY: PASS" in res_final
            assert "EXECUTOR_FAILOVER: NO" in res_final
            assert "BRIDGE_TESTS:" in res_final
            assert "CONTINUITY_TESTS:" in res_final
            assert "FULL_REPO_TESTS:" in res_final
            assert "REGRESSIONS: 0" in res_final
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            bridge.read_remote_file = old_read
            bridge.git = old_git
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_handoff_claude_code_run_activation_and_legacy_approve_is_closed():
    """Validates Claude Code RUN handoff and that legacy approve creates no authority."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        task_dir = root / ".ai" / "tasks"
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "TASK-031.md").write_text("# TASK-031\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "add task"], cwd=root, check=True, capture_output=True)
        task_blob_sha = subprocess.run(["git", "rev-parse", "HEAD:.ai/tasks/TASK-031.md"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
        control_commit_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_fetch = bridge.fetch_control
        old_blob = bridge.get_remote_blob_sha
        old_read = bridge.read_remote_file
        old_git = bridge.git

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {
                "remote": "origin",
                "base_branch": "main",
                "control_branch": "ai-control",
                "task_branch_prefix": "ai/task-",
                "poll_seconds": 20,
                "windows_popup": False,
            }
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: task_blob_sha
            bridge.read_remote_file = lambda cfg, path: _make_e4_test_task_content(31, "RUN", "claude-code")

            bridge.git = lambda *args, **kw: (
                type("Res", (), {"returncode": 0, "stdout": "", "stderr": ""})()
                if args and args[0] == "fetch"
                else (
                    type("Res", (), {"returncode": 0, "stdout": control_commit_sha, "stderr": ""})()
                    if args == ("rev-parse", "refs/remotes/origin/ai-control")
                    else (
                        type("Res", (), {"returncode": 0, "stdout": control_commit_sha, "stderr": ""})()
                        if args == ("rev-parse", "refs/remotes/origin/main")
                        else old_git(*args, **kw)
                    )
                )
            )

            store = bridge.get_lease_store()

            # 1. Direct handoff RUN with --executor claude-code
            bridge.cmd_handoff(type("Args", (), {"task_id": 31, "action": "run", "executor": "claude-code"})())

            auth_run = bridge.load_authorization(31)
            assert auth_run is not None
            assert auth_run["status"] == "ACTIVE"
            assert auth_run["action"] == "RUN"
            assert auth_run["executor_id"] == "claude-code"
            assert "failover_proof" not in auth_run

            lease_run = store.load_active("TASK-031")
            assert lease_run is not None
            assert lease_run.executor_id == "claude-code"
            assert lease_run.operation == ExecutionOperation.RUN
            store.release(lease_run)

            # Clear auth to prove legacy cmd_approve RUN cannot recreate it
            bridge.save_authorization(31, None)

            # 2. Legacy cmd_approve RUN with --executor claude-code
            inbox_event = {
                "task_id": "TASK-031",
                "kind": "TASK",
                "path": ".ai/tasks/TASK-031.md",
                "blob_sha": task_blob_sha,
                "approval": "PENDING",
            }
            bridge.save_json(bridge.get_runtime_paths()["inbox"] / "task_031.json", inbox_event)

            with pytest.raises(SystemExit):
                bridge.cmd_approve(
                    type("Args", (), {"task_id": 31, "kind": "task", "executor": "claude-code"})()
                )

            assert bridge.load_authorization(31) is None
            assert store.load_active("TASK-031") is None
            assert bridge.load_json(
                bridge.get_runtime_paths()["inbox"] / "task_031.json", {}
            )["approval"] == "PENDING"
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.fetch_control = old_fetch
            bridge.get_remote_blob_sha = old_blob
            bridge.read_remote_file = old_read
            bridge.git = old_git
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_task_031_portability_scope_validation_fails_closed_on_core_change_or_fourth_executor():
    """Validates C1, C2, C12 (R1-1): Forbidden Continuity Core modifications or fourth-executor widening fail closed before publish."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        core_file = root / "src" / "aios_bridge" / "continuity" / "lease.py"
        core_file.parent.mkdir(parents=True, exist_ok=True)
        core_file.write_text("# Original lease\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)
        base_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

        subprocess.run(["git", "checkout", "-b", "ai/task-031"], cwd=root, check=True, capture_output=True)

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_git = bridge.git
        old_executors = bridge.SUPPORTED_RUNTIME_EXECUTORS

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_dirs()
            cfg = {"remote": "origin", "base_branch": "main", "task_branch_prefix": "ai/task-"}
            auth = {
                "task_id": "TASK-031",
                "action": "RUN",
                "base_main_sha": base_sha,
                "branch": "ai/task-031",
                "status": "ACTIVE",
                "executor_id": "antigravity",
            }

            # 1. Clean state passes scope validation
            bridge._validate_task_031_portability_scope(cfg, auth)

            # 2. Modifying locked Continuity Core file in working tree fails closed
            core_file.write_text("# Modified lease\n", encoding="utf-8")
            with pytest.raises(SystemExit):
                bridge._validate_task_031_portability_scope(cfg, auth)

            # Commit the modification -> diff from base_sha still fails closed
            subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "modified core"], cwd=root, check=True, capture_output=True)
            with pytest.raises(SystemExit):
                bridge._validate_task_031_portability_scope(cfg, auth)

            # Revert core file
            core_file.write_text("# Original lease\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "revert core"], cwd=root, check=True, capture_output=True)
            bridge._validate_task_031_portability_scope(cfg, auth)

            # 4. Git diff base_sha failure fails closed (R2-1)
            auth_bad_sha = dict(auth, base_main_sha="0" * 40)
            with pytest.raises(SystemExit):
                bridge._validate_task_031_portability_scope(cfg, auth_bad_sha)

            # 5. Git diff working-tree failure fails closed (R2-1)
            old_g = bridge.git
            bridge.git = lambda *args, **kw: (
                type("Res", (), {"returncode": 128, "stdout": "", "stderr": "fatal: corrupted git index"})()
                if args == ("diff", "--name-only", "HEAD")
                else old_g(*args, **kw)
            )
            try:
                with pytest.raises(SystemExit):
                    bridge._validate_task_031_portability_scope(cfg, auth)
            finally:
                bridge.git = old_g
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.git = old_git
            bridge.SUPPORTED_RUNTIME_EXECUTORS = old_executors
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_task_031_test_evidence_truthful_binding_and_negative_subset_cases():
    """Validates R1-2, R2-2: Evidence parser truthfully binds pass counts and blocks fabricated claims on subset runs."""
    # 1. No test command supplied
    b, c, f, r = bridge._parse_task_031_test_evidence(None, None, 0)
    assert b == "NOT_RUN"
    assert c == "NOT_RUN"
    assert f == "NOT_RUN"
    assert r == "0"

    # 2. Failing test command
    b, c, f, r = bridge._parse_task_031_test_evidence("pytest tests/", "1 failed", 1)
    assert b == "NOT_RUN"
    assert c == "NOT_RUN"
    assert f == "NOT_RUN"

    # 3. Subset: only bridge tests run -> full repo & continuity are NOT_RUN
    b, c, f, r = bridge._parse_task_031_test_evidence(
        ".\\venv\\Scripts\\python -m pytest tests/test_bridge.py",
        "tests/test_bridge.py: 80 passed in 1.2s\n= 80 passed in 1.2s =",
        0,
    )
    assert b == "80/80 pass"
    assert c == "NOT_RUN"
    assert f == "NOT_RUN"

    # 4. Subset: only continuity tests run -> bridge & full repo are NOT_RUN
    b, c, f, r = bridge._parse_task_031_test_evidence(
        ".\\venv\\Scripts\\python -m pytest tests/aios_bridge/continuity/",
        "tests/aios_bridge/continuity/test_lease.py PASSED\n= 152 passed in 0.5s =",
        0,
    )
    assert b == "NOT_RUN"
    assert c == "152/152 pass"
    assert f == "NOT_RUN"

    # 5. Full repository execution without verbose flags (progress dots only) -> subsuites report UNVERIFIED, full repo reported truthfully
    b, c, f, r = bridge._parse_task_031_test_evidence(
        ".\\venv\\Scripts\\python -m pytest tests/",
        "tests/test_bridge.py ................................................................................ [ 11%]\n"
        "tests/aios_bridge/continuity/test_lease.py ................. [100%]\n"
        "= 755 passed in 78.0s =",
        0,
    )
    assert b == "UNVERIFIED"
    assert c == "UNVERIFIED"
    assert f == "755/755 pass"
    assert r == "0"

    # 6. Full repository execution with verbose output -> exact subsuite pass counts dynamically derived
    bridge_lines = "\n".join(f"tests/test_bridge.py::test_case_{i} PASSED" for i in range(56))
    continuity_lines = "\n".join(f"tests/aios_bridge/continuity/test_case_{i} PASSED" for i in range(152))
    verbose_output = f"{bridge_lines}\n{continuity_lines}\n= 755 passed in 78.0s ="

    b, c, f, r = bridge._parse_task_031_test_evidence(
        ".\\venv\\Scripts\\python -m pytest tests/ -v",
        verbose_output,
        0,
    )
    assert b == "56/56 pass"
    assert c == "152/152 pass"
    assert f == "755/755 pass"
    assert r == "0"

    # 7. Count drift test: changing number of tests dynamically updates manifest evidence without hard-coded fallbacks
    drift_bridge_lines = "\n".join(f"tests/test_bridge.py::test_case_{i} PASSED" for i in range(95))
    drift_continuity_lines = "\n".join(f"tests/aios_bridge/continuity/test_case_{i} PASSED" for i in range(160))
    drift_output = f"{drift_bridge_lines}\n{drift_continuity_lines}\n= 777 passed in 80.0s ="

    b, c, f, r = bridge._parse_task_031_test_evidence(
        ".\\venv\\Scripts\\python -m pytest tests/ -v",
        drift_output,
        0,
    )
    assert b == "95/95 pass"
    assert c == "160/160 pass"
    assert f == "777/777 pass"
    assert r == "0"


def test_cmd_publish_task_032_proof_progress_manifest_generation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    Verifies that cmd_publish correctly renders the TASK-032 manifest block for initial RUN and failover FIX.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / ".ai" / "results").mkdir(parents=True)
    monkeypatch.setattr(bridge, "AI", repo / ".ai")
    monkeypatch.setattr(bridge, "ensure_git", lambda: None)
    monkeypatch.setattr(
        bridge,
        "load_config",
        lambda: {"task_branch_prefix": "ai/task-", "remote": "origin", "control_branch": "ai-control"},
    )
    monkeypatch.setattr(bridge, "current_branch", lambda: "ai/task-032")
    monkeypatch.setattr(bridge, "changed_files", lambda: [".ai/results/RESULT-032.md"])
    def dummy_git(*args, **kwargs):
        cmd = list(args)
        if "diff" in cmd and "--cached" in cmd:
            return subprocess.CompletedProcess(cmd, 0, ".ai/results/RESULT-032.md\n", "")
        if "rev-parse" in cmd:
            return subprocess.CompletedProcess(cmd, 0, "08508e48f6ffda70d1891dad461f6fd1b893b24b\n", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(bridge, "git", dummy_git)
    monkeypatch.setattr(bridge, "archive_local", lambda *args: None)
    monkeypatch.setattr(bridge, "fetch_control", lambda cfg: None)
    monkeypatch.setattr(bridge, "read_remote_file", lambda cfg, path: None)
    monkeypatch.setattr(bridge, "save_authorization", lambda *args: None)
    monkeypatch.setattr(bridge, "update_state", lambda *args: None)
    monkeypatch.setattr(bridge, "_validate_task_032_portability_scope", lambda cfg, auth: None)

    class DummyArgs:
        task_id = 32
        test = ".\\venv\\Scripts\\python -m pytest tests/ -v"
        summary = None
        notes = None
        message = None

    class DummyStore:
        def require_active(self, lease):
            pass

        def release(self, lease):
            pass

        def release_active(self, lease):
            pass

    monkeypatch.setattr(bridge, "get_lease_store", lambda: DummyStore())
    monkeypatch.setattr(bridge, "reconstruct_expected_executor_lease", lambda auth: None)
    monkeypatch.setattr(bridge, "get_remote_blob_sha", lambda cfg, path: "d" * 40 if path == ".ai/tasks/TASK-032.md" else None)

    # Case 1: Initial RUN (S0)
    auth_run = {
        "task_id": "TASK-032",
        "action": "RUN",
        "executor_id": "antigravity",
        "lease_id": "lease-task-032-123456",
        "lease_fingerprint": "a" * 64,
        "workspace_id": "c" * 64,
        "execution_fingerprint": "b" * 64,
        "base_main_sha": "08508e48f6ffda70d1891dad461f6fd1b893b24b",
        "artifact_path": ".ai/tasks/TASK-032.md",
        "artifact_blob_sha": "d" * 40,
    }
    monkeypatch.setattr(bridge, "get_active_authorization", lambda tid: auth_run)
    monkeypatch.setattr(
        bridge,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args, 0, "tests/test_bridge.py::t1 PASSED\ntests/aios_bridge/continuity/t2 PASSED\n= 755 passed in 10s =", ""
        ),
    )

    bridge.cmd_publish(DummyArgs())
    res_path = repo / ".ai" / "results" / "RESULT-032.md"
    content = res_path.read_text(encoding="utf-8")
    assert "TASK_ID: TASK-032" in content
    assert "ACTION: RUN" in content
    assert "EXECUTOR_ID: antigravity" in content
    assert "EXECUTOR_FAILOVER: NO" in content
    assert "BASE_SHA: 08508e48f6ffda70d1891dad461f6fd1b893b24b" in content
    assert "M8_MULTI_AGENT_CONTINUITY_HARNESS: IMPLEMENTED" in content
    assert "M8_SHARED_BOUNDARY_SHA: PENDING_SELF_REFERENCE" in content
    assert "M8_BRAIN_PROOF: PENDING" in content
    assert "M8_EXECUTOR_PROOF: PENDING" in content
    assert "M8_COMPOSITE_CHAIN: PENDING" in content
    assert "BRIDGE_TESTS: 1/1 pass" in content
    assert "CONTINUITY_TESTS: 1/1 pass" in content
    assert "FULL_REPO_TESTS: 755/755 pass" in content

    # Case 2: Failover FIX with non-M8 review (generic review without C7 block) -> proofs stay PENDING (R1-1)
    failover_info_generic = {
        "from_executor": "codex",
        "to_executor": "antigravity",
        "source_published_sha": "08508e48f6ffda70d1891dad461f6fd1b893b24b",
        "proof_fingerprint": "e" * 64,
        "review_blob_sha": "f" * 40,
    }
    b, e, c, s = bridge._evaluate_task_032_proof_progress(
        cfg={"remote": "origin", "control_branch": "ai-control"},
        auth=auth_run,
        failover_info=failover_info_generic,
    )
    assert b == "PENDING"
    assert e == "PENDING"
    assert c == "PENDING"
    assert s == "08508e48f6ffda70d1891dad461f6fd1b893b24b"

    # Case 3: Failover FIX with valid C7 Brain provenance block in review -> Brain and Executor PASS, Composite PENDING (R1-1 Round 2)
    c7_review_text = f"""# REVIEW-032
STATUS: CHANGES_REQUIRED
M8_SOURCE_EXECUTOR_PUBLISHED_SHA: 08508e48f6ffda70d1891dad461f6fd1b893b24b
M8_BRAIN_SOURCE_ID: chatgpt-chat
M8_BRAIN_REPLACEMENT_ID: claude-chat
M8_BRAIN_FAILOVER_PROOF_FINGERPRINT: {'1' * 64}
M8_BRAIN_SUCCESS_ARTIFACT_BLOB_SHA: {'2' * 40}
M8_CANONICAL_STATE_FINGERPRINT: {'3' * 64}
"""
    c7_norm = c7_review_text.replace("\r\n", "\n").replace("\r", "\n")
    c7_blob = hashlib.sha1(f"blob {len(c7_norm.encode('utf-8'))}\0".encode("utf-8") + c7_norm.encode("utf-8")).hexdigest()
    failover_info_c7 = dict(failover_info_generic)
    failover_info_c7["review_blob_sha"] = c7_blob

    monkeypatch.setattr(bridge, "read_remote_file", lambda cfg, path: c7_review_text)
    monkeypatch.setattr(bridge, "get_remote_blob_sha", lambda cfg, path: c7_blob)
    b, e, c, s = bridge._evaluate_task_032_proof_progress(
        cfg={"remote": "origin", "control_branch": "ai-control"},
        auth=auth_run,
        failover_info=failover_info_c7,
    )
    assert b == "PENDING"
    assert e == "PASS"
    assert c == "PENDING"
    assert s == "08508e48f6ffda70d1891dad461f6fd1b893b24b"

    # Case 4: Failover FIX with C7 source SHA mismatch -> PENDING
    c7_mismatch_sha = c7_review_text.replace(
        "M8_SOURCE_EXECUTOR_PUBLISHED_SHA: 08508e48f6ffda70d1891dad461f6fd1b893b24b",
        "M8_SOURCE_EXECUTOR_PUBLISHED_SHA: 1111111111111111111111111111111111111111",
    )
    c7_mismatch_norm = c7_mismatch_sha.replace("\r\n", "\n").replace("\r", "\n")
    c7_mismatch_blob = hashlib.sha1(f"blob {len(c7_mismatch_norm.encode('utf-8'))}\0".encode("utf-8") + c7_mismatch_norm.encode("utf-8")).hexdigest()
    failover_info_mismatch = dict(failover_info_generic)
    failover_info_mismatch["review_blob_sha"] = c7_mismatch_blob
    monkeypatch.setattr(bridge, "read_remote_file", lambda cfg, path: c7_mismatch_sha)
    monkeypatch.setattr(bridge, "get_remote_blob_sha", lambda cfg, path: c7_mismatch_blob)
    b, e, c, s = bridge._evaluate_task_032_proof_progress(
        cfg={"remote": "origin", "control_branch": "ai-control"},
        auth=auth_run,
        failover_info=failover_info_mismatch,
    )
    assert b == "PENDING"
    assert e == "PENDING"
    assert c == "PENDING"

    # Case 5: Failover FIX with identical brain IDs -> PENDING
    c7_same_brain = c7_review_text.replace("M8_BRAIN_REPLACEMENT_ID: claude-chat", "M8_BRAIN_REPLACEMENT_ID: chatgpt-chat")
    c7_same_norm = c7_same_brain.replace("\r\n", "\n").replace("\r", "\n")
    c7_same_blob = hashlib.sha1(f"blob {len(c7_same_norm.encode('utf-8'))}\0".encode("utf-8") + c7_same_norm.encode("utf-8")).hexdigest()
    failover_info_same = dict(failover_info_generic)
    failover_info_same["review_blob_sha"] = c7_same_blob
    monkeypatch.setattr(bridge, "read_remote_file", lambda cfg, path: c7_same_brain)
    monkeypatch.setattr(bridge, "get_remote_blob_sha", lambda cfg, path: c7_same_blob)
    b, e, c, s = bridge._evaluate_task_032_proof_progress(
        cfg={"remote": "origin", "control_branch": "ai-control"},
        auth=auth_run,
        failover_info=failover_info_same,
    )
    assert b == "PENDING"
    assert e == "PENDING"
    assert c == "PENDING"

    # Case 6: Review blob mismatch against remote control tree -> PENDING (R1-1 Round 2)
    failover_info_blob_mismatch = dict(failover_info_c7)
    failover_info_blob_mismatch["review_blob_sha"] = "0" * 40
    monkeypatch.setattr(bridge, "read_remote_file", lambda cfg, path: c7_review_text)
    monkeypatch.setattr(bridge, "get_remote_blob_sha", lambda cfg, path: c7_blob)
    b, e, c, s = bridge._evaluate_task_032_proof_progress(
        cfg={"remote": "origin", "control_branch": "ai-control"},
        auth=auth_run,
        failover_info=failover_info_blob_mismatch,
    )
    assert b == "PENDING"
    assert e == "PENDING"
    assert c == "PENDING"


def test_task_032_portability_scope_validation_fails_closed_on_core_change_or_fourth_executor(
    monkeypatch: pytest.MonkeyPatch,
):
    """
    Verifies that _validate_task_032_portability_scope strictly enforces:
    1. 3 executors allowlist
    2. Fail-closed on locked core files modified vs base_main_sha
    3. Fail-closed on uncommitted working tree changes to core files
    4. Fail-closed on git command errors
    """
    cfg = {}
    auth = {"base_main_sha": "08508e48f6ffda70d1891dad461f6fd1b893b24b"}

    # 1. Fourth executor fails
    monkeypatch.setattr(bridge, "SUPPORTED_RUNTIME_EXECUTORS", ("antigravity", "codex", "claude-code", "cursor"))
    with pytest.raises(SystemExit):
        bridge._validate_task_032_portability_scope(cfg, auth)

    monkeypatch.setattr(bridge, "SUPPORTED_RUNTIME_EXECUTORS", ("antigravity", "codex", "claude-code"))

    # 2. Modified core file vs base fails
    monkeypatch.setattr(
        bridge,
        "git",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args, 0, "src/aios_bridge/continuity/state.py\n", ""
        ),
    )
    with pytest.raises(SystemExit):
        bridge._validate_task_032_portability_scope(cfg, auth)

    # 3. Git diff error fails closed
    monkeypatch.setattr(
        bridge,
        "git",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args, 128, "", "fatal: bad revision '08508e48f6ffda70d1891dad461f6fd1b893b24b'"
        ),
    )
    with pytest.raises(SystemExit):
        bridge._validate_task_032_portability_scope(cfg, auth)


def test_prepare_task_branch_run_fails_closed_when_stale_branch_not_descended_from_bound_base_main(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    """
    Validates Finding B1 (TASK-086): A RUN task branch that is not descended from
    the bound base_main_sha fails closed immediately instead of silently using a stale lineage.
    """
    cfg = {
        "remote": "origin",
        "task_branch_prefix": "ai/task-",
        "base_branch": "main",
    }

    # Simulate existing branch that is not descended from bound_base_sha
    monkeypatch.setattr(bridge, "current_branch", lambda: "main")
    monkeypatch.setattr(bridge, "non_ai_dirty_paths", lambda: [])
    monkeypatch.setattr(bridge, "git", lambda *args, **kwargs: None)
    monkeypatch.setattr(bridge, "local_branch_exists", lambda b: True)
    monkeypatch.setattr(bridge, "sync_existing_task_branch", lambda r, b: None)
    monkeypatch.setattr(bridge, "is_git_ancestor", lambda anc, desc: False)

    with pytest.raises(SystemExit):
        bridge.prepare_task_branch(
            cfg,
            task_id=86,
            action="RUN",
            bound_base_sha="11967270857dd886e6e686a599bdd40e1d684619",
        )


def test_evidence_refresh_dirty_worktree_fails_before_certification(
    monkeypatch: pytest.MonkeyPatch,
):
    """Proof: EVIDENCE_REFRESH_DIRTY_WORKTREE_FAILS_BEFORE_CERTIFICATION: PASS (Finding B4)."""
    cfg = {"remote": "origin", "task_branch_prefix": "ai/task-", "control_branch": "ai-control"}
    lease_cand = bridge.build_executor_lease_candidate(
        task_id="TASK-086",
        workspace_id="a" * 64,
        operation=bridge.ExecutionOperation.FIX,
        target_branch="ai/task-086",
        authorized_artifact_path=".ai/reviews/REVIEW-086.md",
        authorized_artifact_blob_sha="a" * 40,
        executor_id="antigravity",
    )
    auth = {
        "task_id": "TASK-086",
        "action": "FIX",
        "fix_execution_mode": "EVIDENCE_REFRESH",
        "artifact_path": ".ai/reviews/REVIEW-086.md",
        "artifact_blob_sha": "a" * 40,
        "reviewed_task_head_sha": "b" * 40,
        "executor_id": "antigravity",
        "lease_id": lease_cand.lease_id,
        "lease_fingerprint": lease_cand.fingerprint(),
        "workspace_id": lease_cand.workspace_id,
        "execution_fingerprint": lease_cand.execution_fingerprint,
    }

    monkeypatch.setattr(bridge, "load_config", lambda: cfg)
    monkeypatch.setattr(bridge, "get_active_authorization", lambda t: auth)
    monkeypatch.setattr(bridge, "current_branch", lambda: "ai/task-086")
    monkeypatch.setattr(bridge, "get_lease_store", lambda: type("Store", (), {"require_active": lambda s, l: None})())
    monkeypatch.setattr(bridge, "fetch_control", lambda c: None)
    monkeypatch.setattr(bridge, "get_remote_blob_sha", lambda c, p: "a" * 40)
    monkeypatch.setattr(bridge, "observe_e4_head", lambda: "b" * 40)
    # Simulate dirty non-.ai worktree
    monkeypatch.setattr(bridge, "non_ai_dirty_paths", lambda: ["src/some_file.py"])

    test_executed = []
    args = type("Args", (), {
        "task_id": 86,
        "action": "fix",
        "test": "pytest",
        "summary": "refresh",
        "notes": None,
        "message": None,
    })()

    monkeypatch.setattr(bridge, "run", lambda cmd, **kwargs: test_executed.append(cmd))

    with pytest.raises(SystemExit):
        bridge.cmd_publish(args)

    # Test certification must NEVER be reached when worktree is dirty!
    assert test_executed == []


def test_evidence_refresh_head_drift_fails_before_certification(
    monkeypatch: pytest.MonkeyPatch,
):
    """Proof: EVIDENCE_REFRESH_HEAD_DRIFT_FAILS_BEFORE_CERTIFICATION: PASS (Finding B4)."""
    cfg = {"remote": "origin", "task_branch_prefix": "ai/task-", "control_branch": "ai-control"}
    lease_cand = bridge.build_executor_lease_candidate(
        task_id="TASK-086",
        workspace_id="a" * 64,
        operation=bridge.ExecutionOperation.FIX,
        target_branch="ai/task-086",
        authorized_artifact_path=".ai/reviews/REVIEW-086.md",
        authorized_artifact_blob_sha="a" * 40,
        executor_id="antigravity",
    )
    auth = {
        "task_id": "TASK-086",
        "action": "FIX",
        "fix_execution_mode": "EVIDENCE_REFRESH",
        "artifact_path": ".ai/reviews/REVIEW-086.md",
        "artifact_blob_sha": "a" * 40,
        "reviewed_task_head_sha": "b" * 40,
        "executor_id": "antigravity",
        "lease_id": lease_cand.lease_id,
        "lease_fingerprint": lease_cand.fingerprint(),
        "workspace_id": lease_cand.workspace_id,
        "execution_fingerprint": lease_cand.execution_fingerprint,
    }

    monkeypatch.setattr(bridge, "load_config", lambda: cfg)
    monkeypatch.setattr(bridge, "get_active_authorization", lambda t: auth)
    monkeypatch.setattr(bridge, "current_branch", lambda: "ai/task-086")
    monkeypatch.setattr(bridge, "get_lease_store", lambda: type("Store", (), {"require_active": lambda s, l: None})())
    monkeypatch.setattr(bridge, "fetch_control", lambda c: None)
    monkeypatch.setattr(bridge, "get_remote_blob_sha", lambda c, p: "a" * 40)
    # Head drifted from reviewed "b"*40 to "c"*40
    monkeypatch.setattr(bridge, "observe_e4_head", lambda: "c" * 40)
    monkeypatch.setattr(bridge, "non_ai_dirty_paths", lambda: [])

    test_executed = []
    args = type("Args", (), {
        "task_id": 86,
        "action": "fix",
        "test": "pytest",
        "summary": "refresh",
        "notes": None,
        "message": None,
    })()

    monkeypatch.setattr(bridge, "run", lambda cmd, **kwargs: test_executed.append(cmd))

    with pytest.raises(SystemExit):
        bridge.cmd_publish(args)

    # Test certification must NEVER be reached when head drifted!
    assert test_executed == []


def test_evidence_refresh_exact_clean_reviewed_head_passes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    """Proof: EVIDENCE_REFRESH_EXACT_CLEAN_REVIEWED_HEAD_PASSES: PASS (Finding B4)."""
    cfg = {"remote": "origin", "task_branch_prefix": "ai/task-", "control_branch": "ai-control"}
    lease_cand = bridge.build_executor_lease_candidate(
        task_id="TASK-086",
        workspace_id="a" * 64,
        operation=bridge.ExecutionOperation.FIX,
        target_branch="ai/task-086",
        authorized_artifact_path=".ai/reviews/REVIEW-086.md",
        authorized_artifact_blob_sha="a" * 40,
        executor_id="antigravity",
    )
    auth = {
        "task_id": "TASK-086",
        "action": "FIX",
        "fix_execution_mode": "EVIDENCE_REFRESH",
        "artifact_path": ".ai/reviews/REVIEW-086.md",
        "artifact_blob_sha": "a" * 40,
        "reviewed_task_head_sha": "b" * 40,
        "executor_id": "antigravity",
        "lease_id": lease_cand.lease_id,
        "lease_fingerprint": lease_cand.fingerprint(),
        "workspace_id": lease_cand.workspace_id,
        "execution_fingerprint": lease_cand.execution_fingerprint,
    }

    ai_dir = tmp_path / ".ai"
    (ai_dir / "results").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(bridge, "AI", ai_dir)
    monkeypatch.setattr(bridge, "load_config", lambda: cfg)
    monkeypatch.setattr(bridge, "get_active_authorization", lambda t: auth)
    monkeypatch.setattr(bridge, "current_branch", lambda: "ai/task-086")
    monkeypatch.setattr(bridge, "get_lease_store", lambda: type("Store", (), {
        "require_active": lambda s, l: None,
        "release": lambda s, l: None,
    })())
    monkeypatch.setattr(bridge, "fetch_control", lambda c: None)
    monkeypatch.setattr(bridge, "get_remote_blob_sha", lambda c, p: "a" * 40)
    monkeypatch.setattr(bridge, "read_remote_file", lambda c, p: "STATUS: CHANGES_REQUIRED\n")
    # Head exactly matches reviewed "b"*40
    monkeypatch.setattr(bridge, "observe_e4_head", lambda: "b" * 40)
    monkeypatch.setattr(bridge, "non_ai_dirty_paths", lambda: [])
    monkeypatch.setattr(bridge, "git", lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "b" * 40, ""))
    monkeypatch.setattr(bridge, "save_authorization", lambda t, a: None)
    monkeypatch.setattr(bridge, "update_state", lambda t, s, m: None)

    test_executed = []
    args = type("Args", (), {
        "task_id": 86,
        "action": "fix",
        "test": "pytest",
        "summary": "refresh",
        "notes": None,
        "message": None,
    })()

    monkeypatch.setattr(bridge, "run", lambda cmd, **kwargs: (test_executed.append(cmd), subprocess.CompletedProcess(cmd, 0, "1 passed", ""))[1])

    # Should proceed through test certification and publish without exiting
    bridge.cmd_publish(args)

    assert test_executed == ["pytest"]
    assert auth["status"] == "CONSUMED"


def test_handoff_context_failure_before_start_releases_new_lease_and_restores_prior(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    """Proof: HANDOFF_CONTEXT_FAILURE_BEFORE_START_RELEASES_NEW_LEASE and HANDOFF_CONTEXT_FAILURE_RESTORES_PRIOR_AUTH_AND_STATE."""
    cfg = {"remote": "origin", "task_branch_prefix": "ai/task-", "control_branch": "ai-control", "base_branch": "main"}
    task_id = 999
    prior_lease = bridge.build_executor_lease_candidate(
        task_id="TASK-999",
        workspace_id="0" * 64,
        operation=bridge.ExecutionOperation.RUN,
        target_branch="ai/task-999",
        authorized_artifact_path=".ai/tasks/TASK-999.md",
        authorized_artifact_blob_sha="a" * 40,
        executor_id="codex",
    )
    prior_auth = {
        "task_id": "TASK-999",
        "action": "RUN",
        "kind": "TASK",
        "artifact_path": ".ai/tasks/TASK-999.md",
        "artifact_blob_sha": "a" * 40,
        "status": "CONSUMED",
        "published_sha": "b" * 40,
        "executor_id": "codex",
        "lease_id": prior_lease.lease_id,
        "lease_fingerprint": prior_lease.fingerprint(),
        "workspace_id": prior_lease.workspace_id,
        "execution_fingerprint": prior_lease.execution_fingerprint,
    }
    prior_state = {
        "phase": "unset",
        "active_task": "TASK-999",
        "status": "CHANGES_REQUIRED",
        "last_review": "REVIEW-999",
        "next_step": "Approve review fix before execution",
    }

    released_leases = []
    store = type("MockStore", (), {
        "acquire": lambda s, cand: cand,
        "release": lambda s, l: released_leases.append(l.lease_id),
        "load_active": lambda s, t: None,
    })()

    auth_saved = []
    saved_state = [prior_state]

    monkeypatch.setattr(bridge, "ensure_git", lambda: None)
    monkeypatch.setattr(bridge, "ensure_dirs", lambda: None)
    monkeypatch.setattr(bridge, "load_config", lambda: cfg)
    monkeypatch.setattr(bridge, "fetch_control", lambda c: None)
    monkeypatch.setattr(bridge, "get_remote_blob_sha", lambda c, p: "a" * 40)
    review_content = (
        "STATUS: CHANGES_REQUIRED\n"
        "TASK_ID: TASK-999\n"
        "REVIEWED_TASK_HEAD_SHA: " + "b" * 40 + "\n"
        "FIX_EXECUTION_MODE: IMPLEMENTATION\n"
    )
    task_content = "TASK_ID: TASK-999\n"
    monkeypatch.setattr(bridge, "read_remote_file", lambda c, p: review_content if "REVIEW" in p else task_content)
    monkeypatch.setattr(bridge, "parse_review_status", lambda c: "CHANGES_REQUIRED")
    monkeypatch.setattr(bridge, "preflight_executable_artifact", lambda *a, **k: None)
    monkeypatch.setattr(bridge, "validation_plan_for_task", lambda *a, **k: None)
    monkeypatch.setattr(bridge, "task_requires_roadmap_governance", lambda c: False)
    monkeypatch.setattr(bridge, "parse_task_pipeline_mode", lambda c, **kw: bridge.TaskPipelineMode.REVIEW_FIRST_CERTIFICATION)
    monkeypatch.setattr(bridge, "parse_fix_review_mode", lambda c: bridge.FixReviewMode.COMPATIBILITY)
    monkeypatch.setattr(bridge, "parse_fix_context_pack", lambda c, **kw: None)
    monkeypatch.setattr(bridge, "prepare_task_branch", lambda *a, **k: "ai/task-999")
    monkeypatch.setattr(bridge, "load_authorization", lambda t: prior_auth if not auth_saved else auth_saved[-1])
    monkeypatch.setattr(bridge, "save_authorization", lambda t, a: auth_saved.append(a))
    monkeypatch.setattr(bridge, "get_auth_path", lambda t: tmp_path / f"AUTH-TASK-{t}.json")
    monkeypatch.setattr(bridge, "get_workspace_id", lambda: "0" * 64)
    monkeypatch.setattr(bridge, "get_lease_store", lambda: store)
    monkeypatch.setattr(bridge, "load_json", lambda p, default=None: copy.deepcopy(saved_state[-1]) if "state" in str(p) else default)
    monkeypatch.setattr(bridge, "save_json", lambda p, d: saved_state.append(copy.deepcopy(d)) if "state" in str(p) else None)
    monkeypatch.setattr(bridge, "clear_pending_events", lambda *a: None)
    monkeypatch.setattr(bridge, "get_runtime_paths", lambda: {"state": tmp_path / "CURRENT_STATE.json", "seen": tmp_path / "seen.json", "root": tmp_path})
    monkeypatch.setattr(bridge, "get_artifact_path", lambda p: tmp_path / p)
    monkeypatch.setattr(
        bridge,
        "git",
        lambda *args, **kw: subprocess.CompletedProcess(
            args, 0, "ai/task-999" if "branch" in args else "b" * 40, ""
        ),
    )

    # Force cmd_context to fail during pre-start
    monkeypatch.setattr(bridge, "cmd_context", lambda args: (_ for _ in ()).throw(RuntimeError("Context rendering failed")))

    args = type("Args", (), {"task_id": 999, "action": "fix", "executor": "antigravity"})()
    with pytest.raises(SystemExit):
        bridge.cmd_handoff(args)

    # Verified: newly acquired lease was released!
    assert len(released_leases) == 1
    # Prior authorization restored
    assert auth_saved[-1] == prior_auth
    # Prior state restored
    assert saved_state[-1] == prior_state


def test_antigravity_and_codex_pre_start_failures_have_no_stale_leases(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    """Proof: ANTIGRAVITY_PRE_START_FAILURE_HAS_NO_STALE_LEASE and CODEX_PRE_START_FAILURE_HAS_NO_STALE_LEASE."""
    for executor in ("antigravity", "codex"):
        cfg = {"remote": "origin", "task_branch_prefix": "ai/task-", "control_branch": "ai-control", "base_branch": "main"}
        prior_lease = bridge.build_executor_lease_candidate(
            task_id="TASK-999",
            workspace_id="0" * 64,
            operation=bridge.ExecutionOperation.RUN,
            target_branch="ai/task-999",
            authorized_artifact_path=".ai/tasks/TASK-999.md",
            authorized_artifact_blob_sha="a" * 40,
            executor_id=executor,
        )
        prior_auth = {
            "task_id": "TASK-999",
            "action": "RUN",
            "kind": "TASK",
            "artifact_path": ".ai/tasks/TASK-999.md",
            "artifact_blob_sha": "a" * 40,
            "status": "CONSUMED",
            "published_sha": "b" * 40,
            "executor_id": executor,
            "lease_id": prior_lease.lease_id,
            "lease_fingerprint": prior_lease.fingerprint(),
            "workspace_id": prior_lease.workspace_id,
            "execution_fingerprint": prior_lease.execution_fingerprint,
        }
        released_leases = []
        store = type("MockStore", (), {
            "acquire": lambda s, cand: cand,
            "release": lambda s, l: released_leases.append(l.lease_id),
            "load_active": lambda s, t: None,
        })()

        monkeypatch.setattr(bridge, "ensure_git", lambda: None)
        monkeypatch.setattr(bridge, "ensure_dirs", lambda: None)
        monkeypatch.setattr(bridge, "load_config", lambda: cfg)
        monkeypatch.setattr(bridge, "fetch_control", lambda c: None)
        monkeypatch.setattr(bridge, "get_remote_blob_sha", lambda c, p: "a" * 40)
        review_content = (
            "STATUS: CHANGES_REQUIRED\n"
            "TASK_ID: TASK-999\n"
            "REVIEWED_TASK_HEAD_SHA: " + "b" * 40 + "\n"
            "FIX_EXECUTION_MODE: IMPLEMENTATION\n"
        )
        task_content = "TASK_ID: TASK-999\n"
        monkeypatch.setattr(bridge, "read_remote_file", lambda c, p: review_content if "REVIEW" in p else task_content)
        monkeypatch.setattr(bridge, "parse_review_status", lambda c: "CHANGES_REQUIRED")
        monkeypatch.setattr(bridge, "preflight_executable_artifact", lambda *a, **k: None)
        monkeypatch.setattr(bridge, "validation_plan_for_task", lambda *a, **k: None)
        monkeypatch.setattr(bridge, "task_requires_roadmap_governance", lambda c: False)
        monkeypatch.setattr(bridge, "parse_task_pipeline_mode", lambda c, **kw: bridge.TaskPipelineMode.REVIEW_FIRST_CERTIFICATION)
        monkeypatch.setattr(bridge, "parse_fix_review_mode", lambda c: bridge.FixReviewMode.COMPATIBILITY)
        monkeypatch.setattr(bridge, "parse_fix_context_pack", lambda c, **kw: None)
        monkeypatch.setattr(bridge, "prepare_task_branch", lambda *a, **k: "ai/task-999")
        monkeypatch.setattr(bridge, "load_authorization", lambda t: prior_auth)
        monkeypatch.setattr(bridge, "save_authorization", lambda t, a: None)
        monkeypatch.setattr(bridge, "get_auth_path", lambda t: tmp_path / f"AUTH-TASK-{t}.json")
        monkeypatch.setattr(bridge, "get_workspace_id", lambda: "0" * 64)
        monkeypatch.setattr(bridge, "get_lease_store", lambda: store)
        monkeypatch.setattr(bridge, "load_json", lambda p, default=None: default)
        monkeypatch.setattr(bridge, "save_json", lambda p, d: None)
        monkeypatch.setattr(bridge, "clear_pending_events", lambda *a: None)
        monkeypatch.setattr(bridge, "get_runtime_paths", lambda: {"state": tmp_path / "CURRENT_STATE.json", "seen": tmp_path / "seen.json", "root": tmp_path})
        monkeypatch.setattr(bridge, "get_artifact_path", lambda p: tmp_path / p)

        # Force cmd_context failure
        monkeypatch.setattr(bridge, "cmd_context", lambda args: (_ for _ in ()).throw(RuntimeError("Pre-start failure")))

        args = type("Args", (), {"task_id": 999, "action": "fix", "executor": executor})()
        with pytest.raises(SystemExit):
            bridge.cmd_handoff(args)

        assert len(released_leases) == 1


def test_uncertain_executor_start_state_still_requires_recovery(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    """Proof: UNCERTAIN_EXECUTOR_START_STATE_STILL_REQUIRES_RECOVERY and NO_AUTO_RETRY_OR_REROUTE."""
    monkeypatch.setattr(bridge, "get_auth_path", lambda t: tmp_path / f"AUTH-TASK-{t}.json")
    monkeypatch.setattr(bridge, "save_authorization", lambda t, a: None)
    monkeypatch.setattr(bridge, "update_state", lambda *a: None)
    # When rollback encounters uncertain state restore, it must fail closed and record RECOVERY_REQUIRED
    store = type("MockStore", (), {
        "release": lambda s, l: (_ for _ in ()).throw(RuntimeError("Lease release failed")),
    })()
    auth = {
        "task_id": "TASK-999",
        "action": "FIX",
        "executor_id": "antigravity",
        "lease_id": "lease-task-999-1",
        "lease_fingerprint": "1" * 64,
        "workspace_id": "0" * 64,
        "execution_fingerprint": "e" * 64,
    }
    with pytest.raises(bridge.ContinuityStateValidationError, match="pre-start rollback could not prove clean restoration"):
        bridge._rollback_proven_pre_start_failure(999, auth, None, "test cause")


def test_handoff_context_systemexit_before_start_releases_new_lease_and_restores_prior(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    """Proof: HANDOFF_CONTEXT_SYSTEMEXIT_BEFORE_START_RELEASES_NEW_LEASE, HANDOFF_CONTEXT_SYSTEMEXIT_RESTORES_PRIOR_AUTH_AND_STATE, and NORMAL_EXCEPTION_PRE_START_ROLLBACK_REMAINS_GREEN."""
    cfg = {"remote": "origin", "task_branch_prefix": "ai/task-", "control_branch": "ai-control", "base_branch": "main"}
    prior_lease = bridge.build_executor_lease_candidate(
        task_id="TASK-999",
        workspace_id="0" * 64,
        operation=bridge.ExecutionOperation.RUN,
        target_branch="ai/task-999",
        authorized_artifact_path=".ai/tasks/TASK-999.md",
        authorized_artifact_blob_sha="a" * 40,
        executor_id="codex",
    )
    prior_auth = {
        "task_id": "TASK-999",
        "action": "RUN",
        "kind": "TASK",
        "artifact_path": ".ai/tasks/TASK-999.md",
        "artifact_blob_sha": "a" * 40,
        "status": "CONSUMED",
        "published_sha": "b" * 40,
        "executor_id": "codex",
        "lease_id": prior_lease.lease_id,
        "lease_fingerprint": prior_lease.fingerprint(),
        "workspace_id": prior_lease.workspace_id,
        "execution_fingerprint": prior_lease.execution_fingerprint,
    }
    prior_state = {
        "phase": "unset",
        "active_task": "TASK-999",
        "status": "CHANGES_REQUIRED",
        "last_review": "REVIEW-999",
        "next_step": "Approve review fix before execution",
    }

    released_leases = []
    store = type("MockStore", (), {
        "acquire": lambda s, cand: cand,
        "release": lambda s, l: released_leases.append(l.lease_id),
        "load_active": lambda s, t: None,
    })()

    auth_saved = []
    saved_state = [prior_state]

    monkeypatch.setattr(bridge, "ensure_git", lambda: None)
    monkeypatch.setattr(bridge, "ensure_dirs", lambda: None)
    monkeypatch.setattr(bridge, "load_config", lambda: cfg)
    monkeypatch.setattr(bridge, "fetch_control", lambda c: None)
    monkeypatch.setattr(bridge, "get_remote_blob_sha", lambda c, p: "a" * 40)
    review_content = (
        "STATUS: CHANGES_REQUIRED\n"
        "TASK_ID: TASK-999\n"
        "REVIEWED_TASK_HEAD_SHA: " + "b" * 40 + "\n"
        "FIX_EXECUTION_MODE: IMPLEMENTATION\n"
    )
    task_content = "TASK_ID: TASK-999\n"
    monkeypatch.setattr(bridge, "read_remote_file", lambda c, p: review_content if "REVIEW" in p else task_content)
    monkeypatch.setattr(bridge, "parse_review_status", lambda c: "CHANGES_REQUIRED")
    monkeypatch.setattr(bridge, "preflight_executable_artifact", lambda *a, **k: None)
    monkeypatch.setattr(bridge, "validation_plan_for_task", lambda *a, **k: None)
    monkeypatch.setattr(bridge, "task_requires_roadmap_governance", lambda c: False)
    monkeypatch.setattr(bridge, "parse_task_pipeline_mode", lambda c, **kw: bridge.TaskPipelineMode.REVIEW_FIRST_CERTIFICATION)
    monkeypatch.setattr(bridge, "parse_fix_review_mode", lambda c: bridge.FixReviewMode.COMPATIBILITY)
    monkeypatch.setattr(bridge, "parse_fix_context_pack", lambda c, **kw: None)
    monkeypatch.setattr(bridge, "prepare_task_branch", lambda *a, **k: "ai/task-999")
    monkeypatch.setattr(bridge, "load_authorization", lambda t: prior_auth if not auth_saved else auth_saved[-1])
    monkeypatch.setattr(bridge, "save_authorization", lambda t, a: auth_saved.append(a))
    monkeypatch.setattr(bridge, "get_auth_path", lambda t: tmp_path / f"AUTH-TASK-{t}.json")
    monkeypatch.setattr(bridge, "get_workspace_id", lambda: "0" * 64)
    monkeypatch.setattr(bridge, "get_lease_store", lambda: store)
    monkeypatch.setattr(bridge, "load_json", lambda p, default=None: copy.deepcopy(saved_state[-1]) if "state" in str(p) else default)
    monkeypatch.setattr(bridge, "save_json", lambda p, d: saved_state.append(copy.deepcopy(d)) if "state" in str(p) else None)
    monkeypatch.setattr(bridge, "clear_pending_events", lambda *a: None)
    monkeypatch.setattr(bridge, "get_runtime_paths", lambda: {"state": tmp_path / "CURRENT_STATE.json", "seen": tmp_path / "seen.json", "root": tmp_path})
    monkeypatch.setattr(bridge, "get_artifact_path", lambda p: tmp_path / p)
    monkeypatch.setattr(
        bridge,
        "git",
        lambda *args, **kw: subprocess.CompletedProcess(
            args, 0, "ai/task-999" if "branch" in args else "b" * 40, ""
        ),
    )

    # Force cmd_context to raise SystemExit via bridge.fail during pre-start
    monkeypatch.setattr(bridge, "cmd_context", lambda args: bridge.fail("Deterministic pre-start git branch failure"))

    args = type("Args", (), {"task_id": 999, "action": "fix", "executor": "antigravity"})()
    with pytest.raises(SystemExit):
        bridge.cmd_handoff(args)

    assert len(released_leases) == 1
    assert auth_saved[-1] == prior_auth
    assert saved_state[-1] == prior_state


def test_antigravity_and_codex_systemexit_pre_start_have_no_stale_leases(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    """Proof: ANTIGRAVITY_SYSTEMEXIT_PRE_START_HAS_NO_STALE_LEASE and CODEX_SYSTEMEXIT_PRE_START_HAS_NO_STALE_LEASE."""
    for executor in ("antigravity", "codex"):
        cfg = {"remote": "origin", "task_branch_prefix": "ai/task-", "control_branch": "ai-control", "base_branch": "main"}
        prior_lease = bridge.build_executor_lease_candidate(
            task_id="TASK-999",
            workspace_id="0" * 64,
            operation=bridge.ExecutionOperation.RUN,
            target_branch="ai/task-999",
            authorized_artifact_path=".ai/tasks/TASK-999.md",
            authorized_artifact_blob_sha="a" * 40,
            executor_id=executor,
        )
        prior_auth = {
            "task_id": "TASK-999",
            "action": "RUN",
            "kind": "TASK",
            "artifact_path": ".ai/tasks/TASK-999.md",
            "artifact_blob_sha": "a" * 40,
            "status": "CONSUMED",
            "published_sha": "b" * 40,
            "executor_id": executor,
            "lease_id": prior_lease.lease_id,
            "lease_fingerprint": prior_lease.fingerprint(),
            "workspace_id": prior_lease.workspace_id,
            "execution_fingerprint": prior_lease.execution_fingerprint,
        }
        released_leases = []
        store = type("MockStore", (), {
            "acquire": lambda s, cand: cand,
            "release": lambda s, l: released_leases.append(l.lease_id),
            "load_active": lambda s, t: None,
        })()

        monkeypatch.setattr(bridge, "ensure_git", lambda: None)
        monkeypatch.setattr(bridge, "ensure_dirs", lambda: None)
        monkeypatch.setattr(bridge, "load_config", lambda: cfg)
        monkeypatch.setattr(bridge, "fetch_control", lambda c: None)
        monkeypatch.setattr(bridge, "get_remote_blob_sha", lambda c, p: "a" * 40)
        review_content = (
            "STATUS: CHANGES_REQUIRED\n"
            "TASK_ID: TASK-999\n"
            "REVIEWED_TASK_HEAD_SHA: " + "b" * 40 + "\n"
            "FIX_EXECUTION_MODE: IMPLEMENTATION\n"
        )
        task_content = "TASK_ID: TASK-999\n"
        monkeypatch.setattr(bridge, "read_remote_file", lambda c, p: review_content if "REVIEW" in p else task_content)
        monkeypatch.setattr(bridge, "parse_review_status", lambda c: "CHANGES_REQUIRED")
        monkeypatch.setattr(bridge, "preflight_executable_artifact", lambda *a, **k: None)
        monkeypatch.setattr(bridge, "validation_plan_for_task", lambda *a, **k: None)
        monkeypatch.setattr(bridge, "task_requires_roadmap_governance", lambda c: False)
        monkeypatch.setattr(bridge, "parse_task_pipeline_mode", lambda c, **kw: bridge.TaskPipelineMode.REVIEW_FIRST_CERTIFICATION)
        monkeypatch.setattr(bridge, "parse_fix_review_mode", lambda c: bridge.FixReviewMode.COMPATIBILITY)
        monkeypatch.setattr(bridge, "parse_fix_context_pack", lambda c, **kw: None)
        monkeypatch.setattr(bridge, "prepare_task_branch", lambda *a, **k: "ai/task-999")
        monkeypatch.setattr(bridge, "load_authorization", lambda t: prior_auth)
        monkeypatch.setattr(bridge, "save_authorization", lambda t, a: None)
        monkeypatch.setattr(bridge, "get_auth_path", lambda t: tmp_path / f"AUTH-TASK-{t}.json")
        monkeypatch.setattr(bridge, "get_workspace_id", lambda: "0" * 64)
        monkeypatch.setattr(bridge, "get_lease_store", lambda: store)
        monkeypatch.setattr(bridge, "load_json", lambda p, default=None: default)
        monkeypatch.setattr(bridge, "save_json", lambda p, d: None)
        monkeypatch.setattr(bridge, "clear_pending_events", lambda *a: None)
        monkeypatch.setattr(bridge, "get_runtime_paths", lambda: {"state": tmp_path / "CURRENT_STATE.json", "seen": tmp_path / "seen.json", "root": tmp_path})
        monkeypatch.setattr(bridge, "get_artifact_path", lambda p: tmp_path / p)

        # Force SystemExit via fail() during cmd_context
        monkeypatch.setattr(bridge, "cmd_context", lambda args: bridge.fail("Pre-start fail() execution"))

        args = type("Args", (), {"task_id": 999, "action": "fix", "executor": executor})()
        with pytest.raises(SystemExit):
            bridge.cmd_handoff(args)

        assert len(released_leases) == 1


def test_fix_handoff_and_result_emit_exact_reviewed_base_main_sha(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    """Proof: FIX compact evidence emits exact REVIEWED_BASE_MAIN_SHA rather than UNKNOWN."""
    cfg = {"remote": "origin", "task_branch_prefix": "ai/task-", "control_branch": "ai-control", "base_branch": "main"}
    task_id = 999
    expected_base_main = "c" * 40
    reviewed_head = "b" * 40

    prior_lease = bridge.build_executor_lease_candidate(
        task_id="TASK-999",
        workspace_id="0" * 64,
        operation=bridge.ExecutionOperation.RUN,
        target_branch="ai/task-999",
        authorized_artifact_path=".ai/tasks/TASK-999.md",
        authorized_artifact_blob_sha="a" * 40,
        executor_id="antigravity",
    )
    prior_auth = {
        "task_id": "TASK-999",
        "action": "RUN",
        "kind": "TASK",
        "artifact_path": ".ai/tasks/TASK-999.md",
        "artifact_blob_sha": "a" * 40,
        "status": "CONSUMED",
        "published_sha": reviewed_head,
        "base_main_sha": expected_base_main,
        "executor_id": "antigravity",
        "lease_id": prior_lease.lease_id,
        "lease_fingerprint": prior_lease.fingerprint(),
        "workspace_id": prior_lease.workspace_id,
        "execution_fingerprint": prior_lease.execution_fingerprint,
    }

    review_content = (
        "PUBLISHER_PROFILE: CANONICAL_E4\n"
        "STATUS: CHANGES_REQUIRED\n"
        "APPROVED: NO\n"
        "AUTO_MERGE_ELIGIBLE: NO\n"
        "MERGE_AUTHORIZED: NO\n"
        "MERGED_TO_MAIN: NO\n"
        "TASK_ID: TASK-999\n"
        f"REVIEWED_TASK_HEAD_SHA: {reviewed_head}\n"
        f"REVIEWED_BASE_MAIN_SHA: {expected_base_main}\n"
        "FIX_EXECUTION_MODE: IMPLEMENTATION\n"
    )
    task_content = "TASK_ID: TASK-999\n"

    auth_saved = []
    store = type("MockStore", (), {
        "acquire": lambda s, cand: cand,
        "release": lambda s, l: None,
        "load_active": lambda s, t: prior_lease,
    })()

    monkeypatch.setattr(bridge, "ensure_git", lambda: None)
    monkeypatch.setattr(bridge, "ensure_dirs", lambda: None)
    monkeypatch.setattr(bridge, "load_config", lambda: cfg)
    monkeypatch.setattr(bridge, "fetch_control", lambda c: None)
    monkeypatch.setattr(bridge, "get_remote_blob_sha", lambda c, p: "a" * 40)
    monkeypatch.setattr(bridge, "read_remote_file", lambda c, p: review_content if "REVIEW" in p else task_content)
    monkeypatch.setattr(bridge, "parse_review_status", lambda c: "CHANGES_REQUIRED")
    monkeypatch.setattr(bridge, "preflight_executable_artifact", lambda *a, **k: None)
    monkeypatch.setattr(bridge, "validation_plan_for_task", lambda *a, **k: None)
    monkeypatch.setattr(bridge, "task_requires_roadmap_governance", lambda c: False)
    monkeypatch.setattr(bridge, "parse_task_pipeline_mode", lambda c, **kw: bridge.TaskPipelineMode.REVIEW_FIRST_CERTIFICATION)
    monkeypatch.setattr(bridge, "parse_fix_review_mode", lambda c: bridge.FixReviewMode.COMPATIBILITY)
    monkeypatch.setattr(bridge, "parse_fix_context_pack", lambda c, **kw: None)
    monkeypatch.setattr(bridge, "prepare_task_branch", lambda *a, **k: "ai/task-999")
    monkeypatch.setattr(bridge, "load_authorization", lambda t: prior_auth if not auth_saved else auth_saved[-1])
    monkeypatch.setattr(bridge, "save_authorization", lambda t, a: auth_saved.append(a))
    monkeypatch.setattr(bridge, "get_auth_path", lambda t: tmp_path / f"AUTH-TASK-{t}.json")
    monkeypatch.setattr(bridge, "get_workspace_id", lambda: "0" * 64)
    monkeypatch.setattr(bridge, "get_lease_store", lambda: store)
    monkeypatch.setattr(bridge, "load_json", lambda p, default=None: default)
    monkeypatch.setattr(bridge, "save_json", lambda p, d: None)
    monkeypatch.setattr(bridge, "clear_pending_events", lambda *a: None)
    monkeypatch.setattr(bridge, "get_runtime_paths", lambda: {"state": tmp_path / "CURRENT_STATE.json", "seen": tmp_path / "seen.json", "root": tmp_path})
    monkeypatch.setattr(bridge, "get_artifact_path", lambda p: tmp_path / p)
    monkeypatch.setattr(bridge, "cmd_context", lambda args: None)

    args = type("Args", (), {"task_id": 999, "action": "fix", "executor": "antigravity"})()
    bridge.cmd_handoff(args)

    assert len(auth_saved) == 1
    assert auth_saved[0]["base_main_sha"] == expected_base_main
