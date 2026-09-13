"""Offline structural regressions for the TASK-107 Issue transport adaptation."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "aios-brain-ingress.yml"
POLICY_PATH = ROOT / ".ai" / "brain-ingress-carriers.yaml"
PIN_PATH = ROOT / ".agents" / "skills" / "aios-worker" / "requirements-aios-renew.txt"
EXPECTED_PIN = "f0237a3b98985ce6ebbaf41af1e06fa3eb4e998e"


def _workflow() -> tuple[dict, str]:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    return yaml.load(text, Loader=yaml.BaseLoader), text


def test_policy_binds_exact_repository_actor_marker_and_body_bound() -> None:
    policy = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
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


def test_workflow_has_only_opened_issue_trigger_and_exact_title_gate() -> None:
    workflow, _ = _workflow()
    assert workflow["on"] == {"issues": {"types": ["opened"]}}
    assert workflow["jobs"]["deliver"]["if"] == (
        "github.event.issue.title == '[AIOS BRAIN INGRESS]'"
    )


def test_workflow_permissions_and_concurrency_are_minimal() -> None:
    workflow, text = _workflow()
    assert workflow["permissions"] == {"contents": "write", "issues": "write"}
    assert workflow["concurrency"] == {
        "group": "aios-brain-ingress-${{ github.repository }}",
        "cancel-in-progress": "false",
    }
    for forbidden in (
        "actions: write",
        "pull-requests: write",
        "id-token:",
        "packages:",
        "deployments:",
        "secrets:",
    ):
        assert forbidden not in text


def test_workflow_checks_out_full_history_main_and_installs_only_exact_pin() -> None:
    workflow, text = _workflow()
    steps = workflow["jobs"]["deliver"]["steps"]
    assert steps[0]["uses"] == "actions/checkout@v4"
    assert steps[0]["with"] == {"ref": "main", "fetch-depth": "0"}
    assert steps[1]["uses"] == "actions/setup-python@v5"
    assert steps[1]["with"] == {"python-version": "3.11"}

    install_runs = [
        step["run"]
        for step in steps
        if "run" in step and "pip install" in step["run"]
    ]
    assert install_runs == [
        "python -m pip install --no-input -r "
        ".agents/skills/aios-worker/requirements-aios-renew.txt\n"
    ]
    assert PIN_PATH.read_text(encoding="utf-8").strip().endswith("@" + EXPECTED_PIN)
    assert "pip install --disable-pip-version-check ." not in text


def test_one_pinned_carrier_invocation_uses_opaque_event_file() -> None:
    workflow, text = _workflow()
    runs = [step["run"] for step in workflow["jobs"]["deliver"]["steps"] if "run" in step]
    carrier_calls = [run for run in runs if "aios_renew.github_issue_ingress" in run]
    assert len(carrier_calls) == 1
    call = carrier_calls[0]
    assert '--event "$GITHUB_EVENT_PATH"' in call
    assert "--policy .ai/brain-ingress-carriers.yaml" in call
    assert "--repo ." in call
    assert 'github.event.issue.body' not in text
    assert "aios ingress" not in text
    assert "aios ingest" not in text


def test_bounded_receipt_is_posted_and_issue_closes_only_after_success() -> None:
    workflow, text = _workflow()
    steps = workflow["jobs"]["deliver"]["steps"]
    receipt = next(
        step
        for step in steps
        if step.get("name") == "Post bounded transport receipt"
    )
    assert receipt["if"] == "always()"
    assert receipt["env"] == {
        "AIOS_RECEIPT_PATH": "${{ runner.temp }}/aios-brain-ingress-receipt.txt",
        "AIOS_INGRESS_OUTCOME": "${{ steps.ingress.outcome }}",
    }
    assert text.count("github.rest.issues.createComment") == 1
    assert text.count("github.rest.issues.update") == 1
    assert ".slice(0, 3500)" in text
    assert "if (successful)" in text
    assert steps[-1] == {
        "name": "Preserve failed delivery outcome",
        "if": "always() && steps.ingress.outcome != 'success'",
        "run": "exit 1",
    }


def test_carrier_adds_no_direct_git_or_alternate_publication_authority() -> None:
    _, text = _workflow()
    lowered = text.lower()
    for forbidden in (
        "git push",
        "git update-ref",
        "--force",
        "createorupdatefilecontents",
        "createref",
        "createworkflowdispatch",
        "workflow_dispatch",
        "aios_renew.publication",
        "aios-auto-publish",
    ):
        assert forbidden not in lowered
