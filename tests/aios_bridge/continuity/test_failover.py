"""Comprehensive test suite for AIOS Brain Failover Contract & Proof Harness (ADR-010 / ADR-016 Milestone 3A)."""
from __future__ import annotations

import json
import pytest

from src.aios_bridge.continuity import (
    ArtifactRef,
    BrainCapability,
    BrainFailoverProof,
    BrainOperation,
    BrainOutputType,
    BrainRequest,
    BrainResult,
    BrainResultStatus,
    BranchState,
    ContextRef,
    ContinuityArtifacts,
    ContinuityPhase,
    ContinuityState,
    ContinuityStateValidationError,
    ExecutorState,
    NextOperation,
    OutputContract,
    build_replacement_brain_request,
    validate_brain_failover_eligibility,
)


def _make_valid_state(task_id: str = "TASK-022") -> ContinuityState:
    return ContinuityState(
        schema_version="1",
        task_id=task_id,
        phase=ContinuityPhase.RUNNING,
        next_operation=NextOperation.WAIT_FOR_RESULT,
        main=BranchState(
            branch="main",
            sha="4978e426f3445c086c017c07c844943ac841e4de",
        ),
        task_branch=BranchState(
            branch=f"ai/{task_id.lower()}",
            sha="4978e426f3445c086c017c07c844943ac841e4de",
        ),
        artifacts=ContinuityArtifacts(
            task=ArtifactRef(
                path=f".ai/tasks/{task_id}.md",
                blob_sha="92494bcd64b594d60a5f74a82e3e64c113d817db",
                ref="task",
            ),
        ),
        executor=ExecutorState(last_id="antigravity"),
    )


def _make_valid_source_request(task_id: str = "TASK-022") -> BrainRequest:
    return BrainRequest(
        schema_version="1",
        task_id=task_id,
        request_id=f"req-{task_id.lower()}-task-and-plan-r1",
        brain_id="brain-a",
        operation=BrainOperation.TASK_AND_PLAN,
        objective="Design and author task contract and plan",
        context_refs=(
            ContextRef(
                path=".ai/decisions/ADR-010-OPEN-MULTI-AGENT-CONTINUITY-OS-ARCHITECTURE-LOCK.md",
                blob_sha="a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
                description="Continuity OS architecture lock",
            ),
            ContextRef(
                path=f".ai/tasks/{task_id}.md",
                blob_sha="92494bcd64b594d60a5f74a82e3e64c113d817db",
                description="Task definition",
            ),
        ),
        output_contract=OutputContract(
            expected_output_type=BrainOutputType.TASK_ARTIFACT,
            target_artifact_path=f".ai/tasks/{task_id}.md",
            max_output_bytes=16384,
        ),
    )


def _make_valid_replacement_capability(brain_id: str = "brain-b") -> BrainCapability:
    return BrainCapability(
        brain_id=brain_id,
        supported_operations=(BrainOperation.TASK, BrainOperation.TASK_AND_PLAN, BrainOperation.PLAN),
        declarative_only=True,
    )


def test_valid_replacement_request_construction_and_field_preservation():
    """Derived replacement request preserves all task semantics and changes only brain_id and request_id."""
    src = _make_valid_source_request("TASK-022")
    rep = build_replacement_brain_request(src, "brain-b", "req-task-022-task-and-plan-r2")

    assert rep.task_id == src.task_id
    assert rep.schema_version == src.schema_version
    assert rep.operation == src.operation
    assert rep.objective == src.objective
    assert rep.context_refs == src.context_refs
    assert rep.output_contract == src.output_contract
    assert rep.brain_id == "brain-b"
    assert rep.request_id == "req-task-022-task-and-plan-r2"
    assert rep.fingerprint() != src.fingerprint()


