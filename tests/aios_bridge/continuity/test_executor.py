"""
Unit tests for Open Multi-Agent Continuity OS M4 Executor-Neutral Contract (ADR-018 / TASK-028 / REVIEW-028 FIX Round 1).
Validates vendor-neutral execution request, result, capability, preparation, state binding, and adapter protocol.
"""
from __future__ import annotations

import json
import pytest

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.executor import (
    MAX_CONTEXT_REFS,
    MAX_EVIDENCE_REFS,
    ExecutionCapability,
    ExecutionOperation,
    ExecutionRequest,
    ExecutionResult,
    ExecutionResultStatus,
    ExecutorAdapter,
    ExecutorCapabilities,
    PreparedExecution,
    validate_execution_request_against_state,
    validate_execution_result_against_request,
    validate_executor_eligibility,
    validate_prepared_execution_against_request,
)
from src.aios_bridge.continuity.state import (
    MAX_SERIALIZED_BYTES,
    ArtifactRef,
    BrainOperation,
    BrainState,
    BranchState,
    ContinuityArtifacts,
    ContinuityPhase,
    ContinuityState,
    ExecutorState,
    NextOperation,
)
from src.aios_bridge.continuity.usage import ExecutorAction


def _sample_state(
    task_id: str = "TASK-028",
    phase: ContinuityPhase = ContinuityPhase.READY_FOR_RUN,
    branch_sha: str | None = None,
    with_review: bool = False,
) -> ContinuityState:
    task_ref = ArtifactRef(
        path=f".ai/tasks/{task_id}.md",
        ref="ai-control",
        blob_sha="1111111111111111111111111111111111111111",
    )
    review_ref = None
    if with_review:
        task_num = task_id.split("-")[1]
        review_ref = ArtifactRef(
            path=f".ai/reviews/REVIEW-{task_num}.md",
            ref="ai/task-028",
            blob_sha="2222222222222222222222222222222222222222",
        )

    contract_ref = ArtifactRef(
        path=".ai/decisions/ADR-018-AIOS-CONTINUITY-M4-EXECUTOR-NEUTRAL-CONTRACT-LOCK.md",
        ref="ai-control",
        blob_sha="3333333333333333333333333333333333333333",
    )

    return ContinuityState(
        schema_version="1",
        task_id=task_id,
        phase=phase,
        next_operation=NextOperation.RUN_APPROVAL,
        main=BranchState(branch="main", sha="44436c59eb42dbdbffaee28a738d11694958a4ea"),
        task_branch=BranchState(branch=f"ai/{task_id.lower()}", sha=branch_sha),
        artifacts=ContinuityArtifacts(
            task=task_ref,
            contracts=(contract_ref,),
            plan=None,
            result=None,
            review=review_ref,
        ),
        brain=BrainState(last_id="chatgpt-chat", last_operation=BrainOperation.PLAN),
        executor=ExecutorState(last_id="antigravity"),
    )


def _sample_execution_request(
    state: ContinuityState,
    operation: ExecutionOperation = ExecutionOperation.RUN,
    executor_id: str = "antigravity",
    request_id: str = "req-task-028-01",
) -> ExecutionRequest:
    task_num = state.task_id.split("-")[1]
    if operation == ExecutionOperation.RUN or operation == "RUN":
        work_ref = state.artifacts.task
    elif operation == ExecutionOperation.FIX or operation == "FIX":
        work_ref = state.artifacts.review or ArtifactRef(
            path=f".ai/reviews/REVIEW-{task_num}.md",
            ref="ai/task-028",
            blob_sha="2222222222222222222222222222222222222222",
        )
    else:
        work_ref = state.artifacts.task

    return ExecutionRequest(
        schema_version="1",
        task_id=state.task_id,
        request_id=request_id,
        executor_id=executor_id,
        operation=operation,
        state_fingerprint=state.fingerprint(),
        target_branch=state.task_branch.branch,
        expected_task_head_sha=state.task_branch.sha,
        work_ref=work_ref,
        context_refs=tuple(state.artifacts.contracts),
        required_capabilities=(
            ExecutionCapability.REPOSITORY_READ,
            ExecutionCapability.FILESYSTEM_WRITE,
            ExecutionCapability.TEST_EXECUTION,
        ),
        expected_result_path=f".ai/results/RESULT-{task_num}.md",
    )


def _sample_capabilities(
    executor_id: str = "antigravity",
    operations: Sequence[ExecutionOperation] = (ExecutionOperation.RUN, ExecutionOperation.FIX),
    capabilities: Sequence[ExecutionCapability] = (
        ExecutionCapability.REPOSITORY_READ,
        ExecutionCapability.FILESYSTEM_WRITE,
        ExecutionCapability.SHELL,
        ExecutionCapability.TEST_EXECUTION,
        ExecutionCapability.LOCAL_GIT,
    ),
) -> ExecutorCapabilities:
    return ExecutorCapabilities(
        executor_id=executor_id,
        supported_operations=tuple(operations),
        supported_capabilities=tuple(capabilities),
        declarative_only=True,
    )


# -----------------------------------------------------------------------------
# 1. Operation Domain and Telemetry Alignment Tests
# -----------------------------------------------------------------------------

