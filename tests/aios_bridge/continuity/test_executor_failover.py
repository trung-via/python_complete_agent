"""
Unit & adversarial tests for StableExecutorFailoverProof and validate_stable_executor_failover (ADR-020 / TASK-030 Milestone 6).
"""
from __future__ import annotations

import json
import pytest

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.executor import ExecutionOperation
from src.aios_bridge.continuity.executor_failover import (
    StableExecutorFailoverProof,
    validate_stable_executor_failover,
)
from src.aios_bridge.continuity.lease import ExecutorLease
from src.aios_bridge.continuity.state import MAX_SERIALIZED_BYTES, ArtifactRef


def _sample_source_lease(
    task_id: str = "TASK-030",
    executor_id: str = "executor-a",
    operation: ExecutionOperation = ExecutionOperation.RUN,
    workspace_id: str = "0" * 64,
    execution_fp: str = "1" * 64,
    lease_id: str = "lease-source-123",
) -> ExecutorLease:
    return ExecutorLease(
        schema_version="1",
        lease_id=lease_id,
        task_id=task_id,
        workspace_id=workspace_id,
        executor_id=executor_id,
        operation=operation,
        execution_fingerprint=execution_fp,
    )


def _sample_replacement_lease(
    task_id: str = "TASK-030",
    executor_id: str = "executor-b",
    operation: ExecutionOperation = ExecutionOperation.FIX,
    workspace_id: str = "0" * 64,
    execution_fp: str = "2" * 64,
    lease_id: str = "lease-replacement-456",
) -> ExecutorLease:
    return ExecutorLease(
        schema_version="1",
        lease_id=lease_id,
        task_id=task_id,
        workspace_id=workspace_id,
        executor_id=executor_id,
        operation=operation,
        execution_fingerprint=execution_fp,
    )


def _sample_proof(
    source_lease: ExecutorLease | None = None,
    replacement_lease: ExecutorLease | None = None,
    source_published_sha: str = "a" * 40,
    control_commit_sha: str = "b" * 40,
    review_blob_sha: str = "c" * 40,
    result_blob_sha: str = "d" * 40,
    target_branch: str = "ai/task-030",
) -> StableExecutorFailoverProof:
    s_lease = source_lease or _sample_source_lease()
    r_lease = replacement_lease or _sample_replacement_lease()
    task_num = int(s_lease.task_id.split("-")[1])

    return StableExecutorFailoverProof(
        schema_version="1",
        task_id=s_lease.task_id,
        target_branch=target_branch,
        source_executor_id=s_lease.executor_id,
        source_operation=s_lease.operation,
        source_execution_fingerprint=s_lease.execution_fingerprint,
        source_lease_fingerprint=s_lease.fingerprint(),
        source_published_sha=source_published_sha,
        source_result_ref=ArtifactRef(
            path=f".ai/results/RESULT-{task_num:03d}.md",
            ref=source_published_sha,
            blob_sha=result_blob_sha,
        ),
        replacement_executor_id=r_lease.executor_id,
        replacement_operation=r_lease.operation,
        replacement_execution_fingerprint=r_lease.execution_fingerprint,
        replacement_lease_fingerprint=r_lease.fingerprint(),
        review_ref=ArtifactRef(
            path=f".ai/reviews/REVIEW-{task_num:03d}.md",
            ref=control_commit_sha,
            blob_sha=review_blob_sha,
        ),
    )


