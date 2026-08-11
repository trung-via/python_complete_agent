from typing import Protocol, List, Optional, Dict, Any
from dataclasses import dataclass, field
from src.agent.messages import LLMMessage

@dataclass
class ProviderToolCall:
    provider_call_id: str
    name: str
    arguments: Dict[str, Any]

@dataclass
class LLMResponse:
    provider: str
    provider_response_id: str
    content: Optional[str]
    tool_calls: List[ProviderToolCall] = field(default_factory=list)
    finish_reason: Optional[str] = None
    usage: Dict[str, Any] = field(default_factory=dict)

class LLMProvider(Protocol):
    async def generate(
        self,
        messages: List[LLMMessage],
        tools: List[dict],
    ) -> LLMResponse:
        """
        Generates a response from the LLM provider based on the unified message history and tool schemas.
        """
        ...
