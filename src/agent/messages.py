from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any

class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

@dataclass
class LLMMessage:
    """Represents a standardized message in the conversation history."""
    role: MessageRole
    content: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # We might also want to store tool calls that the assistant made in this message
    # if role == ASSISTANT
    tool_calls: list[dict] = field(default_factory=list)
