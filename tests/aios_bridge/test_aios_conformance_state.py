import hashlib
from pathlib import Path

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
    assert state["capability_authority_policy"] == "ONE_CAPABILITY_ONE_AUTHORITY"

    certification = state["certification"]
    assert certification["task_id"] == "TASK-207"
    assert certification["task_revision"] == 14
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
    assert set(families) == {"phase_1", "phase_2", "p1b_semantic_registries", "executor_profile_policy"}
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
    for phase in (families["phase_1"], families["phase_2"]):
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

    registries = families["p1b_semantic_registries"]
    assert registries["task_scope"] == "TASK-256"
    assert registries["authority"] == "COGNITIVE_AND_PROCEDURE_MATERIAL_ONLY"
    assert registries["stores_chat_memory"] is False
    assert registries["selects_provider_or_model_default"] is False
    assert registries["grants_lifecycle_authority"] is False
    assert registries["grants_mutation_authority"] is False
    assert registries["brain"]["status"] == registries["reviewer"]["status"] == "ACTIVE"
    assert registries["brain"]["registries"] | registries["reviewer"]["registries"] == {
        ".ai/brain-audit-profiles.yaml": "e931c1c7fa4b1b9dfbf7e7c649d5a19e0035d6ba",
        ".ai/brain-return-contracts.yaml": "9d220ece8dd20028e590efd083b1a04b00ffadfe",
        ".ai/flow-cards.yaml": "574edd0407de7f4cca14b8b854a5d00d271be014",
        ".ai/reviewer-procedure-profiles.yaml": "ad510261ff220f9b9165dd7cdc8646fd6915b0a7",
        ".ai/reviewer-return-contracts.yaml": "c805c49fcbe170677ff3bb9dde3fb4c9d308c474",
    }

    profile = families["executor_profile_policy"]
    assert profile["path"] == ".ai/executor-profiles.yaml"
    assert profile["blob"] == "6f0507f2bd15597fba4a2340f1508061bc7bee06"
    profile_bytes = (REPO_ROOT / profile["path"]).read_bytes()
    assert hashlib.sha1(
        b"blob " + str(len(profile_bytes)).encode("ascii") + b"\0" + profile_bytes
    ).hexdigest() == profile["blob"]
    assert profile["override_precedence"] == "EXPLICIT_HUMAN_OVERRIDE"
    assert profile["grants_lifecycle_authority"] is False
    assert profile["codex"] == {
        "default_model": "gpt-6-sol", "default_reasoning_effort": "high",
        "supported_reasoning_efforts": ["none", "low", "medium", "high", "xhigh", "max"],
    }
    assert profile["antigravity"] == {
        "default_model": "gemini-3.8-flash", "default_reasoning_effort": "medium",
        "supported_reasoning_efforts": ["low", "medium", "high"],
    }
    assert yaml.safe_load((REPO_ROOT / profile["path"]).read_bytes())["executors"] == {
        "codex": profile["codex"], "antigravity": profile["antigravity"],
    }


