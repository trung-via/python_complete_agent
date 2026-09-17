"""Deterministic structural certification for AIOS Control Plane Adoption Phase 1."""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
from unittest.mock import MagicMock

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_DIR = REPO_ROOT / ".agents" / "skills" / "aios-worker" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import aios_phase1_wakeup as wakeup  # noqa: E402
import aios_worker as worker  # noqa: E402

INGRESS_POLICY_PATH = REPO_ROOT / ".ai" / "brain-ingress-carriers.yaml"
WAKEUP_POLICY_PATH = REPO_ROOT / ".ai" / "brain-wakeup-carriers.yaml"
ATTENTION_POLICY_PATH = REPO_ROOT / ".ai" / "brain-terminal-attention-carriers.yaml"

INGRESS_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "aios-brain-ingress.yml"
WAKEUP_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "aios-brain-wakeup.yml"
SELF_HOSTED_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "aios-self-hosted-wakeup.yml"
ATTENTION_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "aios-terminal-attention.yml"

REQUIREMENTS_FILE = REPO_ROOT / ".agents" / "skills" / "aios-worker" / "requirements-aios-renew.txt"
ADOPTION_STATE_PATH = REPO_ROOT / ".ai" / "aios-adoption-state.yaml"
ROADMAP_STATE_PATH = REPO_ROOT / ".ai" / "roadmap-state.yaml"


