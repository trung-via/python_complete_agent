"""Focused offline checks for cross-chat roadmap and AIOS-adoption planning state."""
from __future__ import annotations

import re
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ROADMAP_FILE = REPO_ROOT / ".ai" / "roadmap-state.yaml"
P7_2_SEMANTICS_FILE = (
    REPO_ROOT / "docs" / "PHASE_7_P7_2_WINNING_OPPORTUNITY_SEMANTICS.md"
)
ROADMAP_DOCS = (
    REPO_ROOT / "docs" / "POST_M4_PRODUCT_INTELLIGENCE_ROADMAP.md",
    REPO_ROOT / "docs" / "POST_P5_P6_QUALITY_SCALE_ROADMAP.md",
)
ADOPTION_FILE = REPO_ROOT / ".ai" / "aios-adoption-state.yaml"
CONFORMANCE_FILE = REPO_ROOT / ".ai" / "aios-conformance-state.yaml"
PIN_FILE = (
    REPO_ROOT / ".agents" / "skills" / "aios-worker" / "requirements-aios-renew.txt"
)
EXPECTED_PIN = "c96eb8b52acd865b9453409e6598e08a8bd4e48e"
HISTORICAL_TASK_209_PIN = "91a177d5b96b2197a4d8223dbb727dda6201cb64"
HISTORICAL_TASK_208_PIN = "26097405343150dc1b55015b94720528afad50ed"
HISTORICAL_TASK_204_PIN = "652b00b103dd50e2a550dd0ec0fe4063e69631b7"
TASK_201_HISTORICAL_PIN = "f0237a3b98985ce6ebbaf41af1e06fa3eb4e998e"
UPSTREAM_PLANNING_CHECKPOINT = "e95d12122f35bf4e224dbbb28be1866c8250c069"
TASK_192_SOURCE_SHA = "dcb7432abc58ed983e6c26d5456ace1423e49981"
TASK_194_SOURCE_SHA = "e0d8998ee004fda80ca3fbc3de4eb0afb59160a5"
TASK_196_SOURCE_SHA = "4f6d91858c93192f497342315c4650e30b0a2718"
TASK_199_SOURCE_SHA = "702e85e9e77a556f3716717ccaa186919b1a9dab"
TASK_210_SOURCE_SHA = "399ffe4d38d31f7882d22824ba9c27781b9a0974"
TASK_211_SOURCE_SHA = "15cc092d0ea86cd9bce7baed0d32bc3575fa4b08"
ACTIVE_TRACK_ID = "AIOS_FULL_DOWNSTREAM_ADOPTION_AND_GOVERNANCE_REBUILD"
CLOSURE_MILESTONE_ID = "GOVERNANCE_FOUNDATION_CLOSURE_AND_P7_RETURN"
HISTORICAL_CONFORMANCE_NEXT_COMMITMENT = "PROJECT_CONTRACT_REBUILD"


def load_yaml(path: Path) -> dict:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def indexed_families(state: dict) -> dict[str, dict]:
    return {family["id"]: family for family in state["capability_families"]}


def package_capability_for_task(state: dict, task_id: str) -> str:
    matches = [
        family["package_capability_availability"]
        for family in state["capability_families"]
        if task_id in family["upstream_tasks"]
    ]
    assert len(matches) == 1
    return matches[0]


def repository_binding_for_task(state: dict, task_id: str) -> str:
    matches = [
        family["repository_binding_activation"]
        for family in state["capability_families"]
        if task_id in family["upstream_tasks"]
    ]
    assert len(matches) == 1
    return matches[0]


def values_for_key(value: object, key: str) -> list[object]:
    matches: list[object] = []
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            if child_key == key:
                matches.append(child_value)
            matches.extend(values_for_key(child_value, key))
    elif isinstance(value, list):
        for child_value in value:
            matches.extend(values_for_key(child_value, key))
    return matches


