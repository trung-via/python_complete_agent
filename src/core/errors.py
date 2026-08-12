class AgentException(Exception):
    """Base exception for all agent-related errors."""
    def __init__(self, message: str, code: str, retryable: bool = False, details: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable
        self.details = details or {}

class ToolExecutionError(AgentException):
    """Raised when a tool fails to execute completely."""
    def __init__(self, message: str, retryable: bool = False, details: dict = None):
        super().__init__(message, code="TOOL_EXECUTION_ERROR", retryable=retryable, details=details)

class BrowserNavigationError(AgentException):
    """Raised when the browser fails to load or navigate to a target."""
    def __init__(self, message: str, retryable: bool = True, details: dict = None):
        super().__init__(message, code="BROWSER_NAVIGATION_ERROR", retryable=retryable, details=details)

class ExtractionError(AgentException):
    """Raised when data extraction from the DOM fails or returns empty."""
    def __init__(self, message: str, details: dict = None, retryable: bool = True):
        super().__init__(message, code="EXTRACTION_ERROR", retryable=retryable, details=details)

class SystemStateError(Exception):
    """Raised when a critical system state component (e.g., Checkpoint, IdempotencyStore) fails unrecoverably."""
    pass

class RateLimitError(AgentException):
    """Raised when the target service rate-limits the agent."""
    def __init__(self, message: str, retryable: bool = True, details: dict = None):
        super().__init__(message, code="RATE_LIMIT_ERROR", retryable=retryable, details=details)

class DependencyError(AgentException):
    """Raised when a required dependency (e.g., GDrive context) is missing."""
    def __init__(self, message: str, retryable: bool = False, details: dict = None):
        super().__init__(message, code="DEPENDENCY_ERROR", retryable=retryable, details=details)
