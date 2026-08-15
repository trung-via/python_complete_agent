from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from src.core.checkpoint import CheckpointManager
from src.core.checkpoint_contract import (
    CheckpointCorruptionError,
    CheckpointStateError,
)
from src.core.errors import AgentException, SystemStateError
from src.core.idempotency import IdempotencyStore
from src.core.idempotency_contract import (
    ClaimStatus,
    IdempotencyError,
    IdempotencyStoreProtocol,
    RecordKey,
)
from src.core.retry import RetryManager
from src.core.tool_registry import ToolRegistry
from src.core.types import ToolCall, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Executes tools behind validation, idempotency, checkpointing, and retry.

    Supports both the legacy IdempotencyStore and the v2
    IdempotencyStoreProtocol. The legacy backend remains available for
    backward compatibility while JsonlIdempotencyStore is used by new
    production wiring.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        idempotency_store: IdempotencyStore | IdempotencyStoreProtocol,
        retry_manager: RetryManager,
        checkpoints: CheckpointManager,
        context: Dict[str, Any],
    ) -> None:
        self.registry = registry
        self.idempotency_store = idempotency_store
        self.retry_manager = retry_manager
        self.checkpoints = checkpoints
        self.context = context
        self.owner_id = f"process:{os.getpid()}:executor:{id(self)}"

    async def execute(self, call: ToolCall) -> ToolResult:
        run_id = call.run_id

        self.checkpoints.log_tool_call_created(
            run_id,
            call.call_id,
            call.name,
            call.arguments,
        )

        validation_error = self._validate_call(call)
        if validation_error is not None:
            return validation_error

        tool = self.registry.get_tool(call.name)
        if not tool:
            logger.warning("No tool registered for action: %s", call.name)
            self.checkpoints.log_tool_call_rejected(
                run_id,
                call.call_id,
                f"Tool {call.name} not found",
            )
            return self._failure_result(
                call,
                f"Tool {call.name} not found",
                "TOOL_NOT_FOUND",
            )

        if self._is_v2_store():
            return await self._execute_v2(call, tool)

        return await self._execute_legacy(call, tool)

    def _validate_call(self, call: ToolCall) -> Optional[ToolResult]:
        try:
            self.registry.validate_call(call)
        except ValueError as exc:
            logger.error("ToolCall validation failed: %s", exc)
            self.checkpoints.log_tool_call_rejected(
                call.run_id,
                call.call_id,
                str(exc),
            )
            return self._failure_result(
                call,
                f"Validation failed: {exc}",
                "VALIDATION_ERROR",
            )

        return None

    def _is_v2_store(self) -> bool:
        """
        Detect the v2 protocol by its lifecycle methods.

        The legacy store exposes get/save, while v2 exposes claim/complete/fail.
        """
        return all(
            callable(getattr(self.idempotency_store, method, None))
            for method in ("claim", "complete", "fail")
        )

    async def _execute_v2(self, call: ToolCall, tool: Any) -> ToolResult:
        store = self.idempotency_store
        key = self._record_key(call)

        try:
            claim_result = store.claim(key, self.owner_id)
        except IdempotencyError:
            raise
        except OSError as exc:
            raise SystemStateError(
                f"Idempotency claim persistence failed: {exc}"
            ) from exc
        except Exception as exc:
            logger.error(
                "Unexpected idempotency claim failure: %s",
                exc,
                exc_info=True,
            )
            raise SystemStateError(
                f"Idempotency claim failed: {exc}"
            ) from exc

        if claim_result.status == ClaimStatus.ALREADY_COMPLETED:
            return self._replay_completed_result(call, claim_result.record)

        if claim_result.status == ClaimStatus.ALREADY_IN_PROGRESS:
            return self._failure_result(
                call,
                "Tool execution is already in progress for this idempotency key.",
                "IDEMPOTENCY_IN_PROGRESS",
            )

        if claim_result.status == ClaimStatus.FAILED_PERMANENT:
            return self._failure_result(
                call,
                "Tool execution previously failed permanently for this idempotency key.",
                "IDEMPOTENCY_FAILED_PERMANENT",
            )

        if claim_result.status != ClaimStatus.CLAIMED:
            raise SystemStateError(
                f"Unexpected idempotency claim status: "
                f"{claim_result.status!r}"
            )

        return await self._execute_claimed_v2(call, tool, key)

    async def _execute_claimed_v2(
        self,
        call: ToolCall,
        tool: Any,
        key: RecordKey,
    ) -> ToolResult:
        try:
            try:
                result = await self._execute_with_retry(call, tool)
            except AgentException as exc:
                logger.error(
                    "Tool failed after retries: %s - %s",
                    exc.code,
                    exc.message,
                )
                result = ToolResult(
                    call_id=call.call_id,
                    run_id=call.run_id,
                    tool_name=call.name,
                    status=ToolStatus.FAILURE,
                    error=exc,
                )
            except (SystemStateError, CheckpointCorruptionError, CheckpointStateError):
                raise
            except Exception as exc:
                logger.error(
                    "Unexpected tool execution failure: %s",
                    exc,
                    exc_info=True,
                )
                result = ToolResult(
                    call_id=call.call_id,
                    run_id=call.run_id,
                    tool_name=call.name,
                    status=ToolStatus.FAILURE,
                    error=AgentException(
                        str(exc),
                        code="UNKNOWN_TOOL_ERROR",
                    ),
                )

            if result.status == ToolStatus.SUCCESS:
                self._complete_v2(key, result)
                return result

            is_retryable = (
                result.error.retryable
                if isinstance(result.error, AgentException)
                else True
            )

            self._fail_v2(
                key,
                retryable=is_retryable,
                data={
                    "result": result.to_dict(),
                },
            )
            return result

        except (SystemStateError, CheckpointCorruptionError, CheckpointStateError):
            raise

    async def _execute_legacy(self, call: ToolCall, tool: Any) -> ToolResult:
        cached_result = self.idempotency_store.get(call.idempotency_key)

        if cached_result:
            logger.info(
                "Legacy idempotency hit for %s (Key: %s)",
                call.name,
                call.idempotency_key,
            )
            return cached_result

        try:
            result = await self._execute_with_retry(call, tool)

            if result.status == ToolStatus.SUCCESS:
                self.idempotency_store.save(
                    call.idempotency_key,
                    result,
                )

            return result

        except AgentException as exc:
            logger.error(
                "Tool failed after retries: %s - %s",
                exc.code,
                exc.message,
            )
            return ToolResult(
                call_id=call.call_id,
                run_id=call.run_id,
                tool_name=call.name,
                status=ToolStatus.FAILURE,
                error=exc,
            )

        except (SystemStateError, CheckpointCorruptionError, CheckpointStateError):
            raise

        except Exception as exc:
            logger.error(
                "Unexpected tool execution failure: %s",
                exc,
                exc_info=True,
            )
            return ToolResult(
                call_id=call.call_id,
                run_id=call.run_id,
                tool_name=call.name,
                status=ToolStatus.FAILURE,
                error=AgentException(
                    str(exc),
                    code="UNKNOWN_TOOL_ERROR",
                ),
            )

    async def _execute_with_retry(self, call: ToolCall, tool: Any) -> ToolResult:
        def on_attempt_start(attempt: int) -> None:
            self.checkpoints.log_tool_attempt_started(
                call.run_id,
                call.call_id,
                attempt=attempt,
                tool_name=call.name,
                arguments=call.arguments,
            )

        def on_attempt_complete(
            attempt: int,
            status: str,
            error: Optional[str],
        ) -> None:
            self.checkpoints.log_tool_attempt_ended(
                call.run_id,
                call.call_id,
                attempt,
                status,
                error,
            )

        def on_retry_scheduled(
            attempt: int,
            next_attempt: int,
            delay_seconds: float,
            reason: str,
            failure_domain: str,
        ) -> None:
            self.checkpoints.log_retry_scheduled(
                run_id=call.run_id,
                operation="TOOL",
                attempt=attempt,
                next_attempt=next_attempt,
                delay_seconds=delay_seconds,
                reason=reason,
                failure_domain=failure_domain,
                call_id=call.call_id,
            )

        def before_retry_attempt(next_attempt: int) -> bool:
            try:
                from src.core.recovery_diagnostics import RecoveryAnalyzer
                from src.core.checkpoint_contract import RunState
                diag = RecoveryAnalyzer.analyze(call.run_id, self.checkpoints.db_path)
                if diag.current_state in (RunState.HALTED, RunState.FAILED, RunState.COMPLETED):
                    return False
                return True
            except Exception as e:
                logger.warning(f"Error checking run state before retry attempt for {call.run_id}: {e}")
                return True

        return await self.retry_manager.execute_with_retry(
            tool.execute,
            call=call,
            context=self.context,
            on_attempt_start=on_attempt_start,
            on_attempt_complete=on_attempt_complete,
            on_retry_scheduled=on_retry_scheduled,
            before_retry_attempt=before_retry_attempt,
        )

    def _complete_v2(
        self,
        key: RecordKey,
        result: ToolResult,
    ) -> None:
        try:
            self.idempotency_store.complete(
                key,
                self.owner_id,
                data=result.to_dict(),
            )
        except SystemStateError:
            raise
        except OSError as exc:
            raise SystemStateError(
                f"Idempotency completion persistence failed: {exc}"
            ) from exc
        except Exception as exc:
            logger.error(
                "Failed to complete idempotency record: %s",
                exc,
                exc_info=True,
            )
            raise SystemStateError(
                f"Idempotency completion failed: {exc}"
            ) from exc

    def _fail_v2(
        self,
        key: RecordKey,
        *,
        retryable: bool,
        data: Optional[Dict[str, Any]],
    ) -> None:
        try:
            self.idempotency_store.fail(
                key,
                self.owner_id,
                retryable=retryable,
                data=data,
            )
        except SystemStateError:
            raise
        except OSError as exc:
            raise SystemStateError(
                f"Idempotency failure persistence failed: {exc}"
            ) from exc
        except Exception as exc:
            logger.error(
                "Failed to persist idempotency failure state: %s",
                exc,
                exc_info=True,
            )
            raise SystemStateError(
                f"Idempotency failure transition failed: {exc}"
            ) from exc

    @staticmethod
    def _record_key(call: ToolCall) -> RecordKey:
        return RecordKey(
            operation_key=f"tool:{call.name}",
            idempotency_key=call.idempotency_key,
        )

    @staticmethod
    def _replay_completed_result(
        call: ToolCall,
        record: Any,
    ) -> ToolResult:
        if record is None:
            raise SystemStateError(
                "Idempotency store returned ALREADY_COMPLETED "
                "without a record."
            )

        if not isinstance(record.data, dict):
            raise SystemStateError(
                "Completed idempotency record does not contain "
                "serialized ToolResult data."
            )

        result_data = record.data

        if "result" in result_data:
            result_data = result_data["result"]

        try:
            return ToolResult.from_dict(result_data)
        except (KeyError, TypeError, ValueError) as exc:
            raise SystemStateError(
                f"Failed to deserialize completed ToolResult: {exc}"
            ) from exc

    @staticmethod
    def _failure_result(
        call: ToolCall,
        message: str,
        code: str,
    ) -> ToolResult:
        return ToolResult(
            call_id=call.call_id,
            run_id=call.run_id,
            tool_name=call.name,
            status=ToolStatus.FAILURE,
            error=AgentException(
                message,
                code=code,
            ),
        )
