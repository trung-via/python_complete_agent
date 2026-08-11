import pytest
import json
from src.core.types import ToolCall, ToolResult, ToolStatus
from src.core.errors import AgentException

def test_tool_call_keys_generation():
    call = ToolCall(name="test_tool", arguments={"b": 2, "a": 1}, call_id="123", run_id="run456")
    
    # Operation key should be deterministic based on name and sorted arguments
    assert call.operation_key is not None
    assert call.idempotency_key == f"run456_{call.operation_key}"
    
    # Same args different order should yield same operation key
    call2 = ToolCall(name="test_tool", arguments={"a": 1, "b": 2}, call_id="999", run_id="run789")
    assert call.operation_key == call2.operation_key
    assert call2.idempotency_key == f"run789_{call.operation_key}"
    assert call.idempotency_key != call2.idempotency_key

def test_tool_result_serialization():
    result = ToolResult(
        call_id="c1",
        run_id="r1",
        tool_name="tool_a",
        status=ToolStatus.SUCCESS,
        data={"items": [1, 2, 3]},
        duration_ms=150
    )
    
    d = result.to_dict()
    assert d["status"] == "success"
    assert d["data"] == {"items": [1, 2, 3]}
    assert d["error"] is None
    
    restored = ToolResult.from_dict(d)
    assert restored.status == ToolStatus.SUCCESS
    assert restored.data == {"items": [1, 2, 3]}

def test_tool_result_with_error():
    err = AgentException("API failed", code="API_ERR", retryable=True)
    result = ToolResult(
        call_id="c2",
        run_id="r2",
        tool_name="tool_b",
        status=ToolStatus.FAILURE,
        error=err
    )
    
    d = result.to_dict()
    assert d["status"] == "failure"
    assert d["error"]["message"] == "API failed"
    assert d["error"]["code"] == "API_ERR"
    assert d["error"]["retryable"] is True
    
    restored = ToolResult.from_dict(d)
    assert restored.status == ToolStatus.FAILURE
    assert restored.error.message == "API failed"
    assert restored.error.code == "API_ERR"
    assert restored.error.retryable is True
