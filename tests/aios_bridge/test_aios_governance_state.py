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
P7_3_SEMANTICS_FILE = (
    REPO_ROOT
    / "docs"
    / "PHASE_7_P7_3_DECISION_CONTEXT_OPPORTUNITY_HYPOTHESIS.md"
)
P7_4_SEMANTICS_FILE = (
    REPO_ROOT
    / "docs"
    / "PHASE_7_P7_4_TIKTOK_AFFILIATE_EVIDENCE_PROFILE.md"
)
P7_5_SEMANTICS_FILE = (
    REPO_ROOT
    / "docs"
    / "PHASE_7_P7_5_VALUE_OF_INFORMATION_PLANNING.md"
)
P7_6_SEMANTICS_FILE = (
    REPO_ROOT
    / "docs"
    / "PHASE_7_P7_6_MARKET_TEST_FUNNEL_EVIDENCE.md"
)
P7_7_SEMANTICS_FILE = (
    REPO_ROOT
    / "docs"
    / "PHASE_7_P7_7_CALIBRATION_WINNER_VALIDATION.md"
)
P8_0_COMPOSITION_FILE = (
    REPO_ROOT
    / "docs"
    / "PHASE_8_P8_0_REAL_COMMERCE_DECISION_COMPOSITION.md"
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
ACTIVE_PIN = "edd7d8d92d54900c56442bbfcddb8648ec4d2e09"
PRIOR_CERTIFIED_PIN = "49ad4d7a1e57a4c25ba44e60589d8320cb0f57b2"
HISTORICAL_TASK_218_PIN = "49ad4d7a1e57a4c25ba44e60589d8320cb0f57b2"
HISTORICAL_TASK_219_PIN = "1a68db9acb6989dfa81bf875503db62e54a4bed6"
EXPECTED_PIN = ACTIVE_PIN
HISTORICAL_TASK_216_PIN = "c96eb8b52acd865b9453409e6598e08a8bd4e48e"
HISTORICAL_TASK_209_PIN = "91a177d5b96b2197a4d8223dbb727dda6201cb64"
HISTORICAL_TASK_208_PIN = "26097405343150dc1b55015b94720528afad50ed"
HISTORICAL_TASK_204_PIN = "652b00b103dd50e2a550dd0ec0fe4063e69631b7"
TASK_201_HISTORICAL_PIN = "f0237a3b98985ce6ebbaf41af1e06fa3eb4e998e"
UPSTREAM_TASK_146_BASELINE = "89ac1880fed41c7237146422e2e985d98c0eeda8"
UPSTREAM_PLANNING_CHECKPOINT = "e95d12122f35bf4e224dbbb28be1866c8250c069"
TASK_192_SOURCE_SHA = "dcb7432abc58ed983e6c26d5456ace1423e49981"
TASK_194_SOURCE_SHA = "e0d8998ee004fda80ca3fbc3de4eb0afb59160a5"
TASK_196_SOURCE_SHA = "4f6d91858c93192f497342315c4650e30b0a2718"
TASK_199_SOURCE_SHA = "702e85e9e77a556f3716717ccaa186919b1a9dab"
TASK_210_SOURCE_SHA = "399ffe4d38d31f7882d22824ba9c27781b9a0974"
TASK_211_SOURCE_SHA = "15cc092d0ea86cd9bce7baed0d32bc3575fa4b08"
TASK_214_SOURCE_SHA = "123bbb71d44ad15a25e07b07f21f6cb2dd00d20b"
TASK_215_SOURCE_SHA = "dc4c4c8e6f3f4d6eb3441ff4873632e5f51655f9"
TASK_222_SOURCE_SHA = "ca6da00e9e58f66e25f2f6edcb416677bed70b6d"
TASK_223_SOURCE_SHA = "3c67a828857f74466883463abf35a17ecdcc6775"
TASK_224_SOURCE_SHA = "d361361958fbcbe791c04aefbeba3d186c5f9608"
TASK_225_SOURCE_SHA = "6302dd7d01be90624d5ed0072cffbc3c23f2e4a2"
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


def test_roadmap_closes_p8_composition_without_automatic_successor():
    state = load_yaml(ROADMAP_FILE)
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
        "id": "P8_REAL_COMMERCE_DECISION_LOOP_COMPOSITION",
        "title": "P8 Real Commerce Decision Loop Composition",
        "priority_owner": "HUMAN",
        "status": "DONE",
        "completion_basis": "PUBLICATION_GATED",
        "sequence_status": "COMPLETE_ON_EXACT_TASK_226_SOURCE_PUBLICATION",
        "current_milestone": {
            "id": "P8.0",
            "task_id": "TASK-226",
            "title": "Real Commerce Decision Loop Composition",
            "status": "DONE",
            "completion_basis": "PUBLICATION_GATED",
            "composition_contract_only": True,
            "real_pilot_executed": False,
            "semantic_owner": "src/commerce_decision_loop/real_decision_composition.py",
            "authority_identifier": "COMMERCE_DECISION_LOOP_P8_0",
            "effective_only_when": {
                "semantic_review": "PASS",
                "published_source": "EXACT_REVIEWED_CANDIDATE",
                "canonical_main_equals_reviewed_candidate": True,
            },
        },
        "next_milestone": None,
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
    assert values_for_key(state, "status").count("ACTIVE") == 0
    assert state["roadmap_sources"] == [
        "docs/POST_M4_PRODUCT_INTELLIGENCE_ROADMAP.md",
        "docs/POST_P5_P6_QUALITY_SCALE_ROADMAP.md",
    ]
    assert values_for_key(state, "status").count("NEXT") == 0
    assert state["pending_commitments"] == []
    assert values_for_key(state, "status").count("NOT_DONE") == 0
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
    assert state["post_p7_planning_handoff"] == {
        "destination": "P8_REAL_COMMERCE_DECISION_LOOP_COMPOSITION",
        "status": "SELECTED_BY_BRAIN_AND_HUMAN",
        "selected_commitment": "P8.0_REAL_COMMERCE_DECISION_LOOP_COMPOSITION",
        "selection_basis": "FRESH_POST_P7_BRAIN_HUMAN_INTERPRETATION",
        "p7_completion_source_sha": TASK_225_SOURCE_SHA,
        "pending_p7_commitment": None,
        "automatic_next": False,
        "invented_p7_8": False,
        "boundary": (
            "P7.2-P7.7 is complete through the exact published TASK-225 source candidate. Fresh "
            "Human/Brain interpretation selected only the bounded P8.0 composition contract; this "
            "selection does not reopen P7 or transmit P7, Product Intelligence, decision, action, "
            "outcome, roadmap, or future-domain authority into P8.0."
        ),
    }
    assert state["post_p8_planning_handoff"] == {
        "destination": "HUMAN_BRAIN_REAL_DECISION_PILOT_SELECTION",
        "status": "EFFECTIVE_ON_EXACT_TASK_226_SOURCE_PUBLICATION",
        "completed_commitment": "P8.0_REAL_COMMERCE_DECISION_LOOP_COMPOSITION",
        "actual_real_decision_case": None,
        "next_milestone": None,
        "automatic_next": False,
        "automatic_p8_1": False,
        "real_pilot_executed_by_task_226": False,
        "boundary": (
            "TASK-226 freezes the composition contract and does not execute a real pilot. After "
            "exact reviewed source publication, one actual commerce decision case and legitimate "
            "external decision/action lineage require fresh Human/Brain selection. No Runtime, "
            "worker, gap report, represented component, evidence, outcome, score, or assessment "
            "disposition may select or authorize a successor or future intelligence domain."
        ),
    }

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
        assert TASK_214_SOURCE_SHA in roadmap
        assert "P7.3 Decision Context + Opportunity Hypothesis" in roadmap
        assert TASK_215_SOURCE_SHA in roadmap
        assert "P7.4 TikTok Affiliate Evidence Profile" in roadmap
        assert TASK_222_SOURCE_SHA in roadmap
        assert "P7.5 Value-of-Information Planning" in roadmap
        assert TASK_223_SOURCE_SHA in roadmap
        assert "P7.6 Market Test / Funnel Evidence" in roadmap
        assert TASK_224_SOURCE_SHA in roadmap
        assert roadmap.count("P7.7 Calibration & Winner Validation") == 1
        assert "TASK-225 — publication-gated DONE; current/final milestone" in roadmap
        assert "There is no P7.8" in roadmap
        assert "automatic P7 successor" in roadmap
        assert "Fresh Human/Brain interpretation" in roadmap
        assert TASK_225_SOURCE_SHA in roadmap
        assert "P8.0 Real Commerce Decision Loop Composition" in roadmap
        assert "TASK-226 — publication-gated DONE; composition contract only" in roadmap
        assert "does not execute a real pilot" in roadmap
        assert "no automatic P8.1 or other NEXT" in roadmap
        assert "Human/Brain explicitly selects one actual real commerce decision" in roadmap
        assert "P6.2 remains PARKED" in roadmap
        assert "P6.4-P6.6 remain DEFERRED" in roadmap
        for milestone in ("P7.6", "P7.7"):
            assert f"{milestone} " in roadmap
        assert roadmap.count("— NOT_DONE") == 0


def test_p7_3_semantics_record_bounded_authority_and_epistemic_boundaries():
    text = P7_3_SEMANTICS_FILE.read_text(encoding="utf-8")
    for required in (
        "COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_3",
        "DecisionContext != Decision",
        "OpportunityHypothesis != Truth",
        "Evidence reference != evidence ownership",
        "Hypothesis != recommendation",
        "Product Candidate Triage score/rank != opportunity judgment",
        "Opportunity hypothesis != TEST_READY",
        "Observed later outcome != causal attribution",
        "One favorable outcome != scalable winner",
        "does not encode them as an Enum",
        "TASK-191",
        "TASK-214/P7.2 is CLOSED / PUBLISHED",
        TASK_214_SOURCE_SHA,
        EXPECTED_PIN,
        "P7.4 TikTok Affiliate Evidence Profile becomes the",
        "single NEXT commitment",
    ):
        assert required in text


def test_p7_4_semantics_record_bounded_authority_and_epistemic_boundaries():
    text = P7_4_SEMANTICS_FILE.read_text(encoding="utf-8")
    for required in (
        "COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_4",
        "TikTokAffiliateEvidenceProfile",
        "TIKTOK_AFFILIATE_EVIDENCE_DIMENSIONS",
        "create_tiktok_affiliate_evidence_profile",
        "Evidence profile != evidence",
        "Evidence ref != evidence ownership",
        "Unrepresented dimension != evidence absent in the world",
        "Represented dimension != evidence quality",
        "Evidence profile != score/recommendation/decision",
        "TikTok affiliate profile != live TikTok capability",
        "Missing evidence != authorization to collect",
        "Repeated ref across dimensions != multiplied evidence weight",
        "affiliate_commission_rate",
        "estimated_commission_value",
        "creator_count",
        "video_count",
        "TASK-215 / P7.3 is CLOSED / PUBLISHED",
        TASK_215_SOURCE_SHA,
        TASK_214_SOURCE_SHA,
        "40da098b3b0dcf3d1994fc510dd55717b81a2f67",
        EXPECTED_PIN,
        "P7.5 Value-of-Information Planning is the",
        "single NEXT commitment",
    ):
        assert required in text


def test_p7_5_semantics_record_bounded_authority_and_epistemic_boundaries():
    text = P7_5_SEMANTICS_FILE.read_text(encoding="utf-8")
    for required in (
        "COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_5",
        "ValueOfInformationInquiry",
        "ValueOfInformationPlan",
        "VALUE_OF_INFORMATION_DISPOSITIONS",
        "create_value_of_information_plan",
        "missingness != acquisition authorization",
        "collectability != value",
        "planning claim != evidence truth",
        "VOI plan != collector plan",
        "CONTINUE != authorization",
        "STOP != proof no evidence exists",
        "DEFER != permanent rejection",
        "represented != sufficient",
        "disposition != decision",
        "P7.5 != TEST_READY",
        "expected decision impact",
        "uncertainty reduction",
        "cost",
        "latency",
        "access risk",
        "fragility",
        "reliability",
        "opportunity cost",
        "decision deadline",
        "TASK-222 / P7.4 is CLOSED / PUBLISHED",
        TASK_222_SOURCE_SHA,
        TASK_215_SOURCE_SHA,
        TASK_214_SOURCE_SHA,
        EXPECTED_PIN,
        "P7.6 Market Test / Funnel Evidence is the",
        "single NEXT commitment",
    ):
        assert required in text


def test_p7_6_semantics_record_bounded_authority_and_epistemic_boundaries():
    text = P7_6_SEMANTICS_FILE.read_text(encoding="utf-8")
    for required in (
        "COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_6",
        "MarketTestEvidenceProfile",
        "MARKET_TEST_EVIDENCE_DIMENSIONS",
        "create_market_test_evidence_profile",
        "evidence profile != test authorization",
        "test_design_ref != test-design authority",
        "authorization_ref != approval",
        "action_ref != action authority",
        "represented != sufficient",
        "unrepresented != zero/failure",
        "outcome != attribution",
        "outcome != retroactive proof",
        "measurement != winner",
        "one favorable test != scalable winner",
        "P7.6 != P7.7",
        "P7.5 disposition != workflow gate",
        "exposure_evidence_refs",
        "funnel_evidence_refs",
        "economic_evidence_refs",
        "quality_evidence_refs",
        "TASK-223 / P7.5 is CLOSED / PUBLISHED",
        TASK_223_SOURCE_SHA,
        TASK_222_SOURCE_SHA,
        TASK_215_SOURCE_SHA,
        TASK_214_SOURCE_SHA,
        EXPECTED_PIN,
        "P7.7 Calibration & Winner Validation is the",
        "single NEXT commitment",
    ):
        assert required in text


def test_p7_7_semantics_preserve_calibration_validation_and_authority_boundaries():
    text = P7_7_SEMANTICS_FILE.read_text(encoding="utf-8")
    for required in (
        "COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_7",
        "WinnerValidationAssessment",
        "HYPOTHESIS_CALIBRATION_DISPOSITIONS",
        "WINNER_VALIDATION_DISPOSITIONS",
        "create_winner_validation_assessment",
        "Calibration judgment != probability calibration",
        "confidence != probability of winning",
        "Validation disposition != lifecycle state",
        "SUPPORTED` != universal winner truth",
        "outcome != attribution",
        "outcome != retroactive proof",
        "Represented != sufficient",
        "mixed/counter evidence remains visible",
        "one favorable test != scalable winner",
        "Repeated support != automatic scalability",
        "validation != approval/decision",
        "learning != self-authorization",
        "P7.7 does not mutate Product Intelligence policy",
        "TASK-224 / P7.6 is CLOSED / PUBLISHED",
        TASK_224_SOURCE_SHA,
        TASK_223_SOURCE_SHA,
        TASK_222_SOURCE_SHA,
        TASK_215_SOURCE_SHA,
        TASK_214_SOURCE_SHA,
        EXPECTED_PIN,
        "There is no P7.8",
        "no pending or automatic P7 NEXT",
        "fresh Brain/Human interpretation",
    ):
        assert required in text


def test_p7_7_does_not_change_roadmap_or_aios_authority():
    state = load_yaml(ROADMAP_FILE)
    assert state["authority"] == {
        "owner": "BRAIN",
        "purpose": "CROSS_CHAT_PLANNING_BOOKMARK",
        "engineering_truth": False,
        "auto_advance_from_runtime_or_worker_state": False,
        "priority_change_owner": "HUMAN",
    }
    serialized = P7_7_SEMANTICS_FILE.read_text(encoding="utf-8")
    assert "P7.8" in serialized and "There is no P7.8" in serialized
    assert ACTIVE_PIN in serialized
    assert "TASK-207 revision-8 downstream conformance unchanged" in serialized


def test_p8_0_is_one_composition_only_authority_and_human_owned_pilot_handoff():
    text = P8_0_COMPOSITION_FILE.read_text(encoding="utf-8")
    for required in (
        "COMMERCE_DECISION_LOOP_P8_0",
        "Composition != authority",
        "Representation != sufficiency",
        "Missing component != authorization to build it",
        "VOI `CONTINUE`\n  != authorization",
        "decision_authorization_ref != decision authority",
        "Action lineage != action\n  authority",
        "Outcome != attribution",
        "Winner assessment != decision",
        "Composition completeness != real-world\n+success",
        "synthetic fixture != real pilot",
        "does not select Media/Creative Intelligence",
        "Human/Brain selection",
        TASK_225_SOURCE_SHA,
        EXPECTED_PIN,
    ):
        assert required in text

    production_files = tuple(sorted((REPO_ROOT / "src").rglob("*.py")))
    owners = [
        path
        for path in production_files
        if "COMMERCE_DECISION_LOOP_P8_0" in path.read_text(encoding="utf-8")
    ]
    assert owners == [
        REPO_ROOT / "src" / "commerce_decision_loop" / "__init__.py",
        REPO_ROOT
        / "src"
        / "commerce_decision_loop"
        / "real_decision_composition.py",
    ]

    state = load_yaml(ROADMAP_FILE)
    completed = {item["task_id"]: item for item in state["completed_milestones"]}
    assert completed["TASK-225"]["source_sha"] == TASK_225_SOURCE_SHA
    assert completed["TASK-226"]["composition_contract_only"] is True
    assert completed["TASK-226"]["real_pilot_executed"] is False
    assert state["active_track"]["next_milestone"] is None
    assert state["pending_commitments"] == []
    assert state["post_p8_planning_handoff"]["automatic_p8_1"] is False
    assert state["post_p8_planning_handoff"]["actual_real_decision_case"] is None




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
    assert completed["TASK-214"] == {
        "task_id": "TASK-214",
        "track_id": "P7_COMMERCE_OPPORTUNITY_INTELLIGENCE",
        "milestone_id": "P7.2",
        "title": "Winning Opportunity Semantic Reconciliation",
        "status": "DONE",
        "source_sha": TASK_214_SOURCE_SHA,
        "completion_basis": "EXACT_REVIEWED_CANDIDATE_PUBLISHED_TO_CANONICAL_MAIN",
    }
    assert completed["TASK-215"] == {
        "task_id": "TASK-215",
        "track_id": "P7_COMMERCE_OPPORTUNITY_INTELLIGENCE",
        "milestone_id": "P7.3",
        "title": "Decision Context + Opportunity Hypothesis",
        "status": "DONE",
        "source_sha": TASK_215_SOURCE_SHA,
        "completion_basis": "EXACT_REVIEWED_CANDIDATE_PUBLISHED_TO_CANONICAL_MAIN",
    }
    assert completed["TASK-222"] == {
        "task_id": "TASK-222",
        "track_id": "P7_COMMERCE_OPPORTUNITY_INTELLIGENCE",
        "milestone_id": "P7.4",
        "title": "TikTok Affiliate Evidence Profile",
        "status": "DONE",
        "source_sha": TASK_222_SOURCE_SHA,
        "completion_basis": "EXACT_REVIEWED_CANDIDATE_PUBLISHED_TO_CANONICAL_MAIN",
    }
    assert completed["TASK-223"] == {
        "task_id": "TASK-223",
        "track_id": "P7_COMMERCE_OPPORTUNITY_INTELLIGENCE",
        "milestone_id": "P7.5",
        "title": "Value-of-Information Planning",
        "status": "DONE",
        "source_sha": TASK_223_SOURCE_SHA,
        "completion_basis": "EXACT_REVIEWED_CANDIDATE_PUBLISHED_TO_CANONICAL_MAIN",
    }
    assert completed["TASK-224"] == {
        "task_id": "TASK-224",
        "track_id": "P7_COMMERCE_OPPORTUNITY_INTELLIGENCE",
        "milestone_id": "P7.6",
        "title": "Market Test / Funnel Evidence",
        "status": "DONE",
        "source_sha": TASK_224_SOURCE_SHA,
        "completion_basis": "EXACT_REVIEWED_CANDIDATE_PUBLISHED_TO_CANONICAL_MAIN",
    }
    assert completed["TASK-225"] == {
        "task_id": "TASK-225",
        "task_revision": 1,
        "track_id": "P7_COMMERCE_OPPORTUNITY_INTELLIGENCE",
        "milestone_id": "P7.7",
        "title": "Calibration & Winner Validation",
        "status": "DONE",
        "source_sha": TASK_225_SOURCE_SHA,
        "completion_basis": "PUBLICATION_GATED",
        "final_milestone_in_approved_sequence": True,
        "effective_only_when": {
            "semantic_review": "PASS",
            "published_source": "EXACT_REVIEWED_CANDIDATE",
            "canonical_main_equals_reviewed_candidate": True,
        },
    }
    assert completed["TASK-226"] == {
        "task_id": "TASK-226",
        "task_revision": 1,
        "track_id": "P8_REAL_COMMERCE_DECISION_LOOP_COMPOSITION",
        "milestone_id": "P8.0",
        "title": "Real Commerce Decision Loop Composition",
        "status": "DONE",
        "completion_basis": "PUBLICATION_GATED",
        "composition_contract_only": True,
        "real_pilot_executed": False,
        "semantic_owner": "src/commerce_decision_loop/real_decision_composition.py",
        "authority_identifier": "COMMERCE_DECISION_LOOP_P8_0",
        "effective_only_when": {
            "semantic_review": "PASS",
            "published_source": "EXACT_REVIEWED_CANDIDATE",
            "canonical_main_equals_reviewed_candidate": True,
        },
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

    task_209_prereq = state["task_209_historical_prerequisite_pin_migration"]
    assert task_209_prereq["status"] == "DONE"
    assert task_209_prereq["migration_task"] == "TASK-209"
    assert task_209_prereq["downstream_pin"] == HISTORICAL_TASK_209_PIN
    assert task_209_prereq["prior_pin"] == HISTORICAL_TASK_208_PIN
    assert task_209_prereq["prior_migration_task"] == "TASK-208"
    assert task_209_prereq["prerequisite_for"] == "FULL_AIOS_DOWNSTREAM_CONFORMANCE"
    assert task_209_prereq["resume_target"]["task_id"] == "TASK-207"
    assert task_209_prereq["resume_target"]["commitment_id"] == (
        "FULL_AIOS_DOWNSTREAM_CONFORMANCE"
    )
    assert task_209_prereq["resume_target"]["requires_fresh_brain_revision"] is True
    assert task_209_prereq["resume_target"]["supersedes_task_revision"] == 2
    assert task_209_prereq["immutable_old_pin_lineage"] == {
        "task_revision": "TASK-207-REVISION-2",
        "runs": ["RUN-207-001", "RUN-207-002"],
        "repair": "REPAIR-207-001",
        "certification_authority_for_new_pin": False,
    }
    assert task_209_prereq["repository_binding_activation"] == "NONE"
    assert "second bounded prerequisite pin migration" in task_209_prereq["roadmap_effect"]

    task_216_prereq = state["task_216_historical_prerequisite_pin_migration"]
    assert task_216_prereq["status"] == "DONE"
    assert task_216_prereq["migration_task"] == "TASK-216"
    assert task_216_prereq["downstream_pin"] == HISTORICAL_TASK_216_PIN
    assert task_216_prereq["prior_pin"] == HISTORICAL_TASK_209_PIN
    assert task_216_prereq["prior_migration_task"] == "TASK-209"
    assert task_216_prereq["prerequisite_for"] == "FRESH_AIOS_DOWNSTREAM_CONFORMANCE_CERTIFICATION"
    assert task_216_prereq["resume_target"]["task_id"] == "TASK-215"
    assert task_216_prereq["resume_target"]["commitment_id"] == "P7.3"
    assert task_216_prereq["resume_target"]["run_id"] == "RUN-215-002"
    assert task_216_prereq["resume_target"]["requires_fresh_conformance_prerequisite"] is True
    assert task_216_prereq["immutable_old_pin_lineage"] == {
        "conformance_task": "TASK-207",
        "conformance_revision": 3,
        "runs": ["RUN-207-001", "RUN-207-002"],
        "repair": "REPAIR-207-001",
        "downstream_pin": HISTORICAL_TASK_209_PIN,
        "certification_authority_for_new_pin": False,
    }
    assert task_216_prereq["repository_binding_activation"] == "INGRESS_REPAIR_HANDOFF_ACTIVE"
    assert "Migrates the sole active AIOS runtime pin" in task_216_prereq["roadmap_effect"]

    task_218_prereq = state["task_218_historical_prerequisite_pin_migration"]
    assert task_218_prereq["status"] == "DONE"
    assert task_218_prereq["migration_task"] == "TASK-218"
    assert task_218_prereq["downstream_pin"] == HISTORICAL_TASK_218_PIN
    assert task_218_prereq["prior_pin"] == HISTORICAL_TASK_216_PIN
    assert task_218_prereq["prior_migration_task"] == "TASK-216"
    assert task_218_prereq["prerequisite_for"] == "FRESH_AIOS_DOWNSTREAM_CONFORMANCE_CERTIFICATION"
    assert task_218_prereq["resume_target"]["task_id"] == "TASK-215"
    assert task_218_prereq["resume_target"]["task_revision"] == 1
    assert task_218_prereq["resume_target"]["commitment_id"] == "P7.3"
    assert task_218_prereq["resume_target"]["run_id"] == "RUN-215-003"
    assert task_218_prereq["resume_target"]["repair_id"] == "REPAIR-215-002"
    assert task_218_prereq["resume_target"]["failed_head_sha"] == "75cbd814bf5e687c71015dfdce4e5d8a715009c5"
    assert task_218_prereq["resume_target"]["repair_authorization"] == "69b04072dce87c7815afdfea863cb60fde119cbf"
    assert task_218_prereq["resume_target"]["requires_fresh_conformance_prerequisite"] is True
    assert task_218_prereq["immutable_old_pin_lineage"] == {
        "conformance_task": "TASK-207",
        "conformance_revision": 4,
        "downstream_pin": HISTORICAL_TASK_216_PIN,
        "certification_authority_for_new_pin": False,
    }
    assert task_218_prereq["repository_binding_activation"] == "NONE"
    assert "Migrates the sole active AIOS runtime pin" in task_218_prereq["roadmap_effect"]

    task_219_prereq = state["task_219_historical_prerequisite_pin_migration"]
    assert task_219_prereq["status"] == "DONE"
    assert task_219_prereq["migration_task"] == "TASK-219"
    assert task_219_prereq["downstream_pin"] == HISTORICAL_TASK_219_PIN
    assert task_219_prereq["prior_pin"] == HISTORICAL_TASK_218_PIN
    assert task_219_prereq["prior_migration_task"] == "TASK-218"
    assert task_219_prereq["resume_target"]["run_id"] == "RUN-215-004"
    assert task_219_prereq["resume_target"]["prior_finding_id"] == "FINDING-215-001"
    assert task_219_prereq["immutable_old_pin_lineage"] == {
        "conformance_task": "TASK-207",
        "conformance_revision": 5,
        "downstream_pin": HISTORICAL_TASK_218_PIN,
        "certification_authority_for_new_pin": False,
    }

    prereq = state["prerequisite_pin_migration"]
    assert prereq["status"] == "DONE"
    assert prereq["migration_task"] == "TASK-221"
    assert prereq["downstream_pin"] == ACTIVE_PIN
    assert prereq["prior_pin"] == HISTORICAL_TASK_219_PIN
    assert prereq["prior_migration_task"] == "TASK-219"
    assert prereq["prerequisite_for"] == "FRESH_AIOS_DOWNSTREAM_CONFORMANCE_CERTIFICATION"
    assert prereq["upstream_provenance"] == {
        "task_id": "TASK-148",
        "task_revision": 2,
        "run_id": "RUN-148-003",
        "review": "REVIEW-148-003",
        "review_mode": "PRIMARY",
        "review_ac_pass": ["AC1", "AC2", "AC3", "AC4", "AC5", "AC6"],
        "findings": [],
        "source_sha": ACTIVE_PIN,
        "source_published": True,
    }
    assert prereq["conformance_resume"] == {
        "task_id": "TASK-207",
        "expected_revision": 8,
        "authoring_gate": "AFTER_TASK_221_PUBLICATION",
        "downstream_pin": ACTIVE_PIN,
        "status": "PENDING_FRESH_CERTIFICATION",
    }
    assert prereq["resume_target"]["task_id"] == "TASK-215"
    assert prereq["resume_target"]["task_revision"] == 1
    assert prereq["resume_target"]["commitment_id"] == "P7.3"
    assert prereq["resume_target"]["run_id"] == "RUN-215-004"
    assert prereq["resume_target"]["candidate_sha"] == "142bd865f69a6636b321d3cc7a0cd4004db3fdc7"
    assert prereq["resume_target"]["prior_finding_id"] == "FINDING-215-001"
    assert prereq["resume_target"]["predecessor_run_id"] == "RUN-215-003"
    assert prereq["resume_target"]["repair_id"] == "REPAIR-215-002"
    assert prereq["resume_target"]["requires_fresh_conformance_prerequisite"] is True
    assert prereq["immutable_old_pin_lineage"] == {
        "conformance_task": "TASK-207",
        "conformance_revision": 7,
        "terminal_run": "RUN-207-009",
        "downstream_pin": HISTORICAL_TASK_219_PIN,
        "status": "FAILED_OLD_PIN_NON_CERTIFYING_EVIDENCE",
        "repair_after_pin_change": "FORBIDDEN",
        "certification_authority_for_new_pin": False,
    }
    assert prereq["preserved_task_215_lineage"] == {
        "task_id": "TASK-215",
        "task_revision": 1,
        "run_id": "RUN-215-004",
        "candidate_sha": "142bd865f69a6636b321d3cc7a0cd4004db3fdc7",
        "prior_finding_id": "FINDING-215-001",
        "predecessor_run_id": "RUN-215-003",
        "repair_id": "REPAIR-215-002",
        "milestone_id": "P7.3",
        "candidate_preserved": True,
        "product_done": False,
    }
    assert prereq["repository_binding_activation"] == "NONE"
    assert "Migrates the sole active AIOS runtime pin" in prereq["roadmap_effect"]

    assert state["authority"]["owner"] == "BRAIN"
    assert state["authority"]["auto_advance_from_runtime_or_worker_state"] is False

    conformance = state["full_downstream_conformance"]
    assert conformance["status"] == "DONE"
    assert conformance["task_id"] == "TASK-207"
    assert conformance["task_revision"] == 8
    assert conformance["downstream_pin"] == ACTIVE_PIN
    assert conformance["certification_record"] == ".ai/aios-conformance-state.yaml"
    assert conformance["historical_certification"] == {
        "task_id": "TASK-207",
        "task_revision": 5,
        "downstream_pin": PRIOR_CERTIFIED_PIN,
        "effective_only_when": {
            "semantic_review": "PASS",
            "published_source": "EXACT_REVIEWED_CANDIDATE",
            "canonical_main_equals_reviewed_candidate": True,
        },
        "status": "HISTORICAL_OLD_PIN_EVIDENCE_ONLY",
    }
    assert conformance["historical_failed_attempt"] == {
        "task_id": "TASK-207",
        "task_revision": 7,
        "terminal_run": "RUN-207-009",
        "downstream_pin": HISTORICAL_TASK_219_PIN,
        "status": "FAILED_OLD_PIN_NON_CERTIFYING_EVIDENCE",
        "repair_after_pin_change": "FORBIDDEN",
        "certification_authority_for_current_pin": False,
    }
    assert conformance["effective_only_when"] == {
        "semantic_review": "PASS",
        "published_source": "EXACT_REVIEWED_CANDIDATE",
        "canonical_main_equals_reviewed_candidate": True,
    }
    assert conformance["next_commitment"] == "P7.3"
    assert conformance["resume_target"] == {
        "task_id": "TASK-215",
        "task_revision": 1,
        "commitment_id": "P7.3",
        "run_id": "RUN-215-004",
        "candidate_sha": "142bd865f69a6636b321d3cc7a0cd4004db3fdc7",
        "prior_finding_id": "FINDING-215-001",
        "predecessor_run_id": "RUN-215-003",
        "repair_id": "REPAIR-215-002",
    }
    assert "closes FRESH_AIOS_DOWNSTREAM_CONFORMANCE_CERTIFICATION" in conformance["roadmap_effect"]


def test_adoption_registry_pin_audit_authority_and_dimensions_are_explicit():
    state = load_yaml(ADOPTION_FILE)
    conformance = load_yaml(CONFORMANCE_FILE)
    requirement = PIN_FILE.read_text(encoding="utf-8").strip()
    assert requirement.endswith("@" + ACTIVE_PIN)
    assert state["downstream_pin"]["commit"] == ACTIVE_PIN
    assert state["upstream_audit"]["checkpoint"] == ACTIVE_PIN
    assert state["upstream_audit"]["through_authored_task"] == "TASK-148"
    assert state["upstream_audit"]["upstream_revision"] == 2
    assert state["upstream_audit"]["run_id"] == "RUN-148-003"
    assert state["upstream_audit"]["checkpoint_role"] == "REVIEWED_SOURCE_PUBLISHED_PROVENANCE"
    assert state["upstream_audit"]["checkpoint_is_runtime_authority"] is False
    assert state["upstream_audit"]["review"] == "REVIEW-148-003"
    assert state["upstream_audit"]["review_outcome"] == "PRIMARY_PASS"
    assert state["upstream_audit"]["source_published"] is True
    assert state["upstream_audit"]["prior_planning_checkpoint"] == HISTORICAL_TASK_219_PIN
    assert len(state["upstream_audit"]["provenance"]) == 21
    assert [entry["task_id"] for entry in state["upstream_audit"]["provenance"]] == [
        "TASK-114", "TASK-115", "TASK-116", "TASK-117", "TASK-118",
        "TASK-119", "TASK-120", "TASK-121", "TASK-122", "TASK-123",
        "TASK-124", "TASK-125", "TASK-126", "TASK-127", "TASK-128", "TASK-129",
        "TASK-145", "TASK-144", "TASK-140", "TASK-147", "TASK-148",
    ]
    assert state["authority"]["engineering_truth"] is False
    assert state["full_downstream_conformance"] == {
        "status": "CERTIFIED_ON_REVIEWED_SOURCE_PUBLICATION",
        "certification_task": {"id": "TASK-207", "revision": 8},
        "downstream_pin": ACTIVE_PIN,
        "historical_old_pin_certification": {
            "task_id": "TASK-207",
            "revision": 5,
            "downstream_pin": PRIOR_CERTIFIED_PIN,
            "certification_record": ".ai/aios-conformance-state.yaml",
            "status": "HISTORICAL_OLD_PIN_EVIDENCE_ONLY",
        },
        "historical_old_pin_attempts": {
            "task_id": "TASK-207",
            "revision": 7,
            "downstream_pin": HISTORICAL_TASK_219_PIN,
            "terminal_run": "RUN-207-009",
            "status": "FAILED_OLD_PIN_NON_CERTIFYING_EVIDENCE",
            "repair_after_pin_change": "FORBIDDEN",
            "certification_authority_for_current_pin": False,
        },
        "certification_record": ".ai/aios-conformance-state.yaml",
        "effective_only_when": {
            "semantic_review": "PASS",
            "published_source": "EXACT_REVIEWED_CANDIDATE",
            "canonical_main_equals_reviewed_candidate": True,
        },
        "before_gate": "NOT_EFFECTIVE",
        "binding_classifications_changed": False,
        "boundary": (
            "This Brain planning record becomes effective only when the safe Publisher "
            "publishes exactly the reviewed TASK-207 revision-8 source candidate. It is "
            "not Runtime, review, or publication authority and does not replace the separate "
            "canonical evidence lineage. Revision-5 certification remains historical evidence "
            f"for {PRIOR_CERTIFIED_PIN}, while revision 7 and RUN-207-009 remain failed, "
            f"non-certifying old-pin history for {HISTORICAL_TASK_219_PIN}."
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
        "task_revision": 8,
        "downstream_pin": ACTIVE_PIN,
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
            "effective. The safe Publisher must publish exactly the TASK-207 revision-8 "
            "reviewed source candidate, and canonical main must equal that candidate."
        ),
    }
    assert conformance["historical_certification"] == {
        "task_id": "TASK-207",
        "task_revision": 5,
        "downstream_pin": PRIOR_CERTIFIED_PIN,
        "status": "HISTORICAL_OLD_PIN_EVIDENCE_ONLY",
        "certification_authority_for_current_pin": False,
    }
    assert conformance["failed_old_pin_history"] == {
        "task_id": "TASK-207",
        "task_revision": 7,
        "runs": ["RUN-207-007", "RUN-207-008", "RUN-207-009"],
        "terminal_run": "RUN-207-009",
        "downstream_pin": HISTORICAL_TASK_219_PIN,
        "status": "FAILED_OLD_PIN_NON_CERTIFYING_EVIDENCE",
        "repair_after_pin_change": "FORBIDDEN",
        "certification_authority_for_current_pin": False,
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
        "TASK-124", "TASK-125", "TASK-126", "TASK-127", "TASK-128", "TASK-129",
        "TASK-140", "TASK-144", "TASK-145", "TASK-147", "TASK-148",
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
    for task_id in (
        "TASK-114", "TASK-115", "TASK-116", "TASK-117", "TASK-118",
        "TASK-119", "TASK-120", "TASK-121", "TASK-122", "TASK-123",
        "TASK-124", "TASK-125", "TASK-126", "TASK-128", "TASK-129",
        "TASK-140", "TASK-144", "TASK-145", "TASK-147", "TASK-148",
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

    post_canonical_repair = families["POST_CANONICALIZATION_REPAIR_HANDOFF"]
    assert post_canonical_repair["upstream_tasks"] == ["TASK-127"]
    assert post_canonical_repair["package_capability_availability"] == "ADOPTED_BY_PIN"
    assert post_canonical_repair["repository_binding_activation"] == "ACTIVE"

    repair_recon = families["LOCAL_CANONICAL_REPAIR_RECONCILIATION_FIX"]
    assert repair_recon["upstream_tasks"] == ["TASK-145"]
    assert repair_recon["upstream_revision"] == 2
    assert repair_recon["package_capability_availability"] == "ADOPTED_BY_PIN"
    assert repair_recon["repository_binding_activation"] == "NOT_REQUIRED"
    assert repair_recon["consumption"] == "PINNED_KERNEL_ONLY"
    assert repair_recon["source_published"] is True
    assert repair_recon["review"] == "REVIEW-145-001"
    assert repair_recon["run_id"] == "RUN-145-002"
    assert (
        repair_recon["verification_baseline_commit"]
        == UPSTREAM_TASK_146_BASELINE
    )

    repair_review_recon = families["CANONICAL_SUCCESSFUL_REPAIR_REVIEW_RECONSTRUCTION"]
    assert repair_review_recon["upstream_tasks"] == ["TASK-144"]
    assert repair_review_recon["upstream_revision"] == 2
    assert repair_review_recon["package_capability_availability"] == "ADOPTED_BY_PIN"
    assert repair_review_recon["repository_binding_activation"] == "NOT_REQUIRED"
    assert repair_review_recon["consumption"] == "PINNED_KERNEL_ONLY"
    assert repair_review_recon["source_published"] is True
    assert repair_review_recon["review"] == "REVIEW-144-006"
    assert repair_review_recon["run_id"] == "RUN-144-006"

    historical_subject = families["HISTORICAL_SUBJECT_REPOSITORY_SEMANTICS"]
    assert historical_subject["upstream_tasks"] == ["TASK-140", "TASK-147", "TASK-148"]
    assert historical_subject["upstream_revisions"] == {
        "TASK-140": 5,
        "TASK-147": 2,
        "TASK-148": 2,
    }
    assert historical_subject["package_capability_availability"] == "ADOPTED_BY_PIN"
    assert historical_subject["repository_binding_activation"] == "NOT_REQUIRED"
    assert historical_subject["consumption"] == "PINNED_KERNEL_ONLY"
    assert historical_subject["source_published"] is True
    assert historical_subject["reviewed_source_sha"] == ACTIVE_PIN
    assert historical_subject["review"] == "REVIEW-148-003"
    assert historical_subject["run_id"] == "RUN-148-003"
    assert "ordinary repository-local .git directory" in historical_subject["boundary"]
    assert "without moving control HEAD, branch, index, or worktree" in historical_subject["boundary"]
    assert "activates no upstream repository hook" in historical_subject["boundary"]


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


def test_task_220_repair_delivery_boundary_and_immutable_redelivery_governance():
    workflow_doc = (REPO_ROOT / "docs" / "AIOS_UNIFIED_WORKER_WORKFLOW.md").read_text(encoding="utf-8")

    # AC5: Documentation accurately describes canonical AUTHOR_REPAIR handoff
    assert "Canonical AUTHOR_REPAIR handoff" in workflow_doc
    assert "canonical repair authorization plus a bounded handoff" in workflow_doc
    assert "not automatic execution" in workflow_doc
    assert "Brain Ingress contains no repair `createWorkflowDispatch` step" in workflow_doc

    # AC5: Documentation accurately describes dedicated REPAIR wakeup and direct fallback
    assert "Dedicated REPAIR wakeup delivery" in workflow_doc
    assert "dedicated `[AIOS REPAIR WAKEUP]` Issue carrier is the separate Human/Brain delivery step" in workflow_doc
    assert "Direct fallback authorization" in workflow_doc
    assert "strictly gated by `GITHUB_ACTOR == trung-via`" in workflow_doc
    assert "Bot identities, including `github-actions[bot]`, gain no semantic or Executor-selection authority" in workflow_doc

    # AC3 & AC5: Explicit Executor for coding repairs, none for NO_CHANGE, no inference
    assert "Coding REPAIR continuation" in workflow_doc
    assert "requires exactly one explicit supported Executor (`antigravity` or `codex`)" in workflow_doc
    assert "`NO_CHANGE` carries none" in workflow_doc
    assert "No downstream workflow, script, test, or documentation infers, defaults, or silently substitutes Executor identity" in workflow_doc

    # AC4: Pinned Runtime remains sole lifecycle/repair authority
    assert "Pinned Runtime remains the sole authority for the current canonical repair SHA" in workflow_doc
    assert "Repository workflows remain selector couriers only" in workflow_doc

    # AC5: Immutable exact-intent redelivery semantics
    assert "Immutable exact-intent redelivery" in workflow_doc
    assert "The same `repair_dispatch_id`, `failed_run_id`, and `repair_sha` are reused" in workflow_doc
    assert "A selector change represents new delivery intent and must fail closed against an existing durable dispatch record" in workflow_doc

    # AC2: Policies enforce Human gating and exclude bot identities
    ingress_policy = load_yaml(REPO_ROOT / ".ai" / "brain-ingress-carriers.yaml")
    repair_policy = load_yaml(REPO_ROOT / ".ai" / "brain-repair-wakeup-carriers.yaml")
    assert ingress_policy["github_issue"]["authorized_actors"] == ["trung-via"]
    assert repair_policy["github_issue"]["authorized_actors"] == ["trung-via"]
    for bot in ("github-actions[bot]", "github-actions", "bot"):
        assert bot not in ingress_policy["github_issue"]["authorized_actors"]
        assert bot not in repair_policy["github_issue"]["authorized_actors"]

    # AC2: Self-hosted target directly enforces Human actor preflight
    target_text = (REPO_ROOT / ".github" / "workflows" / "aios-self-hosted-repair-wakeup.yml").read_text(encoding="utf-8")
    assert "GITHUB_ACTOR -ne 'trung-via'" in target_text

    # AC1: Brain Ingress does not dispatch repair target
    ingress_text = (REPO_ROOT / ".github" / "workflows" / "aios-brain-ingress.yml").read_text(encoding="utf-8")
    assert "aios-self-hosted-repair-wakeup.yml" not in ingress_text
    assert ingress_text.count("createWorkflowDispatch") == 1

    # AC6: Pin, conformance records, and task history remain unchanged
    pin_text = PIN_FILE.read_text(encoding="utf-8")
    assert ACTIVE_PIN in pin_text
