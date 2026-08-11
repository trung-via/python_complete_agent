from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum

class BrowserState(str, Enum):
    UNINITIALIZED = "UNINITIALIZED"
    STARTING = "STARTING"
    READY = "READY"
    BUSY = "BUSY"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"
    CRASHED = "CRASHED"

@dataclass
class BrowserConfig:
    browser_type: str = "chromium"
    headless: bool = True
    timeout_seconds: int = 30
    viewport_width: int = 1280
    viewport_height: int = 720
    executable_path: Optional[str] = None
    user_agent: Optional[str] = None

@dataclass
class LocatorSpec:
    """
    Abstractions for finding elements.
    Strategy can be: 'css', 'xpath', 'role', 'text', 'test-id', 'label'
    """
    strategy: str
    value: str
    name: Optional[str] = None  # Mainly used with 'role' strategy (e.g. role="button", name="Submit")

@dataclass
class BrowserElement:
    """
    A stable reference to an element on a page, abstracting away the underlying playwright locator.
    element_id should be scoped like: run_id/page_id/e17
    """
    element_id: str
    role: Optional[str] = None
    name: Optional[str] = None
    visible_text: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
