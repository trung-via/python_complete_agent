from __future__ import annotations

import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

import bridge
from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.roadmap_governance import (
    H_SERIES_ROADMAP_BLOB_SHA,
    H_SERIES_ROADMAP_PATH,
    RoadmapTaskBinding,
    git_blob_sha,
    parse_canonical_roadmap,
)
from src.aios_bridge.review_merge import (
    MergeGateDecision,
    MergeGateReason,
    MergeReceipt,
    ReviewHeaderParseError,
    ReviewedMergeInput,
    evaluate_merge_gate,
    parse_review_header,
)


VALID_TASK_SHA = "a" * 40
VALID_MAIN_SHA = "b" * 40
CONTROL_SHA = "c" * 40
CANONICAL_TASK_BLOB_SHA = "d" * 40
ROADMAP_BYTES = subprocess.run(
    ["git", "cat-file", "blob", H_SERIES_ROADMAP_BLOB_SHA],
    check=True,
    stdout=subprocess.PIPE,
).stdout


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
    ("lowercase_status", {"review_status": "pass"}),
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


def test_parse_review_header_ignores_later_fenced_blocks_when_header_is_missing() -> None:
    doc_with_fenced_example_only = f"""# REVIEW-069 ? Fake Title

Here is some prose in the body of the review.

```text
STATUS: PASS
APPROVED: YES
AUTO_MERGE_ELIGIBLE: YES
REVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}
REVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}
```

The above was an example block and should not be parsed as authoritative header.
"""
    with pytest.raises(ReviewHeaderParseError) as excinfo:
        parse_review_header(doc_with_fenced_example_only)
    assert excinfo.value.reason is MergeGateReason.REVIEW_NOT_PASS


def test_parse_review_header_ignores_later_section_keys_when_header_is_incomplete() -> None:
    doc_with_incomplete_header = f"""# REVIEW-069 ? Title

STATUS: PASS
APPROVED: YES

## Later Section
AUTO_MERGE_ELIGIBLE: YES
REVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}
REVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}
"""
    with pytest.raises(ReviewHeaderParseError) as excinfo:
        parse_review_header(doc_with_incomplete_header)
    assert excinfo.value.reason is MergeGateReason.AUTO_MERGE_DISABLED


@pytest.mark.parametrize("header_with_wrapper,expected_reason", [
    (
        f"STATUS: `PASS`\nAPPROVED: YES\nAUTO_MERGE_ELIGIBLE: YES\nREVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}",
        MergeGateReason.REVIEW_NOT_PASS,
    ),
    (
        f"STATUS: PASS\nAPPROVED: \"YES\"\nAUTO_MERGE_ELIGIBLE: YES\nREVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}",
        MergeGateReason.REVIEW_NOT_PASS,
    ),
    (
        f"STATUS: PASS\nAPPROVED: YES\nAUTO_MERGE_ELIGIBLE: YES\nREVIEWED_TASK_HEAD_SHA: `{VALID_TASK_SHA}`\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}",
        MergeGateReason.REVIEW_HEAD_INVALID,
    ),
])
def test_parse_review_header_rejects_markdown_wrappers(
    header_with_wrapper: str, expected_reason: MergeGateReason
) -> None:
    with pytest.raises(ReviewHeaderParseError) as excinfo:
        parse_review_header(header_with_wrapper)
    assert excinfo.value.reason is expected_reason


@pytest.mark.parametrize("header,expected_reason", [
    (
        f"STATUS: PASS\nAPPROVED: YES\nAUTO_MERGE_ELIGIBLE: YES\nAUTO_MERGE_ALLOWED: NO\nREVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}",
        MergeGateReason.AUTO_MERGE_DISABLED,
    ),
    (
        f"STATUS: PASS\nAPPROVED: YES\nAUTO_MERGE_ELIGIBLE: YES\nREVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}\nREVIEWED_HEAD_SHA: {'c'*40}\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}",
        MergeGateReason.REVIEW_HEAD_INVALID,
    ),
    (
        f"STATUS: PASS\nAPPROVED: YES\nAUTO_MERGE_ELIGIBLE: YES\nREVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}\nBASE_MAIN_SHA: {'d'*40}",
        MergeGateReason.REVIEW_BASE_INVALID,
    ),
])
def test_parse_review_header_rejects_alias_conflicts(header: str, expected_reason: MergeGateReason) -> None:
    with pytest.raises(ReviewHeaderParseError) as excinfo:
        parse_review_header(header)
    assert excinfo.value.reason is expected_reason