def test_execution_operation_domain_and_alignment():
    """ExecutionOperation is RUN and FIX only, independent of telemetry but aligned."""
    assert ExecutionOperation.RUN.value == "RUN"
    assert ExecutionOperation.FIX.value == "FIX"
    assert len(ExecutionOperation) == 2

    # Semantic alignment test with telemetry's ExecutorAction
    assert ExecutionOperation.RUN.value == ExecutorAction.RUN.value
    assert ExecutionOperation.FIX.value == ExecutorAction.FIX.value

    # MERGE is forbidden
    with pytest.raises(ValueError):
        ExecutionOperation("MERGE")


def test_execution_operation_parsing_error_wrapped():
    """Invalid operation parsing in ExecutionRequest/ExecutorCapabilities wraps as ContinuityStateValidationError."""
    state = _sample_state()
    with pytest.raises(ContinuityStateValidationError, match="Invalid ExecutionOperation"):
        _sample_execution_request(state, operation="INVALID_OP")  # type: ignore

    with pytest.raises(ContinuityStateValidationError, match="Invalid ExecutionOperation"):
        ExecutorCapabilities(
            executor_id="antigravity",
            supported_operations=("RUN", "INVALID_OP"),  # type: ignore
            supported_capabilities=(ExecutionCapability.REPOSITORY_READ,),
        )


# -----------------------------------------------------------------------------
# 2. ExecutionRequest Invariants and Edge Cases
# -----------------------------------------------------------------------------

def test_execution_request_valid_construction_and_fingerprint():
    """ExecutionRequest constructs cleanly, serializes deterministically, and fingerprints."""
    state = _sample_state()
    req = _sample_execution_request(state)

    assert req.task_id == "TASK-028"
    assert req.operation == ExecutionOperation.RUN
    assert req.expected_result_path == ".ai/results/RESULT-028.md"
    assert len(req.fingerprint()) == 64

    # Canonical JSON round-trip
    canonical_json = req.to_canonical_json()
    req_restored = ExecutionRequest.from_json(canonical_json)
    assert req == req_restored
    assert req.fingerprint() == req_restored.fingerprint()


def test_execution_request_whitespace_and_casing_rejection():
    """ExecutionRequest rejects padded, unnormalized, or non-canonical identifiers."""
    state = _sample_state()
    req_dict = _sample_execution_request(state).to_dict()

    # Padded task_id
    with pytest.raises(ContinuityStateValidationError, match="task_id"):
        ExecutionRequest.from_dict({**req_dict, "task_id": " TASK-028"})
    with pytest.raises(ContinuityStateValidationError, match="task_id"):
        ExecutionRequest.from_dict({**req_dict, "task_id": "task-028"})

    # Padded request_id
    with pytest.raises(ContinuityStateValidationError, match="request_id"):
        ExecutionRequest.from_dict({**req_dict, "request_id": "req-task-028-01 "})

    # Padded executor_id
    with pytest.raises(ContinuityStateValidationError, match="executor_id"):
        ExecutionRequest.from_dict({**req_dict, "executor_id": " antigravity"})

    # Padded state_fingerprint
    with pytest.raises(ContinuityStateValidationError, match="state_fingerprint"):
        ExecutionRequest.from_dict({**req_dict, "state_fingerprint": " " + req_dict["state_fingerprint"]})

    # Uppercase 64-hex state_fingerprint
    with pytest.raises(ContinuityStateValidationError, match="state_fingerprint"):
        ExecutionRequest.from_dict({**req_dict, "state_fingerprint": req_dict["state_fingerprint"].upper()})

    # Padded target_branch
    with pytest.raises(ContinuityStateValidationError, match="target_branch"):
        ExecutionRequest.from_dict({**req_dict, "target_branch": " ai/task-028"})


def test_execution_request_forbidden_authority_keys_fail_closed():
    """ExecutionRequest rejects any self-authorizing or secret fields."""
    state = _sample_state()
    req_dict = _sample_execution_request(state).to_dict()

    for forbidden in [
        "approved",
        "human_approved",
        "authorization_token",
        "api_key",
        "cookie",
        "auth_header",
        "session_secret",
        "merge_allowed",
        "token",
        "auth",
    ]:
        bad_dict = {**req_dict, forbidden: True if "approved" in forbidden else "secret"}
        with pytest.raises(ContinuityStateValidationError, match="Forbidden authority/secret fields"):
            ExecutionRequest.from_dict(bad_dict)


def test_execution_request_work_ref_role_binding():
    """RUN requires .ai/tasks/TASK-NNN.md; FIX requires .ai/reviews/REVIEW-NNN.md."""
    state = _sample_state(with_review=True)

    # 1. RUN pointing to REVIEW fails
    with pytest.raises(ContinuityStateValidationError, match="RUN work_ref path"):
        ExecutionRequest(
            schema_version="1",
            task_id="TASK-028",
            request_id="req-01",
            executor_id="antigravity",
            operation=ExecutionOperation.RUN,
            state_fingerprint=state.fingerprint(),
            target_branch="ai/task-028",
            expected_task_head_sha=None,
            work_ref=state.artifacts.review,  # type: ignore
            context_refs=(),
            required_capabilities=(),
            expected_result_path=".ai/results/RESULT-028.md",
        )

    # 2. FIX pointing to TASK fails
    with pytest.raises(ContinuityStateValidationError, match="FIX work_ref path"):
        ExecutionRequest(
            schema_version="1",
            task_id="TASK-028",
            request_id="req-01",
            executor_id="antigravity",
            operation=ExecutionOperation.FIX,
            state_fingerprint=state.fingerprint(),
            target_branch="ai/task-028",
            expected_task_head_sha=None,
            work_ref=state.artifacts.task,
            context_refs=(),
            required_capabilities=(),
            expected_result_path=".ai/results/RESULT-028.md",
        )

    # 3. Substring alias TASK-0280 fails for TASK-028
    with pytest.raises(ContinuityStateValidationError, match="RUN work_ref path"):
        ExecutionRequest(
            schema_version="1",
            task_id="TASK-028",
            request_id="req-01",
            executor_id="antigravity",
            operation=ExecutionOperation.RUN,
            state_fingerprint=state.fingerprint(),
            target_branch="ai/task-028",
            expected_task_head_sha=None,
            work_ref=ArtifactRef(path=".ai/tasks/TASK-0280.md", ref="ai-control", blob_sha="1" * 40),
            context_refs=(),
            required_capabilities=(),
            expected_result_path=".ai/results/RESULT-028.md",
        )


