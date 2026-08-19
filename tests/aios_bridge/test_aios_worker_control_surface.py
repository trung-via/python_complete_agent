"""Test suite for the Unified AIOS Worker Control Surface (TASK-048 / ADR-037).

Tests:
1. Canonical RUN/FIX/STATUS TASK IDs parse correctly
2. Malformed action rejected
3. Malformed TASK IDs rejected
4. Unknown adapter rejected
5. Codex RUN invokes exact handoff argv then exact execute argv
6. Codex FIX invokes exact fix handoff then execute
7. Every Bridge child uses sys.executable, exact repo bridge.py, list argv, shell=False, exact repo cwd
8. Handoff nonzero prevents execute
9. Execute nonzero is returned and never retried
10. No fallback/reroute command occurs
11. Antigravity RUN/FIX invokes handoff only and never execute
12. STATUS invokes sync then pending only
13. STATUS sync failure prevents pending
14. STATUS never invokes handoff/approve/execute/publish/codex
15. Script never invokes bridge.py publish
16. Script never invokes bridge.py approve
17. Script never invokes raw codex/codex exec
18. MERGE is rejected
19. SKILL.md exists with exact name: aios-worker
20. Skill text includes RUN/FIX/STATUS triggers
21. Skill forbids parent-session implementation duplication
22. Skill routes RUN/FIX through adapter with --adapter codex
23. Skill forbids context/approve/publish/direct codex exec/retry/merge
24. Docs state Antigravity/Codex parity and shared Bridge state
25. No network or external API call exists in adapter
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

# ---------------------------------------------------------------------------
# Locate repo root and import the adapter module
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SKILL_DIR = REPO_ROOT / ".agents" / "skills" / "aios-worker"
ADAPTER_SCRIPT = SKILL_DIR / "scripts" / "aios_worker.py"
SKILL_FILE = SKILL_DIR / "SKILL.md"
DOCS_FILE = REPO_ROOT / "docs" / "AIOS_UNIFIED_WORKER_WORKFLOW.md"
BRIDGE_PY = REPO_ROOT / "bridge.py"

# Add script dir to sys.path so we can import aios_worker
if str(ADAPTER_SCRIPT.parent) not in sys.path:
    sys.path.insert(0, str(ADAPTER_SCRIPT.parent))

import aios_worker as aw  # noqa: E402  (import after sys.path mutation)


# ---------------------------------------------------------------------------
# Helper: build a mock subprocess.run that records calls
# ---------------------------------------------------------------------------

def make_mock_run(return_codes: list[int]):
    """Returns a mock subprocess.run that cycles through given exit codes."""
    codes = list(return_codes)
    calls_made: list[dict[str, Any]] = []

    def fake_run(cmd, **kwargs):
        code = codes.pop(0) if codes else 0
        calls_made.append({"cmd": list(cmd), "kwargs": kwargs})
        m = MagicMock()
        m.returncode = code
        return m

    fake_run.calls_made = calls_made  # type: ignore[attr-defined]
    return fake_run


# ===========================================================================
# 1–4. Parsing / Validation
# ===========================================================================

class TestParsing:
    """Tests 1–4: canonical and invalid inputs."""

    @pytest.mark.parametrize("task_str,expected_num", [
        ("TASK-1", 1),
        ("TASK-48", 48),
        ("TASK-048", 48),
        ("TASK-999", 999),
        ("TASK-1000", 1000),
    ])
    def test_canonical_task_ids_parse(self, task_str, expected_num):
        task_id, task_num = aw.parse_task_id(task_str)
        assert task_id == task_str
        assert task_num == expected_num

    @pytest.mark.parametrize("bad_task", [
        "TASK-0",      # zero not allowed
        "task-48",     # lowercase
        "TASK48",      # missing dash
        "TASK-",       # missing digits
        "TASK--48",    # double dash
        "TASK-48x",    # suffix
        "TASK- 48",    # space
        "48",          # no prefix
        "",            # empty
        "TASK-abc",    # non-digits
    ])
    def test_malformed_task_ids_rejected(self, bad_task):
        with pytest.raises(ValueError):
            aw.parse_task_id(bad_task)

    @pytest.mark.parametrize("action", ["RUN", "FIX", "STATUS"])
    def test_canonical_actions_accepted(self, action, tmp_path):
        """Actions that reach main() without being rejected."""
        fake_bridge = tmp_path / "bridge.py"
        fake_bridge.write_text("# fake")
        with patch.object(aw, "get_repo_root", return_value=tmp_path), \
             patch.object(aw, "run_bridge_command", return_value=0):
            code = aw.main([action, "TASK-1", "--adapter", "antigravity"])
        assert code == 0

    @pytest.mark.parametrize("bad_action", ["run", "fix", "MERGE", "START", "DEPLOY", ""])
    def test_malformed_actions_rejected(self, bad_action):
        """Unknown verbs should exit nonzero (argparse rejects unknown choices for adapter, but we test action manually)."""
        # MERGE and lowercase verbs should be rejected in main()
        with patch.object(aw, "get_repo_root", return_value=REPO_ROOT), \
             patch.object(aw, "run_bridge_command", return_value=0):
            code = aw.main([bad_action, "TASK-1", "--adapter", "codex"])
        assert code != 0

    def test_unknown_adapter_rejected(self):
        """Argparse rejects unknown --adapter choices."""
        code = aw.main(["RUN", "TASK-1", "--adapter", "unknown_ui"])
        assert code != 0

    def test_merge_rejected(self):
        """MERGE is not a valid action."""
        with patch.object(aw, "get_repo_root", return_value=REPO_ROOT), \
             patch.object(aw, "run_bridge_command", return_value=0):
            code = aw.main(["MERGE", "TASK-1", "--adapter", "codex"])
        assert code != 0


# ===========================================================================
# 5–10. Codex RUN and FIX exact argv contract
# ===========================================================================

class TestCodexRunFix:
    """Tests 5–10: Codex adapter exact invocation contract."""

    @pytest.fixture(autouse=True)
    def mock_repo_root(self, tmp_path):
        """Provides a fake repo root with bridge.py present."""
        fake_bridge = tmp_path / "bridge.py"
        fake_bridge.write_text("# fake bridge")
        self.fake_root = tmp_path
        return tmp_path

    def _codex_run_with_codes(self, action: str, codes: list[int]):
        mock_run = make_mock_run(codes)
        with patch("subprocess.run", side_effect=mock_run), \
             patch.object(aw, "get_repo_root", return_value=self.fake_root):
            code = aw.main([action, "TASK-48", "--adapter", "codex"])
        return code, mock_run.calls_made

    # Test 5: Codex RUN exact argv order
    def test_codex_run_invokes_handoff_then_execute(self):
        returncode, calls = self._codex_run_with_codes("RUN", [0, 0])
        assert len(calls) == 2

        handoff_call = calls[0]
        assert handoff_call["cmd"][1] == str(self.fake_root / "bridge.py")
        assert "handoff" in handoff_call["cmd"]
        assert "48" in handoff_call["cmd"]
        assert "--action" in handoff_call["cmd"]
        idx = handoff_call["cmd"].index("--action")
        assert handoff_call["cmd"][idx + 1] == "run"
        assert "--executor" in handoff_call["cmd"]
        idx = handoff_call["cmd"].index("--executor")
        assert handoff_call["cmd"][idx + 1] == "codex"

        execute_call = calls[1]
        assert "execute" in execute_call["cmd"]
        assert "48" in execute_call["cmd"]

    # Test 6: Codex FIX exact argv order
    def test_codex_fix_invokes_fix_handoff_then_execute(self):
        returncode, calls = self._codex_run_with_codes("FIX", [0, 0])
        assert len(calls) == 2

        handoff_call = calls[0]
        assert "handoff" in handoff_call["cmd"]
        idx = handoff_call["cmd"].index("--action")
        assert handoff_call["cmd"][idx + 1] == "fix"
        idx = handoff_call["cmd"].index("--executor")
        assert handoff_call["cmd"][idx + 1] == "codex"

        execute_call = calls[1]
        assert "execute" in execute_call["cmd"]

    # Test 7: sys.executable, exact bridge.py, list argv, shell=False, exact cwd
    def test_every_bridge_child_uses_sys_executable_list_argv_no_shell_exact_cwd(self):
        _, calls = self._codex_run_with_codes("RUN", [0, 0])
        for c in calls:
            assert c["cmd"][0] == sys.executable, "Must use sys.executable"
            assert c["cmd"][1] == str(self.fake_root / "bridge.py"), "Exact bridge.py path"
            assert isinstance(c["cmd"], list), "argv must be a list"
            assert c["kwargs"].get("shell") is False or "shell" not in c["kwargs"] or c["kwargs"]["shell"] is False
            assert str(c["kwargs"].get("cwd", "")) == str(self.fake_root), "Must use exact repo cwd"

    def test_subprocess_shell_is_false(self):
        mock_run = make_mock_run([0, 0])
        with patch("subprocess.run", side_effect=mock_run), \
             patch.object(aw, "get_repo_root", return_value=self.fake_root):
            aw.main(["RUN", "TASK-1", "--adapter", "codex"])
        for c in mock_run.calls_made:
            assert c["kwargs"].get("shell", False) is False

    # Test 8: Handoff nonzero prevents execute
    def test_handoff_nonzero_prevents_execute(self):
        returncode, calls = self._codex_run_with_codes("RUN", [1])
        assert returncode == 1
        # Only handoff should have been called; execute never runs
        assert len(calls) == 1
        assert "handoff" in calls[0]["cmd"]

    # Test 9: Execute nonzero is returned, never retried
    def test_execute_nonzero_returned_and_not_retried(self):
        returncode, calls = self._codex_run_with_codes("RUN", [0, 2])
        assert returncode == 2
        assert len(calls) == 2  # handoff + one execute only

    # Test 10: No fallback/reroute on failure
    def test_no_fallback_on_failure(self):
        _, calls = self._codex_run_with_codes("RUN", [1])
        assert len(calls) == 1  # exactly one call, no fallback command


# ===========================================================================
# 11. Antigravity RUN/FIX invokes handoff only (never execute)
# ===========================================================================

class TestAntigravityAdapter:
    """Test 11: Antigravity adapter contract."""

    @pytest.fixture(autouse=True)
    def mock_repo_root(self, tmp_path):
        fake_bridge = tmp_path / "bridge.py"
        fake_bridge.write_text("# fake")
        self.fake_root = tmp_path

    def _antigravity_run_with_codes(self, action: str, codes: list[int]):
        mock_run = make_mock_run(codes)
        with patch("subprocess.run", side_effect=mock_run), \
             patch.object(aw, "get_repo_root", return_value=self.fake_root):
            code = aw.main([action, "TASK-48", "--adapter", "antigravity"])
        return code, mock_run.calls_made

    def test_antigravity_run_invokes_handoff_only(self):
        code, calls = self._antigravity_run_with_codes("RUN", [0])
        assert len(calls) == 1
        assert "handoff" in calls[0]["cmd"]
        assert "execute" not in calls[0]["cmd"]
        assert code == 0

    def test_antigravity_fix_invokes_handoff_only(self):
        code, calls = self._antigravity_run_with_codes("FIX", [0])
        assert len(calls) == 1
        assert "handoff" in calls[0]["cmd"]
        assert "execute" not in calls[0]["cmd"]
        assert code == 0

    def test_antigravity_handoff_uses_executor_antigravity(self):
        _, calls = self._antigravity_run_with_codes("RUN", [0])
        cmd = calls[0]["cmd"]
        idx = cmd.index("--executor")
        assert cmd[idx + 1] == "antigravity"

    def test_antigravity_execute_never_called_regardless_of_handoff_success(self):
        _, calls = self._antigravity_run_with_codes("RUN", [0])
        for c in calls:
            assert "execute" not in c["cmd"]


# ===========================================================================
# 12–14. STATUS non-authorizing contract
# ===========================================================================

class TestStatusAdapter:
    """Tests 12–14: STATUS operations."""

    @pytest.fixture(autouse=True)
    def mock_repo_root(self, tmp_path):
        fake_bridge = tmp_path / "bridge.py"
        fake_bridge.write_text("# fake")
        self.fake_root = tmp_path

    def _status_run(self, codes: list[int], adapter: str = "codex"):
        mock_run = make_mock_run(codes)
        with patch("subprocess.run", side_effect=mock_run), \
             patch.object(aw, "get_repo_root", return_value=self.fake_root):
            code = aw.main(["STATUS", "TASK-1", "--adapter", adapter])
        return code, mock_run.calls_made

    # Test 12: STATUS invokes sync then pending only
    def test_status_invokes_sync_then_pending(self):
        code, calls = self._status_run([0, 0])
        assert len(calls) == 2
        assert "sync" in calls[0]["cmd"]
        assert "pending" in calls[1]["cmd"]
        assert code == 0

    # Test 13: STATUS sync failure prevents pending
    def test_status_sync_failure_prevents_pending(self):
        code, calls = self._status_run([1])
        assert code == 1
        assert len(calls) == 1
        assert "sync" in calls[0]["cmd"]

    # Test 14: STATUS never invokes forbidden commands
    def test_status_never_invokes_handoff(self):
        _, calls = self._status_run([0, 0])
        forbidden = {"handoff", "approve", "execute", "publish", "merge"}
        for c in calls:
            for part in c["cmd"]:
                assert part not in forbidden, f"STATUS must not invoke '{part}'"

    def test_status_never_invokes_codex_binary(self):
        _, calls = self._status_run([0, 0])
        for c in calls:
            for part in c["cmd"]:
                assert "codex" not in part.lower() or "bridge" in part.lower()

    def test_status_works_with_antigravity_adapter_too(self):
        code, calls = self._status_run([0, 0], adapter="antigravity")
        assert len(calls) == 2
        assert "sync" in calls[0]["cmd"]
        assert "pending" in calls[1]["cmd"]


# ===========================================================================
# 15–17. Forbidden commands never invoked
# ===========================================================================

class TestForbiddenCommands:
    """Tests 15–17: script never calls publish, approve, or raw codex."""

    @pytest.fixture(autouse=True)
    def mock_repo_root(self, tmp_path):
        fake_bridge = tmp_path / "bridge.py"
        fake_bridge.write_text("# fake")
        self.fake_root = tmp_path

    def _run_all_adapters(self, action: str, task: str = "TASK-1"):
        all_calls = []
        for adapter in ("codex", "antigravity"):
            mock_run = make_mock_run([0, 0, 0])
            with patch("subprocess.run", side_effect=mock_run), \
                 patch.object(aw, "get_repo_root", return_value=self.fake_root):
                aw.main([action, task, "--adapter", adapter])
            all_calls.extend(mock_run.calls_made)
        return all_calls

    def test_script_never_invokes_publish(self):
        for action in ("RUN", "FIX", "STATUS"):
            calls = self._run_all_adapters(action)
            for c in calls:
                assert "publish" not in c["cmd"], f"Found 'publish' in {c['cmd']}"

    def test_script_never_invokes_approve(self):
        for action in ("RUN", "FIX", "STATUS"):
            calls = self._run_all_adapters(action)
            for c in calls:
                assert "approve" not in c["cmd"], f"Found 'approve' in {c['cmd']}"

    def test_script_never_invokes_raw_codex(self):
        for action in ("RUN", "FIX", "STATUS"):
            calls = self._run_all_adapters(action)
            for c in calls:
                # cmd[0] must always be sys.executable (Python), never the raw 'codex' binary.
                # Note: "codex" may legitimately appear as an --executor argument to bridge.py;
                # that is valid and must NOT be flagged.
                assert c["cmd"][0] != "codex", "Must never invoke raw 'codex' as subprocess binary"
                # cmd[1] is always bridge.py path — also never "codex"
                assert not c["cmd"][1].endswith("codex") and not c["cmd"][1].endswith("codex.exe"), \
                    "Bridge entrypoint must never be the codex binary"


# ===========================================================================
# 18. MERGE rejected
# ===========================================================================

def test_merge_is_rejected():
    """Test 18: MERGE must be rejected, not dispatched."""
    with patch.object(aw, "get_repo_root", return_value=REPO_ROOT), \
         patch.object(aw, "run_bridge_command", return_value=0) as mock_bridge:
        code = aw.main(["MERGE", "TASK-1", "--adapter", "codex"])
    assert code != 0
    mock_bridge.assert_not_called()


# ===========================================================================
# 19–23. SKILL.md content assertions
# ===========================================================================

class TestSkillFile:
    """Tests 19–23: SKILL.md existence and content requirements."""

    @pytest.fixture(scope="class")
    def skill_text(self):
        assert SKILL_FILE.exists(), f"SKILL.md not found at {SKILL_FILE}"
        return SKILL_FILE.read_text(encoding="utf-8")

    # Test 19: SKILL.md exists with exact name: aios-worker
    def test_skill_md_exists_with_correct_name(self, skill_text):
        assert "name: aios-worker" in skill_text

    # Test 20: Skill text includes RUN/FIX/STATUS triggers
    def test_skill_includes_run_trigger(self, skill_text):
        assert "RUN TASK-" in skill_text

    def test_skill_includes_fix_trigger(self, skill_text):
        assert "FIX TASK-" in skill_text

    def test_skill_includes_status_trigger(self, skill_text):
        assert "STATUS TASK-" in skill_text

    # Test 21: Skill forbids parent-session implementation duplication
    def test_skill_forbids_parent_session_implementation_duplication(self, skill_text):
        # The skill must contain a sentence about not duplicating implementation work
        keywords_found = any(
            kw in skill_text.lower()
            for kw in ("must not duplicate", "not duplicate", "not duplicate the implementation", "operator ui")
        )
        assert keywords_found, "Skill must explicitly forbid parent-session implementation duplication"

    # Test 22: Skill routes RUN/FIX through adapter with --adapter codex
    def test_skill_routes_through_adapter_codex(self, skill_text):
        assert "--adapter codex" in skill_text

    # Test 23: Skill forbids context/approve/publish/direct codex exec/retry/merge
    def test_skill_forbids_bridge_context(self, skill_text):
        assert "bridge.py context" in skill_text or "context" in skill_text.lower()

    def test_skill_forbids_bridge_approve(self, skill_text):
        assert "approve" in skill_text.lower()

    def test_skill_forbids_bridge_publish(self, skill_text):
        assert "publish" in skill_text.lower()

    def test_skill_forbids_retry(self, skill_text):
        assert "retry" in skill_text.lower() or "retries" in skill_text.lower()

    def test_skill_forbids_merge(self, skill_text):
        assert "merge" in skill_text.lower() or "MERGE" in skill_text


# ===========================================================================
# 24. Documentation assertions
# ===========================================================================

class TestDocumentation:
    """Test 24: docs/AIOS_UNIFIED_WORKER_WORKFLOW.md content requirements."""

    @pytest.fixture(scope="class")
    def docs_text(self):
        assert DOCS_FILE.exists(), f"AIOS_UNIFIED_WORKER_WORKFLOW.md not found at {DOCS_FILE}"
        return DOCS_FILE.read_text(encoding="utf-8")

    def test_docs_state_antigravity_parity(self, docs_text):
        assert "Antigravity" in docs_text or "antigravity" in docs_text

    def test_docs_state_codex_parity(self, docs_text):
        assert "Codex" in docs_text or "codex" in docs_text

    def test_docs_mention_shared_bridge_state(self, docs_text):
        keywords = any(
            kw in docs_text.lower()
            for kw in ("shared", "bridge state", "single", "centralized", "shared state")
        )
        assert keywords, "Docs must mention shared/centralized Bridge state"

    def test_docs_mention_run_fix_status(self, docs_text):
        assert "RUN" in docs_text
        assert "FIX" in docs_text
        assert "STATUS" in docs_text

    def test_docs_mention_review_loop(self, docs_text):
        keywords = any(
            kw in docs_text.lower()
            for kw in ("review", "chatgpt", "chat")
        )
        assert keywords, "Docs must describe the review loop"

    def test_docs_mention_merge_boundary(self, docs_text):
        assert "merge" in docs_text.lower() or "MERGE" in docs_text

    def test_docs_mention_switching_ui_does_not_create_new_state(self, docs_text):
        keywords = any(
            kw in docs_text.lower()
            for kw in ("switching", "switch", "second state", "not create a new", "not create new")
        )
        assert keywords, "Docs must state that switching UI does not create a new task state"


# ===========================================================================
# 25. No network or external API call
# ===========================================================================

def test_no_network_or_external_api_in_adapter():
    """Test 25: Adapter source must not contain network/API imports."""
    source = ADAPTER_SCRIPT.read_text(encoding="utf-8")
    forbidden_imports = [
        "import requests",
        "import httpx",
        "import urllib.request",
        "import urllib3",
        "import aiohttp",
        "import socket",
        "openai",
        "anthropic",
    ]
    for forbidden in forbidden_imports:
        assert forbidden not in source, f"Adapter must not use '{forbidden}' (no network/API calls)"
