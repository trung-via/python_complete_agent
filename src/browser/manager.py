from typing import Protocol, Optional
from src.browser.session import BrowserSession
from src.browser.models import BrowserConfig

class BrowserManager(Protocol):
    """
    Manages the lifecycle of BrowserSessions for autonomous agent runs.
    Caches a session per run_id. Resource isolation depends on the implementation
    mode: launched contexts are isolated; CDP sessions may borrow the same page.
    """
    
    async def get_or_create_session(self, run_id: str, config: Optional[BrowserConfig] = None) -> BrowserSession:
        """
        Returns the existing session for the run_id. If none exists, creates and starts a new one.
        """
        ...
        
    async def close_session(self, run_id: str) -> None:
        """
        Closes and removes the session associated with the run_id.
        """
        ...
        
    async def close_all(self) -> None:
        """
        Closes all active sessions. Should be called during graceful shutdown.
        """
        ...
