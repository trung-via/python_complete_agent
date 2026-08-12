import pytest
import asyncio
from src.core.retry import RetryManager, RetryPolicy
from src.core.types import ToolResult, ToolStatus
from src.core.errors import AgentException

@pytest.mark.asyncio
async def test_retry_manager_success_first_try():
    async def mock_op():
        return ToolResult(call_id="c", run_id="r", tool_name="t", status=ToolStatus.SUCCESS, data={"ok": True})
        
    manager = RetryManager(RetryPolicy(max_attempts=3, base_delay=0.1, jitter=False))
    
    callbacks = []
    def on_complete(attempt, status, err):
        callbacks.append((attempt, status, err))
        
    result = await manager.execute_with_retry(mock_op, on_attempt_complete=on_complete)
    assert result.status == ToolStatus.SUCCESS
    assert len(callbacks) == 1
    assert callbacks[0] == (1, "success", None)

@pytest.mark.asyncio
async def test_retry_manager_exhaustion():
    async def mock_fail_op():
        return ToolResult(
            call_id="c", run_id="r", tool_name="t", 
            status=ToolStatus.FAILURE, 
            error=AgentException("Always fails", "TEST_ERR", retryable=True)
        )
        
    manager = RetryManager(RetryPolicy(max_attempts=2, base_delay=0.01, jitter=False))
    
    # Should return the last failure result instead of raising, because it returns a ToolResult
    result = await manager.execute_with_retry(mock_fail_op)
    assert result.status == ToolStatus.FAILURE
    assert result.error.message == "Always fails"

@pytest.mark.asyncio
async def test_retry_manager_bare_raise_fix():
    # If the operation natively raises an exception rather than returning ToolResult
    async def mock_raise_op():
        raise AgentException("Network crash", "NETWORK_ERR", retryable=True)
        
    manager = RetryManager(RetryPolicy(max_attempts=2, base_delay=0.01, jitter=False))
    
    with pytest.raises(AgentException) as excinfo:
        await manager.execute_with_retry(mock_raise_op)
    
    assert "Network crash" in str(excinfo.value)

def test_retry_policy_delay_calculation():
    policy = RetryPolicy(base_delay=1.0, max_delay=10.0, jitter=False)
    
    assert policy.get_delay(1) == 1.0
    assert policy.get_delay(2) == 2.0
    assert policy.get_delay(3) == 4.0
    
    # Test RATE_LIMIT respecting Retry-After
    err = AgentException("Rate limit", code="RATE_LIMIT", details={"retry_after": 15})
    assert policy.get_delay(1, err) == 15.0