def test_valid_stable_executor_failover_proof_and_fingerprint():
    source = _sample_source_lease()
    repl = _sample_replacement_lease()
    proof = _sample_proof(source, repl)

    # 1. Properties
    assert proof.task_id == "TASK-030"
    assert proof.source_executor_id == "executor-a"
    assert proof.replacement_executor_id == "executor-b"
    assert proof.source_operation == ExecutionOperation.RUN
    assert proof.replacement_operation == ExecutionOperation.FIX

    # 2. Canonical serialization roundtrip
    canon_json = proof.to_canonical_json()
    fp = proof.fingerprint()
    assert len(fp) == 64
    assert fp == proof.fingerprint()

    reloaded = StableExecutorFailoverProof.from_json(canon_json)
    assert reloaded == proof
    assert reloaded.fingerprint() == fp

    # 3. Dict input to from_json
    reloaded_dict = StableExecutorFailoverProof.from_json(proof.to_dict())
    assert reloaded_dict == proof


def test_proof_whitespace_and_casing_rejection():
    source = _sample_source_lease()
    repl = _sample_replacement_lease()

    # Whitespace in task_id
    with pytest.raises(ContinuityStateValidationError):
        _sample_proof(source_lease=_sample_source_lease(task_id="TASK-030 "))

    # Lowercase task_id
    with pytest.raises(ContinuityStateValidationError):
        _sample_proof(source_lease=_sample_source_lease(task_id="task-030"))


def test_proof_same_executor_pseudo_failover_rejected():
    """Validates C4: Same-executor FIX cannot construct a failover proof."""
    source = _sample_source_lease(executor_id="antigravity")
    repl = _sample_replacement_lease(executor_id="antigravity")

    with pytest.raises(ContinuityStateValidationError, match="must differ for failover"):
        _sample_proof(source_lease=source, replacement_lease=repl)


def test_proof_replacement_operation_must_be_fix():
    """Validates C5: Replacement operation must be FIX."""
    source = _sample_source_lease()
    repl = _sample_replacement_lease(operation=ExecutionOperation.RUN)

    with pytest.raises(ContinuityStateValidationError, match="replacement_operation must be.*FIX"):
        _sample_proof(source_lease=source, replacement_lease=repl)


def test_proof_source_operation_must_be_run_or_fix():
    """Validates C5: Source operation can be RUN or FIX."""
    # RUN is valid
    p1 = _sample_proof(source_lease=_sample_source_lease(operation=ExecutionOperation.RUN))
    assert p1.source_operation == ExecutionOperation.RUN

    # FIX is valid
    p2 = _sample_proof(source_lease=_sample_source_lease(operation=ExecutionOperation.FIX))
    assert p2.source_operation == ExecutionOperation.FIX


def test_proof_task_id_and_artifact_path_mismatches_rejected():
    """Validates C3: RESULT and REVIEW artifact paths must match exact numeric task identity."""
    source = _sample_source_lease(task_id="TASK-030")
    repl = _sample_replacement_lease(task_id="TASK-030")

    # Mismatched result path (e.g. cross-task alias RESULT-0300.md)
    with pytest.raises(ContinuityStateValidationError, match="does not match task_id"):
        StableExecutorFailoverProof(
            schema_version="1",
            task_id="TASK-030",
            target_branch="ai/task-030",
            source_executor_id=source.executor_id,
            source_operation=source.operation,
            source_execution_fingerprint=source.execution_fingerprint,
            source_lease_fingerprint=source.fingerprint(),
            source_published_sha="a" * 40,
            source_result_ref=ArtifactRef(
                path=".ai/results/RESULT-0300.md",
                ref="a" * 40,
                blob_sha="d" * 40,
            ),
            replacement_executor_id=repl.executor_id,
            replacement_operation=repl.operation,
            replacement_execution_fingerprint=repl.execution_fingerprint,
            replacement_lease_fingerprint=repl.fingerprint(),
            review_ref=ArtifactRef(
                path=".ai/reviews/REVIEW-030.md",
                ref="b" * 40,
                blob_sha="c" * 40,
            ),
        )

    # Mismatched review path (e.g. REVIEW-029.md)
    with pytest.raises(ContinuityStateValidationError, match="does not match task_id"):
        StableExecutorFailoverProof(
            schema_version="1",
            task_id="TASK-030",
            target_branch="ai/task-030",
            source_executor_id=source.executor_id,
            source_operation=source.operation,
            source_execution_fingerprint=source.execution_fingerprint,
            source_lease_fingerprint=source.fingerprint(),
            source_published_sha="a" * 40,
            source_result_ref=ArtifactRef(
                path=".ai/results/RESULT-030.md",
                ref="a" * 40,
                blob_sha="d" * 40,
            ),
            replacement_executor_id=repl.executor_id,
            replacement_operation=repl.operation,
            replacement_execution_fingerprint=repl.execution_fingerprint,
            replacement_lease_fingerprint=repl.fingerprint(),
            review_ref=ArtifactRef(
                path=".ai/reviews/REVIEW-029.md",
                ref="b" * 40,
                blob_sha="c" * 40,
            ),
        )


