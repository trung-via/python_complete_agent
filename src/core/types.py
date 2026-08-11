from dataclasses import dataclass, field
from typing import Any, Dict, Optional

@dataclass
class ToolCall:
    """Represents a request to execute a specific tool with arguments."""
    name: str
    arguments: Dict[str, Any]
    call_id: Optional[str] = None
    
@dataclass
class ToolResult:
    """Represents the standardized output of a tool execution."""
    is_success: bool
    is_partial_success: bool = False
    data: Optional[Any] = None
    error_message: Optional[str] = None
    logs: list[str] = field(default_factory=list)