def test_execution_request_context_refs_sequence_and_collision_rules():
    """context_refs enforces list/tuple only, duplicate rejection, and collision with work_ref."""
    state = _sample_state()
    req = _sample_execution_request(state)

    # 1. Set input is rejected in constructor
    with pytest.raises(ContinuityStateValidationError, match="context_refs must be a list or tuple"):
        ExecutionRequest(
            schema_version="1",
            task_id="TASK-028",
            request_id="req-01",
            executor_id="antigravity",
            operation=ExecutionOperation.RUN,
            state_fingerprint=state.fingerprint(),
            target_branch="ai/task-028",
            expected_task_head_sha=None,
            work_ref=req.work_ref,
            context_refs={req.work_ref},  # type: ignore
            required_capabilities=(),
            expected_result_path=".ai/results/RESULT-028.md",
        )

    # 2. Generator input is rejected in constructor
    with pytest.raises(ContinuityStateValidationError, match="context_refs must be a list or tuple"):
        ExecutionRequest(
            schema_version="1",
            task_id="TASK-028",
            request_id="req-01",
            executor_id="antigravity",
            operation=ExecutionOperation.RUN,
            state_fingerprint=state.fingerprint(),
            target_branch="ai/task-028",
            expected_task_head_sha=None,
            work_ref=req.work_ref,
            context_refs=(r for r in [req.context_refs[0]]),  # type: ignore
            required_capabilities=(),
            expected_result_path=".ai/results/RESULT-028.md",
        )

    # 3. Duplicate context ref path is rejected
    dup_ctx = (req.context_refs[0], req.context_refs[0])
    with pytest.raises(ContinuityStateValidationError, match="Duplicate context_ref path"):
        ExecutionRequest(
            schema_version="1",
            task_id="TASK-028",
            request_id="req-01",
            executor_id="antigravity",
            operation=ExecutionOperation.RUN,
            state_fingerprint=state.fingerprint(),
            target_branch="ai/task-028",
            expected_task_head_sha=None,
            work_ref=req.work_ref,
            context_refs=dup_ctx,
            required_capabilities=(),
            expected_result_path=".ai/results/RESULT-028.md",
        )

    # 4. Context ref colliding with work_ref.path is rejected
    with pytest.raises(ContinuityStateValidationError, match="collides with work_ref.path"):
        ExecutionRequest(
            schema_version="1",
            task_id="TASK-028",
            request_id="req-01",
            executor_id="antigravity",
            operation=ExecutionOperation.RUN,
            state_fingerprint=state.fingerprint(),
            target_branch="ai/task-028",
            expected_task_head_sha=None,
            work_ref=req.work_ref,
            context_refs=(req.work_ref,),
            required_capabilities=(),
            expected_result_path=".ai/results/RESULT-028.md",
        )


def test_from_dict_strict_sequence_validation():
    """from_dict rejects sets, generators, and dicts for context_refs and evidence_refs without laundering (R1-2)."""
    state = _sample_state()
    req_dict = _sample_execution_request(state).to_dict()

    # 1. Generator in context_refs for ExecutionRequest.from_dict
    bad_req_gen = {**req_dict, "context_refs": (r for r in req_dict["context_refs"])}
    with pytest.raises(ContinuityStateValidationError, match="context_refs in dict must be a list or tuple"):
        ExecutionRequest.from_dict(bad_req_gen)

    # 2. Set in context_refs for ExecutionRequest.from_dict
    bad_req_set = {**req_dict, "context_refs": {req_dict["context_refs"][0]["path"]}}
    with pytest.raises(ContinuityStateValidationError, match="context_refs in dict must be a list or tuple"):
        ExecutionRequest.from_dict(bad_req_set)

    # 3. Generator in required_capabilities for ExecutionRequest.from_dict
    bad_req_caps_gen = {**req_dict, "required_capabilities": (c for c in req_dict["required_capabilities"])}
    with pytest.raises(ContinuityStateValidationError, match="required_capabilities in dict must be a list or tuple"):
        ExecutionRequest.from_dict(bad_req_caps_gen)

    # 4. Generator in evidence_refs for ExecutionResult.from_dict
    res_dict = ExecutionResult(
        schema_version="1",
        task_id="TASK-028",
        request_id="req-01",
        executor_id="antigravity",
        operation=ExecutionOperation.RUN,
        status=ExecutionResultStatus.FAILED,
        error_code="FAIL",
    ).to_dict()
    bad_res_gen = {**res_dict, "evidence_refs": (r for r in [ArtifactRef(path=".ai/evidence/01.md", ref="main", blob_sha="1" * 40).to_dict()])}
    with pytest.raises(ContinuityStateValidationError, match="evidence_refs in dict must be a list or tuple"):
        ExecutionResult.from_dict(bad_res_gen)

    # 5. Generator in supported_operations for ExecutorCapabilities.from_dict
    caps_dict = _sample_capabilities().to_dict()
    bad_caps_gen = {**caps_dict, "supported_operations": (o for o in caps_dict["supported_operations"])}
    with pytest.raises(ContinuityStateValidationError, match="supported_operations in dict must be a list or tuple"):
        ExecutorCapabilities.from_dict(bad_caps_gen)


