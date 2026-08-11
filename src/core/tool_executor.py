import logging
from typing import Dict, Any, Optional
from src.core.types import ToolCall, ToolResult, ToolStatus
from src.core.errors import AgentException, SystemStateError
from src.core.tool_registry import ToolRegistry
from src.core.idempotency import IdempotencyStore
from src.core.retry import RetryManager
from src.core.checkpoint import CheckpointManager

logger = logging.getLogger(__name__)

class ToolExecutor:
    """
    Encapsulates the strict execution boundary for a tool.
    Handles Validation -> Idempotency -> Checkpointing -> Retry.
    SystemStateError is allowed to propagate out to halt the loop.
    Recoverable errors are converted into ToolResult(FAILURE).
    """
    def __init__(
        self,
        registry: ToolRegistry,
        idempotency_store: IdempotencyStore,
        retry_manager: RetryManager,
        checkpoints: CheckpointManager,
        context: Dict[str, Any]
    ):
        self.registry = registry
        self.idempotency_store = idempotency_store
        self.retry_manager = retry_manager
        self.checkpoints = checkpoints
        self.context = context

    async def execute(self, call: ToolCall) -> ToolResult:
        run_id = call.run_id
        self.checkpoints.log_tool_call_created(run_id, call.call_id, call.name, call.arguments)

        # 1. Validation
        try:
            self.registry.validate_call(call)
        except ValueError as e:
            logger.error(f"ToolCall validation failed: {e}")
            self.checkpoints.log_tool_call_rejected(run_id, call.call_id, str(e))
            return ToolResult(
                call_id=call.call_id,
                run_id=run_id,
                tool_name=call.name,
                status=ToolStatus.FAILURE,
                error=AgentException(f"Validation failed: {str(e)}", code="VALIDATION_ERROR")
            )

        tool = self.registry.get_tool(call.name)
        if not tool:
            logger.warning(f"No tool registered for action: {call.name}")
            self.checkpoints.log_tool_call_rejected(run_id, call.call_id, f"Tool {call.name} not found")
            return ToolResult(
                call_id=call.call_id,
                run_id=run_id,
                tool_name=call.name,
                status=ToolStatus.FAILURE,
                error=AgentException(f"Tool {call.name} not found", code="TOOL_NOT_FOUND")
            )

        # 2. Idempotency Check
        cached_result = self.idempotency_store.get(call.idempotency_key)
        if cached_result:
            logger.info(f"Idempotency hit! Returning cached result for {call.name} (Key: {call.idempotency_key})")
            return cached_result

        # 3. Execution with Retry
        self.checkpoints.log_tool_attempt_started(run_id, call.call_id)
        try:
            def _log_attempt(attempt: int, status: str, err: Optional[str]):
                self.checkpoints.log_tool_attempt_ended(run_id, call.call_id, attempt, status, err)

            result: ToolResult = await self.retry_manager.execute_with_retry(
                tool.execute,
                call=call,
                context=self.context,
                on_attempt_complete=_log_attempt
            )

            # 4. Save to Idempotency Store (only SUCCESS)
            if result.status == ToolStatus.SUCCESS:
                self.idempotency_store.save(call.idempotency_key, result)

            return result

        except AgentException as e:
            logger.error(f"Tool failed after retries: {e.code} - {e.message}")
            return ToolResult(
                call_id=call.call_id,
                run_id=run_id,
                tool_name=call.name,
                status=ToolStatus.FAILURE,
                error=e
            )
        except SystemStateError:
            # Must propagate immediately to halt the agent loop
            raise
        except Exception as e:
            logger.error(f"Unexpected tool execution failure: {e}", exc_info=True)
            return ToolResult(
                call_id=call.call_id,
                run_id=run_id,
                tool_name=call.name,
                status=ToolStatus.FAILURE,
                error=AgentException(str(e), code="UNKNOWN_TOOL_ERROR")
            )
