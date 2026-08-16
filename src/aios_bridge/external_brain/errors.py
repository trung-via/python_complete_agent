"""Error taxonomy for AIOS Bridge External Brain contracts."""
from __future__ import annotations


class ExternalBrainError(Exception):
    """Base exception for all External Brain contract and boundary errors."""


class ContractValidationError(ExternalBrainError):
    """Raised when an External Brain data contract or field constraint is violated."""


class CorrelationError(ExternalBrainError):
    """Raised when a ModelResponse does not correlate to the associated ModelRequest."""


class OutputContractError(ExternalBrainError):
    """Raised when an output artifact structure violates required section/format rules."""