# -----------------------------------------------------------------------------
# 3. Canonical State Anchoring Tests
# -----------------------------------------------------------------------------

def test_validate_execution_request_against_state_success():
    """Valid request passes state validation cleanly."""
    state = _sample_state(branch_sha="a" * 40)
    req = _sample_execution_request(state)
    validate_execution_request_against_state(req, state)


def test_validate_execution_request_against_state_mismatches():
    """State validation fails closed on task, fingerprint, branch, SHA, or work_ref mismatch."""
    state = _sample_state(branch_sha="a" * 40)
    req = _sample_execution_request(state)

    # 1. State fingerprint mismatch
    req_bad_fp = ExecutionRequest(
        schema_version=req.schema_version,
        task_id=req.task_id,
        request_id=req.request_id,
        executor_id=req.executor_id,
        operation=req.operation,
        state_fingerprint="0" * 64,
        target_branch=req.target_branch,
        expected_task_head_sha=req.expected_task_head_sha,
        work_ref=req.work_ref,
        context_refs=req.context_refs,
        required_capabilities=req.required_capabilities,
        expected_result_path=req.expected_result_path,
    )
    with pytest.raises(ContinuityStateValidationError, match="state_fingerprint"):
        validate_execution_request_against_state(req_bad_fp, state)

    # 2. Target branch mismatch
    req_bad_branch = ExecutionRequest(
        schema_version=req.schema_version,
        task_id=req.task_id,
        request_id=req.request_id,
        executor_id=req.executor_id,
        operation=req.operation,
        state_fingerprint=req.state_fingerprint,
        target_branch="ai/other-task",
        expected_task_head_sha=req.expected_task_head_sha,
        work_ref=req.work_ref,
        context_refs=req.context_refs,
        required_capabilities=req.required_capabilities,
        expected_result_path=req.expected_result_path,
    )
    with pytest.raises(ContinuityStateValidationError, match="target_branch"):
        validate_execution_request_against_state(req_bad_branch, state)

    # 3. Expected task head SHA mismatch
    req_bad_sha = ExecutionRequest(
        schema_version=req.schema_version,
        task_id=req.task_id,
        request_id=req.request_id,
        executor_id=req.executor_id,
        operation=req.operation,
        state_fingerprint=req.state_fingerprint,
        target_branch=req.target_branch,
        expected_task_head_sha="b" * 40,
        work_ref=req.work_ref,
        context_refs=req.context_refs,
        required_capabilities=req.required_capabilities,
        expected_result_path=req.expected_result_path,
    )
    with pytest.raises(ContinuityStateValidationError, match="expected_task_head_sha"):
        validate_execution_request_against_state(req_bad_sha, state)

    # 4. Context ref blob mismatch against state contract
    contract_path = state.artifacts.contracts[0].path
    drifted_ctx = (ArtifactRef(path=contract_path, ref="ai-control", blob_sha="9" * 40),)
    req_bad_ctx = ExecutionRequest(
        schema_version=req.schema_version,
        task_id=req.task_id,
        request_id=req.request_id,
        executor_id=req.executor_id,
        operation=req.operation,
        state_fingerprint=req.state_fingerprint,
        target_branch=req.target_branch,
        expected_task_head_sha=req.expected_task_head_sha,
        work_ref=req.work_ref,
        context_refs=drifted_ctx,
        required_capabilities=req.required_capabilities,
        expected_result_path=req.expected_result_path,
    )
    with pytest.raises(ContinuityStateValidationError, match="mismatches authoritative state"):
        validate_execution_request_against_state(req_bad_ctx, state)


# -----------------------------------------------------------------------------
# 4. ExecutorCapabilities & Eligibility Gate Tests
# -----------------------------------------------------------------------------

def test_executor_capabilities_determinism_and_declarative_constraint():
    """ExecutorCapabilities sorts enums canonically, enforces declarative_only=True, and has no mutable metadata (R1-1)."""
    caps = ExecutorCapabilities(
        executor_id="antigravity",
        supported_operations=[ExecutionOperation.FIX, ExecutionOperation.RUN],
        supported_capabilities=[ExecutionCapability.TEST_EXECUTION, ExecutionCapability.REPOSITORY_READ],
        declarative_only=True,
    )
    # Operations sorted
    assert caps.supported_operations == (ExecutionOperation.FIX, ExecutionOperation.RUN)
    # Capabilities sorted
    assert caps.supported_capabilities == (ExecutionCapability.REPOSITORY_READ, ExecutionCapability.TEST_EXECUTION)

    # declarative_only must be True
    with pytest.raises(ContinuityStateValidationError, match="declarative_only must be boolean True"):
        ExecutorCapabilities(
            executor_id="antigravity",
            supported_operations=(ExecutionOperation.RUN,),
            supported_capabilities=(ExecutionCapability.REPOSITORY_READ,),
            declarative_only=False,  # type: ignore
        )

    # Duplicate capability rejected
    with pytest.raises(ContinuityStateValidationError, match="Duplicate ExecutionCapability"):
        ExecutorCapabilities(
            executor_id="antigravity",
            supported_operations=(ExecutionOperation.RUN,),
            supported_capabilities=(ExecutionCapability.REPOSITORY_READ, ExecutionCapability.REPOSITORY_READ),
        )

    # Rejection of capacity_metadata (R1-1)
    with pytest.raises(ContinuityStateValidationError, match="Unknown fields in ExecutorCapabilities"):
        ExecutorCapabilities.from_dict({**caps.to_dict(), "capacity_metadata": {"foo": "bar"}})


