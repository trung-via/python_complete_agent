"""Unit tests for AIOS Bridge External Brain contracts and value objects."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
import pytest

from src.aios_bridge.external_brain import (
    BrainOperation,
    BrainOutputType,
    BrainRole,
    ContextItem,
    ContextKind,
    ContractValidationError,
    CorrelationError,
    ModelRequest,
    ModelResponse,
    ModelResponseStatus,
    get_expected_output_type,
    validate_request_response_correlation,
)


def test_enum_string_values_match_adr005():
    """Enum values must serialize to the locked string values from ADR-005."""
    assert [k.value for k in ContextKind] == [
        "TASK", "CONTRACT", "SOURCE", "TEST", "DIFF", "ERROR", "ARCHITECTURE"
    ]
    assert [r.value for r in BrainRole] == [
        "ARCHITECT", "CODER", "DEBUGGER", "REVIEWER"
    ]
    assert [o.value for o in BrainOperation] == [
        "PLAN", "GENERATE_PATCH", "DIAGNOSE_FAILURE", "REVIEW_PATCH"
    ]
    assert [t.value for t in BrainOutputType] == [
        "PLAN", "PATCH_PROPOSAL", "DIAGNOSIS", "REVIEW"
    ]
    assert [s.value for s in ModelResponseStatus] == [
        "SUCCESS", "FAILED", "RATE_LIMITED", "UNAVAILABLE", "TIMEOUT", "AUTH_ERROR", "INVALID_RESPONSE"
    ]


def test_operation_to_expected_output_type_mapping():
    """Operation must map strictly to expected output artifact type."""
    assert get_expected_output_type(BrainOperation.PLAN) == BrainOutputType.PLAN
    assert get_expected_output_type(BrainOperation.GENERATE_PATCH) == BrainOutputType.PATCH_PROPOSAL
    assert get_expected_output_type(BrainOperation.DIAGNOSE_FAILURE) == BrainOutputType.DIAGNOSIS
    assert get_expected_output_type(BrainOperation.REVIEW_PATCH) == BrainOutputType.REVIEW


def test_context_item_immutability_and_validation():
    """ContextItem is frozen and validates content and SHA-256 format."""
    item = ContextItem(
        kind=ContextKind.SOURCE,
        content="print('hello')",
        path="src/main.py",
        priority=1,
        content_sha256="a" * 64,
    )
    assert item.kind == ContextKind.SOURCE
    assert item.content == "print('hello')"
    assert item.path == "src/main.py"
    assert item.priority == 1
    assert item.content_sha256 == "a" * 64

    # Frozen
    with pytest.raises(FrozenInstanceError):
        item.content = "new"  # type: ignore

    # Non-string content rejected
    with pytest.raises(ContractValidationError, match="content must be a non-null string"):
        ContextItem(kind=ContextKind.TASK, content=None)  # type: ignore

    # Invalid SHA-256 format rejected (too short, too long, non-hex)
    with pytest.raises(ContractValidationError, match="content_sha256 must be a 64-character"):
        ContextItem(kind=ContextKind.TASK, content="abc", content_sha256="short")
    with pytest.raises(ContractValidationError, match="content_sha256 must be a 64-character"):
        ContextItem(kind=ContextKind.TASK, content="abc", content_sha256="z" * 64)


def test_model_request_validation():
    """ModelRequest validates schema version, task_id pattern, non-empty instruction, and output mapping."""
    ctx = ContextItem(kind=ContextKind.TASK, content="Implement feature")
    req = ModelRequest(
        schema_version="1",
        request_id="req-001",
        task_id="TASK-014",
        role=BrainRole.ARCHITECT,
        operation=BrainOperation.PLAN,
        instruction="Plan the implementation",
        context=(ctx,),
        output_format=BrainOutputType.PLAN,
        max_input_tokens=1000,
        max_output_tokens=2000,
    )
    assert req.schema_version == "1"
    assert req.task_id == "TASK-014"
    assert req.output_format == BrainOutputType.PLAN

    # Invalid schema version
    with pytest.raises(ContractValidationError, match="Unsupported schema_version"):
        ModelRequest(
            schema_version="2",
            request_id="req-001",
            task_id="TASK-014",
            role=BrainRole.ARCHITECT,
            operation=BrainOperation.PLAN,
            instruction="Plan",
            context=(ctx,),
            output_format=BrainOutputType.PLAN,
        )

    # Invalid task_id pattern
    with pytest.raises(ContractValidationError, match="task_id must follow the 'TASK-<digits>' pattern"):
        ModelRequest(
            schema_version="1",
            request_id="req-001",
            task_id="TASK_014",
            role=BrainRole.ARCHITECT,
            operation=BrainOperation.PLAN,
            instruction="Plan",
            context=(ctx,),
            output_format=BrainOutputType.PLAN,
        )

    # Empty instruction
    with pytest.raises(ContractValidationError, match="instruction must be a non-empty string"):
        ModelRequest(
            schema_version="1",
            request_id="req-001",
            task_id="TASK-014",
            role=BrainRole.ARCHITECT,
            operation=BrainOperation.PLAN,
            instruction="   ",
            context=(ctx,),
            output_format=BrainOutputType.PLAN,
        )

    # Operation / output mismatch
    with pytest.raises(ContractValidationError, match="output_format mismatch for operation PLAN"):
        ModelRequest(
            schema_version="1",
            request_id="req-001",
            task_id="TASK-014",
            role=BrainRole.ARCHITECT,
            operation=BrainOperation.PLAN,
            instruction="Plan",
            context=(ctx,),
            output_format=BrainOutputType.PATCH_PROPOSAL,
        )

    # Non-positive token limits
    with pytest.raises(ContractValidationError, match="max_input_tokens must be a positive integer"):
        ModelRequest(
            schema_version="1",
            request_id="req-001",
            task_id="TASK-014",
            role=BrainRole.ARCHITECT,
            operation=BrainOperation.PLAN,
            instruction="Plan",
            context=(ctx,),
            output_format=BrainOutputType.PLAN,
            max_input_tokens=0,
        )


def test_model_response_validation():
    """ModelResponse validates SUCCESS constraints and non-negative usage metrics."""
    resp = ModelResponse(
        schema_version="1",
        request_id="req-001",
        task_id="TASK-014",
        provider="minimax",
        model="MiniMax-Text-01",
        status=ModelResponseStatus.SUCCESS,
        output_type=BrainOutputType.PLAN,
        content="# SUMMARY\nPlan overview\n## STEPS\n1. Do it",
        input_tokens=100,
        output_tokens=200,
        latency_ms=1200,
    )
    assert resp.status == ModelResponseStatus.SUCCESS
    assert resp.input_tokens == 100
    assert resp.latency_ms == 1200

    # SUCCESS requires non-null output_type
    with pytest.raises(ContractValidationError, match="SUCCESS status requires non-null output_type"):
        ModelResponse(
            schema_version="1",
            request_id="req-001",
            task_id="TASK-014",
            provider="minimax",
            model="MiniMax-Text-01",
            status=ModelResponseStatus.SUCCESS,
            output_type=None,
            content="Some content",
        )

    # SUCCESS requires non-empty content
    with pytest.raises(ContractValidationError, match="SUCCESS status requires non-empty content string"):
        ModelResponse(
            schema_version="1",
            request_id="req-001",
            task_id="TASK-014",
            provider="minimax",
            model="MiniMax-Text-01",
            status=ModelResponseStatus.SUCCESS,
            output_type=BrainOutputType.PLAN,
            content="   ",
        )

    # Failure status allows None content and preserves unknown token usage as None
    fail_resp = ModelResponse(
        schema_version="1",
        request_id="req-001",
        task_id="TASK-014",
        provider="deepseek",
        model="deepseek-coder",
        status=ModelResponseStatus.RATE_LIMITED,
        output_type=None,
        content=None,
        error_code="RATE_LIMIT_EXCEEDED",
        error_message="Too many requests",
    )
    assert fail_resp.status == ModelResponseStatus.RATE_LIMITED
    assert fail_resp.input_tokens is None
    assert fail_resp.output_tokens is None

    # Negative usage rejected
    with pytest.raises(ContractValidationError, match="input_tokens must be a non-negative integer"):
        ModelResponse(
            schema_version="1",
            request_id="req-001",
            task_id="TASK-014",
            provider="deepseek",
            model="deepseek-coder",
            status=ModelResponseStatus.FAILED,
            output_type=None,
            content=None,
            input_tokens=-5,
        )

    # Boolean usage / latency rejected
    with pytest.raises(ContractValidationError, match="input_tokens must be a non-negative integer"):
        ModelResponse(
            schema_version="1",
            request_id="req-001",
            task_id="TASK-014",
            provider="deepseek",
            model="deepseek-coder",
            status=ModelResponseStatus.FAILED,
            output_type=None,
            content=None,
            input_tokens=True,
        )


def test_model_response_rejects_contradictory_success_failure_metadata():
    """SUCCESS status must not have error_code or error_message."""
    # 1. SUCCESS with error_code rejected
    with pytest.raises(ContractValidationError, match="SUCCESS status cannot have error_code"):
        ModelResponse(
            schema_version="1",
            request_id="req-001",
            task_id="TASK-014",
            provider="minimax",
            model="MiniMax-Text-01",
            status=ModelResponseStatus.SUCCESS,
            output_type=BrainOutputType.PLAN,
            content="Valid plan content",
            error_code="AUTH_ERROR",
        )

    # 2. SUCCESS with error_message rejected
    with pytest.raises(ContractValidationError, match="SUCCESS status cannot have error_message"):
        ModelResponse(
            schema_version="1",
            request_id="req-001",
            task_id="TASK-014",
            provider="minimax",
            model="MiniMax-Text-01",
            status=ModelResponseStatus.SUCCESS,
            output_type=BrainOutputType.PLAN,
            content="Valid plan content",
            error_message="some error occurred",
        )

    # 3. Normal SUCCESS remains valid
    ok = ModelResponse(
        schema_version="1",
        request_id="req-001",
        task_id="TASK-014",
        provider="minimax",
        model="MiniMax-Text-01",
        status=ModelResponseStatus.SUCCESS,
        output_type=BrainOutputType.PLAN,
        content="Valid plan content",
    )
    assert ok.status == ModelResponseStatus.SUCCESS
    assert ok.error_code is None
    assert ok.error_message is None

    # 4. Non-success with error metadata remains valid
    err = ModelResponse(
        schema_version="1",
        request_id="req-001",
        task_id="TASK-014",
        provider="minimax",
        model="MiniMax-Text-01",
        status=ModelResponseStatus.AUTH_ERROR,
        output_type=None,
        content=None,
        error_code="INVALID_API_KEY",
        error_message="The API key is invalid",
    )
    assert err.status == ModelResponseStatus.AUTH_ERROR
    assert err.error_code == "INVALID_API_KEY"
    assert err.error_message == "The API key is invalid"



def test_validate_request_response_correlation():
    """validate_request_response_correlation asserts request ID, task ID, and output type match."""
    req = ModelRequest(
        schema_version="1",
        request_id="req-001",
        task_id="TASK-014",
        role=BrainRole.CODER,
        operation=BrainOperation.GENERATE_PATCH,
        instruction="Generate patch",
        context=(),
        output_format=BrainOutputType.PATCH_PROPOSAL,
    )

    valid_resp = ModelResponse(
        schema_version="1",
        request_id="req-001",
        task_id="TASK-014",
        provider="deepseek",
        model="deepseek-coder",
        status=ModelResponseStatus.SUCCESS,
        output_type=BrainOutputType.PATCH_PROPOSAL,
        content="# SUMMARY\nPatch summary\n## FILES\nfile.py\n## PATCH\ndiff\n## TESTS\ntest\n## RISKS\nnone",
    )
    # Correlation succeeds with no exception
    validate_request_response_correlation(req, valid_resp)

    # Request ID mismatch
    mismatch_req_id = ModelResponse(
        schema_version="1",
        request_id="req-999",
        task_id="TASK-014",
        provider="deepseek",
        model="deepseek-coder",
        status=ModelResponseStatus.SUCCESS,
        output_type=BrainOutputType.PATCH_PROPOSAL,
        content="content",
    )
    with pytest.raises(CorrelationError, match="Request ID mismatch"):
        validate_request_response_correlation(req, mismatch_req_id)

    # Task ID mismatch
    mismatch_task_id = ModelResponse(
        schema_version="1",
        request_id="req-001",
        task_id="TASK-015",
        provider="deepseek",
        model="deepseek-coder",
        status=ModelResponseStatus.SUCCESS,
        output_type=BrainOutputType.PATCH_PROPOSAL,
        content="content",
    )
    with pytest.raises(CorrelationError, match="Task ID mismatch"):
        validate_request_response_correlation(req, mismatch_task_id)

    # Output type mismatch
    mismatch_output = ModelResponse(
        schema_version="1",
        request_id="req-001",
        task_id="TASK-014",
        provider="deepseek",
        model="deepseek-coder",
        status=ModelResponseStatus.SUCCESS,
        output_type=BrainOutputType.PLAN,
        content="content",
    )
    with pytest.raises(CorrelationError, match="Output type mismatch"):
        validate_request_response_correlation(req, mismatch_output)


def test_deterministic_serialization_equality():
    """Serializing identical contracts produces identical JSON across repeated calls."""
    ctx = ContextItem(
        kind=ContextKind.TASK,
        content="Do something",
        path="task.md",
        priority=0,
        content_sha256="e" * 64,
    )
    req = ModelRequest(
        schema_version="1",
        request_id="req-100",
        task_id="TASK-014",
        role=BrainRole.REVIEWER,
        operation=BrainOperation.REVIEW_PATCH,
        instruction="Review this patch",
        context=(ctx,),
        output_format=BrainOutputType.REVIEW,
        provider="kimi",
        model="moonshot-v1",
        max_input_tokens=4000,
        max_output_tokens=1000,
    )
    d1 = req.to_dict()
    d2 = req.to_dict()
    assert d1 == d2
    json1 = json.dumps(d1, sort_keys=True)
    json2 = json.dumps(d2, sort_keys=True)
    assert json1 == json2


def test_context_immutability_and_order_preservation():
    """Context tuple preserves exact item order and is immutable."""
    c1 = ContextItem(kind=ContextKind.TASK, content="First")
    c2 = ContextItem(kind=ContextKind.SOURCE, content="Second", path="a.py")
    c3 = ContextItem(kind=ContextKind.TEST, content="Third", path="test.py")

    req = ModelRequest(
        schema_version="1",
        request_id="req-order",
        task_id="TASK-014",
        role=BrainRole.CODER,
        operation=BrainOperation.GENERATE_PATCH,
        instruction="Generate",
        context=[c1, c2, c3],  # passed as list
        output_format=BrainOutputType.PATCH_PROPOSAL,
    )

    assert isinstance(req.context, tuple)
    assert len(req.context) == 3
    assert req.context[0].content == "First"
    assert req.context[1].content == "Second"
    assert req.context[2].content == "Third"

