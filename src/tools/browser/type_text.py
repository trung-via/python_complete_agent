from typing import Optional, Dict, Any, Type
from pydantic import BaseModel, Field

from src.tools.browser.base import BaseBrowserTool
from src.tools.browser.click import LocatorArgs
from src.browser.session import BrowserSession
from src.browser.models import LocatorSpec

class TypeTextArgs(BaseModel):
    text: str = Field(..., description="The text to type")
    element_id: Optional[str] = Field(None, description="The ID of the element to type into")
    locator: Optional[LocatorArgs] = Field(None, description="The locator of the element")

class TypeTextTool(BaseBrowserTool):
    @property
    def name(self) -> str:
        return "browser.type"
        
    @property
    def description(self) -> str:
        return "Type text into an input element."
        
    @property
    def retryable(self) -> bool:
        return False
        
    @property
    def idempotent(self) -> bool:
        return False

    def get_arguments_schema(self) -> Type[BaseModel]:
        return TypeTextArgs

    async def execute_browser_action(self, session: BrowserSession, parsed_args: TypeTextArgs) -> Optional[Dict[str, Any]]:
        if not parsed_args.element_id and not parsed_args.locator:
            raise ValueError("Must provide either element_id or locator")
            
        loc_spec = None
        if parsed_args.locator:
            loc_spec = LocatorSpec(
                strategy=parsed_args.locator.strategy,
                value=parsed_args.locator.value,
                name=parsed_args.locator.name
            )
            
        await session.type_text(text=parsed_args.text, element_id=parsed_args.element_id, locator=loc_spec)
        return {"message": "Text typed successfully"}
