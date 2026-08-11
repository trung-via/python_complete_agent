from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List

class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

@dataclass
class AssistantToolCall:
    call_id: str
    name: str
    arguments: Dict[str, Any]

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
    tool_calls: List[AssistantToolCall] = field(default_factory=list)
