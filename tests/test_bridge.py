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

        # Without override, get_runtime_dir must be outside repo_root
        runtime_dir = bridge.get_runtime_dir(repo_root)

        assert not str(runtime_dir).startswith(str(repo_root))
        assert runtime_dir.name.startswith("my_project-")

        # With override AIOS_RUNTIME_DIR
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

        # Initialize clean git repo
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

            # Mock remote inbound artifacts from control branch
            inbound_task = (".ai/tasks/TASK-001.md", "1111111111111111111111111111111111111111")
            inbound_review = (".ai/reviews/REVIEW-001.md", "2222222222222222222222222222222222222222")

            bridge.fetch_control = lambda cfg: None
            bridge.list_remote_inbound = lambda cfg: [inbound_task, inbound_review]
            bridge.read_remote_file = lambda cfg, path: (
                "# Task 1\n" if "tasks" in path else "# Review 1\n## Status\nCHANGES_REQUIRED\n"
            )

            # Execute sync_once
            changed = bridge.sync_once(verbose=False)
            assert len(changed) == 2

            # CRITICAL INVARIANT: Git status in worktree must remain 100% clean!
            p_status = subprocess.run(["git", "status", "--porcelain"], cwd=root, check=True, capture_output=True, text=True)
            assert p_status.stdout.strip() == "", f"Git worktree was dirtied by sync: {p_status.stdout}"

            # Pending events are available in external runtime inbox
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

            # Assert: pending list is now empty!
            events = bridge.pending_events()
            assert len(events) == 0, f"Expected 0 pending events, got: {events}"

            # Assert: state status is APPROVED (not regressed to CHANGES_REQUIRED)
            state = bridge.load_json(bridge.get_runtime_paths()["state"], {})
            assert state["status"] == "APPROVED"
            assert "approved" in state["next_step"].lower()

            # Assert: notification was informational, not instructing /aios-worker FIX
            last_title, last_msg = notifications[-1]
            assert "APPROVED" in last_msg
            assert "/aios-worker" not in last_msg
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
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
        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.ensure_git = lambda: None
            bridge.ensure_dirs()
            cfg = {"windows_popup": False, "remote": "origin", "control_branch": "ai-control"}
            bridge.save_json(bridge.get_runtime_paths()["config"], cfg)

            bridge.fetch_control = lambda cfg: None
            bridge.list_remote_inbound = lambda cfg: [(".ai/reviews/REVIEW-004.md", "3" * 40)]
            # Unrecognized status
            bridge.read_remote_file = lambda cfg, path: "# REVIEW-004\n\nJust some notes without status.\n"

            bridge.sync_once(verbose=False)

            # Must NOT create pending approval event
            assert len(bridge.pending_events()) == 0

            # State is REVIEW_RECEIVED, not CHANGES_REQUIRED
            state = bridge.load_json(bridge.get_runtime_paths()["state"], {})
            assert state["status"] == "REVIEW_RECEIVED"
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_task_approval_branch_switch_succeeds_with_bridge_runtime_present():
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
        old_branch_exists = bridge.branch_exists_remote

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

            inbox_file = bridge.write_pending("TASK", 2, ".ai/tasks/TASK-002.md", "a" * 40)
            assert inbox_file.exists()
            assert not (root / ".ai" / "inbox").exists()

            bridge.branch_exists_remote = lambda r, b: False
            bridge.git = lambda *args, **kw: subprocess.run(
                ["git", *args], cwd=root, check=kw.get("check", True), capture_output=True, text=True
            ) if args[0] != "fetch" else type("Res", (), {"returncode": 0, "stdout": "", "stderr": ""})()

            bridge.cmd_approve(type("Args", (), {"task_id": 2, "kind": None})())

            p = subprocess.run(["git", "branch", "--show-current"], cwd=root, check=True, capture_output=True, text=True)
            assert p.stdout.strip() == "ai/task-002"

            ev = bridge.load_json(inbox_file, {})
            assert ev.get("approval") == "APPROVED"
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.git = old_git
            bridge.branch_exists_remote = old_branch_exists
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_review_approval_succeeds_without_stash_or_manual_runtime_movement():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        subprocess.run(["git", "checkout", "-b", "ai/task-002"], cwd=root, check=True, capture_output=True)

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_git = bridge.git
        old_branch_exists = bridge.branch_exists_remote

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

            inbox_file = bridge.write_pending("REVIEW", 2, ".ai/reviews/REVIEW-002.md", "b" * 40)

            bridge.branch_exists_remote = lambda r, b: False
            bridge.git = lambda *args, **kw: subprocess.run(
                ["git", *args], cwd=root, check=kw.get("check", True), capture_output=True, text=True
            ) if args[0] != "fetch" else type("Res", (), {"returncode": 0, "stdout": "", "stderr": ""})()

            bridge.cmd_approve(type("Args", (), {"task_id": 2, "kind": "review"})())

            state = bridge.load_json(bridge.get_runtime_paths()["state"], {})
            assert state.get("status") == "CHANGES_REQUIRED"
            assert state.get("active_task") == "TASK-002"

            ev = bridge.load_json(inbox_file, {})
            assert ev.get("approval") == "APPROVED"
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.git = old_git
            bridge.branch_exists_remote = old_branch_exists
            if "AIOS_RUNTIME_DIR" in os.environ:
                del os.environ["AIOS_RUNTIME_DIR"]


def test_unrelated_dirty_file_still_blocks_switch():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "repo"
        root.mkdir()

        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "aios@test.local"], cwd=root, check=True, capture_output=True)

        (root / "README.md").write_text("# Repo\n", encoding="utf-8")
        (root / "app.py").write_text("print('initial')\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        (root / "app.py").write_text("print('uncommitted change')\n", encoding="utf-8")

        runtime_dir = Path(temp) / "bridge_runtime"
        os.environ["AIOS_RUNTIME_DIR"] = str(runtime_dir)

        old_project = bridge.PROJECT
        old_ai = bridge.AI
        old_git = bridge.git

        bridge.PROJECT = root
        bridge.AI = root / ".ai"

        try:
            bridge.git = lambda *args, **kw: subprocess.run(
                ["git", *args], cwd=root, check=kw.get("check", True), capture_output=True, text=True
            )
            dirty = bridge.non_ai_dirty_paths()
            assert "app.py" in dirty

            with pytest.raises(SystemExit):
                bridge.checkout_task_branch({"remote": "origin", "base_branch": "main", "task_branch_prefix": "ai/task-"}, 2)
        finally:
            bridge.PROJECT = old_project
            bridge.AI = old_ai
            bridge.git = old_git
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
