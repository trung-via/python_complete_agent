"""Tests for AIOS Engineering Harness Foundation (H0) immutable contracts and authority boundary."""
from __future__ import annotations

import dataclasses
from pathlib import Path
import pytest

from src.aios_engineering.harness.contracts import (
    EvidenceKind,
    HarnessEvidenceExclusion,
    HarnessExtensionPoint,
    HarnessIntelligencePlan,
    HarnessReceipt,
    RepositoryEvidenceRef,
    RepositorySnapshotRef,
    MAX_SCHEMA_VERSION_LENGTH,
    MAX_PATH_LENGTH,
    MAX_REASON_CODE_LENGTH,
    MAX_SYMBOL_LOCATOR_LENGTH,
    MAX_GENERATOR_VERSION_LENGTH,
)
from src.aios_engineering.harness.errors import (
    HarnessError,
    HarnessFingerprintError,
    HarnessValidationError,
)
from src.aios_engineering.harness.fingerprint import (
    canonical_json_bytes,
    compute_candidate_set_fingerprint,
    compute_plan_fingerprint,
    compute_sha256,
)


COMMIT_A = "a" * 40
TREE_A = "b" * 40
BLOB_1 = "1" * 40
BLOB_2 = "2" * 40
BLOB_3 = "3" * 40


def _sample_snapshot() -> RepositorySnapshotRef:
    return RepositorySnapshotRef(
        repository_commit_sha=COMMIT_A,
        repository_tree_sha=TREE_A,
    )


def _sample_evidence(
    path: str = "src/core/main.py",
    blob_sha: str = BLOB_1,
    kind: EvidenceKind = EvidenceKind.SOURCE,
    reason: str = "TASK_TARGET",
    priority: int = 100,
    symbol_locator: str | None = None,
) -> RepositoryEvidenceRef:
    return RepositoryEvidenceRef(
        path=path,
        blob_sha=blob_sha,
        evidence_kind=kind,
        reason_code=reason,
        priority=priority,
        symbol_locator=symbol_locator,
    )


def test_snapshot_roundtrip_and_immutability():
    snap = _sample_snapshot()
    assert snap.repository_commit_sha == COMMIT_A
    assert snap.repository_tree_sha == TREE_A
    assert snap.schema_version == "1"
    assert snap.to_dict() == {
        "repository_commit_sha": COMMIT_A,
        "repository_tree_sha": TREE_A,
        "schema_version": "1",
    }
    with pytest.raises(dataclasses.FrozenInstanceError):
        snap.repository_commit_sha = "c" * 40  # type: ignore


@pytest.mark.parametrize("invalid_sha", [
    "A" * 40,  # uppercase
    "a" * 39,  # too short
    "a" * 41,  # too long
    "g" * 40,  # non-hex
    "",
    123,
    None,
])
def test_snapshot_rejects_invalid_commit_or_tree_sha(invalid_sha):
    with pytest.raises(HarnessValidationError):
        RepositorySnapshotRef(repository_commit_sha=invalid_sha, repository_tree_sha=TREE_A)  # type: ignore
    with pytest.raises(HarnessValidationError):
        RepositorySnapshotRef(repository_commit_sha=COMMIT_A, repository_tree_sha=invalid_sha)  # type: ignore


def test_snapshot_rejects_oversized_schema_version():
    oversized = "x" * (MAX_SCHEMA_VERSION_LENGTH + 1)
    with pytest.raises(HarnessValidationError, match="schema_version length .* exceeds maximum"):
        RepositorySnapshotRef(repository_commit_sha=COMMIT_A, repository_tree_sha=TREE_A, schema_version=oversized)


def test_evidence_kind_coverage():
    expected_kinds = {"SOURCE", "TEST", "DOCUMENTATION", "CONFIGURATION", "CONTRACT", "OTHER"}
    assert {k.value for k in EvidenceKind} == expected_kinds
    for k in EvidenceKind:
        ev = _sample_evidence(kind=k)
        assert ev.evidence_kind == k


