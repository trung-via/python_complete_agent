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
P8_1_SELECTION_FILE = (
    REPO_ROOT
    / "docs"
    / "PHASE_8_P8_1_REAL_DECISION_PILOT_SELECTION.md"
)
P8_2_EVIDENCE_PLAN_FILE = (
    REPO_ROOT
    / "docs"
    / "PHASE_8_P8_2_PRE_ACTION_EVIDENCE_ACQUISITION_PLAN.md"
)
P8_3_MANUAL_AUTHORIZATION_FILE = (
    REPO_ROOT
    / "docs"
    / "PHASE_8_P8_3_MANUAL_WAVE_1_EVIDENCE_CONTRIBUTION_AUTHORIZATION.md"
)
P8_WAVE_0_COMPATIBILITY_FILE = (
    REPO_ROOT / "docs" / "PHASE_8_WAVE_0_TIKTOK_PDP_IDENTITY_COMPATIBILITY.md"
)
P8_PUBLIC_PDP_ACQUISITION_CONTRACT_FILE = (
    REPO_ROOT / "docs" / "PHASE_8_PUBLIC_TIKTOK_PDP_ACQUISITION_CONTRACT.md"
)
P8_PUBLIC_PDP_COLLECTOR_IMPLEMENTATION_FILE = (
    REPO_ROOT / "docs" / "PHASE_8_PUBLIC_TIKTOK_PDP_COLLECTOR_IMPLEMENTATION.md"
)
P8_PUBLIC_PDP_LIVE_PILOT_AUTHORIZATION_FILE = (
    REPO_ROOT / "docs" / "PHASE_8_PUBLIC_TIKTOK_PDP_LIVE_PILOT_AUTHORIZATION.md"
)
P8_PUBLIC_PDP_LIVE_PILOT_REVIEW_FILE = (
    REPO_ROOT
    / "docs"
    / "PHASE_8_PUBLIC_TIKTOK_PDP_LIVE_PILOT_REVIEW_AND_DOM_DIAGNOSTIC.md"
)
P8_PUBLIC_PDP_DOM_DIAGNOSTIC_AUTHORIZATION_FILE = (
    REPO_ROOT
    / "docs"
    / "PHASE_8_PUBLIC_TIKTOK_PDP_DOM_DIAGNOSTIC_AUTHORIZATION.md"
)
P8_PUBLIC_PDP_DOM_DIAGNOSTIC_REVIEW_AND_HARDENING_FILE = (
    REPO_ROOT
    / "docs"
    / "PHASE_8_PUBLIC_TIKTOK_PDP_DOM_DIAGNOSTIC_REVIEW_AND_HARDENING.md"
)
P8_PUBLIC_PDP_DOM_DIAGNOSTIC_FRESH_AUTHORIZATION_FILE = (
    REPO_ROOT
    / "docs"
    / "PHASE_8_PUBLIC_TIKTOK_PDP_DOM_DIAGNOSTIC_FRESH_AUTHORIZATION.md"
)
P8_PUBLIC_PDP_DOM_DIAGNOSTIC_GEN2_REVIEW_AND_ROOT_OBSERVABILITY_FILE = (
    REPO_ROOT
    / "docs"
    / "PHASE_8_PUBLIC_TIKTOK_PDP_DOM_DIAGNOSTIC_GEN2_REVIEW_AND_ROOT_OBSERVABILITY.md"
)
P8_PUBLIC_PDP_DOM_DIAGNOSTIC_GEN3_AUTHORIZATION_FILE = (
    REPO_ROOT
    / "docs"
    / "PHASE_8_PUBLIC_TIKTOK_PDP_DOM_DIAGNOSTIC_GEN3_AUTHORIZATION.md"
)
P8_PUBLIC_PDP_DOM_DIAGNOSTIC_GEN4_AUTHORIZATION_FILE = (
    REPO_ROOT
    / "docs"
    / "PHASE_8_PUBLIC_TIKTOK_PDP_DOM_DIAGNOSTIC_GEN4_AUTHORIZATION.md"
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
TASK_226_SOURCE_SHA = "a9429a5db859ebc6fe7e5fea19aaf17ee11d0d3e"
TASK_227_SOURCE_SHA = "d2752d69c701dd2483ea30f52be3385b5137e008"
TASK_238_PUBLISHED_SOURCE_SHA = "fbdb8851b9f27d24eff11c509db3009e2c614952"
TASK_240_PUBLISHED_SOURCE_SHA = "8ef61df3936652fb7aeda8ca31ce1db3621ff4cf"
TASK_228_SOURCE_SHA = "eb5b09a8208771a25493fd5a68232bb2dd48c700"
TASK_236_SOURCE_SHA = "a53510ff353cdf926a76f1dc84363b7835c5cb4d"
SELECTED_SOURCE_ID = "1731381331718341815"
SELECTED_LISTING_REFERENCE = (
    "https://shop.tiktok.com/vn/pdp/"
    "den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815"
)
ACTIVE_TRACK_ID = "AIOS_FULL_DOWNSTREAM_ADOPTION_AND_GOVERNANCE_REBUILD"
CLOSURE_MILESTONE_ID = "GOVERNANCE_FOUNDATION_CLOSURE_AND_P7_RETURN"
HISTORICAL_CONFORMANCE_NEXT_COMMITMENT = "PROJECT_CONTRACT_REBUILD"
P8_3_AUTHORIZED_OBSERVATIONS = [
    "variant_descriptor",
    "current_price",
    "original_price",
    "discount_percent",
    "affiliate_eligibility",
    "affiliate_commission_rate",
    "estimated_commission_value",
    "sold_count",
    "rating",
    "review_count",
    "inventory_availability",
]
P8_PUBLIC_PDP_V1_ALLOWLIST = [
    "source_product_id",
    "requested_and_observed_url_binding_context",
    "observed_at",
    "title",
    "shop_name",
    "price",
    "original_price",
    "discount_percent",
    "sold_count",
    "rating",
    "review_count",
]



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


def test_task_241_authorizes_one_exact_generation_4_v2_diagnostic_attempt():
    state = load_yaml(ROADMAP_FILE)
    active = state["active_track"]
    milestone = active["current_milestone"]
    handoff = state["post_p8_planning_handoff"]
    authorization = handoff["public_pdp_dom_diagnostic_gen4_authorization"]
    completed = {item["task_id"]: item for item in state["completed_milestones"]}
    document = P8_PUBLIC_PDP_DOM_DIAGNOSTIC_GEN4_AUTHORIZATION_FILE.read_text(
        encoding="utf-8"
    )

    assert active["id"] == "P8_PUBLIC_PDP_DOM_DIAGNOSTIC_GEN4_AUTHORIZATION"
    assert active["sequence_status"] == "COMPLETE_ON_EXACT_TASK_241_SOURCE_PUBLICATION"
    assert milestone["task_id"] == "TASK-241"
    assert milestone["classification"] == (
        "FRESH_GENERATION_4_COMMERCE_OBSERVABILITY_DIAGNOSTIC_AUTHORIZATION_ONLY"
    )
    for record in (milestone, handoff, authorization, completed["TASK-241"]):
        assert record["source_task_id"] == "TASK-240"
        assert record["source_run_id"] == "RUN-240-002"
        assert record["source_review_id"] == "REVIEW-240-001"
        assert record["source_published_sha"] == TASK_240_PUBLISHED_SOURCE_SHA
        assert record["diagnostic_v2_implementation_source_sha"] == (
            TASK_240_PUBLISHED_SOURCE_SHA
        )
        assert record["diagnostic_authorization_generation"] == 4
        assert record["live_dom_diagnostic_authority"] == (
            "ONE_SHOT_ATTACH_ONLY_EXACT_LISTING"
        )
        assert record["generation_4_authorized_diagnostic_attempts"] == 1
        assert record["generation_4_authorized_diagnostic_attempts_remaining"] == 1
        assert record["generation_4_diagnostic_execution_owner"] == "HUMAN_OPERATOR"
        assert record["generation_4_diagnostic_executed"] is False
        assert record["evidence_authority"] == "NONE"
        assert record["root_observability_hardening_implemented"] is True
        assert record["commerce_observability_hardening_implemented"] is True
        assert record["selector_repair_complete"] is False
        assert record["live_public_pdp_acquisition_authority"] == "NONE"
        assert record["automated_public_pdp_acquisition_authority"] == "NONE"
        assert record["market_test_or_action_authority"] == "NONE"
        assert record["automatic_progression"] is False

    assert completed["TASK-240"]["published_source_sha"] == TASK_240_PUBLISHED_SOURCE_SHA
    assert completed["TASK-240"]["diagnostic_implementation_source_sha"] == (
        TASK_238_PUBLISHED_SOURCE_SHA
    )
    assert handoff["destination"] == (
        "HUMAN_OPERATOR_GENERATION_4_COMMERCE_OBSERVABILITY_DIAGNOSTIC_EXECUTION"
    )
    assert active["next_milestone"] is None
    assert handoff["next_milestone"] is None
    assert state["pending_commitments"] == []

    assert milestone["context_id"] == "p8-pilot-001-led-motion-tiktok-vn"
    assert milestone["authorized_source_id"] == SELECTED_SOURCE_ID
    assert milestone["stable_listing_reference"] == SELECTED_LISTING_REFERENCE
    assert milestone["diagnostic_carrier"] == (
        "src/product_intelligence/tiktok_pdp_dom_diagnostic.py"
    )
    assert milestone["diagnostic_schema_version"] == 2
    assert milestone["diagnostic_artifact_filename"] == (
        "tiktok-pdp-dom-diagnostic-v2.json"
    )
    assert milestone["diagnostic_artifact_create_exclusive"] is True
    assert milestone["canonical_cli_command"] == "tiktok-pdp-dom-diagnostic"
    assert milestone["borrowed_session_count"] == 1
    assert milestone["session_evaluate_count"] == 1
    assert milestone["navigation_refresh_click_type_scroll_authority"] == "NONE"
    assert milestone["browser_lifecycle_authority"] == "TASK-137"

    preflight = milestone["preflight_authority"]
    assert milestone["preflight_consumes_attempt"] is False
    assert preflight["cdp_reachability"] == "127.0.0.1:9222"
    assert preflight["exact_already_open_pdp_read_only_target_listing"] is True
    assert preflight["new_external_job_root_requires_v1_absent"] is True
    assert preflight["new_external_job_root_requires_v2_absent"] is True
    assert preflight["execution_critical_file_equivalence_source_sha"] == (
        TASK_240_PUBLISHED_SOURCE_SHA
    )
    assert preflight["execution_critical_files"] == [
        "src/product_intelligence/tiktok_pdp_dom_diagnostic.py",
        "src/product_intelligence/cli.py",
        "src/integrations/playwright/manager.py",
    ]
    assert preflight["repository_head_equality_required"] is False
    assert preflight["diagnostic_carrier_invocation"] is False

    assert milestone["diagnostic_invocation_consumes_attempt"] is True
    assert milestone["terminal_outcome_consumption"] == "EVERY_TERMINAL_OUTCOME"
    assert milestone["automatic_retry_refresh_resume"] is False
    assert milestone["second_invocation_authority"] == "NONE"
    assert milestone["replacement_search_batch_variant_switching_authority"] == "NONE"
    for authority in (
        "arbitrary_target_authority",
        "replacement_target_authority",
        "search_authority",
        "batch_authority",
        "inferred_identity_authority",
        "variant_switching_authority",
        "selector_repair_authority",
        "acquisition_authority",
    ):
        assert milestone[authority] == "NONE"
    assert milestone["root_probe_interpretation"] == "ENGINEERING_DIAGNOSTIC_HINT_ONLY"
    assert milestone["commerce_probe_interpretation"] == "ENGINEERING_DIAGNOSTIC_HINT_ONLY"
    assert milestone["truncated_scan_negative_observations"] == "NON_EXHAUSTIVE"
    assert milestone["shadow_or_iframe_traversal_authority"] == "NONE"
    assert milestone["readiness_or_selector_hint_repair_authority"] == "NONE"

    generation_3 = milestone["historical_generation_3"]
    assert generation_3["diagnostic_executed"] is True
    assert generation_3["diagnostic_outcome"] == "FAIL_CLOSED"
    assert generation_3["diagnostic_failure_reason"] == "NO_BOUNDED_PDP_ROOT"
    assert generation_3["diagnostic_artifact_created"] is True
    assert generation_3["authorized_diagnostic_attempts"] == 1
    assert generation_3["authorized_diagnostic_attempts_remaining"] == 0
    assert generation_3["execution_owner"] == "HUMAN_OPERATOR"
    assert generation_3["live_dom_diagnostic_authority"] == "NONE"
    assert generation_3["artifact"] == {
        "schema_version": 1,
        "filename": "tiktok-pdp-dom-diagnostic-v1.json",
        "sha256": "4CE631661F897F16133EFEAA3CC1CA03C5E468CC56F1F7D46B7F2FF53EBDF00E",
        "size_bytes": 755,
        "observed_at": "2026-09-22T05:59:34.977481+00:00",
        "evidence_authority": "NONE",
    }
    assert generation_3["root_probe"] == {
        "title_anchor_count": 1,
        "price_anchor_count": 0,
        "action_anchor_count": 0,
        "visible_explicit_pdp_root_count": 0,
        "explicit_root_with_commerce_anchors_count": 0,
        "main_present": False,
        "main_visible": False,
        "main_has_commerce_anchors": False,
        "multi_anchor_common_ancestor_found": False,
        "selected_root_kind": "NONE",
    }
    assert milestone["historical_generation_1"]["authorized_diagnostic_attempts_remaining"] == 0
    assert milestone["historical_generation_2"]["authorized_diagnostic_attempts_remaining"] == 0

    assert "C:\\" not in document
    for required in (
        "RUN-240-002",
        "REVIEW-240-001",
        TASK_240_PUBLISHED_SOURCE_SHA,
        "tiktok-pdp-dom-diagnostic-v1.json",
        "tiktok-pdp-dom-diagnostic-v2.json",
        "bounded_scan_truncated=true",
        "document_ready_state=COMPLETE",
        "HUMAN_OPERATOR_GENERATION_4_COMMERCE_OBSERVABILITY_DIAGNOSTIC_EXECUTION",
        "CAPABILITY_IS_NOT_AUTHORITY",
        "EVIDENCE_IS_NOT_PRODUCT_TRUTH",
        "SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY",
        "SNAPSHOT_IS_NOT_TREND",
        "ONE_CAPABILITY_ONE_AUTHORITY",
    ):
        assert required in document


def test_task_240_history_does_not_freeze_current_global_handoff():
    state = load_yaml(ROADMAP_FILE)
    handoff = state["post_p8_planning_handoff"]
    history = handoff[
        "public_pdp_dom_diagnostic_gen3_review_and_commerce_observability"
    ]
    completed = {item["task_id"]: item for item in state["completed_milestones"]}

    assert history["task_id"] == "TASK-240"
    assert history["published_source_sha"] == TASK_240_PUBLISHED_SOURCE_SHA
    assert history["diagnostic_implementation_source_sha"] == TASK_238_PUBLISHED_SOURCE_SHA
    assert history["post_publication_handoff"] == (
        "HUMAN_BRAIN_FRESH_COMMERCE_OBSERVABILITY_DIAGNOSTIC_AUTHORIZATION"
    )
    assert completed["TASK-240"]["post_publication_handoff"] == (
        "HUMAN_BRAIN_FRESH_COMMERCE_OBSERVABILITY_DIAGNOSTIC_AUTHORIZATION"
    )
    assert handoff["destination"] != history["post_publication_handoff"]


def _historical_test_roadmap_closes_task_239_with_generation_3_authorization():
    state = load_yaml(ROADMAP_FILE)
    active = state["active_track"]
    assert active["id"] == "P8_PUBLIC_PDP_DOM_DIAGNOSTIC_GEN3_AUTHORIZATION"
    assert active["status"] == "DONE"
    assert active["sequence_status"] == "COMPLETE_ON_EXACT_TASK_239_SOURCE_PUBLICATION"
    assert active["current_milestone"]["task_id"] == "TASK-239"
    assert active["current_milestone"]["classification"] == (
        "FRESH_GENERATION_3_ROOT_OBSERVABILITY_DIAGNOSTIC_AUTHORIZATION_ONLY"
    )
    assert active["current_milestone"]["source_task_id"] == "TASK-238"
    assert active["current_milestone"]["source_run_id"] == "RUN-238-002"
    assert active["current_milestone"]["source_review_id"] == "REVIEW-238-001"
    assert active["current_milestone"]["diagnostic_implementation_source_sha"] == (
        TASK_238_PUBLISHED_SOURCE_SHA
    )
    assert active["current_milestone"]["diagnostic_authorization_generation"] == 3
    assert active["current_milestone"]["live_dom_diagnostic_authority"] == (
        "ONE_SHOT_ATTACH_ONLY_EXACT_LISTING"
    )
    assert active["current_milestone"]["generation_3_authorized_diagnostic_attempts"] == 1
    assert active["current_milestone"]["generation_3_authorized_diagnostic_attempts_remaining"] == 1
    assert active["current_milestone"]["generation_3_diagnostic_execution_owner"] == "HUMAN_OPERATOR"
    assert active["current_milestone"]["generation_3_diagnostic_executed"] is False
    assert active["current_milestone"]["diagnostic_executed"] is False
    assert active["current_milestone"]["evidence_authority"] == "NONE"
    assert active["current_milestone"]["root_observability_hardening_implemented"] is True
    assert active["current_milestone"]["selector_repair_complete"] is False
    assert active["next_milestone"] is None

    assert values_for_key(state, "status").count("NEXT") == 0
    assert state["pending_commitments"] == []

    handoff = state["post_p8_planning_handoff"]
    historical_authorization = handoff["public_pdp_dom_diagnostic_gen3_authorization"]
    assert historical_authorization["post_publication_handoff"] == (
        "HUMAN_OPERATOR_GENERATION_3_ROOT_OBSERVABILITY_DIAGNOSTIC_EXECUTION"
    )
    assert handoff["status"] == "EFFECTIVE_ON_EXACT_TASK_239_SOURCE_PUBLICATION"
    assert handoff["completed_commitment"] == "P8_PUBLIC_PDP_DOM_DIAGNOSTIC_GEN3_AUTHORIZATION"
    assert handoff["implementation_authorized"] is True
    assert handoff["implementation_exists"] is True
    assert handoff["live_public_pdp_acquisition_authority"] == "NONE"
    assert handoff["authorized_source_id"] == SELECTED_SOURCE_ID
    assert handoff["authorized_capture_attempts"] == 1
    assert handoff["authorized_capture_attempts_remaining"] == 0
    assert handoff["capture_execution_owner"] == "HUMAN_OPERATOR"
    assert handoff["automatic_live_pilot"] is False
    assert handoff["automatic_p8_4"] is False
    assert handoff["market_test_or_action_authority"] == "NONE"
    assert handoff["first_live_capture_handoff"] == "COMPLETE"
    assert handoff["diagnostic_authorization_generation"] == 3
    assert handoff["live_dom_diagnostic_authority"] == "ONE_SHOT_ATTACH_ONLY_EXACT_LISTING"
    assert handoff["generation_3_authorized_diagnostic_attempts"] == 1
    assert handoff["generation_3_authorized_diagnostic_attempts_remaining"] == 1
    assert handoff["generation_3_diagnostic_execution_owner"] == "HUMAN_OPERATOR"
    assert handoff["generation_3_diagnostic_executed"] is False
    assert handoff["diagnostic_executed"] is False
    assert handoff["evidence_authority"] == "NONE"
    assert handoff["preflight_consumes_attempt"] is False
    assert handoff["diagnostic_invocation_consumes_attempt"] is True
    assert handoff["automatic_retry_refresh_resume"] is False
    assert handoff["mandatory_post_diagnostic_review"] == "HUMAN_BRAIN"
    assert handoff["root_observability_hardening_implemented"] is True
    assert handoff["diagnostic_hardening_implemented"] is True
    assert handoff["selector_repair_complete"] is False

    gen1 = handoff["historical_generation_1"]
    assert gen1["diagnostic_executed"] is True
    assert gen1["diagnostic_outcome"] == "FAIL_CLOSED"
    assert gen1["diagnostic_artifact_created"] is False
    assert gen1["authorized_diagnostic_attempts"] == 1
    assert gen1["authorized_diagnostic_attempts_remaining"] == 0
    assert gen1["historical_failure_reason"] == (
        "LEGACY_COMBINED_PUBLIC_PDP_AVAILABILITY_GATE"
    )
    assert gen1["screenshot_context"] == "NON_CANONICAL_DIAGNOSTIC_CONTEXT"

    gen2 = handoff["historical_generation_2"]
    assert gen2["task_id"] == "TASK-237"
    assert gen2["diagnostic_executed"] is True
    assert gen2["diagnostic_outcome"] == "FAIL_CLOSED"
    assert gen2["diagnostic_failure_reason"] == "NO_BOUNDED_PDP_ROOT"
    assert gen2["diagnostic_artifact_created"] is False
    assert gen2["authorized_diagnostic_attempts"] == 1
    assert gen2["authorized_diagnostic_attempts_remaining"] == 0
    assert gen2["execution_owner"] == "HUMAN_OPERATOR"
    assert gen2["terminal_context"] == "NON_CANONICAL_DIAGNOSTIC_CONTEXT"
    assert gen2["screenshot_context"] == "NON_CANONICAL_DIAGNOSTIC_CONTEXT"

    completed = {item["task_id"]: item for item in state["completed_milestones"]}
    assert completed["TASK-228"]["classification"] == (
        "PRE_ACTION_EVIDENCE_ACQUISITION_PLAN_ONLY"
    )
    assert completed["TASK-229"]["classification"] == (
        "MANUAL_WAVE_1_EVIDENCE_CONTRIBUTION_AUTHORIZATION_ONLY"
    )
    assert completed["TASK-230"]["classification"] == (
        "P8_WAVE_0_TIKTOK_PDP_IDENTITY_COMPATIBILITY_ONLY"
    )
    assert completed["TASK-231"]["classification"] == (
        "PUBLIC_PDP_ACQUISITION_CONTRACT_ONLY"
    )
    assert completed["TASK-231"]["collector_implemented"] is False
    assert completed["TASK-231"]["source_sha"] == (
        "c533ee90201a5e0400b7973e89ab5c58677501ba"
    )
    assert completed["TASK-231"]["live_public_pdp_acquisition_authority"] == "NONE"
    assert completed["TASK-232"]["classification"] == (
        "BOUNDED_OFFLINE_FIRST_IMPLEMENTATION_ONLY"
    )
    assert completed["TASK-232"]["implementation_exists"] is True
    assert completed["TASK-232"]["source_sha"] == (
        "cf68d388c740cca66194bc04dafbb12e86cf8049"
    )
    assert completed["TASK-232"]["post_publication_handoff"] == (
        "HUMAN_BRAIN_LIVE_PUBLIC_PDP_PILOT_AUTHORIZATION"
    )
    assert completed["TASK-233"]["classification"] == (
        "ONE_SHOT_LIVE_PUBLIC_PDP_PILOT_ENABLEMENT_AND_AUTHORIZATION"
    )
    assert completed["TASK-233"]["authorized_capture_attempts"] == 1
    assert completed["TASK-233"]["authorized_capture_attempts_remaining"] == 0
    assert completed["TASK-233"]["source_sha"] == (
        "99338787dcfff5e1897b9d58c12b04f7961f6e58"
    )
    assert completed["TASK-233"]["post_publication_handoff"] == "COMPLETE"
    assert completed["TASK-234"]["classification"] == (
        "LIVE_PILOT_RECONCILIATION_AND_OFFLINE_DOM_DIAGNOSTIC_ENABLEMENT_ONLY"
    )
    assert completed["TASK-234"]["source_sha"] == (
        "2859813fd58e63f5434d44f9e76eba78d8a9c41f"
    )
    assert completed["TASK-234"]["post_publication_handoff"] == (
        "HUMAN_BRAIN_ONE_SHOT_PUBLIC_PDP_DOM_DIAGNOSTIC_AUTHORIZATION"
    )
    assert completed["TASK-235"]["classification"] == (
        "ONE_SHOT_ATTACH_ONLY_PUBLIC_PDP_DOM_DIAGNOSTIC_AUTHORIZATION_ONLY"
    )
    assert completed["TASK-235"]["authorized_diagnostic_attempts"] == 1
    assert completed["TASK-235"]["source_sha"] == "eedad88f5c676c647d418da62e554529ea29b161"
    assert completed["TASK-235"]["authorized_diagnostic_attempts_remaining"] == 0
    assert completed["TASK-235"]["diagnostic_outcome"] == "FAIL_CLOSED"
    assert completed["TASK-235"]["post_publication_handoff"] == (
        "CONSUMED_FAIL_CLOSED_PENDING_FRESH_HUMAN_BRAIN_AUTHORIZATION"
    )
    assert completed["TASK-236"]["classification"] == (
        "FAILED_LIVE_DOM_DIAGNOSTIC_RECONCILIATION_AND_BOUNDED_ADMISSION_HARDENING_ONLY"
    )
    assert completed["TASK-236"]["source_sha"] == TASK_236_SOURCE_SHA
    assert completed["TASK-236"]["diagnostic_executed"] is True
    assert completed["TASK-236"]["diagnostic_outcome"] == "FAIL_CLOSED"
    assert completed["TASK-236"]["diagnostic_artifact_created"] is False
    assert completed["TASK-236"]["authorized_diagnostic_attempts"] == 1
    assert completed["TASK-236"]["authorized_diagnostic_attempts_remaining"] == 0
    assert completed["TASK-236"]["live_dom_diagnostic_authority"] == "NONE"
    assert completed["TASK-236"]["diagnostic_hardening_implemented"] is True
    assert completed["TASK-236"]["selector_repair_complete"] is False
    assert completed["TASK-236"]["post_publication_handoff"] == (
        "HUMAN_BRAIN_FRESH_ONE_SHOT_PUBLIC_PDP_DOM_DIAGNOSTIC_AUTHORIZATION"
    )
    assert completed["TASK-237"]["classification"] == (
        "FRESH_ONE_SHOT_ATTACH_ONLY_PUBLIC_PDP_DOM_DIAGNOSTIC_AUTHORIZATION_ONLY"
    )
    assert completed["TASK-237"]["source_sha"] == TASK_236_SOURCE_SHA
    assert completed["TASK-237"]["diagnostic_authorization_generation"] == 2
    assert completed["TASK-237"]["live_dom_diagnostic_authority"] == (
        "ONE_SHOT_ATTACH_ONLY_EXACT_LISTING"
    )
    assert completed["TASK-237"]["fresh_authorized_diagnostic_attempts"] == 1
    assert completed["TASK-237"]["fresh_authorized_diagnostic_attempts_remaining"] == 1
    assert completed["TASK-237"]["fresh_diagnostic_execution_owner"] == "HUMAN_OPERATOR"
    assert completed["TASK-237"]["fresh_diagnostic_executed"] is False
    assert completed["TASK-237"]["diagnostic_hardening_implemented"] is True
    assert completed["TASK-237"]["selector_repair_complete"] is False
    assert completed["TASK-237"]["post_publication_handoff"] == (
        "HUMAN_OPERATOR_FRESH_ONE_SHOT_PUBLIC_PDP_DOM_DIAGNOSTIC_EXECUTION"
    )
    assert completed["TASK-238"]["classification"] == (
        "GENERATION_2_FAIL_CLOSED_RECONCILIATION_AND_BOUNDED_ROOT_OBSERVABILITY_HARDENING_ONLY"
    )
    assert completed["TASK-238"]["published_source_sha"] == TASK_238_PUBLISHED_SOURCE_SHA
    assert completed["TASK-238"]["diagnostic_authorization_generation"] == 2
    assert completed["TASK-238"]["live_dom_diagnostic_authority"] == "NONE"
    assert completed["TASK-238"]["diagnostic_executed"] is True
    assert completed["TASK-238"]["diagnostic_outcome"] == "FAIL_CLOSED"
    assert completed["TASK-238"]["diagnostic_failure_reason"] == "NO_BOUNDED_PDP_ROOT"
    assert completed["TASK-238"]["diagnostic_artifact_created"] is False
    assert completed["TASK-238"]["authorized_diagnostic_attempts"] == 1
    assert completed["TASK-238"]["authorized_diagnostic_attempts_remaining"] == 0
    assert completed["TASK-238"]["diagnostic_execution_owner"] == "HUMAN_OPERATOR"
    assert completed["TASK-238"]["root_observability_hardening_implemented"] is True
    assert completed["TASK-238"]["diagnostic_hardening_implemented"] is True
    assert completed["TASK-238"]["selector_repair_complete"] is False
    assert completed["TASK-238"]["post_publication_handoff"] == (
        "HUMAN_BRAIN_FRESH_ROOT_OBSERVABILITY_DIAGNOSTIC_AUTHORIZATION"
    )
    assert completed["TASK-239"]["classification"] == (
        "FRESH_GENERATION_3_ROOT_OBSERVABILITY_DIAGNOSTIC_AUTHORIZATION_ONLY"
    )
    assert completed["TASK-239"]["source_task_id"] == "TASK-238"
    assert completed["TASK-239"]["source_run_id"] == "RUN-238-002"
    assert completed["TASK-239"]["source_review_id"] == "REVIEW-238-001"
    assert completed["TASK-239"]["diagnostic_implementation_source_sha"] == (
        TASK_238_PUBLISHED_SOURCE_SHA
    )
    assert completed["TASK-239"]["diagnostic_authorization_generation"] == 3
    assert completed["TASK-239"]["generation_3_authorized_diagnostic_attempts"] == 1
    assert completed["TASK-239"]["generation_3_authorized_diagnostic_attempts_remaining"] == 1
    assert completed["TASK-239"]["generation_3_diagnostic_execution_owner"] == "HUMAN_OPERATOR"
    assert completed["TASK-239"]["generation_3_diagnostic_executed"] is False
    assert completed["TASK-239"]["diagnostic_executed"] is False
    assert completed["TASK-239"]["evidence_authority"] == "NONE"
    assert completed["TASK-239"]["post_publication_handoff"] == (
        "HUMAN_OPERATOR_GENERATION_3_ROOT_OBSERVABILITY_DIAGNOSTIC_EXECUTION"
    )
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
    # The publication-gated TASK-230 shape is preserved below as a regression guard,
    # but it must no longer be the current active-track bookmark after TASK-231.
    assert state["active_track"] != {
        "id": "P8_WAVE_0_TIKTOK_PDP_IDENTITY_COMPATIBILITY",
        "title": "P8 Wave-0 TikTok PDP Identity Compatibility",
        "priority_owner": "HUMAN",
        "status": "DONE",
        "completion_basis": "PUBLICATION_GATED",
        "sequence_status": "COMPLETE_ON_EXACT_TASK_230_SOURCE_PUBLICATION",
        "current_milestone": {
            "id": "P8.WAVE_0.COMPATIBILITY",
            "task_id": "TASK-230",
            "title": "TikTok PDP Identity Compatibility and Parser Authority Consolidation",
            "status": "DONE",
            "completion_basis": "PUBLICATION_GATED",
            "classification": "P8_WAVE_0_TIKTOK_PDP_IDENTITY_COMPATIBILITY_ONLY",
            "authorization_owner": "HUMAN_BRAIN",
            "real_pilot_executed": False,
            "live_evidence_acquired": False,
            "automatic_progression": False,
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
    # The old TASK-230 handoff remains historical context, not current state.
    assert state["post_p8_planning_handoff"] != {
        "destination": "HUMAN_BRAIN_PUBLIC_PDP_ACQUISITION_AUTHORIZATION",
        "status": "EFFECTIVE_ON_EXACT_TASK_230_SOURCE_PUBLICATION",
        "completed_commitment": "P8_WAVE_0_TIKTOK_PDP_IDENTITY_COMPATIBILITY",
        "actual_real_decision_case": {
            "context_id": "p8-pilot-001-led-motion-tiktok-vn",
            "record_type": "PILOT_CASE_SELECTION_ONLY",
            "product_label": (
                "Đèn LED Cảm Biến Chuyển Động Tự Động Bật Tắt Điều Chỉnh 3 Chế Độ Sáng"
            ),
            "marketplace": "TikTok Shop Vietnam",
            "channel_context": "TikTok Shop Affiliate",
            "source_id": SELECTED_SOURCE_ID,
            "stable_listing_reference": SELECTED_LISTING_REFERENCE,
            "identity_scope": "SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY",
            "selection_owner": "HUMAN",
            "selection_status": "SELECTED",
            "real_pilot_executed": False,
        },
        "next_milestone": None,
        "automatic_next": False,
        "automatic_p8_4": False,
        "automated_public_pdp_acquisition_authority": "NONE",
        "real_pilot_executed": False,
        "live_evidence_acquired": False,
        "compatibility_closure": {
            "document": "docs/PHASE_8_WAVE_0_TIKTOK_PDP_IDENTITY_COMPATIBILITY.md",
            "classification": "P8_WAVE_0_TIKTOK_PDP_IDENTITY_COMPATIBILITY_ONLY",
            "task_id": "TASK-230",
            "canonical_parser": (
                "src/product_intelligence/adapters/tiktok_parsing.py::"
                "extract_tiktok_product_id"
            ),
            "exact_source_id": SELECTED_SOURCE_ID,
            "parser_authority_count": 1,
            "capability_not_evidence": True,
            "public_pdp_affiliate_dependency": "NONE",
            "source_identity_scope": "SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY",
        },
        "manual_contribution_authorization": {
            "document": (
                "docs/PHASE_8_P8_3_MANUAL_WAVE_1_EVIDENCE_CONTRIBUTION_AUTHORIZATION.md"
            ),
            "classification": "MANUAL_WAVE_1_EVIDENCE_CONTRIBUTION_AUTHORIZATION_ONLY",
            "operation_owner": "HUMAN_OPERATOR",
            "source_surfaces": ["TIKTOK_SHOP_PDP", "TIKTOK_AFFILIATE_UI"],
            "authorized_observation_names": P8_3_AUTHORIZED_OBSERVATIONS,
            "p7_4_organization": {
                "affiliate_economics": [
                    "current_price",
                    "original_price",
                    "discount_percent",
                    "affiliate_eligibility",
                    "affiliate_commission_rate",
                    "estimated_commission_value",
                ],
                "market_traction": ["sold_count", "rating", "review_count"],
                "provenance_context_helpers": [
                    "variant_descriptor",
                    "inventory_availability",
                ],
            },
            "transport_schema": "manual-wave-1-evidence-contribution/v1",
            "transport_location": "EXTERNAL_ONLY",
            "contribution_status": "UNPERFORMED_BY_TASK",
            "review_status": "UNPERFORMED_BY_TASK",
            "exact_binding": "FAIL_CLOSED",
            "artifact_handling": "OPAQUE_SAFE_PROVENANCE_HANDLES_ONLY",
            "production_mutation_authority": "NONE",
            "p7_4_construction_authority": "NONE",
            "p7_5_construction_authority": "NONE",
            "wave_0_authority": "NONE",
            "wave_2_authority": "NONE",
            "market_test_or_action_authority": "NONE",
            "human_owned_inputs_status": "UNSET",
            "collector_authority": "NONE",
            "automated_acquisition_authority": "NONE",
        },
        "boundary": (
            "TASK-230 closes only the Human-selected Wave-0 PDP identity compatibility and "
            "one-parser-authority consolidation for the exact P8.1 case. It acquires, accepts, "
            "freezes, and promotes no evidence; creates no Affiliate dependency for public PDP "
            "product/source intelligence; authorizes no collector, later acquisition, P7.4/P7.5 "
            "construction, Wave 1, Wave 2, market test, P8.4, or commerce action; and executes no "
            "real pilot. TASK-229 remains completed authorization history with contribution and "
            "review unperformed. Control returns to a fresh Human/Brain authorization decision, "
            "and no successor or future domain is automatic."
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
        assert TASK_226_SOURCE_SHA in roadmap
        assert "P8.1 Real Decision Pilot Selection" in roadmap
        assert "TASK-227 — publication-gated DONE; `PILOT_CASE_SELECTION_ONLY`" in roadmap
        assert SELECTED_SOURCE_ID in roadmap
        assert SELECTED_LISTING_REFERENCE in roadmap
        assert "Source identity is not canonical product identity" in roadmap
        assert "P8.2 Pre-Action Evidence Acquisition Plan" in roadmap
        assert "PRE_ACTION_EVIDENCE_ACQUISITION_PLAN_ONLY" in roadmap
        assert TASK_227_SOURCE_SHA in roadmap
        assert "P8.3 Manual Wave-1 Evidence Contribution Authorization" in roadmap
        assert "MANUAL_WAVE_1_EVIDENCE_CONTRIBUTION_AUTHORIZATION_ONLY" in roadmap
        assert TASK_228_SOURCE_SHA in roadmap
        assert "HUMAN_OPERATOR_MANUAL_WAVE_1_CONTRIBUTION_AND_REVIEW" in roadmap
        assert "P8_WAVE_0_TIKTOK_PDP_IDENTITY_COMPATIBILITY_ONLY" in roadmap
        assert "HUMAN_BRAIN_PUBLIC_PDP_ACQUISITION_AUTHORIZATION" in roadmap
        assert "automated_public_pdp_acquisition_authority` is `NONE" in roadmap
        assert "PUBLIC_PDP_ACQUISITION_CONTRACT_ONLY" in roadmap
        assert "P8_PUBLIC_PDP_COLLECTOR_IMPLEMENTATION" in roadmap
        assert "HUMAN_BRAIN_LIVE_PUBLIC_PDP_PILOT_AUTHORIZATION" in roadmap
        assert "live_public_pdp_acquisition_authority` is `NONE" in roadmap
        assert "ONE_SHOT_LIVE_PUBLIC_PDP_PILOT_ENABLEMENT_AND_AUTHORIZATION" in roadmap
        assert "ONE_SHOT_EXACT_LISTING_ONLY" in roadmap
        assert "HUMAN_OPERATOR_ONE_SHOT_PUBLIC_PDP_CAPTURE_EXECUTION" in roadmap
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
        "Composition completeness != real-world\nsuccess",
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
    assert completed["TASK-226"]["source_sha"] == TASK_226_SOURCE_SHA
    assert completed["TASK-226"]["composition_contract_only"] is True
    assert completed["TASK-226"]["real_pilot_executed"] is False
    assert state["active_track"]["next_milestone"] is None
    assert state["pending_commitments"] == []
    assert state["post_p8_planning_handoff"]["automatic_p8_4"] is False


def test_p8_1_records_selection_only_and_preserves_pre_action_boundaries():
    text = P8_1_SELECTION_FILE.read_text(encoding="utf-8")
    for required in (
        "PILOT_CASE_SELECTION_ONLY",
        "Đèn LED Cảm Biến Chuyển Động Tự Động Bật Tắt Điều Chỉnh 3 Chế Độ Sáng",
        "TikTok Shop Vietnam",
        "TikTok Shop Affiliate planning context",
        SELECTED_SOURCE_ID,
        SELECTED_LISTING_REFERENCE,
        "SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY",
        "p8-pilot-001-led-motion-tiktok-vn",
        "p8-pilot-001-positive-contribution-margin",
        "Should the Human authorize a bounded TikTok Shop affiliate market test for this exact "
        "selected listing after reviewing decision-relevant evidence?",
        "Reduce uncertainty enough for the Human to decide whether a bounded affiliate market "
        "test is justified, while preserving evidence gaps, alternatives, and action authority.",
        "Under an authorized bounded TikTok Shop affiliate market test, this exact selected "
        "listing can produce positive contribution margin without violating the Human-defined "
        "quality, exposure, economic, and risk constraints for that test.",
        "This is a hypothesis, not truth, approval, recommendation",
        "Unknown != absent. Unknown != authorization to collect.",
        "Similar-\nlisting search results, URL slug text, historical benchmark cohorts, and synthetic fixtures",
        "PRE-ACTION EVIDENCE\nACQUISITION PLAN",
        "No P8.2 or future domain is automatically selected",
    ):
        assert required in text

    for unknown in (
        "current exact listing price and variant economics",
        "affiliate commission rate and estimated commission value",
        "current sold, review, and rating evidence",
        "creator ecosystem",
        "content activity and video evidence",
        "audience-channel fit",
        "competition saturation",
        "inventory or availability where decision-relevant",
        "contribution-margin threshold, budget, duration, and risk constraints",
    ):
        assert unknown in text

    assert "P7.3 remains the sole semantic owner and constructor" in text
    assert "currently affiliate-eligible" in text
    assert "No current price, shop, sold count, rating" in text

    state = load_yaml(ROADMAP_FILE)
    selected = state["post_p8_planning_handoff"]["actual_real_decision_case"]
    assert selected["source_id"] == SELECTED_SOURCE_ID
    assert selected["stable_listing_reference"] == SELECTED_LISTING_REFERENCE
    assert selected["identity_scope"] == "SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY"
    assert selected["selection_owner"] == "HUMAN"
    assert selected["selection_status"] == "SELECTED"
    assert selected["real_pilot_executed"] is True
    assert state["post_p8_planning_handoff"]["automatic_next"] is False
    assert state["post_p8_planning_handoff"]["automatic_p8_4"] is False
    assert state["active_track"]["next_milestone"] is None
    assert state["pending_commitments"] == []


def test_p8_2_is_plan_only_and_preserves_evidence_and_action_boundaries():
    text = P8_2_EVIDENCE_PLAN_FILE.read_text(encoding="utf-8")

    for required in (
        "PRE_ACTION_EVIDENCE_ACQUISITION_PLAN_ONLY",
        "p8-pilot-001-led-motion-tiktok-vn",
        SELECTED_SOURCE_ID,
        SELECTED_LISTING_REFERENCE,
        "SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY",
        "WAVE_0_COMPATIBILITY_PREREQUISITE",
        "WAVE_1_MINIMUM_DECISION_EVIDENCE",
        "WAVE_2_CONDITIONAL_EVIDENCE",
        "/vn/pdp/<slug>/<id>",
        "not the selected `/vn/pdp/<slug>/<id>` form",
        "TASK-228 does\nnot fix either parser",
        "Technical\ncapability does not authorize use",
        "Human/operator owns login",
        "zero automatic CAPTCHA solving",
        "explicit external job root",
        "Human reviews any `READY` capture",
        "Runtime or worker output\ncannot make that decision",
        "P8.3 is neither\nautomatic nor pending",
    ):
        assert required in text

    stop_section = text.split("## 7. Explicit STOP and DEFER conditions", 1)[1].split(
        "## 8. Boundary for any later live evidence operation", 1
    )[0]
    for required in (
        "would require automated solving, automated retry, bypass, evasion",
        "no legitimate Human-operated path is available",
        "A Human may\nresolve the challenge outside ordinary AIOS verification",
        "challenge resolution grants no\nevidence, collector, test, or action authority",
        "Any resume requires a separate, fresh explicit\nHuman/Brain-authorized operation",
    ):
        assert required in stop_section
    assert "the source requires CAPTCHA solving" not in stop_section

    dimensions = (
        "affiliate_economics",
        "market_traction",
        "creator_ecosystem",
        "content_activity",
        "audience_channel_fit",
        "competition_saturation",
    )
    dimension_section = text.split(
        "## 2. Fixed P7.4 evidence-dimension boundary", 1
    )[1].split("## 3.", 1)[0]
    assert [
        match.group(1)
        for match in re.finditer(r"^\d+\. `([a-z_]+)`$", dimension_section, re.MULTILINE)
    ] == list(dimensions)

    for inquiry in re.split(r"^### W[12]-[A-Z] — ", text, flags=re.MULTILINE)[1:]:
        inquiry = inquiry.split("\n## ", 1)[0]
        for consideration in (
            "**Expected decision impact:**",
            "**Uncertainty reduction:**",
            "**Cost:**",
            "**Latency:**",
            "**Access risk:**",
            "**Fragility:**",
            "**Reliability:**",
            "**Opportunity cost:**",
            "**Decision-deadline consideration:**",
        ):
            assert consideration in inquiry

    for forbidden in (
        "universal numeric VOI score",
        "evidence-priority score",
        "acquisition-order authority",
    ):
        assert forbidden in text

    state = load_yaml(ROADMAP_FILE)
    completed = {item["task_id"]: item for item in state["completed_milestones"]}
    assert completed["TASK-228"]["source_sha"] == TASK_228_SOURCE_SHA
    handoff = state["post_p8_planning_handoff"]
    assert handoff["automatic_next"] is False
    assert handoff["automatic_p8_4"] is False
    assert handoff["real_pilot_executed"] is True
    assert handoff["live_evidence_acquired"] is True
    assert handoff["canonical_evidence_ingested"] is False
    authorization = handoff["manual_contribution_authorization"]
    assert authorization["human_owned_inputs_status"] == "UNSET"
    assert authorization["collector_authority"] == "NONE"
    assert authorization["automated_acquisition_authority"] == "NONE"
    assert state["active_track"]["next_milestone"] is None
    assert state["pending_commitments"] == []


def test_p8_3_authorizes_only_human_manual_contribution_and_review():
    text = P8_3_MANUAL_AUTHORIZATION_FILE.read_text(encoding="utf-8")

    for required in (
        "MANUAL_WAVE_1_EVIDENCE_CONTRIBUTION_AUTHORIZATION_ONLY",
        "p8-pilot-001-led-motion-tiktok-vn",
        SELECTED_SOURCE_ID,
        SELECTED_LISTING_REFERENCE,
        "SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY",
        "manual-wave-1-evidence-contribution/v1",
        "timezone-aware observation time",
        "TIKTOK_SHOP_PDP",
        "TIKTOK_AFFILIATE_UI",
        "displayed_value",
        "binding_basis",
        "artifact_ref",
        "variant_context",
        "Title-only, image-only, seller-only, slug-only",
        "If exact binding cannot be demonstrated",
        "opaque provenance handles only",
        "ACCEPT`, `REJECT`, or `UNKNOWN",
        "usability only as source evidence",
        "Human/operator outside ordinary\nAIOS verification",
        "Automated solving, automated retry, proxy use, stealth, evasion, and bypass",
        "Wave 0 or Wave 2 merely to complete fields",
        "Nothing progresses automatically, including P8.4 or a market test",
        "HUMAN_OPERATOR_MANUAL_WAVE_1_CONTRIBUTION_AND_REVIEW",
    ):
        assert required in text

    observation_section = text.split("## 2. Exact authorized observation set", 1)[1].split(
        "## 3. Human-only operating boundary", 1
    )[0]
    assert [
        match.group(1)
        for match in re.finditer(
            r"^\d+\. `([a-z_]+)`$", observation_section, flags=re.MULTILINE
        )
    ] == P8_3_AUTHORIZED_OBSERVATIONS

    for deferred in (
        "Product/source facts and seller media",
        "Wave 2\ncreator, content, audience, competition, and velocity capture is not authorized",
    ):
        assert deferred in text

    for prohibited_payload in (
        "cookies",
        "tokens",
        "headers",
        "credentials",
        "raw HTML",
        "browser-profile paths",
        "QR/login codes",
        "private messages",
        "exception traces",
        "local absolute paths",
    ):
        assert prohibited_payload in text

    for unset_input in (
        "Budget",
        "duration",
        "exposure controls",
        "contribution-margin threshold",
        "success/failure criteria",
        "target audience",
        "quality constraints",
        "risk constraints",
        "risk acceptance",
        "decision deadline",
    ):
        assert unset_input in text

    state = load_yaml(ROADMAP_FILE)
    authorization = state["post_p8_planning_handoff"][
        "manual_contribution_authorization"
    ]
    assert authorization["authorized_observation_names"] == P8_3_AUTHORIZED_OBSERVATIONS
    assert authorization["transport_location"] == "EXTERNAL_ONLY"
    assert authorization["exact_binding"] == "FAIL_CLOSED"
    assert authorization["production_mutation_authority"] == "NONE"
    assert authorization["p7_4_construction_authority"] == "NONE"
    assert authorization["p7_5_construction_authority"] == "NONE"
    assert authorization["wave_0_authority"] == "NONE"
    assert authorization["wave_2_authority"] == "NONE"
    assert authorization["market_test_or_action_authority"] == "NONE"
    assert state["post_p8_planning_handoff"]["automatic_p8_4"] is False
    assert state["active_track"]["next_milestone"] is None
    assert state["pending_commitments"] == []


def test_task_230_closes_only_pdp_compatibility_with_one_parser_authority():
    closure = P8_WAVE_0_COMPATIBILITY_FILE.read_text(encoding="utf-8")
    parser_source = (
        REPO_ROOT / "src" / "product_intelligence" / "adapters" / "tiktok_parsing.py"
    ).read_text(encoding="utf-8")
    extractor_source = (
        REPO_ROOT / "src" / "product_source" / "platforms" / "tiktok.py"
    ).read_text(encoding="utf-8")

    for required in (
        "P8_WAVE_0_TIKTOK_PDP_IDENTITY_COMPATIBILITY_ONLY",
        "p8-pilot-001-led-motion-tiktok-vn",
        SELECTED_SOURCE_ID,
        SELECTED_LISTING_REFERENCE,
        "SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY",
        "Parser compatibility is capability, not evidence",
        "semantically independent from TikTok Affiliate account",
        "contribution and review remain\nunperformed",
        "HUMAN_BRAIN_PUBLIC_PDP_ACQUISITION_AUTHORIZATION",
        "automated_public_pdp_acquisition_authority` is `NONE",
    ):
        assert required in closure

    assert parser_source.count("def extract_tiktok_product_id(") == 1
    assert (
        "from src.product_intelligence.adapters.tiktok_parsing import "
        "extract_tiktok_product_id"
    ) in extractor_source
    assert "product_id = extract_tiktok_product_id(product_url)" in extractor_source
    assert "def _extract_tiktok_product_id" not in extractor_source
    assert "import re" not in extractor_source
    assert "itemUrl.match(" not in extractor_source

    state = load_yaml(ROADMAP_FILE)
    completed = {item["task_id"]: item for item in state["completed_milestones"]}
    assert completed["TASK-229"]["classification"] == (
        "MANUAL_WAVE_1_EVIDENCE_CONTRIBUTION_AUTHORIZATION_ONLY"
    )
    assert completed["TASK-229"]["contribution_performed_by_task"] is False
    assert completed["TASK-229"]["review_performed_by_task"] is False
    assert completed["TASK-229"]["live_evidence_acquired"] is False
    assert completed["TASK-230"]["classification"] == (
        "P8_WAVE_0_TIKTOK_PDP_IDENTITY_COMPATIBILITY_ONLY"
    )
    assert completed["TASK-230"]["parser_authority_count"] == 1
    assert completed["TASK-230"]["public_pdp_affiliate_dependency"] == "NONE"

    handoff = state["post_p8_planning_handoff"]
    assert handoff["automated_public_pdp_acquisition_authority"] == "NONE"
    assert handoff["automatic_next"] is False
    assert handoff["automatic_p8_4"] is False
    assert handoff["real_pilot_executed"] is True
    assert handoff["live_evidence_acquired"] is True
    assert handoff["canonical_evidence_ingested"] is False
    assert handoff["manual_contribution_authorization"]["contribution_status"] == (
        "UNPERFORMED_BY_TASK"
    )
    assert handoff["manual_contribution_authorization"]["review_status"] == (
        "UNPERFORMED_BY_TASK"
    )
    assert state["active_track"]["next_milestone"] is None
    assert state["pending_commitments"] == []


def test_task_231_contract_preserves_owners_allowlist_and_zero_live_authority():
    contract = P8_PUBLIC_PDP_ACQUISITION_CONTRACT_FILE.read_text(encoding="utf-8")
    parser_source = (
        REPO_ROOT / "src" / "product_intelligence" / "adapters" / "tiktok_parsing.py"
    ).read_text(encoding="utf-8")
    exact_listing_gate = contract.split(
        "## 6. Fail-closed exact-listing admission", 1
    )[1].split("## 7. Public and Affiliate lanes are independent", 1)[0]

    for required in (
        "PUBLIC_PDP_ACQUISITION_CONTRACT_ONLY",
        "CAPABILITY_IS_NOT_AUTHORITY",
        "EVIDENCE_IS_NOT_PRODUCT_TRUTH",
        "SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY",
        "SNAPSHOT_IS_NOT_TREND",
        "ProductCandidateSnapshot",
        "SignalEvidence",
        "ProductSourcePack",
        "seller/source facts, descriptions, and original\nmedia",
        "must not depend on\n`ProductSourcePack` extraction",
        "`TikTokSourceExtractor`",
        "Google Drive",
        "`TikTokScrapeTool`",
        "src/product_intelligence/adapters/tiktok_parsing.py",
        "AMBIGUOUS_PRICE_IS_NOT_EXACT_PRICE",
        "lower bound, upper bound, midpoint, first variant",
        "search-card lower-bound parsing must never be cited as exact-PDP scalar-price evidence",
        "redirect to search, login, challenge",
        "valid requested target source ID",
        "require it to equal the requested\n   target source ID",
        "malformed or unverifiable requested/observed identity",
        "zero fabricated observations",
        "semantically independent from authenticated TikTok\nAffiliate access",
        "Affiliate eligibility",
        "Wave-2 evidence",
        "variant_descriptor",
        "inventory_availability",
        "sales_velocity",
        "review_velocity",
        "creator_velocity",
        "video_velocity",
        "P8_PUBLIC_PDP_COLLECTOR_IMPLEMENTATION",
        "bounded offline-first implementation only",
        "implementation_authorized: true",
        "live_public_pdp_acquisition_authority: NONE",
        "automatic_live_pilot: false",
        "automatic_p8_4: false",
        "market_test_or_action_authority: NONE",
        "HUMAN_BRAIN_LIVE_PUBLIC_PDP_PILOT_AUTHORIZATION",
        "not a\nuniversal V1 source-ID allowlist",
        "reusable capability may validate a requested TikTok PDP target other than the current P8 pilot\nlisting",
        "technical ability grants no authority to acquire it live",
    ):
        assert required in contract

    assert parser_source.count("def extract_tiktok_product_id(") == 1
    assert "canonical TikTok product-ID parser" in exact_listing_gate
    assert "same canonical identity authority" in exact_listing_gate
    assert SELECTED_SOURCE_ID not in exact_listing_gate
    assert "require the requested ID to equal the authorized exact source ID" not in contract

    state = load_yaml(ROADMAP_FILE)
    contract_state = state["post_p8_planning_handoff"][
        "public_pdp_acquisition_contract"
    ]
    assert contract_state["classification"] == "PUBLIC_PDP_ACQUISITION_CONTRACT_ONLY"
    assert contract_state["semantic_owner"] == "ProductCandidateSnapshot"
    assert contract_state["field_evidence_owner"] == "SignalEvidence"
    assert contract_state["product_source_pack_scope"] == (
        "SELLER_FACTS_AND_ORIGINAL_MEDIA_ONLY"
    )
    assert contract_state["parser_authority_count"] == 1
    assert contract_state["public_pdp_affiliate_dependency"] == "NONE"
    assert contract_state["exact_listing_binding"] == "FAIL_CLOSED"
    assert contract_state["ambiguous_price_law"] == (
        "AMBIGUOUS_PRICE_IS_NOT_EXACT_PRICE"
    )
    assert contract_state["snapshot_law"] == "SNAPSHOT_IS_NOT_TREND"
    assert contract_state["v1_observation_allowlist"] == P8_PUBLIC_PDP_V1_ALLOWLIST
    assert contract_state["variant_descriptor_authority"] == "DEFERRED_CONTEXT_ONLY"
    assert contract_state["inventory_availability_authority"] == (
        "DEFERRED_CONTEXT_ONLY"
    )
    assert contract_state["affiliate_fields_authority"] == "NONE"
    assert contract_state["wave_2_authority"] == "NONE"
    assert contract_state["velocity_or_trend_authority"] == "NONE"
    assert contract_state["implementation_authorized"] is True
    assert contract_state["live_public_pdp_acquisition_authority"] == "NONE"
    assert contract_state["automatic_live_pilot"] is False
    assert contract_state["automatic_p8_4"] is False
    assert contract_state["market_test_or_action_authority"] == "NONE"


def test_task_232_collector_preserves_product_browser_and_authority_boundaries():
    document = P8_PUBLIC_PDP_COLLECTOR_IMPLEMENTATION_FILE.read_text(encoding="utf-8")
    adapter = (
        REPO_ROOT / "src" / "product_intelligence" / "adapters" / "tiktok_pdp.py"
    ).read_text(encoding="utf-8")
    parser = (
        REPO_ROOT / "src" / "product_intelligence" / "adapters" / "tiktok_parsing.py"
    ).read_text(encoding="utf-8")

    for required in (
        "BOUNDED_OFFLINE_FIRST_IMPLEMENTATION_ONLY",
        "ProductCandidateSnapshot",
        "SignalEvidence",
        "already-provided `BrowserSession`-like dependency",
        "AMBIGUOUS_PRICE_IS_NOT_EXACT_PRICE",
        "explicit observed zero",
        "transport-only binding receipt",
        "SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY",
        "SNAPSHOT_IS_NOT_TREND",
        "zero live authority",
        "HUMAN_BRAIN_LIVE_PUBLIC_PDP_PILOT_AUTHORIZATION",
    ):
        assert required in document

    assert parser.count("def extract_tiktok_product_id(") == 1
    assert "from src.browser.session import BrowserSession" in adapter
    assert "from src.product_intelligence.models import ProductCandidateSnapshot" in adapter
    assert "PlaywrightBrowserManager" not in adapter
    assert "ProductSourcePack" not in adapter
    assert "TikTokSourceExtractor" not in adapter
    assert "TikTokScrapeTool" not in adapter
    assert ".start(" not in adapter
    assert ".close(" not in adapter
    assert ".click(" not in adapter

    state = load_yaml(ROADMAP_FILE)
    implementation = state["post_p8_planning_handoff"][
        "public_pdp_collector_implementation"
    ]
    assert implementation["semantic_owner"] == "ProductCandidateSnapshot"
    assert implementation["field_evidence_owner"] == "SignalEvidence"
    assert implementation["browser_dependency"] == (
        "ALREADY_PROVIDED_BROWSER_SESSION_ONLY"
    )
    assert implementation["parser_authority_count"] == 1
    assert implementation["product_source_dependency"] == "NONE"
    assert implementation["public_pdp_affiliate_dependency"] == "NONE"
    assert implementation["evidence_authority"] == "NONE"
    assert implementation["velocity_or_trend_authority"] == "NONE"
    assert implementation["implementation_exists"] is True
    assert implementation["offline_only"] is True
    assert implementation["live_public_pdp_acquisition_authority"] == "NONE"
    assert implementation["automated_public_pdp_acquisition_authority"] == "NONE"
    assert state["post_p8_planning_handoff"]["real_pilot_executed"] is True
    assert state["post_p8_planning_handoff"]["live_evidence_acquired"] is True
    assert state["post_p8_planning_handoff"]["canonical_evidence_ingested"] is False
    assert state["active_track"]["next_milestone"] is None
    assert state["pending_commitments"] == []


def test_task_233_authorizes_only_one_exact_human_operated_capture():
    document = P8_PUBLIC_PDP_LIVE_PILOT_AUTHORIZATION_FILE.read_text(
        encoding="utf-8"
    )
    carrier = (
        REPO_ROOT / "src" / "product_intelligence" / "tiktok_pdp_live_pilot.py"
    ).read_text(encoding="utf-8")
    for required in (
        "ONE_SHOT_LIVE_PUBLIC_PDP_PILOT_ENABLEMENT_AND_AUTHORIZATION",
        "p8-pilot-001-led-motion-tiktok-vn",
        SELECTED_SOURCE_ID,
        SELECTED_LISTING_REFERENCE,
        "Human operator owns",
        "explicit external `--job-root`",
        "no automatic retry",
        "mandatory Human review",
        "SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY",
        "EVIDENCE_IS_NOT_PRODUCT_TRUTH",
        "SNAPSHOT_IS_NOT_TREND",
        "HUMAN_OPERATOR_ONE_SHOT_PUBLIC_PDP_CAPTURE_EXECUTION",
    ):
        assert required in document

    assert carrier.count("collector.collect(") == 1
    assert "AUTHORIZED_SOURCE_ID = \"1731381331718341815\"" in carrier
    assert ".close(" not in carrier
    assert "manager.close_session(_SESSION_RUN_ID)" in carrier
    assert "close_all" not in carrier
    assert "ProductSource" not in carrier
    assert "Affiliate" not in carrier

    state = load_yaml(ROADMAP_FILE)
    handoff = state["post_p8_planning_handoff"]
    authorization = handoff["public_pdp_live_pilot_authorization"]
    assert authorization["live_public_pdp_acquisition_authority"] == "NONE"
    assert authorization["authorized_source_id"] == SELECTED_SOURCE_ID
    assert authorization["authorized_capture_attempts"] == 1
    assert authorization["authorized_capture_attempts_remaining"] == 0
    assert authorization["capture_execution_owner"] == "HUMAN_OPERATOR"
    assert authorization["browser_session_owner"] == "HUMAN_OPERATOR"
    assert authorization["artifact_boundary"] == "EXPLICIT_EXTERNAL_JOB_ROOT_ONLY"
    assert authorization["automatic_retry_or_resume"] is False
    assert authorization["public_pdp_affiliate_dependency"] == "NONE"
    assert authorization["source_evidence_only"] is True
    assert authorization["mandatory_post_capture_review"] == "HUMAN"
    assert authorization["automated_public_pdp_acquisition_authority"] == "NONE"
    assert authorization["automatic_live_pilot"] is False
    assert authorization["market_test_or_action_authority"] == "NONE"
    assert authorization["real_pilot_executed"] is True
    assert authorization["live_evidence_acquired"] is True
    assert authorization["canonical_evidence_ingested"] is False
    assert state["active_track"]["next_milestone"] is None
    assert state["pending_commitments"] == []


def test_task_234_reconciliation_and_diagnostic_preserve_authority_separation():
    state = load_yaml(ROADMAP_FILE)
    handoff = state["post_p8_planning_handoff"]
    diagnostic_record = handoff["public_pdp_dom_diagnostic"]
    review = P8_PUBLIC_PDP_LIVE_PILOT_REVIEW_FILE.read_text(encoding="utf-8")
    diagnostic = (
        REPO_ROOT / "src" / "product_intelligence" / "tiktok_pdp_dom_diagnostic.py"
    ).read_text(encoding="utf-8")
    authorization = P8_PUBLIC_PDP_LIVE_PILOT_AUTHORIZATION_FILE.read_text(
        encoding="utf-8"
    )

    assert handoff["authorized_capture_attempts"] == 1
    assert handoff["authorized_capture_attempts_remaining"] == 0
    assert handoff["real_pilot_executed"] is True
    assert handoff["live_evidence_acquired"] is True
    assert handoff["live_evidence_definition"] == (
        "EXTERNAL_BOUNDED_SOURCE_ARTIFACT_ONLY"
    )
    assert handoff["canonical_evidence_ingested"] is False
    assert handoff["observed_field_coverage"] == {
        "identity_binding": "OBSERVED",
        "title": "OBSERVED",
        "shop_name": "UNKNOWN",
        "price": "UNKNOWN",
        "original_price": "UNKNOWN",
        "discount_percent": "UNKNOWN",
        "sold_count": "UNKNOWN",
        "rating": "UNKNOWN",
        "review_count": "UNKNOWN",
    }
    assert handoff["screenshot_or_chat_values_as_canonical_evidence"] is False
    assert handoff["diagnostic_capability_scope"] == "CAPABILITY_IS_NOT_AUTHORITY"
    assert handoff["browser_lifecycle_authority"] == "TASK-137"
    assert diagnostic_record[
        "live_dom_diagnostic_authority_at_task_234_publication"
    ] == "NONE"
    assert handoff["automated_public_pdp_acquisition_authority"] == "NONE"
    assert handoff["market_test_or_action_authority"] == "NONE"
    assert diagnostic_record["diagnostic_executed"] is False
    assert handoff["selector_repair_complete"] is False
    assert handoff["next_milestone"] is None
    assert state["pending_commitments"] == []

    for invariant in (
        "EVIDENCE_IS_NOT_PRODUCT_TRUTH",
        "SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY",
        "SNAPSHOT_IS_NOT_TREND",
        "CAPABILITY_IS_NOT_AUTHORITY",
        "ONE_CAPABILITY_ONE_AUTHORITY",
        "HUMAN_BRAIN_ONE_SHOT_PUBLIC_PDP_DOM_DIAGNOSTIC_AUTHORIZATION",
    ):
        assert invariant in review
        assert all(
            invariant in roadmap.read_text(encoding="utf-8")
            for roadmap in ROADMAP_DOCS
        )

    assert "manager.close_session(run_id)" in authorization
    assert "TASK-137" in authorization
    assert "does not terminate borrowed Human-owned" in authorization
    assert "extract_tiktok_product_id" in diagnostic
    assert '"evidence_authority": "NONE"' in diagnostic
    assert "TikTokPdpCollector" not in diagnostic
    for forbidden in (
        "product_source",
        "affiliate",
        "scoring",
        "ranking",
        "approval",
        "persistence",
    ):
        assert f"from src.product_intelligence.{forbidden}" not in diagnostic.lower()


def test_task_235_authorizes_only_one_attach_only_human_dom_diagnostic_attempt():
    state = load_yaml(ROADMAP_FILE)
    handoff = state["post_p8_planning_handoff"]
    authorization = handoff["public_pdp_dom_diagnostic_authorization"]
    document = P8_PUBLIC_PDP_DOM_DIAGNOSTIC_AUTHORIZATION_FILE.read_text(
        encoding="utf-8"
    )

    assert authorization["classification"] == (
        "ONE_SHOT_ATTACH_ONLY_PUBLIC_PDP_DOM_DIAGNOSTIC_AUTHORIZATION_ONLY"
    )
    assert authorization["task_id"] == "TASK-235"
    assert authorization["diagnostic_implementation_task_id"] == "TASK-234"
    assert authorization["diagnostic_implementation_source_sha"] == (
        "2859813fd58e63f5434d44f9e76eba78d8a9c41f"
    )
    assert authorization["context_id"] == "p8-pilot-001-led-motion-tiktok-vn"
    assert authorization["authorized_source_id"] == SELECTED_SOURCE_ID
    assert authorization["stable_listing_reference"] == SELECTED_LISTING_REFERENCE
    assert authorization["live_dom_diagnostic_authority"] == "NONE"
    assert authorization["authorized_diagnostic_attempts"] == 1
    assert authorization["authorized_diagnostic_attempts_remaining"] == 0
    assert authorization["diagnostic_execution_owner"] == "HUMAN_OPERATOR"
    assert authorization["browser_session_owner"] == "HUMAN_OPERATOR"
    assert authorization["browser_lifecycle_authority"] == "TASK-137"
    assert authorization["exact_current_page_identity_gate"] == "FAIL_CLOSED"
    assert authorization["challenge_login_captcha_unavailable_gate"] == (
        "FAIL_CLOSED_ZERO_NAVIGATION_OR_INTERACTION"
    )
    assert authorization["attach_only"] is True
    assert authorization["navigation_or_interaction_authority"] == "NONE"
    assert authorization["arbitrary_target_or_batch_authority"] == "NONE"
    assert authorization["automatic_retry_refresh_resume"] is False
    assert authorization["artifact_boundary"] == "EXPLICIT_EXTERNAL_JOB_ROOT_ONLY"
    assert authorization["artifact_kind"] == (
        "EXTERNAL_STRUCTURAL_DIAGNOSTIC_OUTPUT_ONLY"
    )
    assert authorization["evidence_authority"] == "NONE"
    assert authorization["product_candidate_snapshot_authority"] == "NONE"
    assert authorization["signal_evidence_authority"] == "NONE"
    assert authorization["product_truth_or_ranking_authority"] == "NONE"
    assert authorization["diagnostic_implementation_exists"] is True
    assert authorization["diagnostic_executed"] is True
    assert authorization["diagnostic_outcome"] == "FAIL_CLOSED"
    assert authorization["diagnostic_artifact_created"] is False
    assert authorization["selector_repair_complete"] is False
    assert authorization["live_public_pdp_acquisition_authority"] == "NONE"
    assert authorization["automated_public_pdp_acquisition_authority"] == "NONE"
    assert authorization["market_test_or_action_authority"] == "NONE"
    assert authorization["automatic_progression"] is False
    assert authorization["mandatory_post_diagnostic_review"] == "HUMAN_BRAIN"

    assert handoff["authorized_capture_attempts_remaining"] == 0
    assert handoff["real_pilot_executed"] is True
    assert handoff["live_evidence_definition"] == (
        "EXTERNAL_BOUNDED_SOURCE_ARTIFACT_ONLY"
    )
    assert handoff["canonical_evidence_ingested"] is False
    assert handoff["next_milestone"] is None
    assert handoff["automatic_progression"] is False
    assert state["pending_commitments"] == []

    for required in (
        "1731381331718341815",
        SELECTED_LISTING_REFERENCE,
        "--job-root",
        "--cdp-endpoint",
        "evidence_authority=NONE",
        "ProductCandidateSnapshot",
        "SignalEvidence",
        "TASK-137",
        "authorized_capture_attempts_remaining=0",
        "HUMAN_OPERATOR_ONE_SHOT_PUBLIC_PDP_DOM_DIAGNOSTIC_EXECUTION",
        "CAPABILITY_IS_NOT_AUTHORITY",
        "EVIDENCE_IS_NOT_PRODUCT_TRUTH",
        "SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY",
        "SNAPSHOT_IS_NOT_TREND",
        "ONE_CAPABILITY_ONE_AUTHORITY",
    ):
        assert required in document
    for gate in ("login", "challenge", "CAPTCHA", "unavailable", "different-product"):
        assert gate in document


def test_task_236_reconciles_consumed_failure_and_hardens_capability_without_authority():
    state = load_yaml(ROADMAP_FILE)
    handoff = state["post_p8_planning_handoff"]
    hardening = handoff["public_pdp_dom_diagnostic_reconciliation_and_hardening"]
    document = P8_PUBLIC_PDP_DOM_DIAGNOSTIC_REVIEW_AND_HARDENING_FILE.read_text(
        encoding="utf-8"
    )

    assert hardening["task_id"] == "TASK-236"
    assert hardening["historical_attempt_task_id"] == "TASK-235"
    assert hardening["historical_attempt_source_sha"] == (
        "eedad88f5c676c647d418da62e554529ea29b161"
    )
    assert hardening["diagnostic_executed"] is True
    assert hardening["diagnostic_outcome"] == "FAIL_CLOSED"
    assert hardening["diagnostic_artifact_created"] is False
    assert hardening["historical_failure_reason"] == (
        "LEGACY_COMBINED_PUBLIC_PDP_AVAILABILITY_GATE"
    )
    assert hardening["screenshot_context"] == "NON_CANONICAL_DIAGNOSTIC_CONTEXT"
    assert hardening["screenshot_proves_internal_failure_reason"] is False
    assert hardening["screenshot_is_marketplace_evidence"] is False
    assert hardening["authorized_diagnostic_attempts"] == 1
    assert hardening["authorized_diagnostic_attempts_remaining"] == 0
    assert hardening["live_dom_diagnostic_authority"] == "NONE"
    assert hardening["diagnostic_hardening_implemented"] is True
    assert hardening["selector_repair_complete"] is False
    assert hardening["evidence_authority"] == "NONE"
    assert hardening["automated_public_pdp_acquisition_authority"] == "NONE"
    assert hardening["live_public_pdp_acquisition_authority"] == "NONE"
    assert hardening["market_test_or_action_authority"] == "NONE"
    assert hardening["post_publication_handoff"] == (
        "HUMAN_BRAIN_FRESH_ONE_SHOT_PUBLIC_PDP_DOM_DIAGNOSTIC_AUTHORIZATION"
    )
    assert handoff["next_milestone"] is None
    assert state["pending_commitments"] == []

    for required in (
        "LEGACY_COMBINED_PUBLIC_PDP_AVAILABILITY_GATE",
        "NON_CANONICAL_DIAGNOSTIC_CONTEXT",
        "BLOCKED_OR_CHALLENGE",
        "LOGIN_GATE",
        "LISTING_UNAVAILABLE",
        "NO_BOUNDED_PDP_ROOT",
        "IDENTITY_MISMATCH",
        "MALFORMED_DIAGNOSTIC_PAYLOAD",
        "evidence_authority=NONE",
        "HUMAN_BRAIN_FRESH_ONE_SHOT_PUBLIC_PDP_DOM_DIAGNOSTIC_AUTHORIZATION",
    ):
        assert required in document
    for roadmap_required in (
        "LEGACY_COMBINED_PUBLIC_PDP_AVAILABILITY_GATE",
        "NON_CANONICAL_DIAGNOSTIC_CONTEXT",
        "HUMAN_BRAIN_FRESH_ONE_SHOT_PUBLIC_PDP_DOM_DIAGNOSTIC_AUTHORIZATION",
    ):
        assert all(
            roadmap_required in roadmap.read_text(encoding="utf-8")
            for roadmap in ROADMAP_DOCS
        )


def test_task_237_authorizes_fresh_generation_2_attach_only_human_dom_diagnostic_attempt():
    state = load_yaml(ROADMAP_FILE)
    handoff = state["post_p8_planning_handoff"]
    fresh_auth = handoff["public_pdp_dom_diagnostic_fresh_authorization"]
    document = P8_PUBLIC_PDP_DOM_DIAGNOSTIC_FRESH_AUTHORIZATION_FILE.read_text(
        encoding="utf-8"
    )

    assert fresh_auth["task_id"] == "TASK-237"
    assert fresh_auth["classification"] == (
        "FRESH_ONE_SHOT_ATTACH_ONLY_PUBLIC_PDP_DOM_DIAGNOSTIC_AUTHORIZATION_ONLY"
    )
    assert fresh_auth["source_sha"] == TASK_236_SOURCE_SHA
    assert fresh_auth["diagnostic_carrier"] == (
        "src/product_intelligence/tiktok_pdp_dom_diagnostic.py"
    )
    assert fresh_auth["context_id"] == "p8-pilot-001-led-motion-tiktok-vn"
    assert fresh_auth["authorized_source_id"] == SELECTED_SOURCE_ID
    assert fresh_auth["stable_listing_reference"] == SELECTED_LISTING_REFERENCE
    assert fresh_auth["diagnostic_authorization_generation"] == 2
    assert fresh_auth["live_dom_diagnostic_authority"] == (
        "ONE_SHOT_ATTACH_ONLY_EXACT_LISTING"
    )
    assert fresh_auth["fresh_authorized_diagnostic_attempts"] == 1
    assert fresh_auth["fresh_authorized_diagnostic_attempts_remaining"] == 1
    assert fresh_auth["fresh_diagnostic_execution_owner"] == "HUMAN_OPERATOR"
    assert fresh_auth["browser_session_owner"] == "HUMAN_OPERATOR"
    assert fresh_auth["browser_lifecycle_authority"] == "TASK-137"
    assert fresh_auth["fresh_diagnostic_executed"] is False
    assert fresh_auth["diagnostic_hardening_implemented"] is True
    assert fresh_auth["selector_repair_complete"] is False
    assert fresh_auth["attach_only"] is True
    assert fresh_auth["navigation_or_interaction_authority"] == "NONE"
    assert fresh_auth["arbitrary_target_or_batch_authority"] == "NONE"
    assert fresh_auth["automatic_retry_refresh_resume"] is False
    assert fresh_auth["artifact_boundary"] == "EXPLICIT_EXTERNAL_JOB_ROOT_ONLY"
    assert fresh_auth["artifact_kind"] == (
        "EXTERNAL_STRUCTURAL_DIAGNOSTIC_OUTPUT_ONLY"
    )
    assert fresh_auth["evidence_authority"] == "NONE"
    assert fresh_auth["product_candidate_snapshot_authority"] == "NONE"
    assert fresh_auth["signal_evidence_authority"] == "NONE"
    assert fresh_auth["product_truth_or_ranking_authority"] == "NONE"
    assert fresh_auth["live_public_pdp_acquisition_authority"] == "NONE"
    assert fresh_auth["automated_public_pdp_acquisition_authority"] == "NONE"
    assert fresh_auth["market_test_or_action_authority"] == "NONE"
    assert fresh_auth["automatic_progression"] is False
    assert fresh_auth["mandatory_post_diagnostic_review"] == "HUMAN_BRAIN"
    assert fresh_auth["post_publication_handoff"] == (
        "HUMAN_OPERATOR_FRESH_ONE_SHOT_PUBLIC_PDP_DOM_DIAGNOSTIC_EXECUTION"
    )

    gen1 = fresh_auth["historical_generation_1"]
    assert gen1["task_id"] == "TASK-235"
    assert gen1["source_sha"] == "eedad88f5c676c647d418da62e554529ea29b161"
    assert gen1["diagnostic_executed"] is True
    assert gen1["diagnostic_outcome"] == "FAIL_CLOSED"
    assert gen1["diagnostic_artifact_created"] is False
    assert gen1["authorized_diagnostic_attempts"] == 1
    assert gen1["authorized_diagnostic_attempts_remaining"] == 0
    assert gen1["historical_failure_reason"] == (
        "LEGACY_COMBINED_PUBLIC_PDP_AVAILABILITY_GATE"
    )
    assert gen1["screenshot_context"] == "NON_CANONICAL_DIAGNOSTIC_CONTEXT"

    assert handoff["next_milestone"] is None
    assert state["pending_commitments"] == []

    for required in (
        "FRESH_ONE_SHOT_ATTACH_ONLY_PUBLIC_PDP_DOM_DIAGNOSTIC_AUTHORIZATION_ONLY",
        "1731381331718341815",
        SELECTED_LISTING_REFERENCE,
        TASK_236_SOURCE_SHA,
        "--job-root",
        "--cdp-endpoint",
        "evidence_authority=NONE",
        "ProductCandidateSnapshot",
        "SignalEvidence",
        "TASK-137",
        "HUMAN_OPERATOR_FRESH_ONE_SHOT_PUBLIC_PDP_DOM_DIAGNOSTIC_EXECUTION",
        "CAPABILITY_IS_NOT_AUTHORITY",
        "EVIDENCE_IS_NOT_PRODUCT_TRUTH",
        "SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY",
        "SNAPSHOT_IS_NOT_TREND",
        "ONE_CAPABILITY_ONE_AUTHORITY",
        "LEGACY_COMBINED_PUBLIC_PDP_AVAILABILITY_GATE",
        "NON_CANONICAL_DIAGNOSTIC_CONTEXT",
        "BLOCKED_OR_CHALLENGE",
        "LOGIN_GATE",
        "LISTING_UNAVAILABLE",
        "NO_BOUNDED_PDP_ROOT",
        "IDENTITY_MISMATCH",
        "MALFORMED_DIAGNOSTIC_PAYLOAD",
    ):
        assert required in document

    for roadmap_required in (
        "FRESH_ONE_SHOT_ATTACH_ONLY_PUBLIC_PDP_DOM_DIAGNOSTIC_AUTHORIZATION_ONLY",
        "HUMAN_OPERATOR_FRESH_ONE_SHOT_PUBLIC_PDP_DOM_DIAGNOSTIC_EXECUTION",
        TASK_236_SOURCE_SHA,
    ):
        assert all(
            roadmap_required in roadmap.read_text(encoding="utf-8")
            for roadmap in ROADMAP_DOCS
        )


def _historical_test_task_239_authorizes_one_exact_generation_3_diagnostic_attempt():
    state = load_yaml(ROADMAP_FILE)
    handoff = state["post_p8_planning_handoff"]
    authorization = handoff["public_pdp_dom_diagnostic_gen3_authorization"]
    document = P8_PUBLIC_PDP_DOM_DIAGNOSTIC_GEN3_AUTHORIZATION_FILE.read_text(
        encoding="utf-8"
    )

    assert authorization["classification"] == (
        "FRESH_GENERATION_3_ROOT_OBSERVABILITY_DIAGNOSTIC_AUTHORIZATION_ONLY"
    )
    assert authorization["source_task_id"] == "TASK-238"
    assert authorization["source_run_id"] == "RUN-238-002"
    assert authorization["source_review_id"] == "REVIEW-238-001"
    assert authorization["diagnostic_implementation_source_sha"] == (
        TASK_238_PUBLISHED_SOURCE_SHA
    )
    assert authorization["implementation_modified"] is False
    assert authorization["context_id"] == "p8-pilot-001-led-motion-tiktok-vn"
    assert authorization["authorized_source_id"] == SELECTED_SOURCE_ID
    assert authorization["stable_listing_reference"] == SELECTED_LISTING_REFERENCE
    assert authorization["diagnostic_authorization_generation"] == 3
    assert authorization["live_dom_diagnostic_authority"] == (
        "ONE_SHOT_ATTACH_ONLY_EXACT_LISTING"
    )
    assert authorization["generation_3_authorized_diagnostic_attempts"] == 1
    assert authorization["generation_3_authorized_diagnostic_attempts_remaining"] == 1
    assert authorization["generation_3_diagnostic_execution_owner"] == "HUMAN_OPERATOR"
    assert authorization["generation_3_diagnostic_executed"] is False
    assert authorization["diagnostic_executed"] is False
    assert authorization["attach_only"] is True
    assert authorization["session_evaluate_count"] == 1
    assert authorization["navigation_or_interaction_authority"] == "NONE"
    assert authorization["arbitrary_target_or_batch_authority"] == "NONE"
    assert authorization["automatic_retry_refresh_resume"] is False
    assert authorization["preflight_consumes_attempt"] is False
    assert authorization["diagnostic_invocation_consumes_attempt"] is True
    assert authorization["evidence_authority"] == "NONE"
    assert authorization["root_observability_hardening_implemented"] is True
    assert authorization["selector_repair_complete"] is False
    assert authorization["live_public_pdp_acquisition_authority"] == "NONE"
    assert authorization["automated_public_pdp_acquisition_authority"] == "NONE"
    assert authorization["market_test_or_action_authority"] == "NONE"
    assert authorization["automatic_progression"] is False
    assert authorization["mandatory_post_diagnostic_review"] == "HUMAN_BRAIN"
    assert authorization["post_publication_handoff"] == (
        "HUMAN_OPERATOR_GENERATION_3_ROOT_OBSERVABILITY_DIAGNOSTIC_EXECUTION"
    )
    assert handoff["next_milestone"] is None
    assert state["pending_commitments"] == []

    gen1 = handoff["historical_generation_1"]
    gen2 = handoff["historical_generation_2"]
    assert gen1["diagnostic_outcome"] == "FAIL_CLOSED"
    assert gen1["authorized_diagnostic_attempts_remaining"] == 0
    assert gen2["diagnostic_outcome"] == "FAIL_CLOSED"
    assert gen2["diagnostic_failure_reason"] == "NO_BOUNDED_PDP_ROOT"
    assert gen2["authorized_diagnostic_attempts_remaining"] == 0
    assert gen2["execution_owner"] == "HUMAN_OPERATOR"

    for required in (
        "FRESH_GENERATION_3_ROOT_OBSERVABILITY_DIAGNOSTIC_AUTHORIZATION_ONLY",
        "source_task_id=TASK-238",
        "source_run_id=RUN-238-002",
        "source_review_id=REVIEW-238-001",
        f"diagnostic_implementation_source_sha={TASK_238_PUBLISHED_SOURCE_SHA}",
        f"published_source_sha={TASK_238_PUBLISHED_SOURCE_SHA}",
        "generation_3_authorized_diagnostic_attempts_remaining=1",
        "ONE_SHOT_ATTACH_ONLY_EXACT_LISTING",
        "session.evaluate(DIAGNOSTIC_SCRIPT)",
        "preflight",
        "evidence_authority=NONE",
        "HUMAN_OPERATOR_GENERATION_3_ROOT_OBSERVABILITY_DIAGNOSTIC_EXECUTION",
        SELECTED_LISTING_REFERENCE,
    ):
        assert required in document

    for roadmap_required in (
        "FRESH_GENERATION_3_ROOT_OBSERVABILITY_DIAGNOSTIC_AUTHORIZATION_ONLY",
        "RUN-238-002",
        "REVIEW-238-001",
        TASK_238_PUBLISHED_SOURCE_SHA,
        "HUMAN_OPERATOR_GENERATION_3_ROOT_OBSERVABILITY_DIAGNOSTIC_EXECUTION",
    ):
        assert all(
            roadmap_required in roadmap.read_text(encoding="utf-8")
            for roadmap in ROADMAP_DOCS
        )


def test_task_238_reconciles_gen2_and_hardens_root_observability():
    state = load_yaml(ROADMAP_FILE)
    handoff = state["post_p8_planning_handoff"]
    reconciliation = handoff[
        "public_pdp_dom_diagnostic_gen2_reconciliation_and_root_observability"
    ]
    document = (
        P8_PUBLIC_PDP_DOM_DIAGNOSTIC_GEN2_REVIEW_AND_ROOT_OBSERVABILITY_FILE.read_text(
            encoding="utf-8"
        )
    )

    assert reconciliation["task_id"] == "TASK-238"
    assert reconciliation["historical_attempt_task_id"] == "TASK-237"
    assert reconciliation["classification"] == (
        "GENERATION_2_FAIL_CLOSED_RECONCILIATION_AND_BOUNDED_ROOT_OBSERVABILITY_HARDENING_ONLY"
    )
    assert reconciliation["diagnostic_executed"] is True
    assert reconciliation["diagnostic_outcome"] == "FAIL_CLOSED"
    assert reconciliation["diagnostic_failure_reason"] == "NO_BOUNDED_PDP_ROOT"
    assert reconciliation["diagnostic_artifact_created"] is False
    assert reconciliation["authorized_diagnostic_attempts"] == 1
    assert reconciliation["authorized_diagnostic_attempts_remaining"] == 0
    assert reconciliation["execution_owner"] == "HUMAN_OPERATOR"
    assert reconciliation["live_dom_diagnostic_authority"] == "NONE"
    assert reconciliation["root_observability_hardening_implemented"] is True
    assert reconciliation["diagnostic_hardening_implemented"] is True
    assert reconciliation["selector_repair_complete"] is False
    assert reconciliation["live_public_pdp_acquisition_authority"] == "NONE"
    assert reconciliation["automated_public_pdp_acquisition_authority"] == "NONE"
    assert reconciliation["market_test_or_action_authority"] == "NONE"
    assert reconciliation["automatic_progression"] is False
    assert reconciliation["post_publication_handoff"] == (
        "HUMAN_BRAIN_FRESH_ROOT_OBSERVABILITY_DIAGNOSTIC_AUTHORIZATION"
    )
    assert handoff["next_milestone"] is None
    assert state["pending_commitments"] == []

    for required in (
        "GENERATION_2_FAIL_CLOSED_RECONCILIATION_AND_BOUNDED_ROOT_OBSERVABILITY_HARDENING_ONLY",
        "NO_BOUNDED_PDP_ROOT",
        "HUMAN_BRAIN_FRESH_ROOT_OBSERVABILITY_DIAGNOSTIC_AUTHORIZATION",
        "title_anchor_count",
        "price_anchor_count",
        "action_anchor_count",
        "visible_explicit_pdp_root_count",
        "explicit_root_with_commerce_anchors_count",
        "main_present",
        "main_visible",
        "main_has_commerce_anchors",
        "multi_anchor_common_ancestor_found",
        "selected_root_kind",
        "evidence_authority=NONE",
        "NON_CANONICAL_DIAGNOSTIC_CONTEXT",
        "LEGACY_COMBINED_PUBLIC_PDP_AVAILABILITY_GATE",
        "TASK-237",
        "4991ade68a5743af7e886342684751744bee49ed",
        "a53510ff353cdf926a76f1dc84363b7835c5cb4d",
        "1731381331718341815",
        SELECTED_LISTING_REFERENCE,
    ):
        assert required in document

    for roadmap_required in (
        "GENERATION_2_FAIL_CLOSED_RECONCILIATION_AND_BOUNDED_ROOT_OBSERVABILITY_HARDENING_ONLY",
        "HUMAN_BRAIN_FRESH_ROOT_OBSERVABILITY_DIAGNOSTIC_AUTHORIZATION",
        "NO_BOUNDED_PDP_ROOT",
    ):
        assert all(
            roadmap_required in roadmap.read_text(encoding="utf-8")
            for roadmap in ROADMAP_DOCS
        )




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
        "source_sha": TASK_226_SOURCE_SHA,
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
    assert completed["TASK-227"] == {
        "task_id": "TASK-227",
        "task_revision": 1,
        "track_id": "P8_REAL_COMMERCE_DECISION_PILOT_SELECTION",
        "milestone_id": "P8.1",
        "title": "Real Decision Pilot Selection",
        "status": "DONE",
        "source_sha": TASK_227_SOURCE_SHA,
        "completion_basis": "PUBLICATION_GATED",
        "classification": "PILOT_CASE_SELECTION_ONLY",
        "selection_owner": "HUMAN",
        "real_pilot_executed": False,
        "effective_only_when": {
            "semantic_review": "PASS",
            "published_source": "EXACT_REVIEWED_CANDIDATE",
            "canonical_main_equals_reviewed_candidate": True,
        },
    }
    assert completed["TASK-228"] == {
        "task_id": "TASK-228",
        "task_revision": 1,
        "track_id": "P8_PRE_ACTION_EVIDENCE_ACQUISITION_PLANNING",
        "milestone_id": "P8.2",
        "title": "Pre-Action Evidence Acquisition Plan",
        "status": "DONE",
        "completion_basis": "PUBLICATION_GATED",
        "classification": "PRE_ACTION_EVIDENCE_ACQUISITION_PLAN_ONLY",
        "planning_owner": "HUMAN_BRAIN",
        "source_sha": TASK_228_SOURCE_SHA,
        "exact_case_preserved": True,
        "live_evidence_acquired": False,
        "real_pilot_executed": False,
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