def test_proof_source_result_ref_must_equal_published_sha():
    """Validates C6: source_result_ref.ref must equal source_published_sha."""
    source = _sample_source_lease()
    repl = _sample_replacement_lease()

    with pytest.raises(ContinuityStateValidationError, match="must equal source_published_sha"):
        StableExecutorFailoverProof(
            schema_version="1",
            task_id="TASK-030",
            target_branch="ai/task-030",
            source_executor_id=source.executor_id,
            source_operation=source.operation,
            source_execution_fingerprint=source.execution_fingerprint,
            source_lease_fingerprint=source.fingerprint(),
            source_published_sha="a" * 40,
            source_result_ref=ArtifactRef(
                path=".ai/results/RESULT-030.md",
                ref="f" * 40,  # Does not match source_published_sha
                blob_sha="d" * 40,
            ),
            replacement_executor_id=repl.executor_id,
            replacement_operation=repl.operation,
            replacement_execution_fingerprint=repl.execution_fingerprint,
            replacement_lease_fingerprint=repl.fingerprint(),
            review_ref=ArtifactRef(
                path=".ai/reviews/REVIEW-030.md",
                ref="b" * 40,
                blob_sha="c" * 40,
            ),
        )


def test_proof_review_ref_must_be_40_hex_commit_sha():
    """Validates C6: review_ref.ref must be an exact immutable 40-hex commit SHA, not a floating branch."""
    source = _sample_source_lease()
    repl = _sample_replacement_lease()

    with pytest.raises(ContinuityStateValidationError, match="review_ref.ref"):
        StableExecutorFailoverProof(
            schema_version="1",
            task_id="TASK-030",
            target_branch="ai/task-030",
            source_executor_id=source.executor_id,
            source_operation=source.operation,
            source_execution_fingerprint=source.execution_fingerprint,
            source_lease_fingerprint=source.fingerprint(),
            source_published_sha="a" * 40,
            source_result_ref=ArtifactRef(
                path=".ai/results/RESULT-030.md",
                ref="a" * 40,
                blob_sha="d" * 40,
            ),
            replacement_executor_id=repl.executor_id,
            replacement_operation=repl.operation,
            replacement_execution_fingerprint=repl.execution_fingerprint,
            replacement_lease_fingerprint=repl.fingerprint(),
            review_ref=ArtifactRef(
                path=".ai/reviews/REVIEW-030.md",
                ref="ai-control",  # Floating branch name rejected!
                blob_sha="c" * 40,
            ),
        )


def test_proof_forbidden_keys_fail_closed():
    """Validates C9: Proof rejects authority/secret/transport keys."""
    proof = _sample_proof()
    d = proof.to_dict()

    for forbidden in ["approved", "api_key", "ttl", "heartbeat", "token", "auth", "pid", "quota", "command"]:
        bad = dict(d, **{forbidden: "invalid"})
        with pytest.raises(ContinuityStateValidationError, match="Forbidden.*keys"):
            StableExecutorFailoverProof.from_json(bad)