@pytest.mark.parametrize("invalid_path", [
    "/absolute/path/foo.py",
    "C:/absolute/windows/path.py",
    r"C:\windows\path.py",
    r"src\core\main.py",
    "src//core/main.py",
    "src/core/main.py/",
    "/src/core/main.py",
    "./src/core/main.py",
    "src/./core/main.py",
    "../src/core/main.py",
    "src/../core/main.py",
    ".git",
    ".git/config",
    "src/.git/hooks",
    "src/core" + chr(0) + "main.py",
    "src/core\nmain.py",
    "",
])
def test_evidence_rejects_unsafe_paths(invalid_path):
    with pytest.raises(HarnessValidationError):
        _sample_evidence(path=invalid_path)


def test_evidence_rejects_oversized_path():
    oversized_path = "src/" + "a" * (MAX_PATH_LENGTH + 1)
    with pytest.raises(HarnessValidationError, match="path length .* exceeds maximum"):
        _sample_evidence(path=oversized_path)


@pytest.mark.parametrize("invalid_reason", [
    "",
    "has whitespace",
    "lowercase_not_allowed",
    "invalid@char",
    "control\nchar",
    "VALID_REASON\n",
    "VALID_REASON\r",
    "VALID_REASON\t",
    "\nVALID_REASON",
    "VALID_REASON\nEXTRA",
])
def test_evidence_rejects_invalid_reason_code(invalid_reason):
    with pytest.raises(HarnessValidationError):
        _sample_evidence(reason=invalid_reason)


@pytest.mark.parametrize("invalid_reason", [
    "",
    "has whitespace",
    "lowercase_not_allowed",
    "invalid@char",
    "control\nchar",
    "VALID_REASON\n",
    "VALID_REASON\r",
    "VALID_REASON\t",
    "\nVALID_REASON",
    "VALID_REASON\nEXTRA",
])
def test_exclusion_rejects_invalid_reason_code(invalid_reason):
    ev = _sample_evidence()
    with pytest.raises(HarnessValidationError):
        HarnessEvidenceExclusion(evidence=ev, reason_code=invalid_reason)


def test_evidence_rejects_oversized_reason_code():
    oversized_reason = "REASON_" + "X" * MAX_REASON_CODE_LENGTH
    with pytest.raises(HarnessValidationError, match="reason_code length .* exceeds maximum"):
        _sample_evidence(reason=oversized_reason)


def test_exclusion_rejects_oversized_reason_code():
    ev = _sample_evidence()
    oversized_reason = "REASON_" + "X" * MAX_REASON_CODE_LENGTH
    with pytest.raises(HarnessValidationError, match="reason_code length .* exceeds maximum"):
        HarnessEvidenceExclusion(evidence=ev, reason_code=oversized_reason)


@pytest.mark.parametrize("invalid_priority", [
    True,  # bool is forbidden
    False,  # bool is forbidden
    -1,
    1001,
    "100",  # string is forbidden
    None,
])
def test_evidence_rejects_invalid_priority(invalid_priority):
    with pytest.raises(HarnessValidationError):
        _sample_evidence(priority=invalid_priority)  # type: ignore


@pytest.mark.parametrize("invalid_locator", [
    "",
    "/absolute/symbol/path",
    r"C:\path\symbol",
    "has\ncontrol",
])
def test_evidence_rejects_invalid_symbol_locator(invalid_locator):
    with pytest.raises(HarnessValidationError):
        _sample_evidence(symbol_locator=invalid_locator)


def test_evidence_rejects_oversized_symbol_locator():
    oversized_loc = "sym_" + "x" * MAX_SYMBOL_LOCATOR_LENGTH
    with pytest.raises(HarnessValidationError, match="symbol_locator length .* exceeds maximum"):
        _sample_evidence(symbol_locator=oversized_loc)


def test_duplicate_exact_evidence_rejected_in_plan():
    snap = _sample_snapshot()
    ev1 = _sample_evidence("src/core/a.py", BLOB_1)
    ev1_dup = _sample_evidence("src/core/a.py", BLOB_1)
    with pytest.raises(HarnessValidationError, match="Duplicate exact evidence"):
        HarnessIntelligencePlan.create(
            task_id="TASK-066",
            snapshot=snap,
            selected_evidence=[ev1, ev1_dup],
        )


