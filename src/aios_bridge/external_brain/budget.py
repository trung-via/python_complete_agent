"""Token budget and counter contracts for AIOS Bridge External Brain."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .errors import ContractValidationError


class TokenCounter(Protocol):
    """
    Protocol for counting tokens or conservative token-equivalents for context budgeting.
    """

    @property
    def counter_id(self) -> str:
        """Stable, non-empty identifier for the counter strategy."""
        ...

    @property
    def is_exact(self) -> bool:
        """True if the counter represents an exact provider tokenizer count; False for conservative estimates."""
        ...

    def count(self, text: str) -> int:
        """Returns the token or byte count for the supplied text."""
        ...


class Utf8ByteConservativeCounter:
    """
    Default dependency-free conservative budgeting counter based on UTF-8 byte length.
    Not labeled as exact provider token usage.
    """

    @property
    def counter_id(self) -> str:
        return "utf8-byte-conservative-v1"

    @property
    def is_exact(self) -> bool:
        return False

    def count(self, text: str) -> int:
        return len(text.encode("utf-8"))


@dataclass(frozen=True)
class ContextBudget:
    """Immutable contract defining context token allocation and protocol reserves."""
    max_context_tokens: int
    protocol_reserve_tokens: int = 0

    def __post_init__(self) -> None:
        if isinstance(self.max_context_tokens, bool) or not isinstance(self.max_context_tokens, int) or self.max_context_tokens <= 0:
            raise ContractValidationError(
                f"max_context_tokens must be a positive integer, got: {self.max_context_tokens!r}"
            )

        if isinstance(self.protocol_reserve_tokens, bool) or not isinstance(self.protocol_reserve_tokens, int) or self.protocol_reserve_tokens < 0:
            raise ContractValidationError(
                f"protocol_reserve_tokens must be a non-negative integer, got: {self.protocol_reserve_tokens!r}"
            )

        if self.protocol_reserve_tokens >= self.max_context_tokens:
            raise ContractValidationError(
                f"protocol_reserve_tokens ({self.protocol_reserve_tokens}) must be strictly less than "
                f"max_context_tokens ({self.max_context_tokens})"
            )

    @property
    def available_context_tokens(self) -> int:
        """Available context budget after deducting protocol reserve tokens."""
        return self.max_context_tokens - self.protocol_reserve_tokens

    def to_dict(self) -> dict[str, Any]:
        """Deterministic JSON-serializable dictionary representation."""
        return {
            "max_context_tokens": self.max_context_tokens,
            "protocol_reserve_tokens": self.protocol_reserve_tokens,
            "available_context_tokens": self.available_context_tokens,
        }
