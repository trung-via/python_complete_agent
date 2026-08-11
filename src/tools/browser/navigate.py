from typing import Optional, Dict, Any, Type
from pydantic import BaseModel, Field

from src.tools.browser.base import BaseBrowserTool
from src.browser.session import BrowserSession

class NavigateArgs(BaseModel):
    url: str = Field(..., description="The URL to navigate to. Must be a complete URL (e.g. 'https://example.com').")

class NavigateTool(BaseBrowserTool):
    @property
    def name(self) -> str:
        return "browser.navigate"
        
    @property
    def description(self) -> str:
        return "Navigate the browser to a specific URL."
        
    @property
    def retryable(self) -> bool:
        return True
        
    @property
    def idempotent(self) -> bool:
        return True

    def get_arguments_schema(self) -> Type[BaseModel]:
        return NavigateArgs

    async def execute_browser_action(self, session: BrowserSession, parsed_args: NavigateArgs) -> Optional[Dict[str, Any]]:
        await session.navigate(parsed_args.url)
        return {"url": parsed_args.url, "message": "Navigation successful"}