def test_validate_executor_eligibility():
    """Eligibility gate enforces matching actor ID, supported operation, and required capabilities."""
    state = _sample_state()
    req = _sample_execution_request(state)
    caps = _sample_capabilities()

    # Success
    validate_executor_eligibility(req, caps)

    # 1. Actor mismatch
    caps_mismatch = _sample_capabilities(executor_id="codex")
    with pytest.raises(ContinuityStateValidationError, match="Executor identity mismatch"):
        validate_executor_eligibility(req, caps_mismatch)

    # 2. Unsupported operation
    caps_no_run = _sample_capabilities(operations=(ExecutionOperation.FIX,))
    with pytest.raises(ContinuityStateValidationError, match="does not support operation 'RUN'"):
        validate_executor_eligibility(req, caps_no_run)

    # 3. Missing required capability
    caps_missing_cap = _sample_capabilities(capabilities=(ExecutionCapability.REPOSITORY_READ,))
    with pytest.raises(ContinuityStateValidationError, match="missing required capabilities"):
        validate_executor_eligibility(req, caps_missing_cap)


# -----------------------------------------------------------------------------
# 5. PreparedExecution & Relational Request Binding Tests
# -----------------------------------------------------------------------------

def test_prepared_execution_invariants_and_no_lease_fields():
    """PreparedExecution binds to request fingerprint and rejects lease/secret fields."""
    state = _sample_state()
    req = _sample_execution_request(state)

    prep = PreparedExecution(
        schema_version="1",
        task_id=req.task_id,
        request_id=req.request_id,
        executor_id=req.executor_id,
        execution_id="exec-task-028-01",
        request_fingerprint=req.fingerprint(),
    )

    assert prep.task_id == "TASK-028"
    assert prep.request_fingerprint == req.fingerprint()

    # Reject lease fields in from_dict
    prep_dict = prep.to_dict()
    for lease_key in ["lease", "lease_id", "lease_owner", "lease_expiry", "generation"]:
        with pytest.raises(ContinuityStateValidationError, match="Forbidden lease/secret fields"):
            PreparedExecution.from_dict({**prep_dict, lease_key: "lease-01"})


def test_validate_prepared_execution_against_request():
    """validate_prepared_execution_against_request mechanically binds receipt to request (R1-3)."""
    state = _sample_state()
    req = _sample_execution_request(state)

    prep_valid = PreparedExecution(
        schema_version=req.schema_version,
        task_id=req.task_id,
        request_id=req.request_id,
        executor_id=req.executor_id,
        execution_id="exec-01",
        request_fingerprint=req.fingerprint(),
    )

    # Valid binding passes
    validate_prepared_execution_against_request(prep_valid, req)

    # 1. Syntactically valid but wrong 64-hex request fingerprint fails (R1-3)
    prep_wrong_fp = PreparedExecution(
        schema_version=req.schema_version,
        task_id=req.task_id,
        request_id=req.request_id,
        executor_id=req.executor_id,
        execution_id="exec-01",
        request_fingerprint="0" * 64,
    )
    with pytest.raises(ContinuityStateValidationError, match="request_fingerprint"):
        validate_prepared_execution_against_request(prep_wrong_fp, req)

    # 2. Task ID mismatch fails
    prep_bad_task = PreparedExecution(
        schema_version=req.schema_version,
        task_id="TASK-029",
        request_id=req.request_id,
        executor_id=req.executor_id,
        execution_id="exec-01",
        request_fingerprint=req.fingerprint(),
    )
    with pytest.raises(ContinuityStateValidationError, match="task_id"):
        validate_prepared_execution_against_request(prep_bad_task, req)

    # 3. Request ID mismatch fails
    prep_bad_req = PreparedExecution(
        schema_version=req.schema_version,
        task_id=req.task_id,
        request_id="req-drifted",
        executor_id=req.executor_id,
        execution_id="exec-01",
        request_fingerprint=req.fingerprint(),
    )
    with pytest.raises(ContinuityStateValidationError, match="request_id"):
        validate_prepared_execution_against_request(prep_bad_req, req)

    # 4. Executor ID mismatch fails
    prep_bad_exec = PreparedExecution(
        schema_version=req.schema_version,
        task_id=req.task_id,
        request_id=req.request_id,
        executor_id="codex",
        execution_id="exec-01",
        request_fingerprint=req.fingerprint(),
    )
    with pytest.raises(ContinuityStateValidationError, match="executor_id"):
        validate_prepared_execution_against_request(prep_bad_exec, req)


# -----------------------------------------------------------------------------
# 6. ExecutionResult Payload Matrix & Request/Result Binding Tests
# -----------------------------------------------------------------------------

