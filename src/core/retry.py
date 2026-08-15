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
        if error and error.code in ("RATE_LIMIT", "RATE_LIMIT_ERROR") and error.details:
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
        on_attempt_start: Optional[Callable[[int], None]] = None,
        on_retry_scheduled: Optional[Callable[[int, int, float, str, str], None]] = None,
        **kwargs
    ) -> Any:
        """
        Executes an asynchronous operation and retries it if a retryable error is returned.
        Returns the ToolResult of the operation.
        """
        from src.core.types import ToolResult, ToolStatus
        from src.core.retry_policy import (
            FailureClassifier,
            RetryContext,
            RetryOperation,
            RetryPolicyEngine,
        )
        
        attempt = 1
        
        while attempt <= self.policy.max_attempts:
            if on_attempt_start:
                on_attempt_start(attempt)

            current_result: Optional[ToolResult] = None
            current_exception: Optional[Exception] = None
            target_err: Any = None

            try:
                result = await operation(*args, **kwargs)
                
                if isinstance(result, ToolResult) and result.status == ToolStatus.FAILURE:
                    current_result = result
                    target_err = result.error
                    if on_attempt_complete:
                        status_str = (
                            "FAILURE"
                            if (result.error and result.error.retryable)
                            else "FATAL_FAILURE"
                        )
                        err_msg = (
                            result.error.message
                            if result.error
                            else "Unknown tool failure"
                        )
                        on_attempt_complete(attempt, status_str, err_msg)
                else:
                    # Success or Partial Success
                    if on_attempt_complete:
                        status_str = result.status.value if isinstance(result, ToolResult) else "SUCCESS"
                        on_attempt_complete(attempt, status_str, None)
                    return result
                    
            except AgentException as e:
                current_exception = e
                target_err = e
                if on_attempt_complete:
                    status_str = "EXCEPTION" if e.retryable else "FATAL_EXCEPTION"
                    on_attempt_complete(attempt, status_str, e.message)
            except Exception as e:
                current_exception = e
                target_err = e
                if on_attempt_complete:
                    on_attempt_complete(attempt, "UNEXPECTED_EXCEPTION", str(e))
                
            failure_domain, is_transient, err_code = FailureClassifier.classify(
                target_err, operation=RetryOperation.TOOL
            )

            ctx = RetryContext(
                operation=RetryOperation.TOOL,
                attempt=attempt,
                max_attempts=self.policy.max_attempts,
                failure_domain=failure_domain,
                error_code=err_code,
                transient=is_transient,
            )

            decision = RetryPolicyEngine.decide(
                ctx,
                base_delay=self.policy.base_delay,
                max_delay=self.policy.max_delay,
            )

            if not decision.should_retry:
                logger.info(
                    f"RetryPolicyEngine decided to STOP retry (attempt {attempt}/{self.policy.max_attempts}): "
                    f"reason={decision.reason.value}"
                )
                if current_exception is not None:
                    raise current_exception
                if current_result is not None:
                    return current_result
                raise RuntimeError("Retry stopped by RetryPolicyEngine.")

            delay = self.policy.get_delay(
                attempt,
                target_err if isinstance(target_err, AgentException) else None,
            )

            if on_retry_scheduled:
                on_retry_scheduled(
                    attempt,
                    decision.next_attempt,
                    delay,
                    decision.reason.value,
                    failure_domain.value,
                )

            logger.info(
                f"RetryPolicyEngine decision: RETRY (attempt {attempt} -> {decision.next_attempt}, "
                f"delay {delay:.2f}s, reason {decision.reason.value})"
            )
            await asyncio.sleep(delay)
            attempt = decision.next_attempt
