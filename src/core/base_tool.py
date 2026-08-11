from abc import ABC, abstractmethod
from typing import Any, Dict

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
    async def execute(self, url: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the tool's core logic.
        
        Args:
            url (str): The target URL to process.
            context (dict): The agent's context (e.g. holding references to gdrive, browser, etc.)
            
        Returns:
            dict: The result of the execution.
        """
        pass