def test_same_brain_pseudo_failover_rejected():
    """Same-Brain replacement derivation and proof fails closed."""
    src = _make_valid_source_request("TASK-022")
    with pytest.raises(ContinuityStateValidationError, match="Same-Brain pseudo-failover rejected"):
        build_replacement_brain_request(src, "brain-a", "req-task-022-r2")

    # In proof directly
    state = _make_valid_state("TASK-022")
    with pytest.raises(ContinuityStateValidationError, match="Same-Brain pseudo-failover rejected"):
        BrainFailoverProof(
            task_id="TASK-022",
            operation=BrainOperation.TASK_AND_PLAN,
            state_fingerprint=state.fingerprint(),
            source_brain_id="brain-a",
            source_request_id="req-1",
            source_request_fingerprint=src.fingerprint(),
            replacement_brain_id="brain-a",
            replacement_request_id="req-2",
            replacement_request_fingerprint=src.fingerprint(),
        )


def test_canonical_actor_id_and_whitespace_padded_pseudo_failover_rejected():
    """R4-1: Non-canonical whitespace-padded Brain IDs fail closed and cannot bypass same-Brain check."""
    src = _make_valid_source_request("TASK-022")
    state = _make_valid_state("TASK-022")
    cap = _make_valid_replacement_capability("brain-b")

    # 1. Padded replacement brain_id in build_replacement_brain_request fails closed
    with pytest.raises(ContinuityStateValidationError, match="must not contain leading or trailing whitespace"):
        build_replacement_brain_request(src, "brain-a ", "req-task-022-r2")

    with pytest.raises(ContinuityStateValidationError, match="must not contain leading or trailing whitespace"):
        build_replacement_brain_request(src, " brain-b", "req-task-022-r2")

    # 2. Padded source brain_id in BrainRequest fails closed when used in failover
    src_padded = BrainRequest(
        schema_version=src.schema_version,
        task_id=src.task_id,
        request_id=src.request_id,
        brain_id="brain-a ",
        operation=src.operation,
        objective=src.objective,
        context_refs=src.context_refs,
        output_contract=src.output_contract,
    )
    rep_normal = build_replacement_brain_request(src, "brain-b", "req-task-022-r2")
    with pytest.raises(ContinuityStateValidationError, match="must not contain leading or trailing whitespace"):
        validate_brain_failover_eligibility(
            src_padded, rep_normal, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap
        )

    # 3. Padded capability brain_id fails closed
    cap_padded = BrainCapability(
        brain_id="brain-b ",
        supported_operations=(BrainOperation.TASK, BrainOperation.TASK_AND_PLAN, BrainOperation.PLAN),
    )
    with pytest.raises(ContinuityStateValidationError, match="must not contain leading or trailing whitespace"):
        validate_brain_failover_eligibility(
            src, rep_normal, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap_padded
        )