def test_conflicting_blob_sha_for_same_path_and_symbol_rejected():
    snap = _sample_snapshot()
    ev1 = _sample_evidence("src/core/a.py", BLOB_1, symbol_locator="foo_fn")
    ev2_conflict = _sample_evidence("src/core/a.py", BLOB_2, symbol_locator="foo_fn")
    with pytest.raises(HarnessValidationError, match="Conflicting blob SHA"):
        HarnessIntelligencePlan.create(
            task_id="TASK-066",
            snapshot=snap,
            selected_evidence=[ev1, ev2_conflict],
        )


def test_candidate_set_fingerprint_is_order_independent_for_selected():
    ev1 = _sample_evidence("src/a.py", BLOB_1, priority=10)
    ev2 = _sample_evidence("src/b.py", BLOB_2, priority=20)
    ev3 = _sample_evidence("src/c.py", BLOB_3, priority=30)
    ex1 = HarnessEvidenceExclusion(evidence=_sample_evidence("src/d.py", BLOB_1), reason_code="EXCLUDED_VENDOR")

    fp_1 = compute_candidate_set_fingerprint([ev1, ev2, ev3], [ex1])
    fp_2 = compute_candidate_set_fingerprint([ev3, ev1, ev2], [ex1])
    fp_3 = compute_candidate_set_fingerprint([ev2, ev3, ev1], [ex1])

    assert fp_1 == fp_2 == fp_3


def test_candidate_set_fingerprint_is_order_independent_for_exclusions():
    ev1 = _sample_evidence("src/a.py", BLOB_1)
    ex1 = HarnessEvidenceExclusion(evidence=_sample_evidence("src/b.py", BLOB_2), reason_code="EXCLUDED_A")
    ex2 = HarnessEvidenceExclusion(evidence=_sample_evidence("src/c.py", BLOB_3), reason_code="EXCLUDED_B")

    fp_forward = compute_candidate_set_fingerprint([ev1], [ex1, ex2])
    fp_reverse = compute_candidate_set_fingerprint([ev1], [ex2, ex1])

    assert fp_forward == fp_reverse


def test_candidate_set_fingerprint_invariant_when_evidence_moves_selected_to_excluded():
    ev1 = _sample_evidence("src/a.py", BLOB_1)
    ev2 = _sample_evidence("src/b.py", BLOB_2)
    ex_for_ev2 = HarnessEvidenceExclusion(evidence=ev2, reason_code="EXCLUDED_FILTER")

    fp_all_selected = compute_candidate_set_fingerprint([ev1, ev2], [])
    fp_one_excluded = compute_candidate_set_fingerprint([ev1], [ex_for_ev2])

    assert fp_all_selected == fp_one_excluded


def test_candidate_set_fingerprint_invariant_when_exclusion_reason_changes():
    ev1 = _sample_evidence("src/a.py", BLOB_1)
    ev2 = _sample_evidence("src/b.py", BLOB_2)
    ex_reason_A = HarnessEvidenceExclusion(evidence=ev2, reason_code="REASON_A")
    ex_reason_B = HarnessEvidenceExclusion(evidence=ev2, reason_code="REASON_B")

    fp_A = compute_candidate_set_fingerprint([ev1], [ex_reason_A])
    fp_B = compute_candidate_set_fingerprint([ev1], [ex_reason_B])

    assert fp_A == fp_B


def test_plan_fingerprint_is_deterministic_for_identical_input():
    snap = _sample_snapshot()
    ev1 = _sample_evidence("src/a.py", BLOB_1)
    ev2 = _sample_evidence("src/b.py", BLOB_2)

    plan_1 = HarnessIntelligencePlan.create("TASK-066", snap, [ev1, ev2])
    plan_2 = HarnessIntelligencePlan.create("TASK-066", snap, [ev1, ev2])

    assert plan_1.candidate_set_fingerprint == plan_2.candidate_set_fingerprint
    assert plan_1.plan_fingerprint == plan_2.plan_fingerprint


