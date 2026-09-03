import asyncio
import logging
from typing import Dict, Optional
from collections import defaultdict

from src.browser.manager import BrowserManager
from src.browser.session import BrowserSession
from src.browser.models import BrowserConfig, BrowserState
from src.browser.errors import BrowserSessionUnavailableError
from src.integrations.playwright.session import PlaywrightBrowserSession

logger = logging.getLogger(__name__)

class PlaywrightBrowserManager(BrowserManager):
    def __init__(self, cdp_endpoint: Optional[str] = None):
        # Mode belongs to the manager, not the per-session launch configuration.
        self._cdp_endpoint = cdp_endpoint
        self._sessions: Dict[str, BrowserSession] = {}
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def get_or_create_session(self, run_id: str, config: Optional[BrowserConfig] = None) -> BrowserSession:
        async with self._locks[run_id]:
            if run_id in self._sessions:
                session = self._sessions[run_id]
                if session.state in (BrowserState.CLOSED, BrowserState.CRASHED):
                    raise BrowserSessionUnavailableError(f"Session for run {run_id} is {session.state.value}.")
                return session
                
            logger.info(f"Creating new PlaywrightBrowserSession for run {run_id}")
            config = config or BrowserConfig()
            session = PlaywrightBrowserSession(run_id, config, cdp_endpoint=self._cdp_endpoint)
            await session.start()
            self._sessions[run_id] = session
            return session
        
    async def close_session(self, run_id: str) -> None:
        async with self._locks[run_id]:
            if run_id in self._sessions:
                session = self._sessions[run_id]
                await session.close()
                del self._sessions[run_id]
                logger.info(f"Removed session for run {run_id}")
            
    async def close_all(self) -> None:
        logger.info(f"Closing all {len(self._sessions)} active browser sessions.")
        for run_id in list(self._sessions):
            await self.close_session(run_id)