def test_live_evidence_selectors_are_typed_and_current_pin_scoped():
    state = load_state()
    selectors = state["live_evidence_selectors"]
    assert list(selectors) == ["AC1", "AC2", "AC3", "AC4", "AC5"]

    assert selectors["AC1"] == {
        "carrier": "AIOS_BRAIN_INGRESS",
        "operation": "AUTHOR_TASK",
        "task_id": "TASK-207",
        "task_revision": 14,
        "expected_actor": "trung-via",
        "expected_predecessor_main": "e67b4c2646f7803210db15ce4ea10b3dcccbb6e7",
        "canonical_task_commit": "a8d3d4d7b03202040d24d26a79e9edf385012c76",
        "canonical_task_blob": "006e6dc6417d726ee4f0aef13030d0208d1e0e3e",
        "repository_carrier": ".github/workflows/aios-brain-ingress.yml",
    }
    assert selectors["AC2"] == {
        "carrier": "AIOS_BRAIN_WAKEUP",
        "dispatch_id": "task207-r14-codex-high-001",
        "task_id": "TASK-207",
        "task_revision": 14,
        "canonical_run_id": "RUN-207-013",
        "executor": "codex",
        "model": "gpt-6-sol",
        "reasoning_effort": "high",
        "execution_profile_source": "EXPLICIT_HUMAN_OVERRIDE",
        "active_pin": EXPECTED_PIN,
        "repository_carrier": ".github/workflows/aios-brain-wakeup.yml",
        "self_hosted_workflow": ".github/workflows/aios-self-hosted-wakeup.yml",
        "self_hosted_bootstrap": ".agents/skills/aios-worker/scripts/aios_phase1_wakeup.py",
        "duplicate_dispatch_boundary": "ONE_FRESH_CANONICAL_RUN_NO_REUSE_OF_FAILED_DISPATCH",
    }
    assert selectors["AC3"] == {
        "carrier": "AIOS_TERMINAL_ATTENTION",
        "task_id": "TASK-207",
        "task_revision": 14,
        "canonical_run_id": "RUN-207-013",
        "terminal_truth": "CANONICAL_REVISION_14_RUN_TERMINAL",
        "terminal_ref_prefix": "refs/heads/aios/terminal-attention/",
        "issue_title": "[AIOS TERMINAL ATTENTION]",
        "repository_carrier": ".github/workflows/aios-terminal-attention.yml",
        "authority": "NOTIFICATION_ONLY",
    }
    assert selectors["AC4"] == {
        "carrier": "AIOS_BRAIN_REMEDIATION_INTENT",
        "correction_dispatch_id": "task-207-r14-remediation-non-authorizing-001",
        "task_id": "TASK-207",
        "task_revision": 14,
        "selector_authority": "NON_AUTHORIZING_PROBE",
        "active_pin": EXPECTED_PIN,
        "expected_outcome": "FAIL_CLOSED_NO_IMPLEMENTATION_RUN",
        "repository_carrier": ".github/workflows/aios-brain-remediation-intent.yml",
        "self_hosted_workflow": ".github/workflows/aios-approved-remediation-intent.yml",
        "self_hosted_bootstrap": (
            ".agents/skills/aios-worker/scripts/aios_phase2_remediation.py"
        ),
    }
    assert selectors["AC5"] == {
        "carrier": "AIOS_BRAIN_REPAIR_WAKEUP",
        "repair_dispatch_id": "task-207-r14-repair-non-authorizing-001",
        "task_id": "TASK-207",
        "task_revision": 14,
        "selector_authority": "NON_AUTHORIZING_PROBE",
        "active_pin": EXPECTED_PIN,
        "action_shape": "NO_CHANGE",
        "executor": None,
        "expected_outcome": "FAIL_CLOSED_NO_IMPLEMENTATION_RUN",
        "repository_carrier": ".github/workflows/aios-brain-repair-wakeup.yml",
        "self_hosted_workflow": ".github/workflows/aios-self-hosted-repair-wakeup.yml",
        "self_hosted_bootstrap": (
            ".agents/skills/aios-worker/scripts/aios_phase2_repair.py"
        ),
    }
    assert state["reviewer_live_evidence_gate"] == {
        "required_before_semantic_pass": True,
        "typed_carriers": ["AC1", "AC2", "AC3", "AC4", "AC5"],
        "source_selectors_are_not_live_receipts": True,
        "missing_or_conflicting_live_evidence": "CHANGES_REQUIRED_OR_NO_PASS",
    }


def test_authority_boundaries_and_old_pin_exclusion_are_explicit():
    state = load_state()
    boundaries = state["authority_boundaries"]
    assert set(boundaries) == {
        "human",
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
    assert boundaries["human"] == "PRIORITY_AND_EXPLICIT_EXECUTOR_SELECTION"
    assert boundaries["attention"] == "NOTIFICATION_ONLY"
    assert boundaries["local_fallbacks"] == "EMERGENCY_DEBUG_ONLY"

    assert state["immediate_historical_certification"] == {
        "task_id": "TASK-207", "task_revision": 8,
        "run_id": "RUN-207-010", "review_id": "REVIEW-207-004",
        "downstream_pin": IMMEDIATE_HISTORICAL_PIN,
        "status": "HISTORICAL_OLD_PIN_EVIDENCE_ONLY",
        "certification_authority_for_current_pin": False,
    }
    assert state["failed_current_pin_history"]["disposition"] == "IMMUTABLE_NOT_REPAIR_OR_SOURCE_AUTHORITY"
    assert state["failed_current_pin_history"]["runs"] == [
        {"run_id": "RUN-207-011", "task_revision": 11,
         "failed_head_sha": "f1580073867f095704bc1c34f2858c160e0cf4d3", "phase": "COMPLETION_GATE",
         "verification_started": False},
        {"run_id": "RUN-207-012", "task_revision": 13,
         "failed_head_sha": "52e2237d6bf918c1552bb4393da17c63737297fb", "phase": "COMPLETION_GATE",
         "verification_started": False},
    ]
    assert state["failed_current_pin_history"]["revision_12_dispatch"] == {
        "dispatch_id": "task207-r12-codex-high-001",
        "phase": "PRIMARY_SYNCHRONIZATION", "run_created": False,
        "disposition": "NON_CANONICAL_OPERATIONAL_HISTORY",
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