def test_proof_unknown_fields_fail_closed():
    proof = _sample_proof()
    d = proof.to_dict()
    d["extra_field"] = "unknown"
    with pytest.raises(ContinuityStateValidationError, match="Unknown fields"):
        StableExecutorFailoverProof.from_json(d)


def test_proof_missing_required_fields_fail_closed():
    proof = _sample_proof()
    d = proof.to_dict()
    for req in [
        "task_id",
        "target_branch",
        "source_executor_id",
        "source_operation",
        "source_execution_fingerprint",
        "source_lease_fingerprint",
        "source_published_sha",
        "source_result_ref",
        "replacement_executor_id",
        "replacement_operation",
        "replacement_execution_fingerprint",
        "replacement_lease_fingerprint",
        "review_ref",
    ]:
        bad = dict(d)
        del bad[req]
        with pytest.raises(ContinuityStateValidationError, match="Missing required fields"):
            StableExecutorFailoverProof.from_json(bad)


def test_proof_oversized_payload_rejected():
    oversized = b"{" + b"a" * (MAX_SERIALIZED_BYTES + 10) + b"}"
    with pytest.raises(ContinuityStateValidationError, match="exceeds limit"):
        StableExecutorFailoverProof.from_json(oversized)


def test_proof_malformed_json_and_invalid_utf8_wrapped():
    with pytest.raises(ContinuityStateValidationError, match="Invalid UTF-8"):
        StableExecutorFailoverProof.from_json(b"\xff\xfe\x00\x00")

    with pytest.raises(ContinuityStateValidationError, match="Malformed JSON"):
        StableExecutorFailoverProof.from_json("not json {")


def test_validate_stable_executor_failover_success():
    source = _sample_source_lease()
    repl = _sample_replacement_lease()
    proof = _sample_proof(source, repl)

    # Pure validation must complete without error
    validate_stable_executor_failover(proof, source_lease=source, replacement_lease=repl)


def test_validate_stable_executor_failover_task_mismatch():
    source = _sample_source_lease(task_id="TASK-030")
    repl = _sample_replacement_lease(task_id="TASK-030")
    proof = _sample_proof(source, repl)

    mismatched_source = _sample_source_lease(task_id="TASK-029")
    with pytest.raises(ContinuityStateValidationError, match="Source lease task_id"):
        validate_stable_executor_failover(proof, source_lease=mismatched_source, replacement_lease=repl)

    mismatched_repl = _sample_replacement_lease(task_id="TASK-029")
    with pytest.raises(ContinuityStateValidationError, match="Replacement lease task_id"):
        validate_stable_executor_failover(proof, source_lease=source, replacement_lease=mismatched_repl)


def test_validate_stable_executor_failover_source_executor_mismatch():
    source = _sample_source_lease(executor_id="executor-a")
    repl = _sample_replacement_lease(executor_id="executor-b")
    proof = _sample_proof(source, repl)

    bad_source = _sample_source_lease(executor_id="executor-c")
    with pytest.raises(ContinuityStateValidationError, match="Source lease executor_id"):
        validate_stable_executor_failover(proof, source_lease=bad_source, replacement_lease=repl)


def test_validate_stable_executor_failover_source_operation_mismatch():
    source = _sample_source_lease(operation=ExecutionOperation.RUN)
    repl = _sample_replacement_lease()
    proof = _sample_proof(source, repl)

    bad_source = _sample_source_lease(operation=ExecutionOperation.FIX)
    with pytest.raises(ContinuityStateValidationError, match="Source lease operation"):
        validate_stable_executor_failover(proof, source_lease=bad_source, replacement_lease=repl)


def test_validate_stable_executor_failover_source_fingerprints_mismatch():
    source = _sample_source_lease(execution_fp="1" * 64)
    repl = _sample_replacement_lease()
    proof = _sample_proof(source, repl)

    # Execution fingerprint mismatch
    bad_source = _sample_source_lease(execution_fp="9" * 64)
    with pytest.raises(ContinuityStateValidationError, match="execution_fingerprint"):
        validate_stable_executor_failover(proof, source_lease=bad_source, replacement_lease=repl)