def test_context_refs_content_anchoring_to_state_snapshot():
    """R6-1: Context references must be content-addressed and match canonical state artifact blobs."""
    state = _make_valid_state("TASK-022")
    src = _make_valid_source_request("TASK-022")
    rep = build_replacement_brain_request(src, "brain-b", "req-task-022-r2")
    cap = _make_valid_replacement_capability("brain-b")

    # 1. Valid case with exact task blob and non-state explicit blob passes
    proof = validate_brain_failover_eligibility(
        src, rep, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap
    )
    assert proof.task_id == "TASK-022"

    # 2. Canonical task ContextRef with blob_sha=None fails closed
    src_none_task_blob = BrainRequest(
        schema_version=src.schema_version,
        task_id=src.task_id,
        request_id=src.request_id,
        brain_id=src.brain_id,
        operation=src.operation,
        objective=src.objective,
        context_refs=(
            ContextRef(
                path=".ai/decisions/ADR-010-OPEN-MULTI-AGENT-CONTINUITY-OS-ARCHITECTURE-LOCK.md",
                blob_sha="a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
            ),
            ContextRef(
                path=f".ai/tasks/{src.task_id}.md",
                blob_sha=None,
            ),
        ),
        output_contract=src.output_contract,
    )
    rep_none_task_blob = build_replacement_brain_request(src_none_task_blob, "brain-b", "req-r2")
    with pytest.raises(ContinuityStateValidationError, match="must have a non-null, content-addressed blob_sha"):
        validate_brain_failover_eligibility(
            src_none_task_blob, rep_none_task_blob, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap
        )

    # 3. Canonical task ContextRef with wrong 40-char blob fails closed
    src_wrong_task_blob = BrainRequest(
        schema_version=src.schema_version,
        task_id=src.task_id,
        request_id=src.request_id,
        brain_id=src.brain_id,
        operation=src.operation,
        objective=src.objective,
        context_refs=(
            ContextRef(
                path=f".ai/tasks/{src.task_id}.md",
                blob_sha="0" * 40,
            ),
        ),
        output_contract=src.output_contract,
    )
    rep_wrong_task_blob = build_replacement_brain_request(src_wrong_task_blob, "brain-b", "req-r2")
    with pytest.raises(ContinuityStateValidationError, match="mismatches canonical state artifact blob_sha"):
        validate_brain_failover_eligibility(
            src_wrong_task_blob, rep_wrong_task_blob, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap
        )

    # 4. Non-state ContextRef with blob_sha=None fails closed
    src_none_nonstate_blob = BrainRequest(
        schema_version=src.schema_version,
        task_id=src.task_id,
        request_id=src.request_id,
        brain_id=src.brain_id,
        operation=src.operation,
        objective=src.objective,
        context_refs=(
            ContextRef(
                path=".ai/decisions/ADR-010-OPEN-MULTI-AGENT-CONTINUITY-OS-ARCHITECTURE-LOCK.md",
                blob_sha=None,
            ),
        ),
        output_contract=src.output_contract,
    )
    rep_none_nonstate_blob = build_replacement_brain_request(src_none_nonstate_blob, "brain-b", "req-r2")
    with pytest.raises(ContinuityStateValidationError, match="must have a non-null, content-addressed blob_sha"):
        validate_brain_failover_eligibility(
            src_none_nonstate_blob, rep_none_nonstate_blob, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap
        )

    # 5. Non-state ContextRef with padded path fails closed
    src_padded_path = BrainRequest(
        schema_version=src.schema_version,
        task_id=src.task_id,
        request_id=src.request_id,
        brain_id=src.brain_id,
        operation=src.operation,
        objective=src.objective,
        context_refs=(
            ContextRef(
                path=" .ai/decisions/ADR-010.md ",
                blob_sha="a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
            ),
        ),
        output_contract=src.output_contract,
    )
    rep_padded_path = build_replacement_brain_request(src_padded_path, "brain-b", "req-r2")
    with pytest.raises(ContinuityStateValidationError, match="ContextRef.path must not contain leading or trailing whitespace"):
        validate_brain_failover_eligibility(
            src_padded_path, rep_padded_path, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap
        )


