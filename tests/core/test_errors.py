import pytest
from src.core.errors import AgentException, SystemStateError

def test_agent_exception_defaults():
    e = AgentException("Something went wrong", "UNKNOWN_ERROR")
    assert e.message == "Something went wrong"
    assert e.code == "UNKNOWN_ERROR"
    assert e.retryable is False
    assert e.details == {}
    assert str(e) == "Something went wrong"

def test_agent_exception_custom():
    e = AgentException("Rate limit hit", "RATE_LIMIT", retryable=True, details={"retry_after": 5})
    assert e.message == "Rate limit hit"
    assert e.code == "RATE_LIMIT"
    assert e.retryable is True
    assert e.details == {"retry_after": 5}
    assert str(e) == "Rate limit hit"

def test_system_state_error_inheritance():
    e = SystemStateError("Disk failure")
    # Must inherit from Exception to be throwable, but should be distinct from AgentException
    assert isinstance(e, Exception)
    assert str(e) == "Disk failure"
