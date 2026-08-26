from abc import ABC, abstractmethod
from typing import Dict, Any, Type, Optional
from pydantic import BaseModel

from src.core.types import ToolResult, ToolStatus, ToolCall
from src.core.base_tool import BaseTool
from src.core.errors import SystemStateError
from src.browser.manager import BrowserManager
from src.browser.errors import BrowserError

class BaseBrowserTool(BaseTool, ABC):
    """
    Base class for all Browser Tools.
    Handles acquiring the BrowserSession and mapping BrowserError to ToolStatus.FAILURE.
    """
    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
        
    def get_schema(self) -> dict:
        return self.get_arguments_schema().model_json_schema()
        
    async def execute(self, call: ToolCall, context: Dict[str, Any]) -> ToolResult:
        session = await self.browser_manager.get_or_create_session(call.run_id)
        
        try:
            # Parse arguments
            schema_model = self.get_arguments_schema()
            parsed_args = schema_model.model_validate(call.arguments)
            
            # Execute concrete tool logic
            data = await self.execute_browser_action(session, parsed_args)
            return ToolResult(
                call_id=call.call_id,
                run_id=call.run_id,
                tool_name=call.name,
                status=ToolStatus.SUCCESS,
                data=data or {}
            )
        except BrowserError as e:
            return ToolResult(
                call_id=call.call_id,
                run_id=call.run_id,
                tool_name=call.name,
                status=ToolStatus.FAILURE,
                data={"error": e.message, "details": e.details},
                error=e
            )
        except Exception as e:
            raise SystemStateError(f"Unexpected error in {self.name}: {e}")

    @abstractmethod
    def get_arguments_schema(self) -> Type[BaseModel]:
        pass

    @abstractmethod
    async def execute_browser_action(self, session, parsed_args: BaseModel) -> Optional[Dict[str, Any]]:
        """Implementation for the specific browser action."""
        pass