def test_semantic_drift_rejection_in_failover_validation():
    """Any semantic drift between source and replacement requests is rejected."""
    state = _make_valid_state("TASK-022")
    src = _make_valid_source_request("TASK-022")
    rep = build_replacement_brain_request(src, "brain-b", "req-task-022-r2")
    cap = _make_valid_replacement_capability("brain-b")

    # Valid case produces valid proof
    proof = validate_brain_failover_eligibility(
        src, rep, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap
    )
    assert proof.task_id == "TASK-022"
    assert proof.source_brain_id == "brain-a"
    assert proof.replacement_brain_id == "brain-b"
    assert proof.state_fingerprint == state.fingerprint()

    # 1. Changed task_id
    rep_bad_task = BrainRequest(
        task_id="TASK-099",
        request_id=rep.request_id,
        brain_id=rep.brain_id,
        operation=rep.operation,
        objective=rep.objective,
        output_contract=OutputContract(
            expected_output_type=BrainOutputType.TASK_ARTIFACT,
            target_artifact_path=".ai/tasks/TASK-099.md",
        ),
        context_refs=rep.context_refs,
    )
    with pytest.raises(ContinuityStateValidationError, match="State task_id mismatch|Task ID drift"):
        validate_brain_failover_eligibility(
            src, rep_bad_task, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap
        )

    # 2. Changed operation
    rep_bad_op = BrainRequest(
        task_id=src.task_id,
        request_id=rep.request_id,
        brain_id=rep.brain_id,
        operation=BrainOperation.PLAN,
        objective=rep.objective,
        output_contract=OutputContract(
            expected_output_type=BrainOutputType.PLAN_ARTIFACT,
            target_artifact_path=".ai/plans/TASK-022.md",
        ),
        context_refs=rep.context_refs,
    )
    with pytest.raises(ContinuityStateValidationError, match="Operation drift in failover"):
        validate_brain_failover_eligibility(
            src, rep_bad_op, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap
        )

    # 3. Changed objective
    rep_bad_obj = BrainRequest(
        task_id=src.task_id,
        request_id=rep.request_id,
        brain_id=rep.brain_id,
        operation=src.operation,
        objective="Different drifted objective",
        output_contract=src.output_contract,
        context_refs=src.context_refs,
    )
    with pytest.raises(ContinuityStateValidationError, match="Objective drift in failover"):
        validate_brain_failover_eligibility(
            src, rep_bad_obj, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap
        )

    # 4. Changed or reordered context refs
    rep_bad_refs = BrainRequest(
        task_id=src.task_id,
        request_id=rep.request_id,
        brain_id=rep.brain_id,
        operation=src.operation,
        objective=src.objective,
        output_contract=src.output_contract,
        context_refs=tuple(reversed(src.context_refs)),
    )
    with pytest.raises(ContinuityStateValidationError, match="ContextRefs drift in failover"):
        validate_brain_failover_eligibility(
            src, rep_bad_refs, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap
        )

    # 5. Changed output contract
    rep_bad_out = BrainRequest(
        task_id=src.task_id,
        request_id=rep.request_id,
        brain_id=rep.brain_id,
        operation=src.operation,
        objective=src.objective,
        output_contract=OutputContract(
            expected_output_type=BrainOutputType.TASK_ARTIFACT,
            target_artifact_path=src.output_contract.target_artifact_path,
            max_output_bytes=8192,
        ),
        context_refs=src.context_refs,
    )
    with pytest.raises(ContinuityStateValidationError, match="OutputContract drift in failover"):
        validate_brain_failover_eligibility(
            src, rep_bad_out, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap
        )


def test_replacement_capability_gate_is_mandatory():
    """Missing or invalid replacement capability fails closed."""
    state = _make_valid_state("TASK-022")
    src = _make_valid_source_request("TASK-022")
    rep = build_replacement_brain_request(src, "brain-b", "req-task-022-r2")

    # None or missing replacement_capability fails closed
    with pytest.raises(ContinuityStateValidationError, match="replacement_capability must be a BrainCapability"):
        validate_brain_failover_eligibility(
            src, rep, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=None  # type: ignore
        )

    # Capability brain_id mismatch
    cap_wrong_id = BrainCapability(
        brain_id="brain-c",
        supported_operations=(BrainOperation.TASK, BrainOperation.TASK_AND_PLAN),
    )
    with pytest.raises(ContinuityStateValidationError, match="Replacement capability brain_id mismatch"):
        validate_brain_failover_eligibility(
            src, rep, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap_wrong_id
        )

    # Capability missing requested operation
    cap_missing_op = BrainCapability(
        brain_id="brain-b",
        supported_operations=(BrainOperation.REVIEW,),
    )
    with pytest.raises(ContinuityStateValidationError, match="does not support operation"):
        validate_brain_failover_eligibility(
            src, rep, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap_missing_op
        )


