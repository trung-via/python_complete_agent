from abc import ABC, abstractmethod
from typing import Any, Dict
from src.core.types import ToolCall, ToolResult

class BaseTool(ABC):
    """
    Abstract base class for all tools in the Agent system.
    Phase 1 Architecture standardizes how tools are executed and identified.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the tool (used by AI to select it)."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A brief description of what the tool does (used by AI context)."""
        pass

    @abstractmethod
    def get_schema(self) -> dict:
        """
        Returns the JSON schema defining the arguments this tool expects.
        Used by the AI Controller for Function Calling.
        """
        pass

    @abstractmethod
    async def execute(self, call: ToolCall, context: Dict[str, Any]) -> ToolResult:
        """
        Executes the tool's core logic.
        
        Args:
            call (ToolCall): The requested action and arguments from the AI.
            context (dict): The agent's context (e.g. holding references to gdrive, browser, etc.)
            
        Returns:
            ToolResult: The result of the execution.
        """
        pass
