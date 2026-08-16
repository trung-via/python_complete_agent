"""Exception taxonomy for AIOS Continuity State contracts."""
from __future__ import annotations


class ContinuityError(Exception):
    """Base exception for all AIOS Continuity State errors."""


class ContinuityStateValidationError(ContinuityError):
    """Raised when Continuity State fails schema, type, semantic, or boundary validation."""


class ContinuityFreshnessError(ContinuityError):
    """Raised on invalid freshness observation parameters."""