def completed(command=(), *, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(command, returncode, stdout, stderr)


def load_yaml(path: Path) -> dict:
    assert path.is_file(), f"File not found: {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_workflow(path: Path) -> tuple[dict, str]:
    assert path.is_file(), f"Workflow not found: {path}"
    text = path.read_text(encoding="utf-8")
    return yaml.load(text, Loader=yaml.BaseLoader), text


class TestPhase1CarrierPolicies:
    """Certifies TASK-107, TASK-108, and TASK-113 canonical policy schemas."""

    def test_brain_ingress_policy_binding(self):
        policy = load_yaml(INGRESS_POLICY_PATH)
        assert policy == {
            "format": "AIOS_BRAIN_INGRESS_CARRIERS_POLICY",
            "version": 1,
            "github_issue": {
                "enabled": True,
                "repository": "trung-via/python_complete_agent",
                "authorized_actors": ["trung-via"],
                "title_marker": "[AIOS BRAIN INGRESS]",
                "max_body_bytes": 131072,
            },
        }

    def test_brain_wakeup_policy_binding(self):
        policy = load_yaml(WAKEUP_POLICY_PATH)
        assert policy == {
            "format": "AIOS_BRAIN_WAKEUP_CARRIERS_POLICY",
            "version": 1,
            "github_issue": {
                "enabled": True,
                "repository": "trung-via/python_complete_agent",
                "authorized_actors": ["trung-via"],
                "title_marker": "[AIOS BRAIN WAKEUP]",
                "max_body_bytes": 4096,
            },
        }

    def test_terminal_attention_policy_binding(self):
        policy = load_yaml(ATTENTION_POLICY_PATH)
        assert policy == {
            "format": "AIOS_BRAIN_TERMINAL_ATTENTION_CARRIERS_POLICY",
            "version": 1,
            "github_issue": {
                "enabled": True,
                "repository": "trung-via/python_complete_agent",
                "main_ref": "refs/heads/main",
                "signal_prefix": "refs/heads/aios/terminal-attention",
                "title_marker": "[AIOS TERMINAL ATTENTION]",
            },
        }


class TestBrainIngressWorkflow:
    """Certifies AC1 and AC5: Brain Issue ingress triggers, minimum permissions, and exact pin."""

    def test_trigger_and_marker_gate(self):
        wf, _ = load_workflow(INGRESS_WORKFLOW_PATH)
        assert wf.get("on") == {"issues": {"types": ["opened"]}}
        job = wf["jobs"]["deliver"]
        assert job["if"] == "github.event.issue.title == '[AIOS BRAIN INGRESS]'"
        assert job["runs-on"] == "ubuntu-latest"

    def test_permissions_add_only_task_110_actions_write(self):
        wf, _ = load_workflow(INGRESS_WORKFLOW_PATH)
        assert wf.get("permissions") == {
            "contents": "write",
            "issues": "write",
            "actions": "write",
        }

    def test_concurrency_group(self):
        wf, _ = load_workflow(INGRESS_WORKFLOW_PATH)
        assert wf.get("concurrency") == {
            "group": "aios-brain-ingress-${{ github.repository }}",
            "cancel-in-progress": "false",
        }

    def test_checkout_is_canonical_main_with_full_history(self):
        wf, _ = load_workflow(INGRESS_WORKFLOW_PATH)
        checkout = wf["jobs"]["deliver"]["steps"][0]
        assert checkout["uses"] == "actions/checkout@v4"
        assert checkout["with"] == {"ref": "main", "fetch-depth": "0"}

    def test_installs_only_from_requirements_pin(self):
        wf, text = load_workflow(INGRESS_WORKFLOW_PATH)
        runs = [s["run"] for s in wf["jobs"]["deliver"]["steps"] if "run" in s]
        install = [r for r in runs if "requirements-aios-renew.txt" in r]
        assert len(install) == 1
        assert "python -m pip install" in install[0]
        assert "git+https" not in text

    def test_one_carrier_call_with_event_file_and_no_body_interpolation(self):
        wf, text = load_workflow(INGRESS_WORKFLOW_PATH)
        runs = [s["run"] for s in wf["jobs"]["deliver"]["steps"] if "run" in s]
        carrier_calls = [r for r in runs if "aios_renew.github_issue_ingress" in r]
        assert len(carrier_calls) == 1
        assert '--event "$GITHUB_EVENT_PATH"' in carrier_calls[0]
        assert '--policy .ai/brain-ingress-carriers.yaml' in carrier_calls[0]
        assert '--repo .' in carrier_calls[0]
        assert '--output "$GITHUB_OUTPUT"' in carrier_calls[0]
        assert "github.event.issue.body" not in text

    def test_phase_1_semantics_preserved_with_only_fixed_publication_continuation(self):
        _, text = load_workflow(INGRESS_WORKFLOW_PATH)
        for forbidden in (
            "aios run",
            "aios remediate",
            "aios repair",
            "aios wakeup",
            "codex",
            "antigravity",
        ):
            assert forbidden not in text
        assert text.count("createWorkflowDispatch") == 2
        assert "workflow_id: 'aios-auto-publish.yml'" in text
        assert "AIOS_RUN_ID: ${{ steps.ingress.outputs.publication_run_id }}" in text
        assert "run_id: process.env.AIOS_RUN_ID" in text
        assert "workflow_id: 'aios-self-hosted-repair-wakeup.yml'" in text
        assert "repair_dispatch_id: process.env.AIOS_REPAIR_DISPATCH_ID" in text
        assert "failed_run_id: process.env.AIOS_FAILED_RUN_ID" in text
        assert "repair_sha: process.env.AIOS_REPAIR_SHA" in text


class TestBrainWakeupWorkflow:
    """Certifies AC2 and AC5: Brain PRIMARY wakeup admission and dispatch boundary."""

    def test_trigger_and_marker_gate(self):
        wf, _ = load_workflow(WAKEUP_WORKFLOW_PATH)
        assert wf.get("on") == {"issues": {"types": ["opened"]}}
        job = wf["jobs"]["admit-and-dispatch"]
        assert job["if"] == "github.event.issue.title == '[AIOS BRAIN WAKEUP]'"
        assert job["runs-on"] == "ubuntu-latest"

    def test_permissions_minimum(self):
        wf, _ = load_workflow(WAKEUP_WORKFLOW_PATH)
        assert wf.get("permissions") == {
            "contents": "read",
            "actions": "write",
            "issues": "write",
        }

    def test_installs_only_from_requirements_pin(self):
        wf, text = load_workflow(WAKEUP_WORKFLOW_PATH)
        runs = [s["run"] for s in wf["jobs"]["admit-and-dispatch"]["steps"] if "run" in s]
        install = [r for r in runs if "requirements-aios-renew.txt" in r]
        assert len(install) == 1
        assert "python -m pip install" in install[0]
        assert "git+https" not in text

    def test_dispatches_exact_self_hosted_workflow_with_sanitized_inputs(self):
        wf, text = load_workflow(WAKEUP_WORKFLOW_PATH)
        steps = wf["jobs"]["admit-and-dispatch"]["steps"]
        dispatch = next(s for s in steps if s.get("id") == "dispatch")
        script = dispatch["with"]["script"]
        assert "owner: 'trung-via'" in script
        assert "repo: 'python_complete_agent'" in script
        assert "workflow_id: 'aios-self-hosted-wakeup.yml'" in script
        assert "ref: 'main'" in script
        assert set(dispatch["env"]) == {
            "AIOS_DISPATCH_ID",
            "AIOS_TASK_ID",
            "AIOS_EXECUTOR",
        }
        assert "github.event.issue.body" not in text

    def test_receipt_is_bounded_and_non_authoritative(self):
        _, text = load_workflow(WAKEUP_WORKFLOW_PATH)
        assert text.count("github.rest.issues.createComment") == 1
        assert ".slice(0, 3500)" in text
        assert "status: DISPATCH_ACCEPTED" in text
        assert "execution_outcome: not_observed" in text
        assert "this is not RUN, verification, review, or publication success" in text


class TestSelfHostedWakeupWorkflow:
    """Certifies AC2 and AC3: Self-hosted PRIMARY workflow with dedicated runner and AIOS_REPO_ROOT."""

    def test_workflow_dispatch_only(self):
        wf, _ = load_workflow(SELF_HOSTED_WORKFLOW_PATH)
        assert list(wf.get("on")) == ["workflow_dispatch"]
        inputs = wf["on"]["workflow_dispatch"]["inputs"]
        assert set(inputs) == {"dispatch_id", "task_id", "executor"}
        assert inputs["executor"]["type"] == "choice"
        assert set(inputs["executor"]["options"]) == {"codex", "antigravity"}

    def test_permissions_strictly_contents_read(self):
        wf, _ = load_workflow(SELF_HOSTED_WORKFLOW_PATH)
        assert wf.get("permissions") == {"contents": "read"}

    def test_dedicated_runner_label(self):
        wf, _ = load_workflow(SELF_HOSTED_WORKFLOW_PATH)
        runs_on = wf["jobs"]["wakeup"]["runs-on"]
        assert runs_on == [
            "self-hosted",
            "windows",
            "x64",
            "python-complete-agent",
        ]

    def test_no_checkout_and_uses_aios_repo_root_var(self):
        wf, text = load_workflow(SELF_HOSTED_WORKFLOW_PATH)
        steps = wf["jobs"]["wakeup"]["steps"]
        assert not any("actions/checkout" in str(s.get("uses", "")) for s in steps)
        assert "AIOS_REPO_ROOT: ${{ vars.AIOS_REPO_ROOT }}" in text

    def test_uses_phase1_wakeup_bootstrap_script_not_ambient_aios(self):
        _, text = load_workflow(SELF_HOSTED_WORKFLOW_PATH)
        assert "aios_phase1_wakeup.py" in text
        assert "Get-Command aios" not in text
        assert re.search(r"\baios\s+wakeup\b", text) is None
        assert re.search(r"\baios\s+run\b", text) is None

    def test_input_data_binding_and_validation(self):
        wf, text = load_workflow(SELF_HOSTED_WORKFLOW_PATH)
        step = wf["jobs"]["wakeup"]["steps"][1]
        assert "${{ inputs." not in step["run"]
        assert step["env"]["AIOS_DISPATCH_ID"] == "${{ inputs.dispatch_id }}"
        assert step["env"]["AIOS_TASK_ID"] == "${{ inputs.task_id }}"
        assert step["env"]["AIOS_EXECUTOR"] == "${{ inputs.executor }}"
        assert "Invalid dispatch_id format" in step["run"]
        assert "Invalid task_id format" in step["run"]


class TestTerminalAttentionWorkflow:
    """Certifies AC4: Terminal attention notification carrier."""

    def test_trigger_and_permissions(self):
        wf, _ = load_workflow(ATTENTION_WORKFLOW_PATH)
        assert set(wf.get("on")) == {"push", "workflow_dispatch"}
        assert wf["on"]["push"]["branches"] == ["aios/terminal-attention/**"]
        assert set(wf["on"]["workflow_dispatch"]["inputs"]) == {
            "run_id",
            "terminal_kind",
            "artifact_sha",
        }
        assert wf.get("permissions") == {"contents": "read", "issues": "write"}

    def test_installs_only_from_requirements_pin(self):
        wf, text = load_workflow(ATTENTION_WORKFLOW_PATH)
        runs = [s["run"] for s in wf["jobs"]["admit-and-notify"]["steps"] if "run" in s]
        install = [r for r in runs if "requirements-aios-renew.txt" in r]
        assert len(install) == 1
        assert "python -m pip install" in install[0]
        assert "git+https" not in text

    def test_delegates_to_pinned_terminal_attention_module(self):
        _, text = load_workflow(ATTENTION_WORKFLOW_PATH)
        assert "python -m aios_renew.terminal_attention" in text
        assert "--policy .ai/brain-terminal-attention-carriers.yaml" in text
        assert "--event-sha \"$GITHUB_SHA\"" in text

    def test_creates_or_reuses_strict_attention_issue_without_execution(self):
        _, text = load_workflow(ATTENTION_WORKFLOW_PATH)
        assert "const title = '[AIOS TERMINAL ATTENTION]'" in text
        assert "format: AIOS_TERMINAL_ATTENTION" in text
        assert "REUSED" in text
        assert "CREATED" in text
        for forbidden in (
            "createWorkflowDispatch",
            "aios run",
            "aios remediate",
            "aios repair",
            "aios wakeup",
            "verdict:",
            "correction:",
        ):
            assert forbidden not in text


class TestPhase1WakeupBootstrapScript:
    """Certifies AC2 and AC3: aios_phase1_wakeup.py bootstrap and delegation."""

    def test_wakeup_command_format(self, tmp_path):
        python = tmp_path / "python.exe"
        repo = tmp_path / "repo"
        cmd = wakeup.wakeup_command(
            python,
            dispatch_id="dispatch-test-1",
            task_id="TASK-205",
            executor="antigravity",
            repo=repo,
        )
        assert cmd == (
            str(python),
            "-m",
            "aios_renew.operator",
            "wakeup",
            "dispatch-test-1",
            "TASK-205",
            "--executor",
            "antigravity",
            "--repo",
            str(repo),
        )

    def test_dispatch_id_validation(self):
        assert wakeup.parse_dispatch_id("valid-id_123") == "valid-id_123"
        for invalid in ("", " ", "-lead", "../escape", "semi;cmd"):
            with pytest.raises(worker.WorkerSurfaceError):
                wakeup.parse_dispatch_id(invalid)

    def test_main_delegates_once_to_kernel(self, tmp_path, monkeypatch):
        repo = tmp_path / "repo"
        (repo / ".ai" / "tasks").mkdir(parents=True)
        python = tmp_path / "runtime" / "python.exe"
        layout = MagicMock()
        invoke = MagicMock(return_value=completed(returncode=0, stdout="WAKEUP PASS\n"))

        monkeypatch.setattr(wakeup, "get_repo_root", lambda: repo)
        monkeypatch.setattr(wakeup, "runtime_layout", lambda r: layout)
        monkeypatch.setattr(wakeup, "ensure_runtime", lambda l: python)
        monkeypatch.setattr(wakeup, "invoke_kernel", invoke)

        ret = wakeup.main([
            "dispatch-001",
            "TASK-205",
            "--executor",
            "antigravity",
            "--repo",
            str(repo),
        ])
        assert ret == 0
        invoke.assert_called_once_with(
            wakeup.wakeup_command(
                python,
                dispatch_id="dispatch-001",
                task_id="TASK-205",
                executor="antigravity",
                repo=repo,
            ),
            repo=repo,
        )

    def test_main_rejects_unproven_runtime(self, tmp_path, monkeypatch):
        repo = tmp_path / "repo"
        (repo / ".ai" / "tasks").mkdir(parents=True)
        monkeypatch.setattr(wakeup, "get_repo_root", lambda: repo)
        monkeypatch.setattr(wakeup, "runtime_layout", lambda r: MagicMock())
        monkeypatch.setattr(
            wakeup,
            "ensure_runtime",
            MagicMock(side_effect=worker.BootstrapError("unproven")),
        )
        invoke = MagicMock()
        monkeypatch.setattr(wakeup, "invoke_kernel", invoke)

        ret = wakeup.main([
            "dispatch-001",
            "TASK-205",
            "--executor",
            "codex",
            "--repo",
            str(repo),
        ])
        assert ret == 1
        invoke.assert_not_called()


class TestNoGenericOrLegacyPhase2Alternates:
    """Phase-1 remains composed with only the dedicated Phase-2 bindings."""

    def test_generic_or_legacy_workflow_names_do_not_exist(self):
        workflows_dir = REPO_ROOT / ".github" / "workflows"
        for forbidden in (
            "aios-review-publication.yml",
            "aios-repair-wakeup.yml",
            "aios-remediation-intent.yml",
            "aios-remediation-wakeup.yml",
        ):
            assert not (workflows_dir / forbidden).exists()

    def test_generic_or_legacy_policy_names_do_not_exist(self):
        ai_dir = REPO_ROOT / ".ai"
        for forbidden in (
            "brain-repair-carriers.yaml",
            "brain-remediation-carriers.yaml",
            "brain-publication-carriers.yaml",
        ):
            assert not (ai_dir / forbidden).exists()