def test_roadmap_activates_approved_p7_sequence_with_one_next():
    state = load_yaml(ROADMAP_FILE)
    roadmap_text = ROADMAP_FILE.read_text(encoding="utf-8")
    assert state["authority"] == {
        "owner": "BRAIN",
        "purpose": "CROSS_CHAT_PLANNING_BOOKMARK",
        "engineering_truth": False,
        "auto_advance_from_runtime_or_worker_state": False,
        "priority_change_owner": "HUMAN",
    }
    assert state["product_checkpoint"] == {
        "task_id": "TASK-191",
        "milestone": "P7.1 Real-Evidence Winning Product Coverage Baseline",
        "source_sha": "40da098b3b0dcf3d1994fc510dd55717b81a2f67",
        "status": "DONE",
    }
    assert state["active_track"] == {
        "id": "P7_COMMERCE_OPPORTUNITY_INTELLIGENCE",
        "title": "P7 Commerce Opportunity Intelligence",
        "priority_owner": "HUMAN",
        "status": "ACTIVE",
        "current_milestone": {
            "id": "P7.2",
            "task_id": "TASK-214",
            "title": "Winning Opportunity Semantic Reconciliation",
            "status": "DONE",
            "completion_basis": "PUBLICATION_GATED",
            "effective_only_when": {
                "semantic_review": "PASS",
                "published_source": "EXACT_REVIEWED_CANDIDATE",
                "canonical_main_equals_reviewed_candidate": True,
            },
        },
        "next_milestone": {
            "id": "P7.3",
            "title": "Decision Context + Opportunity Hypothesis",
        },
    }
    assert state["completed_track"] == {
        "id": ACTIVE_TRACK_ID,
        "title": "AIOS Full Downstream Adoption and Governance Rebuild",
        "priority_owner": "HUMAN",
        "status": "DONE",
        "completion_task": "TASK-213",
        "completion_run": "RUN-213-001",
        "predecessor_reconciliation_task": "TASK-212",
        "predecessor_reconciliation_run": "RUN-212-001",
        "predecessor_reconciliation_source_sha": (
            "0205688d7bf8725cf096c06de5c26055919b0340"
        ),
        "completion_basis": "EXACT_REVIEWED_CANDIDATE_PUBLISHED_TO_CANONICAL_MAIN",
        "effective_only_when": {
            "semantic_review": "PASS",
            "published_source": "EXACT_REVIEWED_CANDIDATE",
            "canonical_main_equals_reviewed_candidate": True,
        },
    }
    assert values_for_key(state, "status").count("ACTIVE") == 1
    assert state["roadmap_sources"] == [
        "docs/POST_M4_PRODUCT_INTELLIGENCE_ROADMAP.md",
        "docs/POST_P5_P6_QUALITY_SCALE_ROADMAP.md",
    ]
    assert values_for_key(state, "status").count("NEXT") == 1
    assert state["pending_commitments"] == [
        {
            "id": "P7.3",
            "title": "Decision Context + Opportunity Hypothesis",
            "status": "NEXT",
        },
        {
            "id": "P7.4",
            "title": "TikTok Affiliate Evidence Profile",
            "status": "NOT_DONE",
        },
        {
            "id": "P7.5",
            "title": "Value-of-Information Planning",
            "status": "NOT_DONE",
        },
        {
            "id": "P7.6",
            "title": "Market Test / Funnel Evidence",
            "status": "NOT_DONE",
        },
        {
            "id": "P7.7",
            "title": "Calibration & Winner Validation",
            "status": "NOT_DONE",
        },
    ]
    assert values_for_key(state, "status").count("NOT_DONE") == 4
    assert state["planning_handoff"] == {
        "destination": "P7_PRODUCT_ROADMAP",
        "checkpoint_task_id": "TASK-191",
        "status": "INTERPRETED_BY_BRAIN_AND_HUMAN",
        "selected_post_p7_1_implementation": (
            "P7.2_WINNING_OPPORTUNITY_SEMANTIC_RECONCILIATION"
        ),
        "boundary": (
            "Governance Foundation closure returned planning authority to the existing P7 "
            "product roadmap at the completed P7.1 checkpoint. Brain/Human interpretation "
            "selected P7.2 semantic reconciliation without reinterpreting TASK-191 or "
            "changing TASK-213 history."
        ),
    }
    assert "TASK-119" not in [item["id"] for item in state["pending_commitments"]]
    assert "TASK-120" not in [item["id"] for item in state["pending_commitments"]]

    superseded = {item["id"]: item for item in state.get("superseded_commitments", [])}
    assert (
        superseded["CHATGPT_PROJECT_CONTRACT_RECONCILIATION"]["status"]
        == "SUPERSEDED"
    )


def test_p7_2_semantics_preserve_triage_evidence_and_history_boundaries():
    text = P7_2_SEMANTICS_FILE.read_text(encoding="utf-8")
    stages = re.findall(
        r"^\d+\. \*\*([A-Z_]+)\*\*", text, flags=re.MULTILINE
    )
    assert stages == [
        "DISCOVERED_CANDIDATE",
        "OPPORTUNITY_HYPOTHESIS",
        "TEST_READY",
        "VALIDATED_WINNER",
        "SCALABLE_WINNER",
    ]
    for required in (
        "Product Contract v2",
        "Product Candidate Triage V1",
        "not a universal market-winner predictor",
        "market pull and unmet demand",
        "momentum and timing",
        "product quality and trust",
        "audience and creator fit",
        "offer and economics",
        "creative and content leverage",
        "competition, content gap, and differentiation",
        "operational feasibility",
        "Missingness identifies an unknown",
        "itself authorize collection",
        "An outcome is not causal attribution",
        "One favorable result does not establish scalability",
        "40da098b3b0dcf3d1994fc510dd55717b81a2f67",
        "bounded search-card surface",
        "insufficient for",
        "the current scorer",
        "exact AIOS-renew pin",
    ):
        assert required in text

    for roadmap_path in ROADMAP_DOCS:
        roadmap = roadmap_path.read_text(encoding="utf-8")
        assert "P7 Commerce Opportunity Intelligence" in roadmap
        assert "P7.2 Winning Opportunity Semantic Reconciliation" in roadmap
        assert roadmap.count("P7.3 Decision Context + Opportunity Hypothesis — NEXT") == 1
        for milestone in ("P7.4", "P7.5", "P7.6", "P7.7"):
            assert f"{milestone} " in roadmap
        assert roadmap.count("— NOT_DONE") >= 4


