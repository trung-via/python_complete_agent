"""Deterministic structural checks for AIOS Control Plane Adoption Phase 2."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from unittest.mock import MagicMock

import yaml


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / ".agents" / "skills" / "aios-worker" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import aios_phase2_remediation as remediation  # noqa: E402
import aios_phase2_repair as repair  # noqa: E402


PIN = "652b00b103dd50e2a550dd0ec0fe4063e69631b7"
REQUIREMENTS = ROOT / ".agents/skills/aios-worker/requirements-aios-renew.txt"
INGRESS = ROOT / ".github/workflows/aios-brain-ingress.yml"
PUBLISH = ROOT / ".github/workflows/aios-auto-publish.yml"
REMEDIATION_POLICY = ROOT / ".ai/brain-remediation-intent-carriers.yaml"
REPAIR_POLICY = ROOT / ".ai/brain-repair-wakeup-carriers.yaml"
REMEDIATION_CARRIER = ROOT / ".github/workflows/aios-brain-remediation-intent.yml"
REMEDIATION_TARGET = ROOT / ".github/workflows/aios-approved-remediation-intent.yml"
REPAIR_CARRIER = ROOT / ".github/workflows/aios-brain-repair-wakeup.yml"
REPAIR_TARGET = ROOT / ".github/workflows/aios-self-hosted-repair-wakeup.yml"


def load_workflow(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    return yaml.load(text, Loader=yaml.BaseLoader), text


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def completed(command=(), *, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(command, returncode, stdout, stderr)


def assert_pin_install(workflow_path: Path, *, job: str) -> None:
    workflow, text = load_workflow(workflow_path)
    runs = [step["run"] for step in workflow["jobs"][job]["steps"] if "run" in step]
    installs = [run for run in runs if "requirements-aios-renew.txt" in run]
    assert len(installs) == 1
    assert "python -m pip install --no-input -r" in installs[0]
    assert "git+https" not in text
    assert "pip install aios-renew" not in text


class TestReviewToPublicationContinuation:
    def test_ingress_adds_only_actions_write_and_one_run_selector_dispatch(self):
        workflow, text = load_workflow(INGRESS)
        assert workflow["permissions"] == {
            "contents": "write",
            "issues": "write",
            "actions": "write",
        }
        dispatch = next(
            step for step in workflow["jobs"]["deliver"]["steps"]
            if step.get("id") == "dispatch"
        )
        assert dispatch["if"] == (
            "steps.ingress.outcome == 'success' && "
            "steps.ingress.outputs.publication_run_id != ''"
        )
        assert dispatch["env"] == {
            "AIOS_RUN_ID": "${{ steps.ingress.outputs.publication_run_id }}"
        }
        script = dispatch["with"]["script"]
        assert text.count("createWorkflowDispatch") == 2
        assert "workflow_id: 'aios-auto-publish.yml'" in script
        assert "ref: 'main'" in script
        assert "run_id: process.env.AIOS_RUN_ID" in script
        for forbidden in (
            "candidate_sha", "verdict", "target_ref", "force", "command",
            "github.event.issue.body",
        ):
            assert forbidden not in script

        repair_dispatch = next(
            step for step in workflow["jobs"]["deliver"]["steps"]
            if step.get("id") == "repair_dispatch"
        )
        assert repair_dispatch["if"] == (
            "steps.ingress.outcome == 'success' && "
            "steps.ingress.outputs.repair_sha != ''"
        )
        assert repair_dispatch["env"] == {
            "AIOS_REPAIR_DISPATCH_ID": "${{ steps.ingress.outputs.repair_dispatch_id }}",
            "AIOS_FAILED_RUN_ID": "${{ steps.ingress.outputs.failed_run_id }}",
            "AIOS_REPAIR_SHA": "${{ steps.ingress.outputs.repair_sha }}",
        }
        repair_script = repair_dispatch["with"]["script"]
        assert "workflow_id: 'aios-self-hosted-repair-wakeup.yml'" in repair_script
        assert "ref: 'main'" in repair_script
        assert "repair_dispatch_id: process.env.AIOS_REPAIR_DISPATCH_ID" in repair_script
        assert "failed_run_id: process.env.AIOS_FAILED_RUN_ID" in repair_script
        assert "repair_sha: process.env.AIOS_REPAIR_SHA" in repair_script
        assert "executor: ''" in repair_script

    def test_non_publication_ingress_has_no_dispatch_and_receipt_is_truthful(self):
        _, text = load_workflow(INGRESS)
        assert "steps.ingress.outputs.publication_run_id != ''" in text
        assert "this is not publication success or verdict" in text
        assert "steps.ingress.outcome != 'success'" in text
        assert text.count("aios_renew.github_issue_ingress") == 1
        assert_pin_install(INGRESS, job="deliver")

    def test_safe_publisher_retains_push_and_adds_bounded_replay(self):
        workflow, text = load_workflow(PUBLISH)
        assert set(workflow["on"]) == {"push", "workflow_dispatch"}
        assert workflow["on"]["push"]["branches"] == ["aios/review-decision/**"]
        inputs = workflow["on"]["workflow_dispatch"]["inputs"]
        assert set(inputs) == {"run_id"}
        assert inputs["run_id"]["required"] == "true"
        assert workflow["permissions"] == {"contents": "write"}
        assert text.count("aios_renew.publication") == 1
        assert 'git fetch --no-tags origin "$decision_ref"' in text
        assert "FETCH_HEAD^{commit}" in text
        assert "--run-id \"$run_id\"" in text
        assert "--decision-sha \"$decision_sha\"" in text
        assert "merge-base" not in text
        assert "git push" not in text
        assert "CHANGES_REQUIRED" not in text
        assert_pin_install(PUBLISH, job="publish")


class TestRemediationIntentBinding:
    def test_policy_is_exact_bounded_python_agent_binding(self):
        assert load_yaml(REMEDIATION_POLICY) == {
            "format": "AIOS_BRAIN_REMEDIATION_INTENT_CARRIERS_POLICY",
            "version": 1,
            "github_issue": {
                "enabled": True,
                "repository": "trung-via/python_complete_agent",
                "authorized_actors": ["trung-via"],
                "title_marker": "[AIOS REMEDIATION INTENT]",
                "max_body_bytes": 4096,
            },
        }

    def test_github_carrier_is_least_privilege_and_calls_one_fixed_target(self):
        workflow, text = load_workflow(REMEDIATION_CARRIER)
        assert workflow["on"] == {"issues": {"types": ["opened"]}}
        admit = workflow["jobs"]["admit"]
        assert admit["if"] == "github.event.issue.title == '[AIOS REMEDIATION INTENT]'"
        assert admit["runs-on"] == "ubuntu-latest"
        assert workflow["permissions"] == {"contents": "read", "issues": "write"}
        dispatch = workflow["jobs"]["dispatch"]
        assert dispatch["uses"] == "./.github/workflows/aios-approved-remediation-intent.yml"
        assert set(dispatch["with"]) == {
            "correction_dispatch_id", "source_run_id", "finding_id", "executor",
        }
        assert text.count("aios_renew.github_issue_remediation_intent") == 1
        assert "github.event.issue.body" not in text
        assert "secrets: inherit" not in text
        assert_pin_install(REMEDIATION_CARRIER, job="admit")

    def test_self_hosted_target_uses_exact_runner_root_actor_and_bootstrap(self):
        workflow, text = load_workflow(REMEDIATION_TARGET)
        assert set(workflow["on"]) == {"workflow_dispatch", "workflow_call"}
        assert workflow["permissions"] == {"contents": "read"}
        job = workflow["jobs"]["approve-and-wake"]
        assert job["runs-on"] == ["self-hosted", "windows", "x64", "python-complete-agent"]
        assert job["env"] == {"AIOS_REPO_ROOT": "${{ vars.AIOS_REPO_ROOT }}"}
        assert "actions/checkout" not in text
        assert "trung-via/python_complete_agent" in text
        assert "GITHUB_ACTOR -ne 'trung-via'" in text
        assert "AIOS_APPROVER: ${{ github.actor }}" in text
        assert text.count("aios_phase2_remediation.py") == 2
        assert "aios approved-remediation-intent" not in text
        assert "secrets." not in text

    def test_bootstrap_delegates_once_to_combined_intent_not_a3_or_a6_directly(self):
        source = (SCRIPT_DIR / "aios_phase2_remediation.py").read_text(encoding="utf-8")
        assert source.count('"approved-remediation-intent"') == 1
        for forbidden in (
            '"remote-approve"', '"approved-remediation-wakeup"',
            '"remediate"', '"repair"', "native_runner", "verification_runner",
        ):
            assert forbidden not in source

        python = Path("runtime/python")
        command = remediation.remediation_command(
            python,
            correction_dispatch_id="correction-206-001",
            source_run_id="RUN-205-002",
            finding_id="F-1",
            executor="codex",
            approver="trung-via",
            repo=ROOT,
        )
        assert command == (
            str(python), "-m", "aios_renew.operator", "approved-remediation-intent",
            "correction-206-001", "RUN-205-002", "F-1", "--executor", "codex",
            "--approver", "trung-via", "--repo", str(ROOT),
        )

    def test_bootstrap_main_preserves_one_exact_operator_invocation(self, monkeypatch):
        runtime_python = ROOT / ".git/aios/worker-runtime/Scripts/python.exe"
        invoke = MagicMock(return_value=completed(returncode=0))
        monkeypatch.setattr(remediation, "ensure_runtime", MagicMock(return_value=runtime_python))
        monkeypatch.setattr(remediation, "invoke_kernel", invoke)
        monkeypatch.setattr(remediation, "_emit_completed", MagicMock())
        assert remediation.main([
            "correction-206-001", "RUN-205-002", "F-1", "--executor", "codex",
            "--approver", "trung-via", "--repo", str(ROOT),
        ]) == 0
        assert invoke.call_count == 1


class TestRepairWakeupBinding:
    def test_policy_is_exact_bounded_python_agent_binding(self):
        assert load_yaml(REPAIR_POLICY) == {
            "format": "AIOS_BRAIN_REPAIR_WAKEUP_CARRIERS_POLICY",
            "version": 1,
            "github_issue": {
                "enabled": True,
                "repository": "trung-via/python_complete_agent",
                "authorized_actors": ["trung-via"],
                "title_marker": "[AIOS REPAIR WAKEUP]",
                "max_body_bytes": 4096,
            },
        }

    def test_github_carrier_is_dedicated_least_privilege_and_fixed(self):
        workflow, text = load_workflow(REPAIR_CARRIER)
        assert workflow["on"] == {"issues": {"types": ["opened"]}}
        admit = workflow["jobs"]["admit"]
        assert admit["if"] == "github.event.issue.title == '[AIOS REPAIR WAKEUP]'"
        assert admit["runs-on"] == "ubuntu-latest"
        assert workflow["permissions"] == {"contents": "read", "issues": "write"}
        dispatch = workflow["jobs"]["dispatch"]
        assert dispatch["uses"] == "./.github/workflows/aios-self-hosted-repair-wakeup.yml"
        assert set(dispatch["with"]) == {
            "repair_dispatch_id", "failed_run_id", "repair_sha", "executor",
        }
        assert text.count("aios_renew.github_issue_repair_wakeup") == 1
        assert "github.event.issue.body" not in text
        assert "secrets: inherit" not in text
        assert_pin_install(REPAIR_CARRIER, job="admit")
        receipt = workflow["jobs"]["receipt"]
        assert receipt["if"] == "always() && github.event.issue.title == '[AIOS REPAIR WAKEUP]'"

    def test_self_hosted_target_is_fixed_dedicated_and_has_optional_executor(self):
        workflow, text = load_workflow(REPAIR_TARGET)
        assert set(workflow["on"]) == {"workflow_dispatch", "workflow_call"}
        assert workflow["permissions"] == {"contents": "read"}
        job = workflow["jobs"]["execute-repair"]
        assert job["runs-on"] == ["self-hosted", "windows", "x64", "python-complete-agent"]
        assert job["env"] == {"AIOS_REPO_ROOT": "${{ vars.AIOS_REPO_ROOT }}"}
        assert workflow["on"]["workflow_call"]["inputs"]["executor"]["required"] == "false"
        assert workflow["on"]["workflow_call"]["inputs"]["executor"]["default"] == ""
        assert "actions/checkout" not in text
        assert "GITHUB_ACTOR -ne 'trung-via'" in text
        assert text.count("aios_phase2_repair.py") == 2
        assert "aios continue" not in text.lower()
        assert "aios repair-wakeup" not in text.lower()
        assert "secrets." not in text

    def test_bootstrap_preserves_zero_executor_and_explicit_executor_shapes(self):
        python = Path("runtime/python")
        common = {
            "repair_dispatch_id": "repair-206-001",
            "failed_run_id": "RUN-205-002",
            "repair_sha": "a" * 40,
            "repo": ROOT,
        }
        no_change = repair.repair_command(python, executor=None, **common)
        code_fix = repair.repair_command(python, executor="antigravity", **common)
        assert no_change == (
            str(python), "-m", "aios_renew.operator", "repair-wakeup",
            "repair-206-001", "RUN-205-002", "a" * 40, "--repo", str(ROOT),
        )
        assert "--executor" not in no_change
        assert code_fix[-4:] == ("--executor", "antigravity", "--repo", str(ROOT))
        source = (SCRIPT_DIR / "aios_phase2_repair.py").read_text(encoding="utf-8")
        assert source.count('"repair-wakeup"') == 1
        for forbidden in ('"continue"', '"repair"', "run_repair", "native_runner"):
            assert forbidden not in source

    def test_bootstrap_main_delegates_no_executor_once(self, monkeypatch):
        runtime_python = ROOT / ".git/aios/worker-runtime/Scripts/python.exe"
        invoke = MagicMock(return_value=completed(returncode=0))
        monkeypatch.setattr(repair, "ensure_runtime", MagicMock(return_value=runtime_python))
        monkeypatch.setattr(repair, "invoke_kernel", invoke)
        monkeypatch.setattr(repair, "_emit_completed", MagicMock())
        assert repair.main([
            "repair-206-001", "RUN-205-002", "a" * 40, "--repo", str(ROOT),
        ]) == 0
        assert invoke.call_count == 1
        assert "--executor" not in invoke.call_args.args[0]


def test_phase_2_surfaces_add_no_generic_router_or_raw_issue_execution():
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            REMEDIATION_CARRIER, REMEDIATION_TARGET, REPAIR_CARRIER, REPAIR_TARGET,
            SCRIPT_DIR / "aios_phase2_remediation.py",
            SCRIPT_DIR / "aios_phase2_repair.py",
        )
    ).lower()
    for forbidden in (
        "github.event.issue.body", "secrets: inherit", "aios continue",
        "lifecycle router", "automatic executor", "git checkout",
    ):
        assert forbidden not in combined


def test_phase_2_changed_surfaces_are_utf8_lf_without_bom():
    for path in (
        INGRESS, PUBLISH, REMEDIATION_POLICY, REPAIR_POLICY,
        REMEDIATION_CARRIER, REMEDIATION_TARGET, REPAIR_CARRIER, REPAIR_TARGET,
        SCRIPT_DIR / "aios_phase2_remediation.py",
        SCRIPT_DIR / "aios_phase2_repair.py",
        Path(__file__),
    ):
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), path
        assert b"\r\n" not in raw, path
