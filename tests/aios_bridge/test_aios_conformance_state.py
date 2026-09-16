from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONFORMANCE_FILE = REPO_ROOT / ".ai" / "aios-conformance-state.yaml"
EXPECTED_PIN = "91a177d5b96b2197a4d8223dbb727dda6201cb64"
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
    assert certification["task_revision"] == 3
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
    assert list(selectors) == ["AC1", "AC2", "AC3", "AC4", "AC5", "AC6"]

    assert selectors["AC1"] == {
        "carrier": "AIOS_BRAIN_INGRESS",
        "issue_number": 27,
        "operation": "AUTHOR_TASK",
        "workflow_run_id": 35071658032,
        "expected_actor": "trung-via",
        "expected_predecessor_main": "ed10b28e068d662e8dd70c8a38af2b0da19fcf65",
        "canonical_task_commit": "ecb4ae02433331f493a1547735049db4a4ea0f46",
    }
    assert selectors["AC2"]["dispatch_id"] == "task-207-r3-live-001"
    assert selectors["AC2"]["run_id"] == "RUN-207-003"
    assert selectors["AC2"]["executor"] == "codex"
    assert selectors["AC3"]["run_id"] == "RUN-207-003"

    assert selectors["AC4"] == {
        "reused_transport_task": "TASK-209",
        "review_ingress_issue_number": 26,
        "run_id": "RUN-209-002",
        "review_id": "REVIEW-209-001",
        "auto_publish_workflow_run_id": 35071342455,
        "published_candidate": "ed10b28e068d662e8dd70c8a38af2b0da19fcf65",
    }
    assert selectors["AC5"]["expected_outcome"] == (
        "FAIL_CLOSED_NO_IMPLEMENTATION_RUN"
    )
    assert selectors["AC6"]["action_shape"] == "NO_CHANGE"
    assert selectors["AC6"]["executor"] is None
    assert selectors["AC6"]["expected_outcome"] == (
        "FAIL_CLOSED_NO_IMPLEMENTATION_RUN"
    )


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

    assert state["historical_exclusions"] == {
        "old_pin_task_revision": "TASK-207-REVISION-2",
        "runs": ["RUN-207-001", "RUN-207-002"],
        "repair": "REPAIR-207-001",
        "certification_authority_for_current_pin": False,
    }
