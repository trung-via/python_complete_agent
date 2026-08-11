from typing import Dict, List, Optional
import logging
from src.core.base_tool import BaseTool

logger = logging.getLogger(__name__)

class ToolRegistry:
    """
    Manages all available tools in the Agent system.
    Phase 1: Centralized registry.
    Phase 2: Can dump schema for AI Function Calling.
    """
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        
    def register_tool(self, tool: BaseTool):
        """Registers a tool instance."""
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' is being overwritten in the registry.")
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
        
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieves a tool by its name."""
        return self._tools.get(name)
        
    def get_all_tools(self) -> List[BaseTool]:
        """Returns all registered tools."""
        return list(self._tools.values())
        
    def get_tools_schema(self) -> List[dict]:
        """
        Returns a simplified schema of all tools.
        Used by the AI Controller to build Function Declarations.
        """
        schemas = []
        for tool in self._tools.values():
            schemas.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.get_schema()
            })
        return schemas