def test_plan_fingerprint_is_invariant_under_exclusion_permutation():
    snap = _sample_snapshot()
    ev1 = _sample_evidence("src/a.py", BLOB_1)
    ex1 = HarnessEvidenceExclusion(evidence=_sample_evidence("src/b.py", BLOB_2), reason_code="REASON_A")
    ex2 = HarnessEvidenceExclusion(evidence=_sample_evidence("src/c.py", BLOB_3), reason_code="REASON_B")

    plan1 = HarnessIntelligencePlan.create("TASK-066", snap, [ev1], [ex1, ex2])
    plan2 = HarnessIntelligencePlan.create("TASK-066", snap, [ev1], [ex2, ex1])

    assert plan1.candidate_set_fingerprint == plan2.candidate_set_fingerprint
    assert plan1.plan_fingerprint == plan2.plan_fingerprint


def test_plan_fingerprint_changes_when_selected_ranking_changes():
    snap = _sample_snapshot()
    ev1 = _sample_evidence("src/a.py", BLOB_1, priority=100)
    ev2 = _sample_evidence("src/b.py", BLOB_2, priority=50)

    plan_forward = HarnessIntelligencePlan.create("TASK-066", snap, [ev1, ev2])
    plan_reverse = HarnessIntelligencePlan.create("TASK-066", snap, [ev2, ev1])

    # Candidate set is identical because it is order-independent
    assert plan_forward.candidate_set_fingerprint == plan_reverse.candidate_set_fingerprint
    # Plan fingerprint MUST differ because selected ranking changed
    assert plan_forward.plan_fingerprint != plan_reverse.plan_fingerprint


def test_plan_fingerprint_changes_when_snapshot_commit_changes():
    snap1 = _sample_snapshot()
    snap2 = RepositorySnapshotRef(repository_commit_sha="c" * 40, repository_tree_sha=TREE_A)
    ev1 = _sample_evidence("src/a.py", BLOB_1)

    plan1 = HarnessIntelligencePlan.create("TASK-066", snap1, [ev1])
    plan2 = HarnessIntelligencePlan.create("TASK-066", snap2, [ev1])

    assert plan1.plan_fingerprint != plan2.plan_fingerprint


def test_plan_fingerprint_changes_when_snapshot_tree_changes():
    snap1 = _sample_snapshot()
    snap2 = RepositorySnapshotRef(repository_commit_sha=COMMIT_A, repository_tree_sha="d" * 40)
    ev1 = _sample_evidence("src/a.py", BLOB_1)

    plan1 = HarnessIntelligencePlan.create("TASK-066", snap1, [ev1])
    plan2 = HarnessIntelligencePlan.create("TASK-066", snap2, [ev1])

    assert plan1.plan_fingerprint != plan2.plan_fingerprint


def test_plan_rejects_forged_or_tampered_fingerprints():
    snap = _sample_snapshot()
    ev1 = _sample_evidence("src/a.py", BLOB_1)
    plan = HarnessIntelligencePlan.create("TASK-066", snap, [ev1])

    with pytest.raises(HarnessFingerprintError, match="Candidate set fingerprint mismatch"):
        HarnessIntelligencePlan(
            task_id=plan.task_id,
            snapshot=plan.snapshot,
            selected_evidence=plan.selected_evidence,
            excluded_evidence=plan.excluded_evidence,
            candidate_set_fingerprint="0" * 64,  # tampered
            plan_fingerprint=plan.plan_fingerprint,
        )

    with pytest.raises(HarnessFingerprintError, match="Plan fingerprint mismatch"):
        HarnessIntelligencePlan(
            task_id=plan.task_id,
            snapshot=plan.snapshot,
            selected_evidence=plan.selected_evidence,
            excluded_evidence=plan.excluded_evidence,
            candidate_set_fingerprint=plan.candidate_set_fingerprint,
            plan_fingerprint="0" * 64,  # tampered
        )