def test_roadmap_records_exact_completion_provenance_and_recovered_upstream_work():
    state = load_yaml(ROADMAP_FILE)
    completed = {
        item["task_id"]: item for item in state["completed_milestones"]
    }
    assert completed["TASK-192"] == {
        "task_id": "TASK-192",
        "track_id": "AIOS_DOWNSTREAM_PARITY",
        "title": "Canonical downstream AIOS adoption baseline",
        "status": "DONE",
        "source_sha": TASK_192_SOURCE_SHA,
    }
    assert completed["TASK-194"] == {
        "task_id": "TASK-194",
        "track_id": "PYTHON_AGENT_GOVERNANCE_FOUNDATION",
        "milestone_id": "PYTHON_AGENT_MANIFESTO",
        "title": "Python Agent Manifesto",
        "status": "DONE",
        "source_sha": TASK_194_SOURCE_SHA,
    }
    assert completed["TASK-196"] == {
        "task_id": "TASK-196",
        "track_id": "PYTHON_AGENT_GOVERNANCE_FOUNDATION",
        "milestone_id": "PYTHON_AGENT_CONSTITUTION",
        "title": "Python Agent Constitution",
        "status": "DONE",
        "source_sha": TASK_196_SOURCE_SHA,
    }
    assert completed["TASK-199"] == {
        "task_id": "TASK-199",
        "track_id": "PYTHON_AGENT_GOVERNANCE_FOUNDATION",
        "milestone_id": "PYTHON_AGENT_PRODUCT_CONTRACT",
        "title": "Python Agent Product Contract",
        "status": "DONE",
        "source_sha": TASK_199_SOURCE_SHA,
    }
    assert completed["TASK-204"] == {
        "task_id": "TASK-204",
        "track_id": ACTIVE_TRACK_ID,
        "milestone_id": "AIOS_DOWNSTREAM_ADOPTION_POLICY_RECONCILIATION",
        "title": "AIOS downstream-adoption policy reconciliation",
        "status": "DONE",
        "upstream_source_sha": HISTORICAL_TASK_204_PIN,
        "boundary": "NO_PHASE_1_OR_PHASE_2_REPOSITORY_BINDING_ACTIVATED",
    }
    assert completed["TASK-205"] == {
        "task_id": "TASK-205",
        "track_id": ACTIVE_TRACK_ID,
        "milestone_id": "FULL_AIOS_CONTROL_PLANE_ADOPTION_PHASE_1",
        "title": "Full AIOS control plane adoption phase 1 (authoring, PRIMARY, terminal-attention)",
        "status": "DONE",
        "upstream_source_sha": HISTORICAL_TASK_204_PIN,
        "phase_1_bindings": {
            "authoring_ingress": "ACTIVE",
            "primary_wakeup": "ACTIVE",
            "terminal_attention": "ACTIVE",
        },
    }
    assert completed["TASK-206"] == {
        "task_id": "TASK-206",
        "track_id": ACTIVE_TRACK_ID,
        "milestone_id": "FULL_AIOS_CONTROL_PLANE_ADOPTION_PHASE_2",
        "title": "Full AIOS control plane adoption phase 2 (review, publication, remediation, repair)",
        "status": "DONE",
        "upstream_source_sha": HISTORICAL_TASK_204_PIN,
        "phase_2_bindings": {
            "review_to_publication": "ACTIVE",
            "remediation_intent_a3_a6": "ACTIVE",
            "repair_wakeup": "ACTIVE",
        },
        "boundary": "DOES_NOT_CLAIM_FULL_AIOS_DOWNSTREAM_CONFORMANCE",
    }
    assert completed["TASK-207"] == {
        "task_id": "TASK-207",
        "task_revision": 3,
        "track_id": ACTIVE_TRACK_ID,
        "milestone_id": "FULL_AIOS_DOWNSTREAM_CONFORMANCE",
        "title": "Full AIOS downstream control plane conformance gate",
        "status": "DONE",
        "downstream_pin": HISTORICAL_TASK_209_PIN,
        "certification_record": ".ai/aios-conformance-state.yaml",
        "effective_only_when": {
            "semantic_review": "PASS",
            "published_source": "EXACT_REVIEWED_CANDIDATE",
            "canonical_main_equals_reviewed_candidate": True,
        },
        "boundary": (
            "DONE is publication-gated and does not become effective from source "
            "candidacy, Runtime PASS, or Reviewer PASS alone. It does not rebuild or "
            "approve a Project Contract, close Governance Foundation, or return the "
            "product roadmap to P7."
        ),
    }
    assert completed["TASK-210"] == {
        "task_id": "TASK-210",
        "track_id": ACTIVE_TRACK_ID,
        "milestone_id": "PROJECT_CONTRACT_REBUILD",
        "title": "Project Contract v2",
        "status": "DONE",
        "run_id": "RUN-210-002",
        "review": "REVIEW-210-001",
        "review_outcome": "PRIMARY_PASS",
        "source_sha": TASK_210_SOURCE_SHA,
        "completion_basis": "EXACT_REVIEWED_CANDIDATE_PUBLISHED_TO_CANONICAL_MAIN",
    }
    assert completed["TASK-211"] == {
        "task_id": "TASK-211",
        "track_id": ACTIVE_TRACK_ID,
        "milestone_id": "PYTHON_AGENT_PRODUCT_CONTRACT_V2",
        "title": "Product Contract v2 — Intelligent Commerce",
        "status": "DONE",
        "run_id": "RUN-211-001",
        "review": "REVIEW-211-001",
        "review_outcome": "PRIMARY_PASS",
        "source_sha": TASK_211_SOURCE_SHA,
        "authority_status": "CURRENT_PRODUCT_CONTRACT",
        "historical_predecessor": "TASK-199",
    }
    assert completed["TASK-213"] == {
        "task_id": "TASK-213",
        "track_id": ACTIVE_TRACK_ID,
        "milestone_id": CLOSURE_MILESTONE_ID,
        "title": "Governance Foundation closure and return to P7 product roadmap",
        "status": "DONE",
        "run_id": "RUN-213-001",
        "completion_basis": "EXACT_REVIEWED_CANDIDATE_PUBLISHED_TO_CANONICAL_MAIN",
        "roadmap_handoff": "BRAIN_HUMAN_INTERPRETATION_AFTER_P7_1",
        "selected_post_p7_1_implementation": None,
    }
    assert state["current_governance_authorities"]["product_contract"] == {
        "document": "docs/PYTHON_AGENT_PRODUCT_CONTRACT.md",
        "version": 2,
        "title": "Product Contract v2 — Intelligent Commerce",
        "task_id": "TASK-211",
        "run_id": "RUN-211-001",
        "review": "REVIEW-211-001",
        "review_outcome": "PRIMARY_PASS",
        "source_sha": TASK_211_SOURCE_SHA,
        "authority_status": "CURRENT",
        "historical_predecessor": {
            "task_id": "TASK-199",
            "status": "PRESERVED_COMPLETED_HISTORY",
        },
    }

    upstream = state["upstream_recovery"]
    assert upstream["status"] == "ADOPTED_BY_PIN"
    assert upstream["blocking_current_track"] is False
    assert upstream["recovery_kind"] == "NON_PRODUCT_CONTROL_PLANE"
    assert upstream["recovery_task"] == "TASK-198"
    assert [item["task_id"] for item in upstream["items"]] == [
        "TASK-101",
        "TASK-103",
    ]
    assert all(
        item["status"] == "ADOPTED_BY_PIN"
        and item["blocking_current_track"] is False
        for item in upstream["items"]
    )
    assert upstream["downstream_pin"] == "a3b723b49cd65677f548c5694a52a6fc006a9e2a"
    assert "does not advance" in upstream["roadmap_effect"]

    migration = state["historical_upstream_migration"]
    assert migration["status"] == "SUPERSEDED_PIN_HISTORY"
    assert migration["blocking_current_track"] is False
    assert migration["migration_kind"] == "NON_PRODUCT_AIOS_MIGRATION"
    assert migration["migration_task"] == "TASK-201"
    assert migration["historical_downstream_pin"] == TASK_201_HISTORICAL_PIN
    assert migration["runtime_authority"] is False
    assert migration["superseded_by"] == "TASK-204"
    assert "does not advance" in migration["roadmap_effect"]

    reconciliation = state["adoption_policy_reconciliation"]
    assert reconciliation["status"] == "DONE"
    assert reconciliation["migration_task"] == "TASK-204"
    assert reconciliation["downstream_pin"] == HISTORICAL_TASK_204_PIN
    assert reconciliation["upstream_provenance"] == [
        "TASK-114", "TASK-115", "TASK-116",
    ]
    assert reconciliation["closed_commitment"] == (
        "AIOS_DOWNSTREAM_ADOPTION_POLICY_RECONCILIATION"
    )
    assert reconciliation["next_commitment"] == (
        "FULL_AIOS_CONTROL_PLANE_ADOPTION_PHASE_1"
    )
    assert reconciliation["repository_binding_activation"] == "NONE"
    assert "does not implement" in reconciliation["roadmap_effect"]

    phase_1 = state["control_plane_adoption_phase_1"]
    assert phase_1["status"] == "DONE"
    assert phase_1["migration_task"] == "TASK-205"
    assert phase_1["downstream_pin"] == HISTORICAL_TASK_204_PIN
    assert phase_1["closed_commitment"] == (
        "FULL_AIOS_CONTROL_PLANE_ADOPTION_PHASE_1"
    )
    assert phase_1["next_commitment"] == "FULL_AIOS_CONTROL_PLANE_ADOPTION_PHASE_2"
    assert phase_1["repository_binding_activation"] == "PHASE_1_ACTIVE"
    assert "Closes Phase 1" in phase_1["roadmap_effect"]

    phase_2 = state["control_plane_adoption_phase_2"]
    assert phase_2["status"] == "DONE"
    assert phase_2["migration_task"] == "TASK-206"
    assert phase_2["downstream_pin"] == HISTORICAL_TASK_204_PIN
    assert phase_2["closed_commitment"] == "FULL_AIOS_CONTROL_PLANE_ADOPTION_PHASE_2"
    assert phase_2["next_commitment"] == "FULL_AIOS_DOWNSTREAM_CONFORMANCE"
    assert phase_2["repository_binding_activation"] == "PHASE_2_ACTIVE"
    assert "does not claim that conformance" in phase_2["roadmap_effect"]

    historical_prereq = state["historical_prerequisite_pin_migration"]
    assert historical_prereq["status"] == "DONE"
    assert historical_prereq["migration_task"] == "TASK-208"
    assert historical_prereq["downstream_pin"] == HISTORICAL_TASK_208_PIN
    assert historical_prereq["prior_pin"] == HISTORICAL_TASK_204_PIN
    assert historical_prereq["repository_binding_activation"] == "NONE"

    prereq = state["prerequisite_pin_migration"]
    assert prereq["status"] == "DONE"
    assert prereq["migration_task"] == "TASK-209"
    assert prereq["downstream_pin"] == HISTORICAL_TASK_209_PIN
    assert prereq["prior_pin"] == HISTORICAL_TASK_208_PIN
    assert prereq["prior_migration_task"] == "TASK-208"
    assert prereq["prerequisite_for"] == "FULL_AIOS_DOWNSTREAM_CONFORMANCE"
    assert prereq["resume_target"]["task_id"] == "TASK-207"
    assert prereq["resume_target"]["commitment_id"] == (
        "FULL_AIOS_DOWNSTREAM_CONFORMANCE"
    )
    assert prereq["resume_target"]["requires_fresh_brain_revision"] is True
    assert prereq["resume_target"]["supersedes_task_revision"] == 2
    assert prereq["immutable_old_pin_lineage"] == {
        "task_revision": "TASK-207-REVISION-2",
        "runs": ["RUN-207-001", "RUN-207-002"],
        "repair": "REPAIR-207-001",
        "certification_authority_for_new_pin": False,
    }
    assert prereq["repository_binding_activation"] == "NONE"
    assert "second bounded prerequisite pin migration" in prereq["roadmap_effect"]

    recovery = state["control_plane_recovery_prerequisite"]
    assert recovery["status"] == "DONE"
    assert recovery["migration_task"] == "TASK-216"
    assert recovery["downstream_pin"] == EXPECTED_PIN
    assert recovery["prior_pin"] == HISTORICAL_TASK_209_PIN
    assert recovery["prerequisite_for"] == (
        "FULL_AIOS_DOWNSTREAM_CONFORMANCE_FRESH_CERTIFICATION"
    )
    assert recovery["preserved_task_215_lineage"] == {
        "task_id": "TASK-215",
        "task_revision": 1,
        "runs": ["RUN-215-001", "RUN-215-002"],
        "product_milestone": "P7.3",
        "disposition": "IMMUTABLE_CORRECTION_LINEAGE",
    }
    assert recovery["conformance_status"] == "PENDING_FRESH_CERTIFICATION"

    assert state["authority"]["owner"] == "BRAIN"
    assert state["authority"]["auto_advance_from_runtime_or_worker_state"] is False

    conformance = state["full_downstream_conformance"]
    assert conformance["status"] == "DONE"
    assert conformance["task_id"] == "TASK-207"
    assert conformance["task_revision"] == 3
    assert conformance["downstream_pin"] == HISTORICAL_TASK_209_PIN
    assert conformance["effective_only_when"] == {
        "semantic_review": "PASS",
        "published_source": "EXACT_REVIEWED_CANDIDATE",
        "canonical_main_equals_reviewed_candidate": True,
    }
    assert conformance["next_commitment"] == HISTORICAL_CONFORMANCE_NEXT_COMMITMENT
    assert conformance["fresh_certification_required"] is True
    assert conformance["fresh_certification_pin"] == EXPECTED_PIN


