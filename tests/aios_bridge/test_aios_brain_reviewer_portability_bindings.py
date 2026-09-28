"""Offline P1B registry identity and pinned-package compatibility checks."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from aios_renew.brain_audit import parse_profile_registry as parse_brain_audit
from aios_renew.brain_context import BrainContextError, load_flow_cards
from aios_renew.brain_return_contract import parse_return_contract_registry
from aios_renew.reviewer_procedure import select_reviewer_procedure
from aios_renew.reviewer_return_contract import select_reviewer_return_contract


ROOT = Path(__file__).resolve().parents[2]
REGISTRIES = {
    ".ai/brain-audit-profiles.yaml": "e931c1c7fa4b1b9dfbf7e7c649d5a19e0035d6ba",
    ".ai/brain-return-contracts.yaml": "9d220ece8dd20028e590efd083b1a04b00ffadfe",
    ".ai/flow-cards.yaml": "574edd0407de7f4cca14b8b854a5d00d271be014",
    ".ai/reviewer-procedure-profiles.yaml": "ad510261ff220f9b9165dd7cdc8646fd6915b0a7",
    ".ai/reviewer-return-contracts.yaml": "c805c49fcbe170677ff3bb9dde3fb4c9d308c474",
}
PIN = "31fd2482cd87d97fd818e05eb5b4dcec69ffeee6"


def git_blob_id(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def test_exact_registry_blobs_and_active_adoption_binding():
    state = yaml.safe_load((ROOT / ".ai/aios-adoption-state.yaml").read_bytes())
    binding = state["p1b_semantic_registries"]
    assert binding["task_scope"] == "TASK-256"
    assert set(binding) == {"brain", "reviewer", "task_scope"}
    assert binding["brain"]["status"] == binding["reviewer"]["status"] == "ACTIVE"
    assert set(binding["brain"]) == set(binding["reviewer"]) == {"status", "registries"}
    declared = binding["brain"]["registries"] | binding["reviewer"]["registries"]
    assert declared == REGISTRIES
    assert len(declared) == 5
    for path, expected in REGISTRIES.items():
        assert git_blob_id((ROOT / path).read_bytes()) == expected
    assert state["authority"]["engineering_truth"] is False
    assert state["downstream_pin"]["commit"] == PIN
    assert state["full_downstream_conformance"]["status"] == "REQUIRED_PENDING"
    assert state["full_downstream_conformance"]["fresh_post_pin_certification"] == "REQUIRED_PENDING"


def test_substituted_or_duplicate_registry_material_is_rejected():
    blobs = [(ROOT / path).read_bytes() for path in REGISTRIES]
    assert len(set(blobs)) == 5
    for path, raw in zip(REGISTRIES, blobs):
        assert git_blob_id(raw + b"\n") != REGISTRIES[path]
        for other_path, other_raw in zip(REGISTRIES, blobs):
            if path != other_path:
                assert git_blob_id(other_raw) != REGISTRIES[path]


def test_pinned_package_parses_closed_brain_and_reviewer_material(tmp_path: Path):
    cards = load_flow_cards(repo=ROOT)
    assert set(cards) == {
        "ARCHITECTURE", "TASK_AUTHORING", "SEMANTIC_REVIEW",
        "REMEDIATION_AUTHORING", "REPAIR_AUTHORING", "DIAGNOSTIC",
    }
    forbidden = {"chat_history", "credentials", "raw_logs", "unbounded_repository_content"}
    for flow, card in cards.items():
        assert set(card["forbidden_context"]) == forbidden
        assert "FRESH_COMPOSITION_FOR_CONTINUATION" in card["invalidation_rules"]
        assert card["authority_owner"] == ("REVIEWER" if flow == "SEMANTIC_REVIEW" else "BRAIN")

    audit = parse_brain_audit((ROOT / ".ai/brain-audit-profiles.yaml").read_bytes())["profiles"][0]
    assert (audit["id"], audit["version"]) == ("brain-high-value-v2", 2)
    assert len(audit["lenses"]) == 8
    assert audit["procedure"]["stages"] == ["CONSTRUCT", "ADVERSARIAL_AUDIT_AND_RECONCILE"]

    brain_returns = parse_return_contract_registry((ROOT / ".ai/brain-return-contracts.yaml").read_bytes())
    assert {item["selected_flow"] for item in brain_returns["contracts"]} == set(cards) - {"SEMANTIC_REVIEW"}
    for contract in brain_returns["contracts"]:
        assert contract["authority_owner"] == "BRAIN"
        assert contract["candidate_contract"]["representation"] == "STRICT_JSON_MAPPING"
        flow = contract["selected_flow"]
        for field in ("decision_family_ref", "handoff_target", "expected_return_shape"):
            assert contract[field] == cards[flow][field]
    task_return = next(item for item in brain_returns["contracts"] if item["selected_flow"] == "TASK_AUTHORING")
    assert {item["path"] for item in task_return["candidate_contract"]["bindings"]} == {"task_id", "revision"}
    assert {item["source"] for item in task_return["candidate_contract"]["bindings"]} == {"EXTERNAL_REQUEST_BINDING_REQUIRED"}

    procedure_raw = (ROOT / ".ai/reviewer-procedure-profiles.yaml").read_bytes()
    primary = select_reviewer_procedure(procedure_raw, "PRIMARY")
    delta = select_reviewer_procedure(procedure_raw, "DELTA")
    assert primary["procedure"]["mode"] == "PRIMARY"
    assert delta["procedure"]["mode"] == "DELTA"
    assert primary["profile"]["one_call_semantics"] is True
    assert primary["profile"]["authority_owner"] == "REVIEWER"
    assert primary["reviewer_procedure_ref"] == delta["reviewer_procedure_ref"]

    reviewer = select_reviewer_return_contract((ROOT / ".ai/reviewer-return-contracts.yaml").read_bytes())["contract"]
    assert reviewer["authority_owner"] == cards["SEMANTIC_REVIEW"]["authority_owner"]
    assert reviewer["representation"] == "STRICT_JSON_MAPPING"
    assert reviewer["grammar"]["verdicts"] == ["PASS", "CHANGES_REQUIRED", "BLOCKED"]
    assert reviewer["grammar"]["finding_actions"] == ["CODE_FIX", "EVIDENCE_ONLY"]
    assert "ACCEPTANCE_NORMALIZED_IN_TASK_ORDER" in reviewer["rules"]

    duplicate = yaml.safe_load((ROOT / ".ai/flow-cards.yaml").read_bytes())
    duplicate["cards"][-1]["id"] = "ARCHITECTURE"
    duplicate_path = tmp_path / "flow-cards.yaml"
    duplicate_path.write_text(yaml.safe_dump(duplicate), encoding="utf-8")
    with pytest.raises(BrainContextError):
        load_flow_cards(duplicate_path)
