from __future__ import annotations

from typing import Any, Dict, Optional

import pytest

from src.core.errors import AgentException, SystemStateError
from src.core.idempotency_contract import (
    ClaimResult,
    ClaimStatus,
    IdempotencyRecord,
    RecordKey,
    RecordStatus,
)
from src.core.tool_executor import ToolExecutor
from src.core.types import ToolResult, ToolStatus


class FakeCheckpoints:
    def __getattr__(self, name: str) -> Any:
        def noop(*args: Any, **kwargs: Any) -> None:
            return None

        return noop


class FakeTool:
    def __init__(
        self,
        result: Optional[ToolResult] = None,
        error: Optional[Exception] = None,
    ) -> None:
        self.result = result
        self.error = error
        self.execute_count = 0

    async def execute(self, *args: Any, **kwargs: Any) -> ToolResult:
        self.execute_count += 1

        if self.error is not None:
            raise self.error

        if self.result is None:
            raise AssertionError("FakeTool has no configured result")

        return self.result


class FakeRegistry:
    def __init__(self, tool: FakeTool) -> None:
        self.tool = tool

    def validate_call(self, call: Any) -> None:
        return None

    def get_tool(self, name: str) -> FakeTool:
        return self.tool


class FakeRetryManager:
    async def execute_with_retry(
        self,
        execute: Any,
        *,
        call: Any,
        context: Dict[str, Any],
        on_attempt_complete: Any,
        on_retry_scheduled: Any = None,
    ) -> ToolResult:
        try:
            result = await execute(
                call=call,
                context=context,
            )
        except Exception as exc:
            retryable = (
                exc.retryable
                if isinstance(exc, AgentException)
                else False
            )
            on_attempt_complete(
                1,
                "FAILURE",
                str(exc),
            )

            if retryable:
                raise

            raise

        on_attempt_complete(1, result.status.value, None)
        return result


