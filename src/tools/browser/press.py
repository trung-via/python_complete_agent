from typing import Optional, Dict, Any, Type
from pydantic import BaseModel, Field

from src.tools.browser.base import BaseBrowserTool
from src.browser.session import BrowserSession

class PressArgs(BaseModel):
    key: str = Field(..., description="The key to press (e.g. 'Enter', 'Escape', 'Tab', 'ArrowDown')")

class PressTool(BaseBrowserTool):
    @property
    def name(self) -> str:
        return "browser.press"
        
    @property
    def description(self) -> str:
        return "Press a specific keyboard key."
        
    @property
    def retryable(self) -> bool:
        return False
        
    @property
    def idempotent(self) -> bool:
        return False

    def get_arguments_schema(self) -> Type[BaseModel]:
        return PressArgs

    async def execute_browser_action(self, session: BrowserSession, parsed_args: PressArgs) -> Optional[Dict[str, Any]]:
        await session.press(parsed_args.key)
        return {"message": f"Pressed {parsed_args.key}"}
