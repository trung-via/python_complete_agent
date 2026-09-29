from pathlib import Path
import subprocess

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONFORMANCE_FILE = REPO_ROOT / ".ai" / "aios-conformance-state.yaml"
EXPECTED_PIN = "44eee353eda376c9db8cd88d97184d3122651bf5"
IMMEDIATE_HISTORICAL_PIN = "edd7d8d92d54900c56442bbfcddb8648ec4d2e09"
HISTORICAL_PIN = "49ad4d7a1e57a4c25ba44e60589d8320cb0f57b2"
FAILED_OLD_PIN = "1a68db9acb6989dfa81bf875503db62e54a4bed6"
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
    assert certification["task_revision"] == 13
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
        "expected_predecessor_main": "46b379bd3fcf47dd376c0a6d7b44885d38a897e1",
        "task_revision": 13,
    }
    assert selectors["AC2"] == {
        "carrier": "AIOS_BRAIN_WAKEUP",
        "dispatch_id": "task207-r13-codex-high-001",
        "task_revision": 13,
        "executor": "codex",
        "model": "gpt-6-sol",
        "reasoning_effort": "high",
        "profile_source": "EXPLICIT_HUMAN_OVERRIDE",
        "downstream_pin": EXPECTED_PIN,
    }
    assert selectors["AC3"] == {
        "carrier": "AIOS_TERMINAL_ATTENTION",
        "task_revision": 13,
        "terminal_truth": "CANONICAL_REVISION_13_RUN",
        "terminal_ref_prefix": "refs/heads/aios/terminal-attention/",
        "issue_title": "[AIOS TERMINAL ATTENTION]",
    }
    assert selectors["AC4"] == {
        "carrier": "AIOS_BRAIN_REMEDIATION_INTENT",
        "correction_dispatch_id": "task-207-r13-remediation-non-authorizing-001",
        "task_id": "TASK-207",
        "task_revision": 13,
        "expected_outcome": "FAIL_CLOSED_NO_IMPLEMENTATION_RUN",
        "self_hosted_bootstrap": (
            ".agents/skills/aios-worker/scripts/aios_phase2_remediation.py"
        ),
    }
    assert selectors["AC5"] == {
        "carrier": "AIOS_BRAIN_REPAIR_WAKEUP",
        "repair_dispatch_id": "task-207-r13-repair-non-authorizing-001",
        "task_id": "TASK-207",
        "task_revision": 13,
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

    assert state["immediate_historical_certification"] == {
        "task_id": "TASK-207",
        "task_revision": 8,
        "run_id": "RUN-207-010",
        "review_id": "REVIEW-207-004",
        "downstream_pin": IMMEDIATE_HISTORICAL_PIN,
        "status": "HISTORICAL_OLD_PIN_EVIDENCE_ONLY",
        "certification_authority_for_current_pin": False,
    }

    assert state["historical_certification"] == {
        "task_id": "TASK-207",
        "task_revision": 5,
        "downstream_pin": HISTORICAL_PIN,
        "status": "HISTORICAL_OLD_PIN_EVIDENCE_ONLY",
        "certification_authority_for_current_pin": False,
    }

    assert state["failed_old_pin_history"] == {
        "task_id": "TASK-207",
        "task_revision": 7,
        "runs": ["RUN-207-007", "RUN-207-008", "RUN-207-009"],
        "terminal_run": "RUN-207-009",
        "downstream_pin": FAILED_OLD_PIN,
        "status": "FAILED_OLD_PIN_NON_CERTIFYING_EVIDENCE",
        "repair_after_pin_change": "FORBIDDEN",
        "certification_authority_for_current_pin": False,
    }

    assert state["historical_exclusions"] == {
        "old_pin_task_revision": "TASK-207-REVISION-2",
        "runs": ["RUN-207-001", "RUN-207-002"],
        "repair": "REPAIR-207-001",
        "certification_authority_for_current_pin": False,
    }


def test_portability_bindings_preserve_exact_blobs_and_policy_boundaries():
    bindings = load_state()["portability_bindings"]
    registries = bindings["p1b_semantic_registries"]
    assert registries["task_scope"] == "TASK-256"
    assert registries["status"] == "ACTIVE"
    assert registries["consumption"] == "EXTERNAL_BRAIN_REVIEWER_SEMANTIC_MATERIAL_ONLY"
    assert registries["registries"] == {
        ".ai/brain-audit-profiles.yaml": "e931c1c7fa4b1b9dfbf7e7c649d5a19e0035d6ba",
        ".ai/brain-return-contracts.yaml": "9d220ece8dd20028e590efd083b1a04b00ffadfe",
        ".ai/flow-cards.yaml": "574edd0407de7f4cca14b8b854a5d00d271be014",
        ".ai/reviewer-procedure-profiles.yaml": "ad510261ff220f9b9165dd7cdc8646fd6915b0a7",
        ".ai/reviewer-return-contracts.yaml": "c805c49fcbe170677ff3bb9dde3fb4c9d308c474",
    }
    assert "no chat memory" in registries["boundary"]
    profiles = bindings["executor_profiles"]
    assert profiles["path"] == ".ai/executor-profiles.yaml"
    assert profiles["blob"] == "6f0507f2bd15597fba4a2340f1508061bc7bee06"
    assert profiles["codex"] == {
        "default_model": "gpt-6-sol",
        "default_reasoning_effort": "high",
        "supported_reasoning_efforts": ["none", "low", "medium", "high", "xhigh", "max"],
    }
    assert profiles["antigravity"] == {
        "default_model": "gemini-3.8-flash",
        "default_reasoning_effort": "medium",
        "supported_reasoning_efforts": ["low", "medium", "high"],
    }
    assert profiles["explicit_human_override_precedence"] is True
    profile_path = REPO_ROOT / profiles["path"]
    assert yaml.safe_load(profile_path.read_bytes())["executors"] == {
        "codex": profiles["codex"],
        "antigravity": profiles["antigravity"],
    }
    assert subprocess.check_output(
        ["git", "rev-parse", "--verify", "HEAD:.ai/executor-profiles.yaml"],
        cwd=REPO_ROOT,
        text=True,
    ).strip() == profiles["blob"]