def test_adoption_registry_pin_audit_authority_and_dimensions_are_explicit():
    state = load_yaml(ADOPTION_FILE)
    conformance = load_yaml(CONFORMANCE_FILE)
    requirement = PIN_FILE.read_text(encoding="utf-8").strip()
    assert requirement.endswith("@" + EXPECTED_PIN)
    assert state["downstream_pin"]["commit"] == EXPECTED_PIN
    assert state["upstream_audit"]["checkpoint"] == EXPECTED_PIN
    assert state["upstream_audit"]["through_authored_task"] == "TASK-129"
    assert (
        state["upstream_audit"]["checkpoint_role"]
        == "REVIEWED_SOURCE_PUBLISHED_PROVENANCE"
    )
    assert state["upstream_audit"]["checkpoint_is_runtime_authority"] is False
    assert state["upstream_audit"]["review"] == "REVIEW-129-001"
    assert state["upstream_audit"]["review_outcome"] == "PRIMARY_PASS"
    assert state["upstream_audit"]["source_published"] is True
    assert (
        state["upstream_audit"]["prior_planning_checkpoint"]
        == HISTORICAL_TASK_209_PIN
    )
    provenance_tasks = [
        p["task_id"] for p in state["upstream_audit"]["provenance"]
    ]
    assert provenance_tasks == [
        "TASK-114",
        "TASK-115",
        "TASK-116",
        "TASK-117",
        "TASK-118",
        "TASK-119",
        "TASK-120",
        "TASK-121",
        "TASK-122",
        "TASK-123",
        "TASK-124",
        "TASK-125",
        "TASK-126",
        "TASK-127",
        "TASK-128",
        "TASK-129",
    ]
    task_127_p = next(
        p
        for p in state["upstream_audit"]["provenance"]
        if p["task_id"] == "TASK-127"
    )
    assert task_127_p["activates_repository_binding"] is True
    assert state["authority"]["engineering_truth"] is False
    assert state["full_downstream_conformance"] == {
        "status": "PENDING_FRESH_CERTIFICATION",
        "conformance_for_current_pin": "NOT_CURRENT",
        "current_pin": EXPECTED_PIN,
        "historical_certification": {
            "task_id": "TASK-207",
            "revision": 3,
            "downstream_pin": HISTORICAL_TASK_209_PIN,
            "certification_record": ".ai/aios-conformance-state.yaml",
            "status": "CERTIFIED_ON_HISTORICAL_PIN",
        },
        "effective_only_when": {
            "semantic_review": "PASS",
            "published_source": "EXACT_REVIEWED_CANDIDATE",
            "canonical_main_equals_reviewed_candidate": True,
        },
        "before_gate": "NOT_EFFECTIVE",
        "binding_classifications_changed": False,
        "boundary": (
            "Historical TASK-207 revision-3 conformance was certified under 91a177d5b96b2197a4d8223dbb727dda6201cb64. "
            "Following migration to c96eb8b52acd865b9453409e6598e08a8bd4e48e, fresh full downstream "
            "conformance certification is pending and not current until authored, reviewed, and published "
            "under the new pin."
        ),
    }
    assert conformance["authority"] == {
        "owner": "BRAIN_REVIEW",
        "purpose": "PUBLICATION_GATED_DOWNSTREAM_CERTIFICATION",
        "runtime_truth_store": False,
        "evidence_store": False,
        "grants_lifecycle_authority": False,
    }
    assert conformance["certification"] == {
        "task_id": "TASK-207",
        "task_revision": 3,
        "downstream_pin": HISTORICAL_TASK_209_PIN,
        "status": "CERTIFIED_ON_REVIEWED_SOURCE_PUBLICATION",
        "effective_only_when": {
            "semantic_review": "PASS",
            "review_mode": "PRIMARY",
            "published_source": "EXACT_REVIEWED_CANDIDATE",
            "canonical_main_equals_reviewed_candidate": True,
        },
        "before_gate": "NOT_EFFECTIVE",
        "boundary": (
            "Runtime PASS and Reviewer PASS do not by themselves make this certification "
            "effective. The safe Publisher must publish exactly the TASK-207 revision-3 "
            "reviewed source candidate, and canonical main must equal that candidate."
        ),
    }
    assert conformance["historical_exclusions"] == {
        "old_pin_task_revision": "TASK-207-REVISION-2",
        "runs": ["RUN-207-001", "RUN-207-002"],
        "repair": "REPAIR-207-001",
        "certification_authority_for_current_pin": False,
    }
    dimensions = state["classification_dimensions"]
    assert set(dimensions["package_capability_availability"]) == {
        "ADOPTED_BY_PIN",
        "PORT_GOVERNANCE",
        "BLOCKED_PENDING_UPSTREAM",
    }
    assert set(dimensions["repository_binding_activation"]) == {
        "ACTIVE",
        "REQUIRED_PENDING",
        "NOT_REQUIRED",
    }


