import asyncio
import logging
from typing import Callable, Any
from src.core.errors import AgentException

logger = logging.getLogger(__name__)

class RetryManager:
    """
    Handles robust execution of tools with granular, policy-based retry logic.
    """
    def __init__(self, max_retries: int = 3, base_delay: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        
    async def execute_with_retry(self, operation: Callable, *args, **kwargs) -> Any:
        """
        Executes an asynchronous operation and retries it if a retryable error is returned.
        Returns the ToolResult of the operation.
        """
        from src.core.types import ToolResult, ToolStatus
        
        attempt = 1
        last_result = None
        
        while attempt <= self.max_retries:
            try:
                result = await operation(*args, **kwargs)
                
                if isinstance(result, ToolResult) and result.status == ToolStatus.FAILURE:
                    if result.error and result.error.retryable:
                        logger.warning(f"Operation failed with retryable error (Attempt {attempt}/{self.max_retries}): {result.error.code} - {result.error.message}")
                        last_result = result
                    else:
                        logger.error(f"Operation failed with non-retryable error: {result.error.message if result.error else 'Unknown'}")
                        return result
                else:
                    # Success or Partial Success
                    return result
                    
            except AgentException as e:
                if not e.retryable:
                    logger.error(f"Operation raised non-retryable AgentException: {e.code} - {e.message}")
                    raise
                logger.warning(f"Operation raised retryable AgentException (Attempt {attempt}/{self.max_retries}): {e.code} - {e.message}")
            except Exception as e:
                logger.error(f"Operation raised unexpected exception (Attempt {attempt}/{self.max_retries}): {e}")
                
            if attempt == self.max_retries:
                logger.error("All retries exhausted.")
                if last_result:
                    return last_result
                raise
                
            delay = self.base_delay * attempt
            logger.info(f"Waiting {delay}s before retrying...")
            await asyncio.sleep(delay)
            attempt += 1
