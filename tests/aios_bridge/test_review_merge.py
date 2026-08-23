from __future__ import annotations

import pytest

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.review_merge import (
    MergeGateDecision,
    MergeGateReason,
    MergeReceipt,
    ReviewedMergeInput,
    evaluate_merge_gate,
    parse_review_header,
)


VALID_TASK_SHA = "a" * 40
VALID_MAIN_SHA = "b" * 40


def _valid_input(**kwargs: object) -> ReviewedMergeInput:
    args = {
        "task_id": "TASK-069",
        "review_status": "PASS",
        "review_approved": True,
        "auto_merge_eligible": True,
        "reviewed_task_head_sha": VALID_TASK_SHA,
        "reviewed_base_main_sha": VALID_MAIN_SHA,
        "current_task_head_sha": VALID_TASK_SHA,
        "current_main_sha": VALID_MAIN_SHA,
        "merge_base_sha": VALID_MAIN_SHA,
        "ahead_by": 1,
        "behind_by": 0,
    }
    args.update(kwargs)
    return ReviewedMergeInput(**args)  # type: ignore[arg-type]


def test_reviewed_merge_input_immutability_and_validation() -> None:
    inp = _valid_input()
    assert inp.task_id == "TASK-069"
    assert inp.review_status == "PASS"
    assert inp.review_approved is True
    assert inp.auto_merge_eligible is True
    assert inp.reviewed_task_head_sha == VALID_TASK_SHA
    assert inp.ahead_by == 1

    with pytest.raises(Exception):
        inp.ahead_by = 2  # type: ignore


@pytest.mark.parametrize("invalid_field,kwargs", [
    ("invalid_task_id", {"task_id": "task-69"}),
    ("non_canonical_task_id", {"task_id": "TASK69"}),
    ("empty_status", {"review_status": ""}),
    ("bool_as_ahead_count", {"ahead_by": True}),
    ("bool_as_behind_count", {"behind_by": False}),
    ("negative_ahead", {"ahead_by": -1}),
    ("negative_behind", {"behind_by": -1}),
    ("short_sha", {"reviewed_task_head_sha": "a" * 39}),
    ("uppercase_sha", {"reviewed_task_head_sha": "A" * 40}),
    ("non_hex_sha", {"current_main_sha": "g" * 40}),
    ("str_as_bool", {"review_approved": "YES"}),
    ("str_as_eligible", {"auto_merge_eligible": "YES"}),
])
def test_reviewed_merge_input_rejects_invalid_values(invalid_field: str, kwargs: dict) -> None:
    with pytest.raises(ContinuityStateValidationError):
        _valid_input(**kwargs)


def test_evaluate_merge_gate_happy_path_returns_pass_eligible() -> None:
    inp = _valid_input(ahead_by=3, behind_by=0)
    decision = evaluate_merge_gate(inp)
    assert isinstance(decision, MergeGateDecision)
    assert decision.eligible is True
    assert decision.reason is MergeGateReason.PASS_ELIGIBLE
    assert "satisfied" in decision.message


def test_evaluate_merge_gate_rejects_non_pass_status() -> None:
    inp = _valid_input(review_status="CHANGES_REQUIRED")
    decision = evaluate_merge_gate(inp)
    assert decision.eligible is False
    assert decision.reason is MergeGateReason.REVIEW_NOT_PASS
    assert "CHANGES_REQUIRED" in decision.message


def test_evaluate_merge_gate_rejects_unapproved_review() -> None:
    inp = _valid_input(review_approved=False)
    decision = evaluate_merge_gate(inp)
    assert decision.eligible is False
    assert decision.reason is MergeGateReason.REVIEW_NOT_APPROVED


def test_evaluate_merge_gate_rejects_auto_merge_disabled() -> None:
    inp = _valid_input(auto_merge_eligible=False)
    decision = evaluate_merge_gate(inp)
    assert decision.eligible is False
    assert decision.reason is MergeGateReason.AUTO_MERGE_DISABLED


def test_evaluate_merge_gate_rejects_task_head_drift() -> None:
    drifted_task_sha = "c" * 40
    inp = _valid_input(current_task_head_sha=drifted_task_sha)
    decision = evaluate_merge_gate(inp)
    assert decision.eligible is False
    assert decision.reason is MergeGateReason.TASK_HEAD_DRIFT
    assert drifted_task_sha in decision.message


def test_evaluate_merge_gate_rejects_main_drift() -> None:
    drifted_main_sha = "d" * 40
    inp = _valid_input(current_main_sha=drifted_main_sha)
    decision = evaluate_merge_gate(inp)
    assert decision.eligible is False
    assert decision.reason is MergeGateReason.MAIN_DRIFT
    assert drifted_main_sha in decision.message


def test_evaluate_merge_gate_rejects_branch_behind_main() -> None:
    inp = _valid_input(behind_by=2)
    decision = evaluate_merge_gate(inp)
    assert decision.eligible is False
    assert decision.reason is MergeGateReason.BRANCH_BEHIND_MAIN
    assert "2" in decision.message


