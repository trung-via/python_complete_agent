import logging
from typing import Dict, Optional

from src.browser.manager import BrowserManager
from src.browser.session import BrowserSession
from src.browser.models import BrowserConfig
from src.integrations.playwright.session import PlaywrightBrowserSession

logger = logging.getLogger(__name__)

class PlaywrightBrowserManager(BrowserManager):
    def __init__(self):
        self._sessions: Dict[str, BrowserSession] = {}

    async def get_or_create_session(self, run_id: str, config: Optional[BrowserConfig] = None) -> BrowserSession:
        if run_id in self._sessions:
            session = self._sessions[run_id]
            # If crashed or closed, we might need to recreate, but for now just return it
            # The tool can handle throwing errors or the manager can do auto-recovery
            return session
            
        logger.info(f"Creating new PlaywrightBrowserSession for run {run_id}")
        config = config or BrowserConfig()
        session = PlaywrightBrowserSession(run_id, config)
        await session.start()
        self._sessions[run_id] = session
        return session
        
    async def close_session(self, run_id: str) -> None:
        if run_id in self._sessions:
            session = self._sessions[run_id]
            await session.close()
            del self._sessions[run_id]
            logger.info(f"Removed session for run {run_id}")
            
    async def close_all(self) -> None:
        logger.info(f"Closing all {len(self._sessions)} active browser sessions.")
        for run_id, session in list(self._sessions.items()):
            await session.close()
        self._sessions.clear()
