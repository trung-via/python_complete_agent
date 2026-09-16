"""Deterministic structural checks for AIOS Conformance State."""
from __future__ import annotations

from pathlib import Path
import re
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFORMANCE_FILE = REPO_ROOT / ".ai" / "aios-conformance-state.yaml"
ADOPTION_FILE = REPO_ROOT / ".ai" / "aios-adoption-state.yaml"
ROADMAP_FILE = REPO_ROOT / ".ai" / "roadmap-state.yaml"
PIN_FILE = REPO_ROOT / ".agents" / "skills" / "aios-worker" / "requirements-aios-renew.txt"

EXPECTED_PIN = "26097405343150dc1b55015b94720528afad50ed"
EXPECTED_PREDECESSOR_MAIN = "2209af41dfa99a5ac6db851d35d196471c383481"


def load_yaml(path: Path) -> dict:
    assert path.is_file(), f"File does not exist: {path}"
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_conformance_state_schema_and_authority():
    assert CONFORMANCE_FILE.is_file()
    state = load_yaml(CONFORMANCE_FILE)
    assert state["schema_version"] == 1
    assert state["kind"] == "aios_downstream_conformance_state"
    assert state["project"] == "Python Agent"

    authority = state["authority"]
    assert authority["owner"] == "BRAIN"
    assert authority["purpose"] == "DOWNSTREAM_CONFORMANCE_CERTIFICATION_RECORD"
    assert authority["engineering_truth"] is False
    assert authority["live_evidence_required"] is True
    assert authority["live_evidence_evaluator"] == "INDEPENDENT_SEMANTIC_REVIEWER"
    assert authority["effective_on"] == "REVIEWED_SOURCE_PUBLICATION"
    assert authority["second_runtime_truth_store"] is False
    assert set(authority["classification_does_not_prove"]) == {
        "RUNTIME_PASS",
        "LIVE_EXECUTION_EVIDENCE",
        "SOURCE_PUBLICATION",
    }


def test_conformance_task_and_exact_pin():
    state = load_yaml(CONFORMANCE_FILE)
    cert = state["certification"]
    assert cert["task_id"] == "TASK-207"
    assert cert["task_revision"] == 2
    assert cert["status"] == "CERTIFIED_ON_REVIEWED_SOURCE_PUBLICATION"
    assert cert["exact_downstream_pin"] == EXPECTED_PIN
    assert cert["predecessor_main"] == EXPECTED_PREDECESSOR_MAIN
    assert cert["effective_on"] == "REVIEWED_SOURCE_PUBLICATION"
    assert cert["live_evidence_required"] is True

    requirement = PIN_FILE.read_text(encoding="utf-8").strip()
    assert requirement.endswith("@" + EXPECTED_PIN)


def test_certified_binding_families_and_referenced_paths_exist():
    state = load_yaml(CONFORMANCE_FILE)
    families = state["binding_families_under_certification"]

    phase_1 = {item["id"]: item for item in families["phase_1"]}
    assert set(phase_1.keys()) == {
        "RECOVERED_BRAIN_AUTHORING_INGRESS",
        "REPOSITORY_SPECIFIC_PHASE_1_OUTER_AUTOMATION",
        "AUDITED_A1_A2_PRIMARY_WAKEUP_CARRIERS",
        "TERMINAL_ATTENTION_PACKAGE_COMPATIBILITY",
    }
    assert all(item["status"] == "ACTIVE" for item in phase_1.values())

    # Verify referenced Phase-1 paths exist on disk
    assert (REPO_ROOT / phase_1["RECOVERED_BRAIN_AUTHORING_INGRESS"]["carrier"]).is_file()
    assert (REPO_ROOT / phase_1["REPOSITORY_SPECIFIC_PHASE_1_OUTER_AUTOMATION"]["ingress_carrier"]).is_file()
    assert (REPO_ROOT / phase_1["REPOSITORY_SPECIFIC_PHASE_1_OUTER_AUTOMATION"]["wakeup_carrier"]).is_file()
    assert (REPO_ROOT / phase_1["AUDITED_A1_A2_PRIMARY_WAKEUP_CARRIERS"]["workflow"]).is_file()
    assert (REPO_ROOT / phase_1["AUDITED_A1_A2_PRIMARY_WAKEUP_CARRIERS"]["bootstrap"]).is_file()
    assert (REPO_ROOT / phase_1["TERMINAL_ATTENTION_PACKAGE_COMPATIBILITY"]["workflow"]).is_file()
    assert (REPO_ROOT / phase_1["TERMINAL_ATTENTION_PACKAGE_COMPATIBILITY"]["policy"]).is_file()

    phase_2 = {item["id"]: item for item in families["phase_2"]}
    assert set(phase_2.keys()) == {
        "REPOSITORY_SPECIFIC_PHASE_2_OUTER_AUTOMATION",
        "AUDITED_A3_A6_CORRECTION_AUTOMATION_CARRIERS",
    }
    assert all(item["status"] == "ACTIVE" for item in phase_2.values())

    # Verify referenced Phase-2 paths exist on disk
    p2_auto = phase_2["REPOSITORY_SPECIFIC_PHASE_2_OUTER_AUTOMATION"]
    assert (REPO_ROOT / p2_auto["review_to_publication"]["ingress_workflow"]).is_file()
    assert (REPO_ROOT / p2_auto["review_to_publication"]["publish_workflow"]).is_file()
    assert p2_auto["review_to_publication"]["selector"] == "run_id"

    assert (REPO_ROOT / p2_auto["remediation_intent"]["policy"]).is_file()
    assert (REPO_ROOT / p2_auto["remediation_intent"]["carrier_workflow"]).is_file()
    assert (REPO_ROOT / p2_auto["remediation_intent"]["self_hosted_workflow"]).is_file()
    assert (REPO_ROOT / p2_auto["remediation_intent"]["bootstrap"]).is_file()

    assert (REPO_ROOT / p2_auto["repair_wakeup"]["policy"]).is_file()
    assert (REPO_ROOT / p2_auto["repair_wakeup"]["carrier_workflow"]).is_file()
    assert (REPO_ROOT / p2_auto["repair_wakeup"]["self_hosted_workflow"]).is_file()
    assert (REPO_ROOT / p2_auto["repair_wakeup"]["bootstrap"]).is_file()

    a3_a6 = phase_2["AUDITED_A3_A6_CORRECTION_AUTOMATION_CARRIERS"]
    assert a3_a6["authority_boundaries"] == {
        "a3_exact_approval": "PINNED_SEPARATE_AUTHORITY",
        "a6_durable_dispatch": "PINNED_SEPARATE_AUTHORITY",
    }