def test_source_result_and_duplicate_output_blocking():
    """SUCCESS source result blocks failover; REJECTED/FAILED/INCOMPLETE or None allows failover."""
    state = _make_valid_state("TASK-022")
    src = _make_valid_source_request("TASK-022")
    rep = build_replacement_brain_request(src, "brain-b", "req-task-022-r2")
    cap = _make_valid_replacement_capability("brain-b")

    # None source result allows failover
    proof_none = validate_brain_failover_eligibility(
        src, rep, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap, source_result=None
    )
    assert proof_none.source_result_status is None

    # REJECTED source result allows failover
    res_rejected = BrainResult(
        task_id=src.task_id,
        request_id=src.request_id,
        brain_id=src.brain_id,
        operation=src.operation,
        status=BrainResultStatus.REJECTED,
        output_type=BrainOutputType.TASK_ARTIFACT,
        error_code="CAPACITY_EXCEEDED",
    )
    proof_rej = validate_brain_failover_eligibility(
        src, rep, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap, source_result=res_rejected
    )
    assert proof_rej.source_result_status == BrainResultStatus.REJECTED

    # FAILED and INCOMPLETE allow failover
    for st in (BrainResultStatus.FAILED, BrainResultStatus.INCOMPLETE):
        res = BrainResult(
            task_id=src.task_id,
            request_id=src.request_id,
            brain_id=src.brain_id,
            operation=src.operation,
            status=st,
            output_type=BrainOutputType.TASK_ARTIFACT,
        )
        p = validate_brain_failover_eligibility(
            src, rep, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap, source_result=res
        )
        assert p.source_result_status == st

    # SUCCESS source result MUST FAIL CLOSED to prevent duplicate outputs
    res_success = BrainResult(
        task_id=src.task_id,
        request_id=src.request_id,
        brain_id=src.brain_id,
        operation=src.operation,
        status=BrainResultStatus.SUCCESS,
        output_type=BrainOutputType.TASK_ARTIFACT,
        artifact_ref=ArtifactRef(path=".ai/tasks/TASK-022.md", blob_sha="92494bcd64b594d60a5f74a82e3e64c113d817db", ref="task"),
    )
    with pytest.raises(ContinuityStateValidationError, match="source request already succeeded with status SUCCESS"):
        validate_brain_failover_eligibility(
            src, rep, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap, source_result=res_success
        )


def test_source_result_identity_mismatches_fail_closed():
    """Source result with wrong task_id, request_id, brain_id, or operation is rejected."""
    state = _make_valid_state("TASK-022")
    src = _make_valid_source_request("TASK-022")
    rep = build_replacement_brain_request(src, "brain-b", "req-task-022-r2")
    cap = _make_valid_replacement_capability("brain-b")

    # 1. Mismatched task_id in source result
    res_wrong_task = BrainResult(
        task_id="TASK-099",
        request_id=src.request_id,
        brain_id=src.brain_id,
        operation=src.operation,
        status=BrainResultStatus.FAILED,
        output_type=BrainOutputType.TASK_ARTIFACT,
    )
    with pytest.raises(ContinuityStateValidationError, match="Source result task_id mismatch"):
        validate_brain_failover_eligibility(
            src, rep, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap, source_result=res_wrong_task
        )

    # 2. Mismatched request_id in source result
    res_wrong_req = BrainResult(
        task_id=src.task_id,
        request_id="req-other-id",
        brain_id=src.brain_id,
        operation=src.operation,
        status=BrainResultStatus.FAILED,
        output_type=BrainOutputType.TASK_ARTIFACT,
    )
    with pytest.raises(ContinuityStateValidationError, match="Source result request_id mismatch"):
        validate_brain_failover_eligibility(
            src, rep, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap, source_result=res_wrong_req
        )

    # 3. Mismatched brain_id in source result
    res_wrong_brain = BrainResult(
        task_id=src.task_id,
        request_id=src.request_id,
        brain_id="brain-c",
        operation=src.operation,
        status=BrainResultStatus.FAILED,
        output_type=BrainOutputType.TASK_ARTIFACT,
    )
    with pytest.raises(ContinuityStateValidationError, match="Source result brain_id mismatch"):
        validate_brain_failover_eligibility(
            src, rep, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap, source_result=res_wrong_brain
        )

    # 4. Mismatched operation in source result
    res_wrong_op = BrainResult(
        task_id=src.task_id,
        request_id=src.request_id,
        brain_id=src.brain_id,
        operation=BrainOperation.REVIEW,
        status=BrainResultStatus.FAILED,
        output_type=BrainOutputType.REVIEW_ARTIFACT,
    )
    with pytest.raises(ContinuityStateValidationError, match="Source result operation mismatch"):
        validate_brain_failover_eligibility(
            src, rep, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap, source_result=res_wrong_op
        )