def test_execution_result_payload_matrix():
    """SUCCESS requires SHA and result_ref; Non-SUCCESS requires error_code and null artifacts."""
    # 1. SUCCESS valid
    succ = ExecutionResult(
        schema_version="1",
        task_id="TASK-028",
        request_id="req-task-028-01",
        executor_id="antigravity",
        operation=ExecutionOperation.RUN,
        status=ExecutionResultStatus.SUCCESS,
        implementation_sha="a" * 40,
        result_ref=ArtifactRef(path=".ai/results/RESULT-028.md", ref="ai/task-028", blob_sha="b" * 40),
    )
    assert succ.status == ExecutionResultStatus.SUCCESS

    # 2. SUCCESS missing implementation_sha fails
    with pytest.raises(ContinuityStateValidationError, match="SUCCESS ExecutionResult requires non-null implementation_sha"):
        ExecutionResult(
            schema_version="1",
            task_id="TASK-028",
            request_id="req-task-028-01",
            executor_id="antigravity",
            operation=ExecutionOperation.RUN,
            status=ExecutionResultStatus.SUCCESS,
            implementation_sha=None,
            result_ref=ArtifactRef(path=".ai/results/RESULT-028.md", ref="ai/task-028", blob_sha="b" * 40),
        )

    # 3. SUCCESS missing result_ref fails
    with pytest.raises(ContinuityStateValidationError, match="SUCCESS ExecutionResult requires non-null result_ref"):
        ExecutionResult(
            schema_version="1",
            task_id="TASK-028",
            request_id="req-task-028-01",
            executor_id="antigravity",
            operation=ExecutionOperation.RUN,
            status=ExecutionResultStatus.SUCCESS,
            implementation_sha="a" * 40,
            result_ref=None,
        )

    # 4. SUCCESS with error_code fails
    with pytest.raises(ContinuityStateValidationError, match="SUCCESS ExecutionResult cannot have non-null error_code"):
        ExecutionResult(
            schema_version="1",
            task_id="TASK-028",
            request_id="req-task-028-01",
            executor_id="antigravity",
            operation=ExecutionOperation.RUN,
            status=ExecutionResultStatus.SUCCESS,
            implementation_sha="a" * 40,
            result_ref=ArtifactRef(path=".ai/results/RESULT-028.md", ref="ai/task-028", blob_sha="b" * 40),
            error_code="UNEXPECTED_ERROR",
        )

    # 5. FAILED valid
    failed = ExecutionResult(
        schema_version="1",
        task_id="TASK-028",
        request_id="req-task-028-01",
        executor_id="antigravity",
        operation=ExecutionOperation.RUN,
        status=ExecutionResultStatus.FAILED,
        error_code="BUILD_FAILURE",
    )
    assert failed.status == ExecutionResultStatus.FAILED

    # 6. FAILED with implementation_sha fails
    with pytest.raises(ContinuityStateValidationError, match="FAILED ExecutionResult cannot contain implementation_sha"):
        ExecutionResult(
            schema_version="1",
            task_id="TASK-028",
            request_id="req-task-028-01",
            executor_id="antigravity",
            operation=ExecutionOperation.RUN,
            status=ExecutionResultStatus.FAILED,
            implementation_sha="a" * 40,
            error_code="BUILD_FAILURE",
        )

    # 7. FAILED without error_code fails
    with pytest.raises(ContinuityStateValidationError, match="FAILED ExecutionResult requires bounded error_code"):
        ExecutionResult(
            schema_version="1",
            task_id="TASK-028",
            request_id="req-task-028-01",
            executor_id="antigravity",
            operation=ExecutionOperation.RUN,
            status=ExecutionResultStatus.FAILED,
            error_code=None,
        )


def test_validate_execution_result_against_request():
    """Validates relational consistency between ExecutionResult and ExecutionRequest."""
    state = _sample_state()
    req = _sample_execution_request(state)

    res_succ = ExecutionResult(
        schema_version="1",
        task_id=req.task_id,
        request_id=req.request_id,
        executor_id=req.executor_id,
        operation=req.operation,
        status=ExecutionResultStatus.SUCCESS,
        implementation_sha="a" * 40,
        result_ref=ArtifactRef(path=req.expected_result_path, ref=req.target_branch, blob_sha="b" * 40),
    )

    validate_execution_result_against_request(res_succ, req)

    # 1. Result task_id mismatch
    res_bad_task = ExecutionResult(
        schema_version="1",
        task_id="TASK-029",
        request_id=req.request_id,
        executor_id=req.executor_id,
        operation=req.operation,
        status=ExecutionResultStatus.SUCCESS,
        implementation_sha="a" * 40,
        result_ref=ArtifactRef(path=".ai/results/RESULT-029.md", ref=req.target_branch, blob_sha="b" * 40),
    )
    with pytest.raises(ContinuityStateValidationError, match="task_id"):
        validate_execution_result_against_request(res_bad_task, req)

    # 2. Result branch ref mismatch
    res_bad_branch = ExecutionResult(
        schema_version="1",
        task_id=req.task_id,
        request_id=req.request_id,
        executor_id=req.executor_id,
        operation=req.operation,
        status=ExecutionResultStatus.SUCCESS,
        implementation_sha="a" * 40,
        result_ref=ArtifactRef(path=req.expected_result_path, ref="ai/other-branch", blob_sha="b" * 40),
    )
    with pytest.raises(ContinuityStateValidationError, match="result_ref.ref"):
        validate_execution_result_against_request(res_bad_branch, req)

    # 3. Request ID drift
    res_bad_req_id = ExecutionResult(
        schema_version="1",
        task_id=req.task_id,
        request_id="req-task-028-drifted",
        executor_id=req.executor_id,
        operation=req.operation,
        status=ExecutionResultStatus.SUCCESS,
        implementation_sha="a" * 40,
        result_ref=ArtifactRef(path=req.expected_result_path, ref=req.target_branch, blob_sha="b" * 40),
    )
    with pytest.raises(ContinuityStateValidationError, match="request_id"):
        validate_execution_result_against_request(res_bad_req_id, req)