class FakeV2Store:
    def __init__(
        self,
        claim_status: ClaimStatus = ClaimStatus.CLAIMED,
        completed_record: Optional[IdempotencyRecord] = None,
        claim_error: Optional[Exception] = None,
        complete_error: Optional[Exception] = None,
        fail_error: Optional[Exception] = None,
    ) -> None:
        self.claim_status = claim_status
        self.completed_record = completed_record
        self.claim_error = claim_error
        self.complete_error = complete_error
        self.fail_error = fail_error

        self.claim_calls: list[tuple[RecordKey, str]] = []
        self.complete_calls: list[
            tuple[RecordKey, str, Optional[Dict[str, Any]]]
        ] = []
        self.fail_calls: list[
            tuple[RecordKey, str, bool, Optional[Dict[str, Any]]]
        ] = []

    def claim(
        self,
        key: RecordKey,
        owner_id: str,
    ) -> ClaimResult:
        self.claim_calls.append((key, owner_id))

        if self.claim_error is not None:
            raise self.claim_error

        if self.claim_status == ClaimStatus.ALREADY_COMPLETED:
            return ClaimResult(
                status=ClaimStatus.ALREADY_COMPLETED,
                record=self.completed_record,
            )

        return ClaimResult(
            status=self.claim_status,
            record=self.completed_record,
        )

    def complete(
        self,
        key: RecordKey,
        owner_id: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.complete_calls.append((key, owner_id, data))

        if self.complete_error is not None:
            raise self.complete_error

    def fail(
        self,
        key: RecordKey,
        owner_id: str,
        *,
        retryable: bool,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.fail_calls.append(
            (key, owner_id, retryable, data),
        )

        if self.fail_error is not None:
            raise self.fail_error

    def get(self, key: RecordKey) -> Optional[IdempotencyRecord]:
        return self.completed_record


class FakeLegacyStore:
    def __init__(self) -> None:
        self.values: Dict[str, ToolResult] = {}
        self.get_calls = 0
        self.save_calls = 0

    def get(self, key: str) -> Optional[ToolResult]:
        self.get_calls += 1
        return self.values.get(key)

    def save(self, key: str, result: ToolResult) -> None:
        self.save_calls += 1
        self.values[key] = result


class MockCall:
    def __init__(
        self,
        *,
        call_id: str = "call-1",
        run_id: str = "run-1",
        name: str = "test_tool",
        idempotency_key: str = "idem-1",
        arguments: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.call_id = call_id
        self.run_id = run_id
        self.name = name
        self.idempotency_key = idempotency_key
        self.arguments = arguments or {}


def make_result(
    call: MockCall,
    *,
    status: ToolStatus = ToolStatus.SUCCESS,
    data: Optional[Dict[str, Any]] = None,
    error: Optional[AgentException] = None,
) -> ToolResult:
    return ToolResult(
        call_id=call.call_id,
        run_id=call.run_id,
        tool_name=call.name,
        status=status,
        data=data,
        error=error,
    )


def make_executor(
    store: Any,
    tool: FakeTool,
) -> ToolExecutor:
    return ToolExecutor(
        registry=FakeRegistry(tool),
        idempotency_store=store,
        retry_manager=FakeRetryManager(),
        checkpoints=FakeCheckpoints(),
        context={},
    )


@pytest.mark.asyncio
async def test_claimed_success_executes_once_and_completes() -> None:
    call = MockCall()
    result = make_result(
        call,
        data={"value": 42},
    )
    tool = FakeTool(result=result)
    store = FakeV2Store(
        claim_status=ClaimStatus.CLAIMED,
    )

    executor = make_executor(store, tool)

    actual = await executor.execute(call)

    assert actual is result
    assert tool.execute_count == 1
    assert len(store.claim_calls) == 1
    assert len(store.complete_calls) == 1
    assert store.fail_calls == []

    key, owner_id, data = store.complete_calls[0]

    assert key == RecordKey(
        operation_key="tool:test_tool",
        idempotency_key="idem-1",
    )
    assert owner_id.startswith("process:")
    assert data == result.to_dict()


@pytest.mark.asyncio
async def test_already_completed_replays_result_without_execution() -> None:
    call = MockCall()
    stored_result = make_result(
        call,
        data={"cached": True},
    )

    record = IdempotencyRecord(
        key=RecordKey(
            operation_key="tool:test_tool",
            idempotency_key="idem-1",
        ),
        status=RecordStatus.COMPLETED,
        created_at=1.0,
        updated_at=2.0,
        owner_id="process:123",
        attempt=1,
        data=stored_result.to_dict(),
    )

    tool = FakeTool(
        result=make_result(
            call,
            data={"should_not_execute": True},
        ),
    )
    store = FakeV2Store(
        claim_status=ClaimStatus.ALREADY_COMPLETED,
        completed_record=record,
    )

    executor = make_executor(store, tool)

    actual = await executor.execute(call)

    assert actual.to_dict() == stored_result.to_dict()
    assert actual is not stored_result
    assert tool.execute_count == 0
    assert store.complete_calls == []
    assert store.fail_calls == []


@pytest.mark.asyncio
async def test_already_in_progress_does_not_execute() -> None:
    call = MockCall()
    tool = FakeTool(
        result=make_result(call),
    )
    store = FakeV2Store(
        claim_status=ClaimStatus.ALREADY_IN_PROGRESS,
    )

    executor = make_executor(store, tool)

    result = await executor.execute(call)

    assert result.status == ToolStatus.FAILURE
    assert result.error is not None
    assert result.error.code == "IDEMPOTENCY_IN_PROGRESS"
    assert tool.execute_count == 0
    assert store.complete_calls == []
    assert store.fail_calls == []


@pytest.mark.asyncio
async def test_failed_permanent_does_not_execute() -> None:
    call = MockCall()
    tool = FakeTool(
        result=make_result(call),
    )
    store = FakeV2Store(
        claim_status=ClaimStatus.FAILED_PERMANENT,
    )

    executor = make_executor(store, tool)

    result = await executor.execute(call)

    assert result.status == ToolStatus.FAILURE
    assert result.error is not None
    assert result.error.code == "IDEMPOTENCY_FAILED_PERMANENT"
    assert tool.execute_count == 0
    assert store.complete_calls == []
    assert store.fail_calls == []


@pytest.mark.asyncio
async def test_retryable_agent_failure_calls_fail_retryable() -> None:
    call = MockCall()
    error = AgentException(
        "temporary failure",
        code="TEMPORARY",
        retryable=True,
    )
    tool = FakeTool(error=error)
    store = FakeV2Store(
        claim_status=ClaimStatus.CLAIMED,
    )

    executor = make_executor(store, tool)

    result = await executor.execute(call)

    assert result.status == ToolStatus.FAILURE
    assert result.error is error
    assert tool.execute_count == 1
    assert len(store.fail_calls) == 1
    assert store.complete_calls == []

    key, owner_id, retryable, data = store.fail_calls[0]

    assert key == RecordKey(
        operation_key="tool:test_tool",
        idempotency_key="idem-1",
    )
    assert owner_id.startswith("process:")
    assert retryable is True
    assert data is not None
    assert "result" in data


@pytest.mark.asyncio
async def test_permanent_agent_failure_calls_fail_non_retryable() -> None:
    call = MockCall()
    error = AgentException(
        "permanent failure",
        code="PERMANENT",
        retryable=False,
    )
    tool = FakeTool(error=error)
    store = FakeV2Store(
        claim_status=ClaimStatus.CLAIMED,
    )

    executor = make_executor(store, tool)

    result = await executor.execute(call)

    assert result.status == ToolStatus.FAILURE
    assert result.error is error
    assert tool.execute_count == 1
    assert len(store.fail_calls) == 1

    _, _, retryable, _ = store.fail_calls[0]

    assert retryable is False


@pytest.mark.asyncio
async def test_non_retryable_tool_result_failure_calls_fail_non_retryable() -> None:
    call = MockCall()
    perm_error = AgentException("permanent", code="PERMANENT", retryable=False)
    failure_result = make_result(call, status=ToolStatus.FAILURE, error=perm_error)
    tool = FakeTool(result=failure_result)
    store = FakeV2Store(claim_status=ClaimStatus.CLAIMED)

    executor = make_executor(store, tool)

    result = await executor.execute(call)

    assert result.status == ToolStatus.FAILURE
    assert tool.execute_count == 1
    assert len(store.fail_calls) == 1

    _, _, retryable, data = store.fail_calls[0]
    assert retryable is False
    assert data is not None


@pytest.mark.asyncio
async def test_claim_persistence_error_becomes_system_state_error() -> None:
    call = MockCall()
    tool = FakeTool(
        result=make_result(call),
    )
    store = FakeV2Store(
        claim_error=OSError("disk full"),
    )

    executor = make_executor(store, tool)

    with pytest.raises(SystemStateError, match="claim persistence failed"):
        await executor.execute(call)

    assert tool.execute_count == 0


@pytest.mark.asyncio
async def test_complete_persistence_error_becomes_system_state_error() -> None:
    call = MockCall()
    tool = FakeTool(
        result=make_result(call),
    )
    store = FakeV2Store(
        claim_status=ClaimStatus.CLAIMED,
        complete_error=OSError("write failed"),
    )

    executor = make_executor(store, tool)

    with pytest.raises(
        SystemStateError,
        match="completion persistence failed",
    ):
        await executor.execute(call)

    assert tool.execute_count == 1
    assert len(store.complete_calls) == 1


@pytest.mark.asyncio
async def test_fail_persistence_error_becomes_system_state_error() -> None:
    call = MockCall()
    error = AgentException(
        "temporary failure",
        code="TEMPORARY",
        retryable=True,
    )
    tool = FakeTool(error=error)
    store = FakeV2Store(
        claim_status=ClaimStatus.CLAIMED,
        fail_error=OSError("write failed"),
    )

    executor = make_executor(store, tool)

    with pytest.raises(
        SystemStateError,
        match="failure persistence failed",
    ):
        await executor.execute(call)

    assert tool.execute_count == 1
    assert len(store.fail_calls) == 1


@pytest.mark.asyncio
async def test_system_state_error_from_tool_is_not_swallowed() -> None:
    call = MockCall()
    error = SystemStateError("browser infrastructure unavailable")
    tool = FakeTool(error=error)
    store = FakeV2Store(
        claim_status=ClaimStatus.CLAIMED,
    )

    executor = make_executor(store, tool)

    with pytest.raises(SystemStateError, match="browser infrastructure"):
        await executor.execute(call)

    assert tool.execute_count == 1
    assert store.complete_calls == []
    assert store.fail_calls == []


@pytest.mark.asyncio
async def test_v2_record_key_is_scoped_by_tool_name() -> None:
    call = MockCall(
        name="navigate",
        idempotency_key="same-key",
    )
    tool = FakeTool(
        result=make_result(call),
    )
    store = FakeV2Store(
        claim_status=ClaimStatus.CLAIMED,
    )

    executor = make_executor(store, tool)

    await executor.execute(call)

    key, _, _ = store.complete_calls[0]

    assert key.operation_key == "tool:navigate"
    assert key.idempotency_key == "same-key"


@pytest.mark.asyncio
async def test_legacy_store_path_remains_compatible() -> None:
    call = MockCall()
    result = make_result(
        call,
        data={"legacy": True},
    )
    tool = FakeTool(result=result)
    store = FakeLegacyStore()

    executor = make_executor(store, tool)

    actual = await executor.execute(call)

    assert actual is result
    assert tool.execute_count == 1
    assert store.get_calls == 1
    assert store.save_calls == 1


@pytest.mark.asyncio
async def test_legacy_store_cached_result_is_replayed() -> None:
    call = MockCall()
    cached = make_result(
        call,
        data={"cached": True},
    )
    tool = FakeTool(
        result=make_result(
            call,
            data={"must_not_run": True},
        ),
    )
    store = FakeLegacyStore()
    store.values[call.idempotency_key] = cached

    executor = make_executor(store, tool)

    actual = await executor.execute(call)

    assert actual is cached
    assert tool.execute_count == 0
    assert store.get_calls == 1
    assert store.save_calls == 0