def test_evaluate_merge_gate_rejects_not_fast_forward_merge_base() -> None:
    diverged_merge_base = "e" * 40
    inp = _valid_input(merge_base_sha=diverged_merge_base)
    decision = evaluate_merge_gate(inp)
    assert decision.eligible is False
    assert decision.reason is MergeGateReason.NOT_FAST_FORWARD


def test_evaluate_merge_gate_rejects_no_task_delta() -> None:
    inp = _valid_input(ahead_by=0)
    decision = evaluate_merge_gate(inp)
    assert decision.eligible is False
    assert decision.reason is MergeGateReason.NO_TASK_DELTA


def test_parse_review_header_canonical_pass() -> None:
    header = f"""
# REVIEW-069 ? Title

STATUS: PASS
APPROVED: YES
AUTO_MERGE_ELIGIBLE: YES
REVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}
REVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}

## Notes
Some markdown commentary
"""
    res = parse_review_header(header)
    assert res["status"] == "PASS"
    assert res["approved"] is True
    assert res["auto_merge_eligible"] is True
    assert res["reviewed_task_head_sha"] == VALID_TASK_SHA
    assert res["reviewed_base_main_sha"] == VALID_MAIN_SHA


def test_parse_review_header_supports_legacy_aliases() -> None:
    header = f"""
STATUS: PASS
APPROVED: YES
AUTO_MERGE_ALLOWED: YES
REVIEWED_HEAD_SHA: {VALID_TASK_SHA}
BASE_MAIN_SHA: {VALID_MAIN_SHA}
"""
    res = parse_review_header(header)
    assert res["status"] == "PASS"
    assert res["approved"] is True
    assert res["auto_merge_eligible"] is True
    assert res["reviewed_task_head_sha"] == VALID_TASK_SHA
    assert res["reviewed_base_main_sha"] == VALID_MAIN_SHA


def test_parse_review_header_rejects_duplicate_keys() -> None:
    header = f"""
STATUS: PASS
APPROVED: YES
STATUS: PASS
AUTO_MERGE_ELIGIBLE: YES
REVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}
REVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}
"""
    with pytest.raises(ContinuityStateValidationError, match="Duplicate"):
        parse_review_header(header)


@pytest.mark.parametrize("missing_key,header", [
    ("STATUS", f"APPROVED: YES\nAUTO_MERGE_ELIGIBLE: YES\nREVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}"),
    ("APPROVED", f"STATUS: PASS\nAUTO_MERGE_ELIGIBLE: YES\nREVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}"),
    ("AUTO_MERGE_ELIGIBLE", f"STATUS: PASS\nAPPROVED: YES\nREVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}"),
    ("REVIEWED_TASK_HEAD_SHA", f"STATUS: PASS\nAPPROVED: YES\nAUTO_MERGE_ELIGIBLE: YES\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}"),
    ("REVIEWED_BASE_MAIN_SHA", f"STATUS: PASS\nAPPROVED: YES\nAUTO_MERGE_ELIGIBLE: YES\nREVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}"),
])
def test_parse_review_header_rejects_missing_required_keys(missing_key: str, header: str) -> None:
    with pytest.raises(ContinuityStateValidationError, match="Missing required"):
        parse_review_header(header)


@pytest.mark.parametrize("invalid_val_header", [
    f"STATUS: PASS\nAPPROVED: TRUE\nAUTO_MERGE_ELIGIBLE: YES\nREVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}",
    f"STATUS: PASS\nAPPROVED: YES\nAUTO_MERGE_ELIGIBLE: MAYBE\nREVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}",
    f"STATUS: PASS\nAPPROVED: YES\nAUTO_MERGE_ELIGIBLE: YES\nREVIEWED_TASK_HEAD_SHA: invalid_sha\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}",
])
def test_parse_review_header_rejects_malformed_values(invalid_val_header: str) -> None:
    with pytest.raises(ContinuityStateValidationError):
        parse_review_header(invalid_val_header)


def test_parse_review_header_does_not_infer_pass_from_prose() -> None:
    prose_only = "This task is totally PASS and we should definitely merge it."
    with pytest.raises(ContinuityStateValidationError):
        parse_review_header(prose_only)


def test_merge_receipt_dataclass_and_json() -> None:
    receipt = MergeReceipt(
        task_id="TASK-069",
        reviewed_task_head_sha=VALID_TASK_SHA,
        reviewed_base_main_sha=VALID_MAIN_SHA,
        pre_merge_main_sha=VALID_MAIN_SHA,
        post_merge_main_sha=VALID_TASK_SHA,
        merge_method="FAST_FORWARD",
        force_update=False,
        auto_merge=True,
        gate_reason="PASS_ELIGIBLE",
        post_merge_identity_verified=True,
    )
    d = receipt.to_dict()
    assert d["task_id"] == "TASK-069"
    assert d["force_update"] is False
    assert d["merge_method"] == "FAST_FORWARD"
    assert d["gate_reason"] == "PASS_ELIGIBLE"
    assert d["post_merge_identity_verified"] is True
    assert '"task_id": "TASK-069"' in receipt.to_json()
