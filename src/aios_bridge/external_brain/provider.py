"""Provider protocol definition for AIOS Bridge External Brain."""
from __future__ import annotations

from typing import Protocol

from .contracts import ModelRequest, ModelResponse


class ProviderAdapter(Protocol):
    """
    Protocol for External Brain provider adapters.
    External Brain providers are stateless reasoning/code-generation proposal engines.
    They have NO filesystem, shell, browser, Git, or tool execution authority.
    """

    @property
    def provider_id(self) -> str:
        """Unique identifier for this provider (e.g. 'minimax', 'deepseek', 'kimi')."""
        ...

    async def invoke(self, request: ModelRequest) -> ModelResponse:
        """Invokes the external model with the given immutable ModelRequest and returns ModelResponse."""
        ...
