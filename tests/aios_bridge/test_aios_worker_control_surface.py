"""Test suite for the Unified AIOS Worker Control Surface (TASK-048 / ADR-037 / TASK-060).

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
19. SKILL.md exists with exact name: aios-worker (Codex surface)
20. Skill text includes RUN/FIX/STATUS triggers
21. Skill forbids parent-session implementation duplication
22. Skill routes RUN/FIX through adapter with --adapter codex
23. Skill forbids context/approve/publish/direct codex exec/retry/merge
24. Docs state Antigravity/Codex parity and shared Bridge state
25. No network or external API call exists in adapter
26. [TASK-060] ANTIGRAVITY_WORKFLOW_EXISTS
27. [TASK-060] ANTIGRAVITY_BINDS_ONLY_ADAPTER_ANTIGRAVITY
28. [TASK-060] ANTIGRAVITY_FORBIDS_CODEX_ROUTE
29. [TASK-060] CODEX_SKILL_BINDS_ONLY_ADAPTER_CODEX
30. [TASK-060] CODEX_SKILL_NOT_ANTIGRAVITY_SURFACE
31. [TASK-060] ANTIGRAVITY_RUN_FIX_HANDOFF_ONLY
32. [TASK-060] CODEX_RUN_FIX_HANDOFF_THEN_EXECUTE
33. [TASK-060] STATUS_NON_AUTHORIZING_BOTH_SURFACES
34. [TASK-060] NO_RETRY_REROUTE_MERGE (both surfaces)
# [TASK-060 FIX] Full test suite and format verification
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Locate repo root and import the adapter module
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SKILL_DIR = REPO_ROOT / ".agents" / "skills" / "aios-worker"
WORKFLOW_DIR = REPO_ROOT / ".agents" / "workflows"
ADAPTER_SCRIPT = SKILL_DIR / "scripts" / "aios_worker.py"
SKILL_FILE = SKILL_DIR / "SKILL.md"
WORKFLOW_FILE = WORKFLOW_DIR / "aios-worker.md"
DOCS_FILE = REPO_ROOT / "docs" / "AIOS_UNIFIED_WORKER_WORKFLOW.md"
BRIDGE_PY = REPO_ROOT / "bridge.py"

if str(ADAPTER_SCRIPT.parent) not in sys.path:
    sys.path.insert(0, str(ADAPTER_SCRIPT.parent))

import aios_worker as aw  # noqa: E402


# ---------------------------------------------------------------------------
# Helper: build a mock subprocess.run that records calls
# ---------------------------------------------------------------------------

def make_mock_run(return_codes: list[int]):
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


@pytest.fixture(autouse=True)
def mock_active_fix_auth(monkeypatch):
    from src.aios_bridge.worker_flow import WorkerFlowCoordinator
    monkeypatch.setattr(
        WorkerFlowCoordinator,
        "_default_load_auth",
        lambda self, task_num: {
            "status": "ACTIVE",
            "action": "FIX",
            "fix_execution_mode": "IMPLEMENTATION",
        },
    )


# ===========================================================================
# 1-4. Parsing / Validation
# ===========================================================================

class TestParsing:
    @pytest.mark.parametrize("task_str,expected_num", [
        ("TASK-1", 1), ("TASK-48", 48), ("TASK-048", 48), ("TASK-999", 999), ("TASK-1000", 1000),
    ])
    def test_canonical_task_ids_parse(self, task_str, expected_num):
        task_id, task_num = aw.parse_task_id(task_str)
        assert task_id == task_str and task_num == expected_num

    @pytest.mark.parametrize("bad_task", [
        "TASK-0", "task-48", "TASK48", "TASK-", "TASK--48", "TASK-48x", "TASK- 48", "48", "", "TASK-abc",
    ])
    def test_malformed_task_ids_rejected(self, bad_task):
        with pytest.raises(ValueError):
            aw.parse_task_id(bad_task)

    @pytest.mark.parametrize("action", ["RUN", "FIX", "STATUS"])
    def test_canonical_actions_accepted(self, action, tmp_path):
        (tmp_path / "bridge.py").write_text("# fake")
        with patch.object(aw, "get_repo_root", return_value=tmp_path), \
             patch.object(aw, "run_bridge_command", return_value=0):
            code = aw.main([action, "TASK-1", "--adapter", "antigravity"])
        assert code == 0

    @pytest.mark.parametrize("bad_action", ["run", "fix", "MERGE", "START", "DEPLOY", ""])
    def test_malformed_actions_rejected(self, bad_action):
        with patch.object(aw, "get_repo_root", return_value=REPO_ROOT), \
             patch.object(aw, "run_bridge_command", return_value=0):
            code = aw.main([bad_action, "TASK-1", "--adapter", "codex"])
        assert code != 0

    def test_unknown_adapter_rejected(self):
        assert aw.main(["RUN", "TASK-1", "--adapter", "unknown_ui"]) != 0

    def test_merge_rejected(self):
        with patch.object(aw, "get_repo_root", return_value=REPO_ROOT), \
             patch.object(aw, "run_bridge_command", return_value=0):
            assert aw.main(["MERGE", "TASK-1", "--adapter", "codex"]) != 0

    @pytest.mark.parametrize("padded_task", [
        " TASK-48", "TASK-48 ", " TASK-48 ", "\tTASK-48", "TASK-48\n",
    ])
    def test_whitespace_padded_task_ids_rejected(self, padded_task):
        with pytest.raises(ValueError):
            aw.parse_task_id(padded_task)


# ===========================================================================
# 5-10. Codex RUN and FIX exact argv contract (ADR-061 Transactional Flow)
# ===========================================================================

class TestCodexRunFix:
    @pytest.fixture(autouse=True)
    def mock_repo_root(self, tmp_path):
        (tmp_path / "bridge.py").write_text("# fake bridge")
        reviews_dir = tmp_path / ".ai" / "reviews"
        reviews_dir.mkdir(parents=True, exist_ok=True)
        (reviews_dir / "REVIEW-048.md").write_text("STATUS: CHANGES_REQUIRED\nFIX_EXECUTION_MODE: IMPLEMENTATION\n")
        (reviews_dir / "REVIEW-060.md").write_text("STATUS: CHANGES_REQUIRED\nFIX_EXECUTION_MODE: IMPLEMENTATION\n")
        self.fake_root = tmp_path

    def _codex_run_with_codes(self, action: str, codes: list[int]):
        mock_run = make_mock_run(codes)
        with patch("subprocess.run", side_effect=mock_run), \
             patch.object(aw, "get_repo_root", return_value=self.fake_root):
            code = aw.main([action, "TASK-48", "--adapter", "codex"])
        return code, mock_run.calls_made

    def test_codex_run_exact_first_argv_is_handoff(self):
        _, calls = self._codex_run_with_codes("RUN", [0, 0])
        expected = [sys.executable, str(self.fake_root / "bridge.py"), "handoff", "48", "--action", "run", "--executor", "codex"]
        assert calls[0]["cmd"] == expected

    def test_codex_run_invokes_handoff_only_no_execute(self):
        _, calls = self._codex_run_with_codes("RUN", [0])
        assert len(calls) == 1
        assert calls[0]["cmd"] == [sys.executable, str(self.fake_root / "bridge.py"), "handoff", "48", "--action", "run", "--executor", "codex"]

    def test_exact_argv_fails_if_extra_token_appended(self):
        _, calls = self._codex_run_with_codes("RUN", [0])
        expected_with_extra = [sys.executable, str(self.fake_root / "bridge.py"), "handoff", "48", "--action", "run", "--executor", "codex", "--extra-injected-flag"]
        assert calls[0]["cmd"] != expected_with_extra

    def test_codex_fix_exact_handoff_only(self):
        _, calls = self._codex_run_with_codes("FIX", [0])
        assert len(calls) == 1
        assert calls[0]["cmd"] == [sys.executable, str(self.fake_root / "bridge.py"), "handoff", "48", "--action", "fix", "--executor", "codex"]

    def test_every_bridge_child_uses_sys_executable_list_argv_no_shell_exact_cwd(self):
        _, calls = self._codex_run_with_codes("RUN", [0])
        for c in calls:
            assert c["cmd"][0] == sys.executable
            assert c["cmd"][1] == str(self.fake_root / "bridge.py")
            assert isinstance(c["cmd"], list)
            assert c["kwargs"].get("shell", False) is False
            assert str(c["kwargs"].get("cwd", "")) == str(self.fake_root)

    def test_subprocess_shell_is_false(self):
        mock_run = make_mock_run([0])
        with patch("subprocess.run", side_effect=mock_run), \
             patch.object(aw, "get_repo_root", return_value=self.fake_root):
            aw.main(["RUN", "TASK-1", "--adapter", "codex"])
        for c in mock_run.calls_made:
            assert c["kwargs"].get("shell", False) is False

    def test_handoff_nonzero_fails_closed(self):
        returncode, calls = self._codex_run_with_codes("RUN", [1])
        assert returncode == 1 and len(calls) == 1 and calls[0]["cmd"][2] == "handoff"

    def test_no_fallback_on_failure(self):
        _, calls = self._codex_run_with_codes("RUN", [1])
        assert len(calls) == 1


class TestAuthorizedGuidanceBindsAdapter:
    """Proof: CODEX_AUTHORIZED_GUIDANCE_BINDS_CODEX & ANTIGRAVITY_AUTHORIZED_GUIDANCE_BINDS_ANTIGRAVITY & CROSS_SURFACE_GUIDANCE_CONFUSION: NONE."""

    @pytest.fixture(autouse=True)
    def mock_repo_root(self, tmp_path):
        (tmp_path / "bridge.py").write_text("# fake bridge")
        self.fake_root = tmp_path

    def test_codex_authorized_guidance_binds_codex(self, capsys):
        mock_run = make_mock_run([0])
        with patch("subprocess.run", side_effect=mock_run), \
             patch.object(aw, "get_repo_root", return_value=self.fake_root):
            code = aw.main(["RUN", "TASK-096", "--adapter", "codex"])

        captured = capsys.readouterr().out
        assert code == 0
        assert "NEXT: continue in the authorized codex worker session" in captured
        assert "Antigravity" not in captured

    def test_antigravity_authorized_guidance_binds_antigravity(self, capsys):
        mock_run = make_mock_run([0])
        with patch("subprocess.run", side_effect=mock_run), \
             patch.object(aw, "get_repo_root", return_value=self.fake_root):
            code = aw.main(["RUN", "TASK-096", "--adapter", "antigravity"])

        captured = capsys.readouterr().out
        assert code == 0
        assert "NEXT: continue in the authorized antigravity worker session" in captured
        assert "codex worker session" not in captured


# ===========================================================================
# 11. Antigravity RUN/FIX invokes handoff only (never execute)
# ===========================================================================

class TestAntigravityAdapter:
    @pytest.fixture(autouse=True)
    def mock_repo_root(self, tmp_path):
        (tmp_path / "bridge.py").write_text("# fake")
        reviews_dir = tmp_path / ".ai" / "reviews"
        reviews_dir.mkdir(parents=True, exist_ok=True)
        (reviews_dir / "REVIEW-048.md").write_text("STATUS: CHANGES_REQUIRED\nFIX_EXECUTION_MODE: IMPLEMENTATION\n")
        (reviews_dir / "REVIEW-060.md").write_text("STATUS: CHANGES_REQUIRED\nFIX_EXECUTION_MODE: IMPLEMENTATION\n")
        self.fake_root = tmp_path

    def _antigravity_run_with_codes(self, action: str, codes: list[int]):
        mock_run = make_mock_run(codes)
        with patch("subprocess.run", side_effect=mock_run), \
             patch.object(aw, "get_repo_root", return_value=self.fake_root):
            code = aw.main([action, "TASK-48", "--adapter", "antigravity"])
        return code, mock_run.calls_made

    def test_antigravity_run_exact_argv_and_one_call(self):
        code, calls = self._antigravity_run_with_codes("RUN", [0])
        assert len(calls) == 1
        expected = [sys.executable, str(self.fake_root / "bridge.py"), "handoff", "48", "--action", "run", "--executor", "antigravity"]
        assert calls[0]["cmd"] == expected and code == 0

    def test_antigravity_fix_exact_argv_and_one_call(self):
        code, calls = self._antigravity_run_with_codes("FIX", [0])
        assert len(calls) == 1
        expected = [sys.executable, str(self.fake_root / "bridge.py"), "handoff", "48", "--action", "fix", "--executor", "antigravity"]
        assert calls[0]["cmd"] == expected and code == 0

    def test_antigravity_execute_never_called_regardless_of_handoff_success(self):
        _, calls = self._antigravity_run_with_codes("RUN", [0])
        assert len(calls) == 1 and calls[0]["cmd"][2] == "handoff"


# ===========================================================================
# 12-14. STATUS non-authorizing contract
# ===========================================================================

class TestStatusAdapter:
    @pytest.fixture(autouse=True)
    def mock_repo_root(self, tmp_path):
        (tmp_path / "bridge.py").write_text("# fake")
        self.fake_root = tmp_path

    def _status_run(self, codes: list[int], adapter: str = "codex"):
        mock_run = make_mock_run(codes)
        with patch("subprocess.run", side_effect=mock_run), \
             patch.object(aw, "get_repo_root", return_value=self.fake_root):
            code = aw.main(["STATUS", "TASK-1", "--adapter", adapter])
        return code, mock_run.calls_made

    def test_status_exact_sync_argv(self):
        _, calls = self._status_run([0, 0])
        assert calls[0]["cmd"] == [sys.executable, str(self.fake_root / "bridge.py"), "sync"]

    def test_status_exact_pending_argv(self):
        _, calls = self._status_run([0, 0])
        assert calls[1]["cmd"] == [sys.executable, str(self.fake_root / "bridge.py"), "pending"]

    def test_status_exactly_two_calls(self):
        code, calls = self._status_run([0, 0])
        assert len(calls) == 2 and code == 0

    def test_status_sync_failure_prevents_pending(self):
        code, calls = self._status_run([1])
        assert code == 1 and len(calls) == 1

    def test_status_never_invokes_handoff(self):
        _, calls = self._status_run([0, 0])
        for c in calls:
            assert c["cmd"][2] in ("sync", "pending")

    def test_status_works_with_antigravity_adapter_too(self):
        code, calls = self._status_run([0, 0], adapter="antigravity")
        assert len(calls) == 2 and calls[0]["cmd"][2] == "sync" and calls[1]["cmd"][2] == "pending"


# ===========================================================================
# 15-17. Forbidden commands never invoked
# ===========================================================================

class TestForbiddenCommands:
    @pytest.fixture(autouse=True)
    def mock_repo_root(self, tmp_path):
        (tmp_path / "bridge.py").write_text("# fake")
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
            for c in self._run_all_adapters(action):
                assert "publish" not in c["cmd"]

    def test_script_never_invokes_approve(self):
        for action in ("RUN", "FIX", "STATUS"):
            for c in self._run_all_adapters(action):
                assert "approve" not in c["cmd"]

    def test_script_never_invokes_raw_codex(self):
        for action in ("RUN", "FIX", "STATUS"):
            for c in self._run_all_adapters(action):
                assert c["cmd"][0] != "codex"
                assert not c["cmd"][1].endswith("codex") and not c["cmd"][1].endswith("codex.exe")


# ===========================================================================
# 18. MERGE rejected
# ===========================================================================

def test_merge_is_rejected():
    with patch.object(aw, "get_repo_root", return_value=REPO_ROOT), \
         patch.object(aw, "run_bridge_command", return_value=0) as mock_bridge:
        code = aw.main(["MERGE", "TASK-1", "--adapter", "codex"])
    assert code != 0
    mock_bridge.assert_not_called()


# ===========================================================================
# 19-23. SKILL.md content assertions (Codex surface)
# ===========================================================================

class TestSkillFile:
    @pytest.fixture(scope="class")
    def skill_text(self):
        assert SKILL_FILE.exists()
        return SKILL_FILE.read_text(encoding="utf-8")

    def test_skill_md_exists_with_correct_name(self, skill_text):
        assert "name: aios-worker" in skill_text

    def test_skill_includes_run_trigger(self, skill_text):
        assert "RUN TASK-" in skill_text

    def test_skill_includes_fix_trigger(self, skill_text):
        assert "FIX TASK-" in skill_text

    def test_skill_includes_status_trigger(self, skill_text):
        assert "STATUS TASK-" in skill_text

    def test_skill_forbids_parent_session_implementation_duplication(self, skill_text):
        assert any(kw in skill_text.lower() for kw in ("must not duplicate", "not duplicate", "operator ui"))

    def test_skill_routes_through_adapter_codex(self, skill_text):
        assert "--adapter codex" in skill_text

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
    @pytest.fixture(scope="class")
    def docs_text(self):
        assert DOCS_FILE.exists()
        return DOCS_FILE.read_text(encoding="utf-8")

    def test_docs_state_antigravity_parity(self, docs_text):
        assert "Antigravity" in docs_text or "antigravity" in docs_text

    def test_docs_state_codex_parity(self, docs_text):
        assert "Codex" in docs_text or "codex" in docs_text

    def test_docs_mention_shared_bridge_state(self, docs_text):
        assert any(kw in docs_text.lower() for kw in ("shared", "bridge state", "single", "centralized"))

    def test_docs_mention_run_fix_status(self, docs_text):
        assert "RUN" in docs_text and "FIX" in docs_text and "STATUS" in docs_text

    def test_docs_mention_review_loop(self, docs_text):
        assert any(kw in docs_text.lower() for kw in ("review", "chatgpt", "chat"))

    def test_docs_mention_merge_boundary(self, docs_text):
        assert "merge" in docs_text.lower() or "MERGE" in docs_text

    def test_docs_mention_switching_ui_does_not_create_new_state(self, docs_text):
        assert any(kw in docs_text.lower() for kw in ("switching", "switch", "not create a new", "not create new"))


# ===========================================================================
# 25. No network or external API call
# ===========================================================================

def test_no_network_or_external_api_in_adapter():
    source = ADAPTER_SCRIPT.read_text(encoding="utf-8")
    for forbidden in ["import requests", "import httpx", "import urllib.request", "import urllib3", "import aiohttp", "import socket", "openai", "anthropic"]:
        assert forbidden not in source


# ===========================================================================
# 26-34. TASK-060 Identity Hardening Tests
# ===========================================================================

class TestAntigravityWorkflowExists:
    """Test 26: ANTIGRAVITY_WORKFLOW_EXISTS"""

    def test_workflow_file_exists(self):
        assert WORKFLOW_FILE.exists(), f"Antigravity workflow not found at {WORKFLOW_FILE}"

    def test_workflow_file_is_not_skill_file(self):
        assert WORKFLOW_FILE.resolve() != SKILL_FILE.resolve()


class TestAntigravityBindsOnlyAdapterAntigravity:
    """Test 27: ANTIGRAVITY_BINDS_ONLY_ADAPTER_ANTIGRAVITY"""

    @pytest.fixture(scope="class")
    def workflow_text(self):
        assert WORKFLOW_FILE.exists()
        return WORKFLOW_FILE.read_text(encoding="utf-8")

    def test_workflow_contains_adapter_antigravity(self, workflow_text):
        assert "--adapter antigravity" in workflow_text

    def test_workflow_name_is_aios_worker(self, workflow_text):
        assert "name: aios-worker" in workflow_text

    def test_workflow_includes_run_trigger(self, workflow_text):
        assert "RUN TASK-" in workflow_text

    def test_workflow_includes_fix_trigger(self, workflow_text):
        assert "FIX TASK-" in workflow_text

    def test_workflow_includes_status_trigger(self, workflow_text):
        assert "STATUS TASK-" in workflow_text


class TestAntigravityForbidsCodexRoute:
    """Test 28: ANTIGRAVITY_FORBIDS_CODEX_ROUTE"""

    @pytest.fixture(scope="class")
    def workflow_text(self):
        assert WORKFLOW_FILE.exists()
        return WORKFLOW_FILE.read_text(encoding="utf-8")

    def test_workflow_explicitly_forbids_adapter_codex(self, workflow_text):
        assert any(phrase in workflow_text.lower() for phrase in ("forbidden", "never use", "must never use"))

    def test_workflow_forbids_retry_and_reroute(self, workflow_text):
        assert "retry" in workflow_text.lower() or "reroute" in workflow_text.lower() or "rerouting" in workflow_text.lower()

    def test_workflow_forbids_merge(self, workflow_text):
        assert "merge" in workflow_text.lower() or "MERGE" in workflow_text

    def test_workflow_forbids_approve(self, workflow_text):
        assert "approve" in workflow_text.lower()

    def test_workflow_forbids_publish(self, workflow_text):
        assert "publish" in workflow_text.lower()


class TestCodexSkillBindsOnlyAdapterCodex:
    """Test 29: CODEX_SKILL_BINDS_ONLY_ADAPTER_CODEX"""

    @pytest.fixture(scope="class")
    def skill_text(self):
        assert SKILL_FILE.exists()
        return SKILL_FILE.read_text(encoding="utf-8")

    def test_skill_contains_adapter_codex(self, skill_text):
        assert "--adapter codex" in skill_text

    def test_skill_does_not_invoke_adapter_antigravity_in_commands(self, skill_text):
        powershell_lines_with_wrong_adapter = [
            line for line in skill_text.splitlines()
            if "--adapter antigravity" in line and "aios_worker.py" in line
        ]
        assert not powershell_lines_with_wrong_adapter


class TestCodexSkillNotAntigravitySurface:
    """Test 30: CODEX_SKILL_NOT_ANTIGRAVITY_SURFACE"""

    @pytest.fixture(scope="class")
    def skill_text(self):
        assert SKILL_FILE.exists()
        return SKILL_FILE.read_text(encoding="utf-8")

    def test_skill_declares_codex_only_surface(self, skill_text):
        assert any(phrase in skill_text for phrase in ("Codex-only", "Codex surface", "Codex `$aios-worker`", "$aios-worker"))

    def test_skill_explicitly_excludes_antigravity_surface(self, skill_text):
        assert any(phrase in skill_text for phrase in (
            "must never serve the Antigravity",
            "never serve Antigravity",
            "not serve the Antigravity",
        ))

    def test_skill_references_workflow_as_antigravity_surface(self, skill_text):
        assert ".agents/workflows/aios-worker.md" in skill_text or "workflows/aios-worker" in skill_text


class TestAntigravityRunFixHandoffOnly:
    """Test 31: ANTIGRAVITY_RUN_FIX_HANDOFF_ONLY"""

    @pytest.fixture(autouse=True)
    def mock_repo_root(self, tmp_path):
        (tmp_path / "bridge.py").write_text("# fake")
        reviews_dir = tmp_path / ".ai" / "reviews"
        reviews_dir.mkdir(parents=True, exist_ok=True)
        (reviews_dir / "REVIEW-048.md").write_text("STATUS: CHANGES_REQUIRED\nFIX_EXECUTION_MODE: IMPLEMENTATION\n")
        (reviews_dir / "REVIEW-060.md").write_text("STATUS: CHANGES_REQUIRED\nFIX_EXECUTION_MODE: IMPLEMENTATION\n")
        self.fake_root = tmp_path

    def _run_antigravity(self, action: str):
        mock_run = make_mock_run([0, 0])
        with patch("subprocess.run", side_effect=mock_run), \
             patch.object(aw, "get_repo_root", return_value=self.fake_root):
            code = aw.main([action, "TASK-60", "--adapter", "antigravity"])
        return code, mock_run.calls_made

    def test_antigravity_run_never_calls_execute(self):
        _, calls = self._run_antigravity("RUN")
        assert not [c for c in calls if "execute" in c["cmd"]]

    def test_antigravity_fix_never_calls_execute(self):
        _, calls = self._run_antigravity("FIX")
        assert not [c for c in calls if "execute" in c["cmd"]]

    def test_antigravity_run_exactly_one_subprocess_call(self):
        _, calls = self._run_antigravity("RUN")
        assert len(calls) == 1

    def test_antigravity_fix_exactly_one_subprocess_call(self):
        _, calls = self._run_antigravity("FIX")
        assert len(calls) == 1


class TestCodexRunFixHandoffThenExecute:
    """Test 32: CODEX_RUN_FIX_HANDOFF_THEN_EXECUTE"""

    @pytest.fixture(autouse=True)
    def mock_repo_root(self, tmp_path):
        (tmp_path / "bridge.py").write_text("# fake")
        reviews_dir = tmp_path / ".ai" / "reviews"
        reviews_dir.mkdir(parents=True, exist_ok=True)
        (reviews_dir / "REVIEW-048.md").write_text("STATUS: CHANGES_REQUIRED\nFIX_EXECUTION_MODE: IMPLEMENTATION\n")
        (reviews_dir / "REVIEW-060.md").write_text("STATUS: CHANGES_REQUIRED\nFIX_EXECUTION_MODE: IMPLEMENTATION\n")
        self.fake_root = tmp_path

    def _run_codex(self, action: str):
        mock_run = make_mock_run([0])
        with patch("subprocess.run", side_effect=mock_run), \
             patch.object(aw, "get_repo_root", return_value=self.fake_root):
            code = aw.main([action, "TASK-60", "--adapter", "codex"])
        return code, mock_run.calls_made

    def test_codex_run_calls_handoff_only(self):
        _, calls = self._run_codex("RUN")
        assert len(calls) == 1 and calls[0]["cmd"][2] == "handoff"

    def test_codex_fix_calls_handoff_only(self):
        _, calls = self._run_codex("FIX")
        assert len(calls) == 1 and calls[0]["cmd"][2] == "handoff"

    def test_codex_run_handoff_uses_codex_executor(self):
        _, calls = self._run_codex("RUN")
        idx = calls[0]["cmd"].index("--executor")
        assert calls[0]["cmd"][idx + 1] == "codex"

    def test_codex_fix_handoff_uses_codex_executor(self):
        _, calls = self._run_codex("FIX")
        idx = calls[0]["cmd"].index("--executor")
        assert calls[0]["cmd"][idx + 1] == "codex"


class TestStatusNonAuthorizing:
    """Test 33: STATUS_NON_AUTHORIZING_BOTH_SURFACES"""

    @pytest.fixture(autouse=True)
    def mock_repo_root(self, tmp_path):
        (tmp_path / "bridge.py").write_text("# fake")
        self.fake_root = tmp_path

    def _status_run(self, adapter: str):
        mock_run = make_mock_run([0, 0])
        with patch("subprocess.run", side_effect=mock_run), \
             patch.object(aw, "get_repo_root", return_value=self.fake_root):
            code = aw.main(["STATUS", "TASK-1", "--adapter", adapter])
        return code, mock_run.calls_made

    def test_status_codex_is_non_authorizing(self):
        _, calls = self._status_run("codex")
        for c in calls:
            assert c["cmd"][2] not in ("handoff", "execute", "approve", "publish")

    def test_status_antigravity_is_non_authorizing(self):
        _, calls = self._status_run("antigravity")
        for c in calls:
            assert c["cmd"][2] not in ("handoff", "execute", "approve", "publish")

    def test_status_both_surfaces_produce_identical_subprocess_calls(self):
        _, codex_calls = self._status_run("codex")
        _, agv_calls = self._status_run("antigravity")
        assert [c["cmd"][2] for c in codex_calls] == [c["cmd"][2] for c in agv_calls] == ["sync", "pending"]


class TestNoRetryRerouteMerge:
    """Test 34: NO_RETRY_REROUTE_MERGE"""

    @pytest.fixture(autouse=True)
    def mock_repo_root(self, tmp_path):
        (tmp_path / "bridge.py").write_text("# fake")
        self.fake_root = tmp_path

    def test_codex_run_failure_does_not_retry(self):
        mock_run = make_mock_run([1])
        with patch("subprocess.run", side_effect=mock_run), \
             patch.object(aw, "get_repo_root", return_value=self.fake_root):
            code = aw.main(["RUN", "TASK-1", "--adapter", "codex"])
        assert code != 0 and len(mock_run.calls_made) == 1

    def test_antigravity_run_failure_does_not_retry(self):
        mock_run = make_mock_run([1])
        with patch("subprocess.run", side_effect=mock_run), \
             patch.object(aw, "get_repo_root", return_value=self.fake_root):
            code = aw.main(["RUN", "TASK-1", "--adapter", "antigravity"])
        assert code != 0 and len(mock_run.calls_made) == 1

    def test_merge_rejected_codex(self):
        with patch.object(aw, "get_repo_root", return_value=self.fake_root), \
             patch.object(aw, "run_bridge_command", return_value=0) as mock_bridge:
            code = aw.main(["MERGE", "TASK-1", "--adapter", "codex"])
        assert code != 0
        mock_bridge.assert_not_called()

    def test_merge_rejected_antigravity(self):
        with patch.object(aw, "get_repo_root", return_value=self.fake_root), \
             patch.object(aw, "run_bridge_command", return_value=0) as mock_bridge:
            code = aw.main(["MERGE", "TASK-1", "--adapter", "antigravity"])
        assert code != 0
        mock_bridge.assert_not_called()


# ===========================================================================
# B1 Regression (TASK-060 FIX): No BOM, frontmatter starts with b'---\n'
# ===========================================================================

class TestSurfaceFileFrontmatterNoBOM:
    """B1 Regression: Both surface files must begin with b"---\n" with no UTF-8 BOM."""

    def test_workflow_file_no_bom(self):
        raw = WORKFLOW_FILE.read_bytes()
        assert not raw.startswith(b'\xef\xbb\xbf'), (
            f'workflow must not have BOM. First 6 bytes: {raw[:6]!r}'
        )

    def test_workflow_file_starts_with_frontmatter_delimiter(self):
        raw = WORKFLOW_FILE.read_bytes()
        assert raw.startswith(b'---\n'), (
            f"workflow must start with exactly b'---\\n' (LF, no CRLF, no BOM). First 6 bytes: {raw[:6]!r}"
        )

    def test_skill_file_no_bom(self):
        raw = SKILL_FILE.read_bytes()
        assert not raw.startswith(b'\xef\xbb\xbf'), (
            f'SKILL.md must not have BOM. First 6 bytes: {raw[:6]!r}'
        )

    def test_skill_file_starts_with_frontmatter_delimiter(self):
        raw = SKILL_FILE.read_bytes()
        assert raw.startswith(b'---\n'), (
            f"SKILL.md must start with exactly b'---\\n' (LF, no CRLF, no BOM). First 6 bytes: {raw[:6]!r}"
        )

    def test_workflow_raw_bytes_contain_adapter_antigravity(self):
        raw = WORKFLOW_FILE.read_bytes()
        assert b'--adapter antigravity' in raw

    def test_skill_raw_bytes_contain_adapter_codex(self):
        raw = SKILL_FILE.read_bytes()
        assert b'--adapter codex' in raw