def test_relevant_upstream_tasks_have_distinct_package_and_binding_dimensions():
    state = load_yaml(ADOPTION_FILE)

    all_audited_tasks = [
        "TASK-064", "TASK-065", "TASK-066", "TASK-067", "TASK-068", "TASK-069",
        "TASK-070", "TASK-071", "TASK-072", "TASK-073", "TASK-074", "TASK-075",
        "TASK-076", "TASK-077", "TASK-078", "TASK-079", "TASK-080", "TASK-081",
        "TASK-083", "TASK-084", "TASK-085", "TASK-086", "TASK-087", "TASK-088",
        "TASK-089", "TASK-090", "TASK-091", "TASK-092", "TASK-093", "TASK-094",
        "TASK-095", "TASK-096", "TASK-097", "TASK-098", "TASK-099", "TASK-100",
        "TASK-101", "TASK-102", "TASK-103", "TASK-104", "TASK-105", "TASK-106",
        "TASK-107", "TASK-108", "TASK-110", "TASK-111", "TASK-112", "TASK-113",
        "TASK-114", "TASK-115", "TASK-116", "TASK-117", "TASK-118",
        "TASK-119", "TASK-120", "TASK-121", "TASK-122", "TASK-123",
        "TASK-124", "TASK-125", "TASK-126", "TASK-127", "TASK-128",
        "TASK-129",
    ]

    for task_id in all_audited_tasks:
        pkg_cap = package_capability_for_task(state, task_id)
        if task_id in ("TASK-083", "TASK-114", "TASK-116"):
            assert pkg_cap == "PORT_GOVERNANCE"
        else:
            assert pkg_cap == "ADOPTED_BY_PIN"

    assert repository_binding_for_task(state, "TASK-069") == "NOT_REQUIRED"
    assert repository_binding_for_task(state, "TASK-071") == "NOT_REQUIRED"

    assert repository_binding_for_task(state, "TASK-070") == "NOT_REQUIRED"
    assert repository_binding_for_task(state, "TASK-072") == "NOT_REQUIRED"

    for task_id in ("TASK-066", "TASK-068", "TASK-073"):
        assert repository_binding_for_task(state, task_id) == "ACTIVE"
    for task_id in ("TASK-074", "TASK-084"):
        assert repository_binding_for_task(state, task_id) == "ACTIVE"

    assert repository_binding_for_task(state, "TASK-104") == "ACTIVE"
    assert repository_binding_for_task(state, "TASK-105") == "ACTIVE"

    for task_id in ("TASK-107", "TASK-108"):
        assert repository_binding_for_task(state, task_id) == "ACTIVE"
    for task_id in ("TASK-110", "TASK-111", "TASK-112"):
        assert repository_binding_for_task(state, task_id) == "ACTIVE"

    assert repository_binding_for_task(state, "TASK-113") == "ACTIVE"
    assert repository_binding_for_task(state, "TASK-114") == "NOT_REQUIRED"
    assert repository_binding_for_task(state, "TASK-115") == "NOT_REQUIRED"
    assert repository_binding_for_task(state, "TASK-116") == "NOT_REQUIRED"
    assert repository_binding_for_task(state, "TASK-117") == "NOT_REQUIRED"
    assert repository_binding_for_task(state, "TASK-118") == "NOT_REQUIRED"
    for task_id in (
        "TASK-119",
        "TASK-120",
        "TASK-121",
        "TASK-122",
        "TASK-123",
        "TASK-124",
        "TASK-125",
        "TASK-126",
        "TASK-128",
        "TASK-129",
    ):
        assert repository_binding_for_task(state, task_id) == "NOT_REQUIRED"
    assert repository_binding_for_task(state, "TASK-127") == "ACTIVE"

    families = indexed_families(state)

    assert families["PACKAGE_RUNTIME_OPERATOR_HARDENING"]["upstream_tasks"] == [
        "TASK-069", "TASK-071",
    ]
    assert families["PACKAGE_PUBLICATION_CONTROL_HARDENING"]["upstream_tasks"] == [
        "TASK-070", "TASK-072",
    ]

    assert families["AUDITED_A1_A2_PRIMARY_WAKEUP_CARRIERS"]["upstream_tasks"] == [
        "TASK-066", "TASK-068", "TASK-073",
    ]
    assert families["AUDITED_A1_A2_PRIMARY_WAKEUP_CARRIERS"]["repository_binding_activation"] == "ACTIVE"
    assert families["AUDITED_A3_A6_CORRECTION_AUTOMATION_CARRIERS"]["upstream_tasks"] == [
        "TASK-074", "TASK-084",
    ]
    assert families["AUDITED_A3_A6_CORRECTION_AUTOMATION_CARRIERS"]["repository_binding_activation"] == "ACTIVE"
    assert families["AUDITED_A3_A6_CORRECTION_AUTOMATION_CARRIERS"]["authority_boundaries"] == {
        "a3_exact_approval": "PINNED_SEPARATE_AUTHORITY",
        "a6_durable_dispatch": "PINNED_SEPARATE_AUTHORITY",
    }

    ingress = families["RECOVERED_BRAIN_AUTHORING_INGRESS"]
    assert ingress["upstream_tasks"] == ["TASK-104", "TASK-105"]
    assert ingress["carrier"] == ".agents/skills/aios-worker/scripts/aios_brain_ingress.py"
    assert ingress["repository_binding_activation"] == "ACTIVE"

    assert families["REPOSITORY_SPECIFIC_PHASE_1_OUTER_AUTOMATION"]["upstream_tasks"] == [
        "TASK-107", "TASK-108",
    ]
    assert families["REPOSITORY_SPECIFIC_PHASE_1_OUTER_AUTOMATION"]["repository_binding_activation"] == "ACTIVE"
    assert families["REPOSITORY_SPECIFIC_PHASE_2_OUTER_AUTOMATION"]["upstream_tasks"] == [
        "TASK-110", "TASK-111", "TASK-112",
    ]
    phase_2_family = families["REPOSITORY_SPECIFIC_PHASE_2_OUTER_AUTOMATION"]
    assert phase_2_family["repository_binding_activation"] == "ACTIVE"
    assert phase_2_family["review_to_publication"]["selector"] == "run_id"
    assert phase_2_family["remediation_intent"]["status"] == "ACTIVE"
    assert phase_2_family["repair_wakeup"]["status"] == "ACTIVE"
    assert families["TERMINAL_ATTENTION_PACKAGE_COMPATIBILITY"]["upstream_tasks"] == [
        "TASK-113",
    ]
    assert families["TERMINAL_ATTENTION_PACKAGE_COMPATIBILITY"]["repository_binding_activation"] == "ACTIVE"
    safe_publication = families["SAFE_PUBLICATION_ZERO_DELTA_HARDENING"]
    assert safe_publication["upstream_tasks"] == ["TASK-115"]
    assert safe_publication["package_capability_availability"] == "ADOPTED_BY_PIN"
    assert safe_publication["repository_binding_activation"] == "NOT_REQUIRED"

    policy = families["DOWNSTREAM_PORTABILITY_POLICY_PROVENANCE"]
    assert policy["upstream_tasks"] == ["TASK-114", "TASK-116"]
    assert policy["package_capability_availability"] == "PORT_GOVERNANCE"
    assert policy["repository_binding_activation"] == "NOT_REQUIRED"

    carrier_portability = families["CARRIER_PORTABILITY_HARDENING"]
    assert carrier_portability["upstream_tasks"] == ["TASK-117"]
    assert carrier_portability["package_capability_availability"] == "ADOPTED_BY_PIN"
    assert carrier_portability["repository_binding_activation"] == "NOT_REQUIRED"

    terminal_portability = families["TERMINAL_ATTENTION_PORTABILITY_HARDENING"]
    assert terminal_portability["upstream_tasks"] == ["TASK-118"]
    assert terminal_portability["package_capability_availability"] == "ADOPTED_BY_PIN"
    assert terminal_portability["repository_binding_activation"] == "NOT_REQUIRED"
    assert terminal_portability["review"] == "REVIEW-118-001"

    repair_utf8 = families["REPAIR_ISOLATION_AND_WINDOWS_UTF8_HARDENING"]
    assert repair_utf8["upstream_tasks"] == ["TASK-119", "TASK-120"]
    assert repair_utf8["package_capability_availability"] == "ADOPTED_BY_PIN"
    assert repair_utf8["repository_binding_activation"] == "NOT_REQUIRED"

    sync_snapshots = families["CANONICAL_BRAIN_SYNC_SNAPSHOTS"]
    assert sync_snapshots["upstream_tasks"] == ["TASK-121", "TASK-128"]
    assert sync_snapshots["package_capability_availability"] == "ADOPTED_BY_PIN"
    assert sync_snapshots["repository_binding_activation"] == "NOT_REQUIRED"

    response_loss = families["NATIVE_TERMINAL_RESPONSE_LOSS_RECOVERY"]
    assert response_loss["upstream_tasks"] == ["TASK-122"]
    assert response_loss["package_capability_availability"] == "ADOPTED_BY_PIN"
    assert response_loss["repository_binding_activation"] == "NOT_REQUIRED"

    repair_supersession = families[
        "REPAIR_AUTHORIZATION_SUPERSESSION_AND_LINEAGE_HARDENING"
    ]
    assert repair_supersession["upstream_tasks"] == [
        "TASK-123",
        "TASK-124",
        "TASK-125",
    ]
    assert (
        repair_supersession["package_capability_availability"]
        == "ADOPTED_BY_PIN"
    )
    assert (
        repair_supersession["repository_binding_activation"]
        == "NOT_REQUIRED"
    )

    antigravity_transport = families[
        "ANTIGRAVITY_READ_ONLY_COMPLETION_TRANSPORT"
    ]
    assert antigravity_transport["upstream_tasks"] == ["TASK-126"]
    assert (
        antigravity_transport["package_capability_availability"]
        == "ADOPTED_BY_PIN"
    )
    assert (
        antigravity_transport["repository_binding_activation"]
        == "NOT_REQUIRED"
    )

    post_canonical_repair = families["POST_CANONICALIZATION_REPAIR_HANDOFF"]
    assert post_canonical_repair["upstream_tasks"] == ["TASK-127"]
    assert (
        post_canonical_repair["package_capability_availability"]
        == "ADOPTED_BY_PIN"
    )
    assert (
        post_canonical_repair["repository_binding_activation"] == "ACTIVE"
    )
    assert (
        post_canonical_repair["carrier"]
        == ".github/workflows/aios-brain-ingress.yml"
    )
    assert (
        post_canonical_repair["dispatch_target"]
        == ".github/workflows/aios-self-hosted-repair-wakeup.yml"
    )

    repair_after_remediation = families["REPAIR_AFTER_FAILED_REMEDIATION"]
    assert repair_after_remediation["upstream_tasks"] == ["TASK-129"]
    assert (
        repair_after_remediation["package_capability_availability"]
        == "ADOPTED_BY_PIN"
    )
    assert (
        repair_after_remediation["repository_binding_activation"]
        == "NOT_REQUIRED"
    )


def test_task_197_malformed_decision_remains_incident_only():
    state = load_yaml(ADOPTION_FILE)
    assert state["incident_lineage"] == {
        "run_id": "RUN-197-001",
        "task_revision": 1,
        "candidate": "8992e64654b1342a70ad37c9c0aa693ce537a975",
        "review": "REVIEW-197-001",
        "semantic_review": "PASS",
        "malformed_decision": "f334312384543dd4726e83089601e375dd5da17b",
        "disposition": "IMMUTABLE_NOT_PUBLICATION_AUTHORITY",
        "resumed": False,
    }