def test_validate_stable_executor_failover_replacement_executor_mismatch():
    source = _sample_source_lease(executor_id="executor-a")
    repl = _sample_replacement_lease(executor_id="executor-b")
    proof = _sample_proof(source, repl)

    bad_repl = _sample_replacement_lease(executor_id="executor-c")
    with pytest.raises(ContinuityStateValidationError, match="Replacement lease executor_id"):
        validate_stable_executor_failover(proof, source_lease=source, replacement_lease=bad_repl)


def test_validate_stable_executor_failover_replacement_operation_mismatch():
    source = _sample_source_lease()
    repl = _sample_replacement_lease(operation=ExecutionOperation.FIX)
    proof = _sample_proof(source, repl)

    bad_repl = _sample_replacement_lease(operation=ExecutionOperation.RUN)
    with pytest.raises(ContinuityStateValidationError, match="must be FIX"):
        validate_stable_executor_failover(proof, source_lease=source, replacement_lease=bad_repl)


def test_validate_stable_executor_failover_workspace_mismatch():
    """Validates C8: Source and replacement workspace IDs must be identical."""
    source = _sample_source_lease(workspace_id="1" * 64)
    repl = _sample_replacement_lease(workspace_id="2" * 64)
    # Proof post_init passes since it doesn't take workspace_id directly
    proof = _sample_proof(source, repl)

    with pytest.raises(ContinuityStateValidationError, match="same-workspace failover"):
        validate_stable_executor_failover(proof, source_lease=source, replacement_lease=repl)


def test_validate_stable_executor_failover_type_validation():
    source = _sample_source_lease()
    repl = _sample_replacement_lease()
    proof = _sample_proof(source, repl)

    with pytest.raises(ContinuityStateValidationError, match="proof must be StableExecutorFailoverProof"):
        validate_stable_executor_failover("invalid_proof", source_lease=source, replacement_lease=repl)

    with pytest.raises(ContinuityStateValidationError, match="source_lease must be ExecutorLease"):
        validate_stable_executor_failover(proof, source_lease="invalid_lease", replacement_lease=repl)

    with pytest.raises(ContinuityStateValidationError, match="replacement_lease must be ExecutorLease"):
        validate_stable_executor_failover(proof, source_lease=source, replacement_lease="invalid_lease")


def test_proof_alias_paths_rejected_strictly():
    """Validates R1-4: Exact token matching without alias normalization (e.g. RESULT-30.md rejected for TASK-030)."""
    source = _sample_source_lease(task_id="TASK-030")
    repl = _sample_replacement_lease(task_id="TASK-030")

    # RESULT-30.md (unpadded alias) rejected for TASK-030
    with pytest.raises(ContinuityStateValidationError, match="does not match task_id 'TASK-030'"):
        StableExecutorFailoverProof(
            schema_version="1",
            task_id="TASK-030",
            target_branch="ai/task-030",
            source_executor_id=source.executor_id,
            source_operation=source.operation,
            source_execution_fingerprint=source.execution_fingerprint,
            source_lease_fingerprint=source.fingerprint(),
            source_published_sha="a" * 40,
            source_result_ref=ArtifactRef(
                path=".ai/results/RESULT-30.md",  # Alias!
                ref="a" * 40,
                blob_sha="d" * 40,
            ),
            replacement_executor_id=repl.executor_id,
            replacement_operation=repl.operation,
            replacement_execution_fingerprint=repl.execution_fingerprint,
            replacement_lease_fingerprint=repl.fingerprint(),
            review_ref=ArtifactRef(
                path=".ai/reviews/REVIEW-030.md",
                ref="b" * 40,
                blob_sha="c" * 40,
            ),
        )

    # REVIEW-30.md (unpadded alias) rejected for TASK-030
    with pytest.raises(ContinuityStateValidationError, match="does not match task_id 'TASK-030'"):
        StableExecutorFailoverProof(
            schema_version="1",
            task_id="TASK-030",
            target_branch="ai/task-030",
            source_executor_id=source.executor_id,
            source_operation=source.operation,
            source_execution_fingerprint=source.execution_fingerprint,
            source_lease_fingerprint=source.fingerprint(),
            source_published_sha="a" * 40,
            source_result_ref=ArtifactRef(
                path=".ai/results/RESULT-030.md",
                ref="a" * 40,
                blob_sha="d" * 40,
            ),
            replacement_executor_id=repl.executor_id,
            replacement_operation=repl.operation,
            replacement_execution_fingerprint=repl.execution_fingerprint,
            replacement_lease_fingerprint=repl.fingerprint(),
            review_ref=ArtifactRef(
                path=".ai/reviews/REVIEW-30.md",  # Alias!
                ref="b" * 40,
                blob_sha="c" * 40,
            ),
        )