@pytest.mark.parametrize("invalid_casing_header,expected_reason", [
    (
        f"STATUS: pass\nAPPROVED: YES\nAUTO_MERGE_ELIGIBLE: YES\nREVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}",
        MergeGateReason.REVIEW_NOT_PASS,
    ),
    (
        f"STATUS: PASS\nAPPROVED: yes\nAUTO_MERGE_ELIGIBLE: YES\nREVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}",
        MergeGateReason.REVIEW_NOT_APPROVED,
    ),
    (
        f"STATUS: PASS\nAPPROVED: YES\nAUTO_MERGE_ELIGIBLE: yes\nREVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}",
        MergeGateReason.AUTO_MERGE_DISABLED,
    ),
    (
        f"STATUS: PASS\nAPPROVED: YES\nAUTO_MERGE_ELIGIBLE: YES\nREVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA.upper()}\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}",
        MergeGateReason.REVIEW_HEAD_INVALID,
    ),
    (
        f"STATUS: PASS\nAPPROVED: YES\nAUTO_MERGE_ELIGIBLE: YES\nREVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA.upper()}",
        MergeGateReason.REVIEW_BASE_INVALID,
    ),
])
def test_parse_review_header_rejects_non_canonical_casing(
    invalid_casing_header: str, expected_reason: MergeGateReason
) -> None:
    with pytest.raises(ReviewHeaderParseError) as excinfo:
        parse_review_header(invalid_casing_header)
    assert excinfo.value.reason is expected_reason


def test_parse_review_header_rejects_duplicate_keys() -> None:
    header = f"""
STATUS: PASS
APPROVED: YES
STATUS: PASS
AUTO_MERGE_ELIGIBLE: YES
REVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}
REVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}
"""
    with pytest.raises(ReviewHeaderParseError) as excinfo:
        parse_review_header(header)
    assert excinfo.value.reason is MergeGateReason.REVIEW_MISSING


@pytest.mark.parametrize("missing_key,header,expected_reason", [
    ("STATUS", f"APPROVED: YES\nAUTO_MERGE_ELIGIBLE: YES\nREVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}", MergeGateReason.REVIEW_NOT_PASS),
    ("APPROVED", f"STATUS: PASS\nAUTO_MERGE_ELIGIBLE: YES\nREVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}", MergeGateReason.REVIEW_NOT_APPROVED),
    ("AUTO_MERGE_ELIGIBLE", f"STATUS: PASS\nAPPROVED: YES\nREVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}", MergeGateReason.AUTO_MERGE_DISABLED),
    ("REVIEWED_TASK_HEAD_SHA", f"STATUS: PASS\nAPPROVED: YES\nAUTO_MERGE_ELIGIBLE: YES\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}", MergeGateReason.REVIEW_HEAD_INVALID),
    ("REVIEWED_BASE_MAIN_SHA", f"STATUS: PASS\nAPPROVED: YES\nAUTO_MERGE_ELIGIBLE: YES\nREVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}", MergeGateReason.REVIEW_BASE_INVALID),
])
def test_parse_review_header_rejects_missing_required_keys(
    missing_key: str, header: str, expected_reason: MergeGateReason
) -> None:
    with pytest.raises(ReviewHeaderParseError) as excinfo:
        parse_review_header(header)
    assert excinfo.value.reason is expected_reason


def test_parse_review_header_does_not_infer_pass_from_prose() -> None:
    prose_only = "This task is totally PASS and we should definitely merge it."
    with pytest.raises(ReviewHeaderParseError):
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


def _governed_command_artifacts(*, audit: str) -> tuple[str, str]:
    roadmap = parse_canonical_roadmap(
        ROADMAP_BYTES,
        artifact_path=H_SERIES_ROADMAP_PATH,
        expected_blob_sha=git_blob_sha(ROADMAP_BYTES),
    )
    milestone = roadmap.milestone("H0")
    binding = RoadmapTaskBinding(
        roadmap_id=roadmap.roadmap_id,
        roadmap_version=roadmap.roadmap_version,
        roadmap_blob_sha=roadmap.roadmap_blob_sha,
        roadmap_fingerprint=roadmap.roadmap_fingerprint,
        roadmap_fingerprint_algorithm_version=roadmap.algorithm_version,
        milestone="H0",
        capability_id=milestone.capability_id,
        requirement_bindings=(milestone.requirements[0],),
        scope_in=("bounded",),
        scope_out=("authority",),
    )
    policy = {
        "allow_paid_api": False,
        "candidates": [{
            "capacity_class": "SUBSCRIPTION",
            "executor_id": "codex",
            "preference_rank": 0,
            "supported_capabilities": ["SHELL"],
            "supported_operations": ["RUN"],
        }],
        "operation": "RUN",
        "required_capabilities": ["SHELL"],
    }
    task = f"""# TASK-069 — H0 governed implementation
STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: AIOS ENGINEERING H-SERIES
MILESTONE: H0
ROADMAP_BINDING_JSON: {json.dumps(binding.to_dict(), separators=(',', ':'))}
EXECUTOR_CONTEXT_REFS_JSON: [{{"path":"{H_SERIES_ROADMAP_PATH}","blob_sha":"{H_SERIES_ROADMAP_BLOB_SHA}"}}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {json.dumps(policy, separators=(',', ':'))}
"""
    audit_lines = ""
    if audit != "missing":
        fingerprint = "0" * 64 if audit == "wrong" else binding.roadmap_fingerprint
        audit_lines = f"""ROADMAP_AUDIT: PASS
ROADMAP_ID: {binding.roadmap_id}
ROADMAP_VERSION: {binding.roadmap_version}
ROADMAP_BLOB_SHA: {binding.roadmap_blob_sha}
ROADMAP_FINGERPRINT: {fingerprint}
MILESTONE: {binding.milestone}
CAPABILITY_ID: {binding.capability_id}
REQUIREMENT_BINDINGS_FINGERPRINT: {binding.requirement_bindings_fingerprint()}
"""
    review = f"""# REVIEW-069 — governed review
STATUS: PASS
APPROVED: YES
AUTO_MERGE_ELIGIBLE: YES
REVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}
REVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}
TASK_ARTIFACT_BLOB_SHA: {CANONICAL_TASK_BLOB_SHA}
{audit_lines}
## Findings
Bounded review.
"""
    return task, review