def test_fallback_and_emergency_posture_is_bounded():
    state = load_yaml(CONFORMANCE_FILE)
    posture = state["fallback_and_emergency_posture"]
    assert posture["local_brain_ingress"]["role"] == "EMERGENCY_DEBUG_FALLBACK"
    assert (REPO_ROOT / posture["local_brain_ingress"]["script"]).is_file()

    assert posture["human_facing_workers"]["role"] == "EMERGENCY_DEBUG_LOCAL_FALLBACK"
    assert (REPO_ROOT / posture["human_facing_workers"]["antigravity_workflow"]).is_file()
    assert (REPO_ROOT / posture["human_facing_workers"]["codex_skill"]).is_file()

    assert posture["direct_operator_paths"]["role"] == "BOUNDED_DEBUG_ESCAPE_HATCHES"


def test_live_evidence_requirements_structure():
    state = load_yaml(CONFORMANCE_FILE)
    evidence_reqs = state["live_evidence_requirements"]
    assert set(evidence_reqs.keys()) == {"ac1", "ac2", "ac3", "ac4", "ac5", "ac6"}
    for ac_key in ("ac1", "ac2", "ac3", "ac4", "ac5", "ac6"):
        entry = evidence_reqs[ac_key]
        assert "carrier" in entry
        assert "action" in entry
        assert entry["evaluation"] == "REVIEWER_OBSERVATION"
    assert evidence_reqs["ac1"]["target_predecessor_main"] == EXPECTED_PREDECESSOR_MAIN


def test_conformance_state_contains_no_secrets_tokens_or_mutable_state():
    text = CONFORMANCE_FILE.read_text(encoding="utf-8")
    for forbidden in (
        "ghp_",
        "github_pat_",
        "Bearer ",
        "token:",
        "password:",
        "secret:",
        "runner/work",
    ):
        assert forbidden.lower() not in text.lower(), f"Forbidden pattern '{forbidden}' found in conformance state"
    assert not re.search(r"[\/\\]_work[\/\\]", text), "Transient runner _work path found in conformance state"


def test_conformance_consistency_with_adoption_and_roadmap():
    conf_state = load_yaml(CONFORMANCE_FILE)
    adopt_state = load_yaml(ADOPTION_FILE)
    road_state = load_yaml(ROADMAP_FILE)

    assert adopt_state["conformance_certification"]["task_id"] == conf_state["certification"]["task_id"]
    assert adopt_state["conformance_certification"]["task_revision"] == conf_state["certification"]["task_revision"]
    assert adopt_state["conformance_certification"]["downstream_pin"] == conf_state["certification"]["exact_downstream_pin"]
    assert adopt_state["conformance_certification"]["conformance_record"] == ".ai/aios-conformance-state.yaml"

    assert road_state["control_plane_conformance"]["migration_task"] == conf_state["certification"]["task_id"]
    assert road_state["control_plane_conformance"]["task_revision"] == conf_state["certification"]["task_revision"]
    assert road_state["control_plane_conformance"]["downstream_pin"] == conf_state["certification"]["exact_downstream_pin"]
    assert road_state["control_plane_conformance"]["status"] == "DONE"

    completed = {item["task_id"]: item for item in road_state["completed_milestones"]}
    assert completed["TASK-207"]["status"] == "DONE"
    assert completed["TASK-207"]["task_revision"] == 2
    assert completed["TASK-207"]["upstream_source_sha"] == conf_state["certification"]["exact_downstream_pin"]
