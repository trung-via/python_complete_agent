from typing import Optional, Dict, Any, Type
from pydantic import BaseModel, Field

from src.tools.browser.base import BaseBrowserTool
from src.browser.session import BrowserSession
from src.browser.models import LocatorSpec

class LocatorArgs(BaseModel):
    strategy: str = Field(..., description="The locator strategy: 'css', 'xpath', 'role', 'text'")
    value: str = Field(..., description="The value of the locator")
    name: Optional[str] = Field(None, description="Optional name (mainly for 'role' strategy)")

class ClickArgs(BaseModel):
    element_id: Optional[str] = Field(None, description="The ID of the element to click (obtained from browser.inspect)")
    locator: Optional[LocatorArgs] = Field(None, description="The locator of the element to click (if element_id is not used)")

class ClickTool(BaseBrowserTool):
    @property
    def name(self) -> str:
        return "browser.click"
        
    @property
    def description(self) -> str:
        return "Click on an element. Prefer using element_id if possible."
        
    @property
    def retryable(self) -> bool:
        # Clicks are not safely retryable by default as they may cause side-effects
        return False
        
    @property
    def idempotent(self) -> bool:
        return False

    def get_arguments_schema(self) -> Type[BaseModel]:
        return ClickArgs

    async def execute_browser_action(self, session: BrowserSession, parsed_args: ClickArgs) -> Optional[Dict[str, Any]]:
        if not parsed_args.element_id and not parsed_args.locator:
            raise ValueError("Must provide either element_id or locator")
            
        loc_spec = None
        if parsed_args.locator:
            loc_spec = LocatorSpec(
                strategy=parsed_args.locator.strategy,
                value=parsed_args.locator.value,
                name=parsed_args.locator.name
            )
            
        await session.click(element_id=parsed_args.element_id, locator=loc_spec)
        return {"message": "Click successful"}