# -----------------------------------------------------------------------------
# 7. Adapter Protocol Neutrality Tests (Three Distinct Neutral Stubs)
# -----------------------------------------------------------------------------

class NeutralExecutorA:
    """Stub for executor-a."""
    @property
    def executor_id(self) -> str:
        return "executor-a"

    def capabilities(self) -> ExecutorCapabilities:
        return ExecutorCapabilities(
            executor_id=self.executor_id,
            supported_operations=(ExecutionOperation.RUN, ExecutionOperation.FIX),
            supported_capabilities=(ExecutionCapability.REPOSITORY_READ, ExecutionCapability.FILESYSTEM_WRITE),
        )

    def prepare(self, request: ExecutionRequest) -> PreparedExecution:
        return PreparedExecution(
            schema_version="1",
            task_id=request.task_id,
            request_id=request.request_id,
            executor_id=self.executor_id,
            execution_id="exec-a-01",
            request_fingerprint=request.fingerprint(),
        )

    def collect_result(self, execution_id: str) -> ExecutionResult:
        return ExecutionResult(
            schema_version="1",
            task_id="TASK-028",
            request_id="req-01",
            executor_id=self.executor_id,
            operation=ExecutionOperation.RUN,
            status=ExecutionResultStatus.FAILED,
            error_code="A_ERROR",
        )


class NeutralExecutorB:
    """Stub for executor-b."""
    @property
    def executor_id(self) -> str:
        return "executor-b"

    def capabilities(self) -> ExecutorCapabilities:
        return ExecutorCapabilities(
            executor_id=self.executor_id,
            supported_operations=(ExecutionOperation.RUN,),
            supported_capabilities=(ExecutionCapability.REPOSITORY_READ, ExecutionCapability.TEST_EXECUTION),
        )

    def prepare(self, request: ExecutionRequest) -> PreparedExecution:
        return PreparedExecution(
            schema_version="1",
            task_id=request.task_id,
            request_id=request.request_id,
            executor_id=self.executor_id,
            execution_id="exec-b-01",
            request_fingerprint=request.fingerprint(),
        )

    def collect_result(self, execution_id: str) -> ExecutionResult:
        return ExecutionResult(
            schema_version="1",
            task_id="TASK-028",
            request_id="req-01",
            executor_id=self.executor_id,
            operation=ExecutionOperation.RUN,
            status=ExecutionResultStatus.SUCCESS,
            implementation_sha="f" * 40,
            result_ref=ArtifactRef(path=".ai/results/RESULT-028.md", ref="ai/task-028", blob_sha="e" * 40),
        )


class NeutralExecutorC:
    """Third neutral stub for executor-c conforming with zero Continuity Core changes."""
    @property
    def executor_id(self) -> str:
        return "executor-c"

    def capabilities(self) -> ExecutorCapabilities:
        return ExecutorCapabilities(
            executor_id=self.executor_id,
            supported_operations=(ExecutionOperation.FIX,),
            supported_capabilities=(ExecutionCapability.LOCAL_GIT, ExecutionCapability.SHELL),
        )

    def prepare(self, request: ExecutionRequest) -> PreparedExecution:
        return PreparedExecution(
            schema_version="1",
            task_id=request.task_id,
            request_id=request.request_id,
            executor_id=self.executor_id,
            execution_id="exec-c-01",
            request_fingerprint=request.fingerprint(),
        )

    def collect_result(self, execution_id: str) -> ExecutionResult:
        return ExecutionResult(
            schema_version="1",
            task_id="TASK-028",
            request_id="req-01",
            executor_id=self.executor_id,
            operation=ExecutionOperation.FIX,
            status=ExecutionResultStatus.INCOMPLETE,
            error_code="C_INCOMPLETE",
        )


def test_executor_adapter_protocol_conformance():
    """Demonstrates three distinct neutral stubs conforming to ExecutorAdapter Protocol."""
    adapter_a = NeutralExecutorA()
    adapter_b = NeutralExecutorB()
    adapter_c = NeutralExecutorC()

    assert isinstance(adapter_a, ExecutorAdapter)
    assert isinstance(adapter_b, ExecutorAdapter)
    assert isinstance(adapter_c, ExecutorAdapter)

    assert adapter_a.executor_id == "executor-a"
    assert adapter_b.executor_id == "executor-b"
    assert adapter_c.executor_id == "executor-c"


# -----------------------------------------------------------------------------
# 8. Exhaustive Serialization, Bounds, UTF-8 & Unknown Field Tests
# -----------------------------------------------------------------------------

