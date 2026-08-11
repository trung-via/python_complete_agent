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
        Executes an asynchronous operation and retries it if a retryable exception is raised.
        Returns the result of the operation if successful.
        Raises the last exception if all retries are exhausted.
        """
        attempt = 1
        while attempt <= self.max_retries:
            try:
                return await operation(*args, **kwargs)
            except AgentException as e:
                if not e.retryable:
                    logger.error(f"Operation failed with non-retryable AgentException: {e.code} - {e.message}")
                    raise
                
                logger.warning(f"Operation failed with retryable AgentException (Attempt {attempt}/{self.max_retries}): {e.code} - {e.message}")
            except Exception as e:
                logger.error(f"Operation failed with unexpected exception (Attempt {attempt}/{self.max_retries}): {e}")
                
            if attempt == self.max_retries:
                logger.error("All retries exhausted.")
                raise
                
            delay = self.base_delay * attempt
            logger.info(f"Waiting {delay}s before retrying...")
            await asyncio.sleep(delay)
            attempt += 1
