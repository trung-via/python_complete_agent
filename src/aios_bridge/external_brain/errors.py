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


class ContextBuildError(ExternalBrainError):
    """Base exception for context construction, integrity, and safety errors."""


class ContextIntegrityError(ContextBuildError):
    """Raised when a ContextItem's content_sha256 does not match its computed SHA-256 digest."""


class SensitiveContextError(ContextBuildError):
    """Raised when a sensitive file path or secret-bearing content is detected in context candidates."""


class MissingMandatoryContextError(ContextBuildError):
    """Raised when no mandatory TASK context items are present."""


class MandatoryContextBudgetError(ContextBuildError):
    """Raised when mandatory context items exceed the available context token budget."""
