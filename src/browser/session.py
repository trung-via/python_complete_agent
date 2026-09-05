from typing import Protocol, Optional, List, Dict, Any
from src.browser.models import BrowserState, LocatorSpec, BrowserElement


EVALUATE_ARG_UNSET = object()

class BrowserSession(Protocol):
    """
    Protocol defining the atomic browser capabilities exposed to the Agent.
    Implementations (e.g. PlaywrightBrowserSession) wrap the actual browser process.
    """
    
    @property
    def state(self) -> BrowserState:
        ...

    @property
    def run_id(self) -> str:
        ...

    async def start(self) -> None:
        """
        Starts the session.

        Launch mode creates an isolated browser context and default page. CDP mode
        may instead attach to a browser and borrow an existing context and page.
        """
        ...

    async def close(self) -> None:
        """Closes the browser session and frees all resources."""
        ...

    async def navigate(self, url: str) -> None:
        """Navigates the current page to a URL."""
        ...

    async def inspect(self) -> Dict[str, Any]:
        """
        Returns a structured representation of the current page,
        including URL, title, and a list of interactive elements (BrowserElement).
        """
        ...

    async def click(self, element_id: Optional[str] = None, locator: Optional[LocatorSpec] = None) -> None:
        """
        Clicks an element. Must provide either an element_id (from inspect) or a LocatorSpec.
        """
        ...

    async def type_text(self, text: str, element_id: Optional[str] = None, locator: Optional[LocatorSpec] = None) -> None:
        """
        Types text into an element.
        """
        ...
        
    async def press(self, key: str) -> None:
        """
        Presses a key (e.g., 'Enter', 'Escape') on the page.
        """
        ...

    async def screenshot(self) -> bytes:
        """
        Takes a screenshot of the current page and returns the raw image bytes.
        """
        ...

    async def evaluate(self, script: str, arg: Any = EVALUATE_ARG_UNSET) -> Any:
        """
        Evaluates JavaScript in the current page, optionally passing one argument.

        Omitting ``arg`` is distinct from explicitly passing ``None``.
        """
        ...