def test_receipt_valid_and_immutability():
    receipt = HarnessReceipt(
        task_id="TASK-066",
        repository_commit_sha=COMMIT_A,
        input_fingerprint="1" * 64,
        output_fingerprint="2" * 64,
        generator_version="0.1.0",
        candidate_count=3,
        selected_count=2,
        excluded_count=1,
    )
    assert receipt.candidate_count == 3
    assert receipt.authority_created is False
    assert receipt.network_used is False
    assert receipt.llm_used is False
    assert receipt.paid_api_used is False


@pytest.mark.parametrize("flag_name", [
    "authority_created",
    "network_used",
    "llm_used",
    "paid_api_used",
])
def test_receipt_rejects_any_authority_or_side_effect_flag_true(flag_name):
    kwargs = {
        "task_id": "TASK-066",
        "repository_commit_sha": COMMIT_A,
        "input_fingerprint": "1" * 64,
        "output_fingerprint": "2" * 64,
        "generator_version": "0.1.0",
        "candidate_count": 3,
        "selected_count": 2,
        "excluded_count": 1,
        flag_name: True,
    }
    with pytest.raises(HarnessValidationError, match=f"{flag_name} must be False"):
        HarnessReceipt(**kwargs)


def test_receipt_rejects_count_mismatch():
    with pytest.raises(HarnessValidationError, match=r"candidate_count .* must equal"):
        HarnessReceipt(
            task_id="TASK-066",
            repository_commit_sha=COMMIT_A,
            input_fingerprint="1" * 64,
            output_fingerprint="2" * 64,
            generator_version="0.1.0",
            candidate_count=5,  # Mismatch: 2 + 1 != 5
            selected_count=2,
            excluded_count=1,
        )


def test_receipt_rejects_oversized_strings():
    oversized = "x" * (MAX_SCHEMA_VERSION_LENGTH + 1)
    with pytest.raises(HarnessValidationError, match="schema_version length .* exceeds maximum"):
        HarnessReceipt(
            task_id="TASK-066",
            repository_commit_sha=COMMIT_A,
            input_fingerprint="1" * 64,
            output_fingerprint="2" * 64,
            generator_version="0.1.0",
            candidate_count=1,
            selected_count=1,
            excluded_count=0,
            schema_version=oversized,
        )

    oversized_gen = "gen_" + "x" * MAX_GENERATOR_VERSION_LENGTH
    with pytest.raises(HarnessValidationError, match="generator_version length .* exceeds maximum"):
        HarnessReceipt(
            task_id="TASK-066",
            repository_commit_sha=COMMIT_A,
            input_fingerprint="1" * 64,
            output_fingerprint="2" * 64,
            generator_version=oversized_gen,
            candidate_count=1,
            selected_count=1,
            excluded_count=0,
        )


def test_extension_point_enum_exact_identities():
    expected = {"SKILL_COMPILER", "SKILL_PRECEDENCE", "EXECUTOR_SPECIFIC_RENDERING"}
    assert {ep.value for ep in HarnessExtensionPoint} == expected


def test_package_source_contains_no_aios_bridge_imports():
    harness_dir = Path("src/aios_engineering/harness")
    for py_file in harness_dir.glob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        assert "aios_bridge" not in content, f"{py_file} contains forbidden import of aios_bridge"
        assert "import bridge" not in content, f"{py_file} contains forbidden import of bridge"


def test_contracts_contain_no_authority_or_dispatch_fields():
    forbidden_field_substrings = [
        "lease",
        "dispatch",
        "executor_id",
        "allow_paid_api",
        "token_limit",
        "retry",
        "failover",
        "approval",
    ]
    for cls in [RepositorySnapshotRef, RepositoryEvidenceRef, HarnessIntelligencePlan, HarnessReceipt]:
        field_names = [f.name for f in dataclasses.fields(cls)]
        for fn in field_names:
            for sub in forbidden_field_substrings:
                assert sub not in fn, f"Class {cls.__name__} has forbidden authority field {fn}"
