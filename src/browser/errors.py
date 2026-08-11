from src.core.errors import AgentException

class BrowserError(AgentException):
    """Base class for all browser-related errors."""
    def __init__(self, message: str, code: str = "BROWSER_ERROR", retryable: bool = False, details: dict = None):
        super().__init__(message, code=code, retryable=retryable, details=details)

class BrowserNotStartedError(BrowserError):
    def __init__(self, message: str = "Browser session is not started or is closed."):
        super().__init__(message, code="BROWSER_NOT_STARTED", retryable=False)

class NavigationError(BrowserError):
    def __init__(self, message: str, url: str):
        super().__init__(message, code="NAVIGATION_ERROR", retryable=True, details={"url": url})

class NavigationTimeoutError(NavigationError):
    def __init__(self, url: str):
        super().__init__(f"Timeout waiting for navigation to {url}", url=url)

class ElementNotFoundError(BrowserError):
    def __init__(self, message: str = "Element not found.", details: dict = None):
        super().__init__(message, code="ELEMENT_NOT_FOUND", retryable=True, details=details)

class ElementNotVisibleError(BrowserError):
    def __init__(self, message: str = "Element is present but not visible.", details: dict = None):
        super().__init__(message, code="ELEMENT_NOT_VISIBLE", retryable=True, details=details)

class ElementInteractionError(BrowserError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="ELEMENT_INTERACTION_ERROR", retryable=False, details=details)

class PageClosedError(BrowserError):
    def __init__(self, message: str = "Target page is already closed."):
        super().__init__(message, code="PAGE_CLOSED", retryable=False)

class BrowserContextError(BrowserError):
    def __init__(self, message: str = "Browser context is invalid or corrupted."):
        super().__init__(message, code="BROWSER_CONTEXT_ERROR", retryable=False)
