"""AIOS Bridge External Brain subsystem contracts and boundaries."""
from __future__ import annotations

from .budget import ContextBudget, TokenCounter, Utf8ByteConservativeCounter
from .context import (
    ContextBuilder,
    ContextBuildResult,
    ContextExclusion,
    ContextExclusionReason,
    render_context_item,
)
from .contracts import (
    OPERATION_OUTPUT_MAP,
    BrainOperation,
    BrainOutputType,
    BrainRole,
    ContextItem,
    ContextKind,
    ModelRequest,
    ModelResponse,
    ModelResponseStatus,
    get_expected_output_type,
    validate_request_response_correlation,
)
from .errors import (
    ContextBuildError,
    ContextIntegrityError,
    ContractValidationError,
    CorrelationError,
    ExternalBrainError,
    MandatoryContextBudgetError,
    MissingMandatoryContextError,
    OutputContractError,
    SensitiveContextError,
)
from .provider import ProviderAdapter
from .transport import ModelTransport, TransportRequest, TransportResult
from .validation import (
    ALLOWED_REVIEW_STATUSES,
    REQUIRED_SECTIONS,
    parse_artifact_sections,
    validate_artifact_structure,
)

__all__ = [
    # Errors
    "ExternalBrainError",
    "ContractValidationError",
    "CorrelationError",
    "OutputContractError",
    "ContextBuildError",
    "ContextIntegrityError",
    "SensitiveContextError",
    "MissingMandatoryContextError",
    "MandatoryContextBudgetError",
    # Enums
    "ContextKind",
    "BrainRole",
    "BrainOperation",
    "BrainOutputType",
    "ModelResponseStatus",
    "ContextExclusionReason",
    # Mappings & helpers
    "OPERATION_OUTPUT_MAP",
    "get_expected_output_type",
    "validate_request_response_correlation",
    # Contracts
    "ContextItem",
    "ModelRequest",
    "ModelResponse",
    # Provider protocol
    "ProviderAdapter",
    # Transport protocol & types
    "TransportRequest",
    "TransportResult",
    "ModelTransport",
    # Artifact validation
    "REQUIRED_SECTIONS",
    "ALLOWED_REVIEW_STATUSES",
    "parse_artifact_sections",
    "validate_artifact_structure",
    # Budget & Token Counter
    "TokenCounter",
    "Utf8ByteConservativeCounter",
    "ContextBudget",
    # Context Builder & Audit
    "ContextExclusion",
    "ContextBuildResult",
    "ContextBuilder",
    "render_context_item",
]