def test_proof_schema_version_required_and_strictly_one():
    """Validates R1-4: schema_version must be explicit and strictly '1'."""
    source = _sample_source_lease()
    repl = _sample_replacement_lease()

    # Invalid schema_version
    with pytest.raises(ContinuityStateValidationError, match="Unsupported schema_version"):
        StableExecutorFailoverProof(
            schema_version="2",
            task_id="TASK-030",
            target_branch="ai/task-030",
            source_executor_id=source.executor_id,
            source_operation=source.operation,
            source_execution_fingerprint=source.execution_fingerprint,
            source_lease_fingerprint=source.fingerprint(),
            source_published_sha="a" * 40,
            source_result_ref=ArtifactRef(
                path=".ai/results/RESULT-030.md",
                ref="a" * 40,
                blob_sha="d" * 40,
            ),
            replacement_executor_id=repl.executor_id,
            replacement_operation=repl.operation,
            replacement_execution_fingerprint=repl.execution_fingerprint,
            replacement_lease_fingerprint=repl.fingerprint(),
            review_ref=ArtifactRef(
                path=".ai/reviews/REVIEW-030.md",
                ref="b" * 40,
                blob_sha="c" * 40,
            ),
        )

    # Missing schema_version in from_dict fails closed
    d = _sample_proof().to_dict()
    del d["schema_version"]
    with pytest.raises(ContinuityStateValidationError, match="Missing required fields"):
        StableExecutorFailoverProof.from_dict(d)


def test_proof_oversized_direct_construction_rejected():
    """Validates R1-4: Direct construction exceeding MAX_SERIALIZED_BYTES fails closed in __post_init__."""
    source = _sample_source_lease()
    repl = _sample_replacement_lease()
    huge_branch = "ai/" + "x" * MAX_SERIALIZED_BYTES

    with pytest.raises(ContinuityStateValidationError, match="exceeds maximum allowed"):
        StableExecutorFailoverProof(
            schema_version="1",
            task_id="TASK-030",
            target_branch=huge_branch,
            source_executor_id=source.executor_id,
            source_operation=source.operation,
            source_execution_fingerprint=source.execution_fingerprint,
            source_lease_fingerprint=source.fingerprint(),
            source_published_sha="a" * 40,
            source_result_ref=ArtifactRef(
                path=".ai/results/RESULT-030.md",
                ref="a" * 40,
                blob_sha="d" * 40,
            ),
            replacement_executor_id=repl.executor_id,
            replacement_operation=repl.operation,
            replacement_execution_fingerprint=repl.execution_fingerprint,
            replacement_lease_fingerprint=repl.fingerprint(),
            review_ref=ArtifactRef(
                path=".ai/reviews/REVIEW-030.md",
                ref="b" * 40,
                blob_sha="c" * 40,
            ),
        )
