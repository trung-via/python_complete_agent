from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
import pytest

import bridge


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
            bridge.read_remote_file = lambda cfg, path: "# TASK-006 Content\n"
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
            bridge.read_remote_file = lambda cfg, path: "# REVIEW-006\n\n## Status\nCHANGES_REQUIRED\n\nPlease fix unit tests."

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
            }
            bridge.save_authorization(6, auth)

            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: "c" * 40

            # Mock git push
            bridge.git = lambda *args, **kw: (
                type("Res", (), {"returncode": 0, "stdout": "", "stderr": ""})()
                if args[0] == "push"
                else subprocess.run(["git", *args], cwd=root, check=kw.get("check", True), capture_output=True, text=True)
            )

            bridge.cmd_publish(type("Args", (), {
                "task_id": 6,
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

            auth = {
                "task_id": "TASK-006",
                "action": "RUN",
                "kind": "TASK",
                "artifact_path": ".ai/tasks/TASK-006.md",
                "artifact_blob_sha": "d" * 40,
                "approved_at": bridge.now(),
                "branch": "ai/task-006",
                "status": "ACTIVE",
            }
            bridge.save_authorization(6, auth)

            bridge.fetch_control = lambda cfg: None
            bridge.get_remote_blob_sha = lambda cfg, path: "d" * 40

            with pytest.raises(SystemExit):
                bridge.cmd_publish(type("Args", (), {
                    "task_id": 6,
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
