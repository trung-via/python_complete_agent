from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONFORMANCE_FILE = REPO_ROOT / ".ai" / "aios-conformance-state.yaml"
EXPECTED_PIN = "49ad4d7a1e57a4c25ba44e60589d8320cb0f57b2"
HISTORICAL_PIN = "c96eb8b52acd865b9453409e6598e08a8bd4e48e"
PUBLICATION_GATE = {
    "semantic_review": "PASS",
    "review_mode": "PRIMARY",
    "published_source": "EXACT_REVIEWED_CANDIDATE",
    "canonical_main_equals_reviewed_candidate": True,
}


def load_state() -> dict:
    value = yaml.safe_load(CONFORMANCE_FILE.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def all_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(str(key))
            keys.update(all_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(all_keys(child))
    return keys


def test_certification_is_small_publication_gated_brain_review_state():
    state = load_state()
    assert state["kind"] == "aios_downstream_conformance_certification"
    assert state["authority"] == {
        "owner": "BRAIN_REVIEW",
        "purpose": "PUBLICATION_GATED_DOWNSTREAM_CERTIFICATION",
        "runtime_truth_store": False,
        "evidence_store": False,
        "grants_lifecycle_authority": False,
    }

    certification = state["certification"]
    assert certification["task_id"] == "TASK-207"
    assert certification["task_revision"] == 5
    assert certification["downstream_pin"] == EXPECTED_PIN
    assert certification["status"] == "CERTIFIED_ON_REVIEWED_SOURCE_PUBLICATION"
    assert certification["effective_only_when"] == PUBLICATION_GATE
    assert certification["before_gate"] == "NOT_EFFECTIVE"
    assert "Runtime PASS and Reviewer PASS do not by themselves" in certification["boundary"]

    forbidden_keys = {
        "token",
        "tokens",
        "secret",
        "secrets",
        "raw_log",
        "raw_logs",
        "runner_path",
        "workspace",
    }
    assert all_keys(state).isdisjoint(forbidden_keys)


def test_phase_1_and_phase_2_binding_families_are_certified_without_duplication():
    families = load_state()["binding_families"]
    assert set(families["phase_1"]) == {
        "brain_authoring_ingress",
        "primary_wakeup",
        "terminal_attention",
    }
    assert set(families["phase_2"]) == {
        "review_to_publication",
        "remediation_intent",
        "repair_wakeup",
    }
    for phase in families.values():
        assert all(binding["status"] == "ACTIVE" for binding in phase.values())

    assert families["phase_1"]["primary_wakeup"]["bootstrap"].endswith(
        "aios_phase1_wakeup.py"
    )
    assert families["phase_2"]["remediation_intent"]["bootstrap"].endswith(
        "aios_phase2_remediation.py"
    )
    assert families["phase_2"]["repair_wakeup"]["bootstrap"].endswith(
        "aios_phase2_repair.py"
    )


def test_live_evidence_selectors_are_typed_and_current_pin_scoped():
    state = load_state()
    selectors = state["live_evidence_selectors"]
    assert list(selectors) == ["AC1", "AC2", "AC3", "AC4", "AC5"]

    assert selectors["AC1"] == {
        "carrier": "AIOS_BRAIN_INGRESS",
        "operation": "AUTHOR_TASK",
        "expected_actor": "trung-via",
        "expected_predecessor_main": "ada9a4e5b765a7daa4e081db1d56917410a73873",
        "canonical_task_commit": "258f9635be5ac80eaaa35f1e802f292d17eb65c7",
    }
    assert selectors["AC2"] == {
        "carrier": "AIOS_BRAIN_WAKEUP",
        "dispatch_id": "task207-r5-antigravity-001",
        "run_id": "RUN-207-005",
        "executor": "antigravity",
        "self_hosted_workflow_run_id": 35484892275,
    }
    assert selectors["AC3"] == {
        "carrier": "AIOS_TERMINAL_ATTENTION",
        "run_id": "RUN-207-005",
        "terminal_ref_prefix": "refs/heads/aios/terminal-attention/",
        "issue_title": "[AIOS TERMINAL ATTENTION]",
    }
    assert selectors["AC4"] == {
        "carrier": "AIOS_BRAIN_REMEDIATION_INTENT",
        "correction_dispatch_id": "task-207-r5-remediation-non-authorizing-001",
        "task_id": "TASK-207",
        "expected_outcome": "FAIL_CLOSED_NO_IMPLEMENTATION_RUN",
        "self_hosted_bootstrap": (
            ".agents/skills/aios-worker/scripts/aios_phase2_remediation.py"
        ),
    }
    assert selectors["AC5"] == {
        "carrier": "AIOS_BRAIN_REPAIR_WAKEUP",
        "repair_dispatch_id": "task-207-r5-repair-non-authorizing-001",
        "task_id": "TASK-207",
        "action_shape": "NO_CHANGE",
        "executor": None,
        "expected_outcome": "FAIL_CLOSED_NO_IMPLEMENTATION_RUN",
        "self_hosted_bootstrap": (
            ".agents/skills/aios-worker/scripts/aios_phase2_repair.py"
        ),
    }


def test_authority_boundaries_and_old_pin_exclusion_are_explicit():
    state = load_state()
    boundaries = state["authority_boundaries"]
    assert set(boundaries) == {
        "brain",
        "runtime",
        "executor",
        "reviewer",
        "publisher",
        "a3",
        "a6",
        "repair",
        "attention",
        "local_fallbacks",
    }
    assert boundaries["attention"] == "NOTIFICATION_ONLY"
    assert boundaries["local_fallbacks"] == "EMERGENCY_DEBUG_ONLY"

    assert state["historical_certification"] == {
        "task_id": "TASK-207",
        "task_revision": 4,
        "downstream_pin": HISTORICAL_PIN,
        "status": "HISTORICAL_OLD_PIN_EVIDENCE_ONLY",
        "certification_authority_for_current_pin": False,
    }

    assert state["historical_exclusions"] == {
        "old_pin_task_revision": "TASK-207-REVISION-2",
        "runs": ["RUN-207-001", "RUN-207-002"],
        "repair": "REPAIR-207-001",
        "certification_authority_for_current_pin": False,
    }