def test_state_anchor_and_fingerprint_mandatory_validation():
    """State task_id mismatch, missing fingerprint, or wrong fingerprint fails closed."""
    state = _make_valid_state("TASK-022")
    src = _make_valid_source_request("TASK-022")
    rep = build_replacement_brain_request(src, "brain-b", "req-task-022-r2")
    cap = _make_valid_replacement_capability("brain-b")

    # Valid expected fingerprint passes
    proof = validate_brain_failover_eligibility(
        src, rep, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap
    )
    assert proof.state_fingerprint == state.fingerprint()

    # Mismatched expected fingerprint fails closed
    wrong_fp = "0" * 64
    with pytest.raises(ContinuityStateValidationError, match="State fingerprint mismatch"):
        validate_brain_failover_eligibility(
            src, rep, state, expected_state_fingerprint=wrong_fp, replacement_capability=cap
        )

    # Malformed expected fingerprint fails closed
    with pytest.raises(ContinuityStateValidationError, match="must be an exact 64-character lowercase hex"):
        validate_brain_failover_eligibility(
            src, rep, state, expected_state_fingerprint="not-a-sha256", replacement_capability=cap
        )

    # Whitespace-padded expected fingerprint fails closed (R4-2)
    with pytest.raises(ContinuityStateValidationError, match="must not contain leading or trailing whitespace"):
        validate_brain_failover_eligibility(
            src, rep, state, expected_state_fingerprint=f" {state.fingerprint()} ", replacement_capability=cap
        )

    # Missing / omitted expected_state_fingerprint fails closed (TypeError)
    with pytest.raises(TypeError):
        validate_brain_failover_eligibility(  # type: ignore[call-arg]
            src, rep, state, replacement_capability=cap
        )

    # Explicit None expected_state_fingerprint fails closed
    with pytest.raises(ContinuityStateValidationError, match="expected_state_fingerprint must be a non-empty string"):
        validate_brain_failover_eligibility(
            src, rep, state, expected_state_fingerprint=None, replacement_capability=cap  # type: ignore[arg-type]
        )

    # State for a different task fails closed
    state_other_task = _make_valid_state("TASK-099")
    src_other_task = _make_valid_source_request("TASK-099")
    rep_other_task = build_replacement_brain_request(src_other_task, "brain-b", "req-r2")
    with pytest.raises(ContinuityStateValidationError, match="State task_id mismatch"):
        validate_brain_failover_eligibility(
            src, rep, state_other_task, expected_state_fingerprint=state_other_task.fingerprint(), replacement_capability=cap
        )