def test_unknown_fields_rejected_in_all_models():
    """All M4 models reject unrecognized fields in from_dict (AIP-1 / C14)."""
    state = _sample_state()
    req = _sample_execution_request(state)
    caps = _sample_capabilities()
    prep = PreparedExecution(
        schema_version="1",
        task_id=req.task_id,
        request_id=req.request_id,
        executor_id=req.executor_id,
        execution_id="exec-01",
        request_fingerprint=req.fingerprint(),
    )
    res = ExecutionResult(
        schema_version="1",
        task_id=req.task_id,
        request_id=req.request_id,
        executor_id=req.executor_id,
        operation=req.operation,
        status=ExecutionResultStatus.FAILED,
        error_code="FAIL",
    )

    # 1. ExecutionRequest
    with pytest.raises(ContinuityStateValidationError, match="Unknown fields in ExecutionRequest"):
        ExecutionRequest.from_dict({**req.to_dict(), "extra_field": "bad"})

    # 2. ExecutorCapabilities
    with pytest.raises(ContinuityStateValidationError, match="Unknown fields in ExecutorCapabilities"):
        ExecutorCapabilities.from_dict({**caps.to_dict(), "extra_field": "bad"})

    # 3. PreparedExecution
    with pytest.raises(ContinuityStateValidationError, match="Unknown fields in PreparedExecution"):
        PreparedExecution.from_dict({**prep.to_dict(), "extra_field": "bad"})

    # 4. ExecutionResult
    with pytest.raises(ContinuityStateValidationError, match="Unknown fields in ExecutionResult"):
        ExecutionResult.from_dict({**res.to_dict(), "extra_field": "bad"})


def test_missing_required_fields_rejected_in_all_models():
    """All M4 models require mandatory fields in from_dict."""
    state = _sample_state()
    req_dict = _sample_execution_request(state).to_dict()
    caps_dict = _sample_capabilities().to_dict()

    # Missing task_id in ExecutionRequest
    bad_req = dict(req_dict)
    del bad_req["task_id"]
    with pytest.raises(ContinuityStateValidationError, match="Missing required field 'task_id'"):
        ExecutionRequest.from_dict(bad_req)

    # Missing executor_id in ExecutorCapabilities
    bad_caps = dict(caps_dict)
    del bad_caps["executor_id"]
    with pytest.raises(ContinuityStateValidationError, match="Missing required field 'executor_id'"):
        ExecutorCapabilities.from_dict(bad_caps)


def test_oversized_payload_rejection_in_from_json():
    """Payloads exceeding 16 KiB are rejected before or during JSON parsing."""
    state = _sample_state()
    req = _sample_execution_request(state)

    huge_raw = json.dumps(req.to_dict()) + (" " * 20000)
    with pytest.raises(ContinuityStateValidationError, match="exceeds maximum allowed"):
        ExecutionRequest.from_json(huge_raw)

    with pytest.raises(ContinuityStateValidationError, match="exceeds maximum allowed"):
        ExecutionRequest.from_json(huge_raw.encode("utf-8"))


def test_bounds_context_refs_and_evidence_refs():
    """context_refs and evidence_refs enforce max limit of 32."""
    state = _sample_state()
    req = _sample_execution_request(state)

    # > 32 context_refs
    too_many_ctx = tuple(
        ArtifactRef(path=f".ai/decisions/ADR-{i:03d}.md", ref="ai-control", blob_sha=f"{i:040d}")
        for i in range(35)
    )
    with pytest.raises(ContinuityStateValidationError, match="context_refs count"):
        ExecutionRequest(
            schema_version="1",
            task_id="TASK-028",
            request_id="req-01",
            executor_id="antigravity",
            operation=ExecutionOperation.RUN,
            state_fingerprint=state.fingerprint(),
            target_branch="ai/task-028",
            expected_task_head_sha=None,
            work_ref=req.work_ref,
            context_refs=too_many_ctx,
            required_capabilities=(),
            expected_result_path=".ai/results/RESULT-028.md",
        )

    # > 32 evidence_refs
    too_many_ev = tuple(
        ArtifactRef(path=f".ai/evidence/EV-{i:03d}.md", ref="ai/task-028", blob_sha=f"{i:040d}")
        for i in range(35)
    )
    with pytest.raises(ContinuityStateValidationError, match="evidence_refs count"):
        ExecutionResult(
            schema_version="1",
            task_id="TASK-028",
            request_id="req-01",
            executor_id="antigravity",
            operation=ExecutionOperation.RUN,
            status=ExecutionResultStatus.FAILED,
            error_code="FAIL",
            evidence_refs=too_many_ev,
        )


def test_malformed_json_wraps_continuity_error():
    """Malformed JSON in from_json wraps as ContinuityStateValidationError."""
    with pytest.raises(ContinuityStateValidationError, match="Malformed JSON"):
        ExecutionRequest.from_json("{invalid json")

    with pytest.raises(ContinuityStateValidationError, match="Malformed JSON"):
        ExecutorCapabilities.from_json("{invalid json")

    with pytest.raises(ContinuityStateValidationError, match="Malformed JSON"):
        PreparedExecution.from_json("{invalid json")

    with pytest.raises(ContinuityStateValidationError, match="Malformed JSON"):
        ExecutionResult.from_json("{invalid json")


def test_invalid_utf8_bytes_wrapped_in_from_json():
    """Invalid UTF-8 bytes in from_json(bytes) wrap as ContinuityStateValidationError (R1-4)."""
    invalid_utf8 = b"\x80\x81\xff"

    with pytest.raises(ContinuityStateValidationError, match="Invalid UTF-8 encoding in input bytes for ExecutionRequest"):
        ExecutionRequest.from_json(invalid_utf8)

    with pytest.raises(ContinuityStateValidationError, match="Invalid UTF-8 encoding in input bytes for ExecutorCapabilities"):
        ExecutorCapabilities.from_json(invalid_utf8)

    with pytest.raises(ContinuityStateValidationError, match="Invalid UTF-8 encoding in input bytes for PreparedExecution"):
        PreparedExecution.from_json(invalid_utf8)

    with pytest.raises(ContinuityStateValidationError, match="Invalid UTF-8 encoding in input bytes for ExecutionResult"):
        ExecutionResult.from_json(invalid_utf8)
