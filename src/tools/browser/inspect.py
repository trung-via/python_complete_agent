from typing import Optional, Dict, Any, Type
from pydantic import BaseModel

from src.tools.browser.base import BaseBrowserTool
from src.browser.session import BrowserSession

class InspectArgs(BaseModel):
    pass

class InspectTool(BaseBrowserTool):
    @property
    def name(self) -> str:
        return "browser.inspect"
        
    @property
    def description(self) -> str:
        return "Inspect the current page to retrieve its title, URL, and a list of interactive elements (with element_id)."
        
    @property
    def retryable(self) -> bool:
        return True
        
    @property
    def idempotent(self) -> bool:
        return True

    def get_arguments_schema(self) -> Type[BaseModel]:
        return InspectArgs

    async def execute_browser_action(self, session: BrowserSession, parsed_args: InspectArgs) -> Optional[Dict[str, Any]]:
        data = await session.inspect()
        return data
