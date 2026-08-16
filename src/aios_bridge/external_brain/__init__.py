"""AIOS Bridge External Brain subsystem contracts and boundaries."""
from __future__ import annotations

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
    ContractValidationError,
    CorrelationError,
    ExternalBrainError,
    OutputContractError,
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
    # Enums
    "ContextKind",
    "BrainRole",
    "BrainOperation",
    "BrainOutputType",
    "ModelResponseStatus",
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
]
