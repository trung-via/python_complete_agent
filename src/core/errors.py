class AgentException(Exception):
    """Base exception for all agent-related errors."""
    pass

class ToolExecutionError(AgentException):
    """Raised when a tool fails to execute completely."""
    pass

class BrowserNavigationError(AgentException):
    """Raised when the browser fails to load or navigate to a target."""
    pass

class ExtractionError(AgentException):
    """Raised when data extraction from a page fails."""
    pass

class RateLimitError(AgentException):
    """Raised when the target service rate-limits the agent."""
    pass

class DependencyError(AgentException):
    """Raised when a required dependency (e.g., GDrive context) is missing."""
    pass