@pytest.mark.parametrize(
    "case,expected_reason",
    (
        ("missing_audit", MergeGateReason.ROADMAP_AUDIT_MISSING),
        ("wrong_roadmap", MergeGateReason.ROADMAP_IDENTITY_MISMATCH),
        ("wrong_task_blob", MergeGateReason.ROADMAP_TASK_INVALID),
        ("missing_task", MergeGateReason.ROADMAP_TASK_MISSING),
    ),
)
def test_cmd_merge_reviewed_governed_control_evidence_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
    case: str,
    expected_reason: MergeGateReason,
) -> None:
    audit = (
        "missing" if case == "missing_audit"
        else "wrong" if case == "wrong_roadmap"
        else "exact"
    )
    task, review = _governed_command_artifacts(audit=audit)
    if case == "wrong_task_blob":
        review = review.replace(CANONICAL_TASK_BLOB_SHA, "e" * 40)
    pushes = _install_governed_merge_command(
        monkeypatch,
        tmp_path,
        task=task,
        review=review,
        task_missing=case == "missing_task",
    )
    with pytest.raises(SystemExit):
        bridge.cmd_merge_reviewed(SimpleNamespace(task_id=69))
    assert pushes == []
    assert f"[MERGE_GATE] {expected_reason.value}:" in capsys.readouterr().out


def test_cmd_merge_reviewed_exact_control_roadmap_reaches_existing_gates(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    task, review = _governed_command_artifacts(audit="exact")
    pushes = _install_governed_merge_command(
        monkeypatch,
        tmp_path,
        task=task,
        review=review,
    )
    receipt = bridge.cmd_merge_reviewed(SimpleNamespace(task_id=69))
    assert receipt.gate_reason == MergeGateReason.PASS_ELIGIBLE.value
    assert pushes == [["push", "origin", f"{VALID_TASK_SHA}:refs/heads/main"]]


def _install_governed_merge_command(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    task: str,
    review: str,
    task_missing: bool = False,
) -> list[list[str]]:
    pushed = False
    pushes: list[list[str]] = []
    monkeypatch.setattr(bridge, "ensure_git", lambda: None)
    monkeypatch.setattr(bridge, "load_config", lambda: {
        "remote": "origin",
        "base_branch": "main",
        "control_branch": "ai-control",
        "task_branch_prefix": "ai/task-",
    })
    monkeypatch.setattr(
        bridge,
        "get_runtime_paths",
        lambda repo_root=None: {"root": tmp_path / "runtime"},
    )
    monkeypatch.setattr(
        bridge,
        "resolve_exact_roadmap_bytes",
        lambda ref, path, blob: ROADMAP_BYTES,
    )

    def fake_git(*args: str, check: bool = True) -> SimpleNamespace:
        nonlocal pushed
        op = args[0]
        if op == "fetch":
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if op == "show":
            target = args[1]
            if target.endswith(".ai/reviews/REVIEW-069.md"):
                return SimpleNamespace(returncode=0, stdout=review, stderr="")
            if target.endswith(".ai/tasks/TASK-069.md"):
                return SimpleNamespace(
                    returncode=1 if task_missing else 0,
                    stdout="" if task_missing else task,
                    stderr="missing" if task_missing else "",
                )
        if op == "rev-parse":
            target = args[1]
            if target == "refs/remotes/origin/ai-control":
                value = CONTROL_SHA
            elif target.endswith(":.ai/tasks/TASK-069.md"):
                if task_missing:
                    return SimpleNamespace(returncode=1, stdout="", stderr="missing")
                value = CANONICAL_TASK_BLOB_SHA
            elif target == "refs/remotes/origin/main":
                value = VALID_TASK_SHA if pushed else VALID_MAIN_SHA
            else:
                value = VALID_TASK_SHA
            return SimpleNamespace(returncode=0, stdout=value + "\n", stderr="")
        if op == "merge-base":
            return SimpleNamespace(returncode=0, stdout=VALID_MAIN_SHA + "\n", stderr="")
        if op == "rev-list":
            return SimpleNamespace(returncode=0, stdout="0\t1\n", stderr="")
        if op == "push":
            pushes.append(list(args))
            pushed = True
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(bridge, "git", fake_git)
    return pushes
