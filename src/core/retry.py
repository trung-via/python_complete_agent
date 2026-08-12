import asyncio
import logging
import random
from typing import Callable, Any, Optional
from dataclasses import dataclass
from src.core.errors import AgentException

logger = logging.getLogger(__name__)

@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 2.0
    max_delay: float = 30.0
    jitter: bool = True

    def get_delay(self, attempt: int, error: Optional[AgentException] = None) -> float:
        """Calculates the backoff delay based on attempt and error type."""
        # Special case: Respect RateLimit Retry-After if provided in details
        if error and error.code == "RATE_LIMIT" and error.details:
            retry_after = error.details.get("retry_after")
            if retry_after:
                return float(retry_after)
                
        # Exponential backoff
        delay = min(self.max_delay, self.base_delay * (2 ** (attempt - 1)))
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            delay = delay * (0.5 + random.random())
            
        return delay

class RetryManager:
    """
    Handles robust execution of tools with granular, policy-based retry logic.
    """
    def __init__(self, default_policy: Optional[RetryPolicy] = None):
        self.policy = default_policy or RetryPolicy()
        
    async def execute_with_retry(
        self, 
        operation: Callable, 
        *args, 
        on_attempt_complete: Optional[Callable[[int, str, Optional[str]], None]] = None,
        on_retry_scheduled: Optional[Callable[[int, int, float, str, str], None]] = None,
        **kwargs
    ) -> Any:
        """
        Executes an asynchronous operation and retries it if a retryable error is returned.
        Returns the ToolResult of the operation.
        """
        from src.core.types import ToolResult, ToolStatus
        
        attempt = 1
        last_result = None
        last_exception = None
        
        while attempt <= self.policy.max_attempts:
            error_to_eval = None
            try:
                result = await operation(*args, **kwargs)
                
                if isinstance(result, ToolResult) and result.status == ToolStatus.FAILURE:
                    if result.error and result.error.retryable:
                        logger.warning(f"Operation failed with retryable error (Attempt {attempt}/{self.policy.max_attempts}): {result.error.code} - {result.error.message}")
                        last_result = result
                        error_to_eval = result.error
                        if on_attempt_complete:
                            on_attempt_complete(attempt, "FAILURE", result.error.message)
                    else:
                        logger.error(f"Operation failed with non-retryable error: {result.error.message if result.error else 'Unknown'}")
                        if on_attempt_complete:
                            on_attempt_complete(attempt, "FATAL_FAILURE", result.error.message if result.error else 'Unknown')
                        return result
                else:
                    # Success or Partial Success
                    if on_attempt_complete:
                        status_str = result.status.value if isinstance(result, ToolResult) else "SUCCESS"
                        on_attempt_complete(attempt, status_str, None)
                    return result
                    
            except AgentException as e:
                last_exception = e
                if not e.retryable:
                    logger.error(f"Operation raised non-retryable AgentException: {e.code} - {e.message}")
                    if on_attempt_complete:
                        on_attempt_complete(attempt, "FATAL_EXCEPTION", e.message)
                    raise
                logger.warning(f"Operation raised retryable AgentException (Attempt {attempt}/{self.policy.max_attempts}): {e.code} - {e.message}")
                error_to_eval = e
                if on_attempt_complete:
                    on_attempt_complete(attempt, "EXCEPTION", e.message)
            except Exception as e:
                last_exception = e
                logger.error(f"Operation raised unexpected exception (Attempt {attempt}/{self.policy.max_attempts}): {e}")
                if on_attempt_complete:
                    on_attempt_complete(attempt, "UNEXPECTED_EXCEPTION", str(e))
                
            from src.core.checkpoint_contract import FailureDomain
            from src.core.retry_policy import (
                RetryContext,
                RetryOperation,
                RetryPolicyEngine,
            )

            is_transient = False
            err_code = ""
            if error_to_eval:
                is_transient = getattr(error_to_eval, "retryable", True)
                err_code = getattr(error_to_eval, "code", "")
            elif last_exception:
                is_transient = getattr(last_exception, "retryable", False)
                err_code = getattr(last_exception, "code", "")

            ctx = RetryContext(
                operation=RetryOperation.TOOL,
                attempt=attempt,
                max_attempts=self.policy.max_attempts,
                failure_domain=FailureDomain.TOOL_EXECUTION,
                error_code=err_code,
                transient=is_transient,
            )

            decision = RetryPolicyEngine.decide(
                ctx,
                base_delay=self.policy.base_delay,
                max_delay=self.policy.max_delay,
            )

            if not decision.should_retry:
                logger.error(
                    f"RetryPolicyEngine decided to STOP retry (attempt {attempt}/{self.policy.max_attempts}): "
                    f"reason={decision.reason.value}"
                )
                if last_result:
                    return last_result
                if last_exception:
                    raise last_exception
                raise RuntimeError("Retry stopped by RetryPolicyEngine.")

            delay = decision.delay_seconds
            logger.info(
                f"RetryPolicyEngine decision: RETRY (attempt {attempt} -> {decision.next_attempt}, "
                f"delay {delay:.2f}s, reason {decision.reason.value})"
            )
            if on_retry_scheduled:
                on_retry_scheduled(
                    attempt,
                    decision.next_attempt,
                    delay,
                    decision.reason.value,
                    decision.failure_domain.value,
                )
            await asyncio.sleep(delay)
            attempt = decision.next_attempt