def test_exact_fingerprints_and_canonical_request_id_in_proof():
    """R4-2 & R4-3: Proof rejects whitespace-padded fingerprints and request IDs in direct, from_dict, and from_json."""
    state = _make_valid_state("TASK-022")
    src = _make_valid_source_request("TASK-022")
    rep = build_replacement_brain_request(src, "brain-b", "req-task-022-r2")
    cap = _make_valid_replacement_capability("brain-b")

    valid_proof = validate_brain_failover_eligibility(
        src, rep, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap
    )
    d = valid_proof.to_dict()

    # 1. Whitespace-padded state_fingerprint rejected
    d_bad_fp = dict(d)
    d_bad_fp["state_fingerprint"] = f" {d['state_fingerprint']} "
    with pytest.raises(ContinuityStateValidationError, match="must not contain leading or trailing whitespace"):
        BrainFailoverProof.from_dict(d_bad_fp)

    # 2. Whitespace-padded source_request_fingerprint rejected
    d_bad_src_fp = dict(d)
    d_bad_src_fp["source_request_fingerprint"] = f" {d['source_request_fingerprint']}"
    with pytest.raises(ContinuityStateValidationError, match="must not contain leading or trailing whitespace"):
        BrainFailoverProof.from_dict(d_bad_src_fp)

    # 3. Whitespace-padded replacement_request_fingerprint rejected
    d_bad_rep_fp = dict(d)
    d_bad_rep_fp["replacement_request_fingerprint"] = f"{d['replacement_request_fingerprint']} "
    with pytest.raises(ContinuityStateValidationError, match="must not contain leading or trailing whitespace"):
        BrainFailoverProof.from_dict(d_bad_rep_fp)

    # 4. Whitespace-padded request_id rejected (R4-3)
    d_bad_req_id = dict(d)
    d_bad_req_id["source_request_id"] = f" {d['source_request_id']} "
    with pytest.raises(ContinuityStateValidationError, match="must not contain leading or trailing whitespace"):
        BrainFailoverProof.from_dict(d_bad_req_id)

    d_bad_rep_req_id = dict(d)
    d_bad_rep_req_id["replacement_request_id"] = f"{d['replacement_request_id']} "
    with pytest.raises(ContinuityStateValidationError, match="must not contain leading or trailing whitespace"):
        BrainFailoverProof.from_dict(d_bad_rep_req_id)

    # 5. Whitespace-padded brain_id in proof rejected (R4-1)
    d_bad_brain = dict(d)
    d_bad_brain["replacement_brain_id"] = "brain-b "
    with pytest.raises(ContinuityStateValidationError, match="must not contain leading or trailing whitespace"):
        BrainFailoverProof.from_dict(d_bad_brain)


def test_deterministic_canonical_json_fingerprint_and_unknown_fields():
    """Failover proof canonical JSON serialization is deterministic and unknown fields fail closed."""
    state = _make_valid_state("TASK-022")
    src = _make_valid_source_request("TASK-022")
    rep = build_replacement_brain_request(src, "brain-b", "req-task-022-r2")
    cap = _make_valid_replacement_capability("brain-b")

    proof1 = validate_brain_failover_eligibility(
        src, rep, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap
    )
    json1 = proof1.to_canonical_json()
    fp1 = proof1.fingerprint()

    proof2 = BrainFailoverProof.from_json(json1)
    json2 = proof2.to_canonical_json()
    fp2 = proof2.fingerprint()

    assert json1 == json2
    assert fp1 == fp2
    assert len(fp1) == 64

    # Unknown fields rejected
    d = proof1.to_dict()
    d["unauthorized_field"] = "extra"
    with pytest.raises(ContinuityStateValidationError, match="Unknown root fields"):
        BrainFailoverProof.from_dict(d)

    # Rejection of forbidden fields (transcripts, raw content, reasoning)
    for forbidden in ["transcript", "raw_output", "reasoning", "secret_key"]:
        d_forbidden = proof1.to_dict()
        d_forbidden[forbidden] = "value"
        with pytest.raises(ContinuityStateValidationError, match="Unknown root fields"):
            BrainFailoverProof.from_dict(d_forbidden)


def test_16kib_fail_closed_limit():
    """16 KiB limit is strictly enforced on BrainFailoverProof."""
    state = _make_valid_state("TASK-022")
    src = _make_valid_source_request("TASK-022")
    rep = build_replacement_brain_request(src, "brain-b", "req-task-022-r2")
    cap = _make_valid_replacement_capability("brain-b")
    proof = validate_brain_failover_eligibility(
        src, rep, state, expected_state_fingerprint=state.fingerprint(), replacement_capability=cap
    )

    # Oversized JSON input
    huge_bytes = b" " * 16385
    with pytest.raises(ContinuityStateValidationError, match="exceeds maximum allowable size"):
        BrainFailoverProof.from_json(huge_bytes)
