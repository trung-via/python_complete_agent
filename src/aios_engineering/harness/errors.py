"""AIOS Engineering Harness errors."""
from __future__ import annotations


class HarnessError(Exception):
    """Base exception for all AIOS Engineering Harness errors."""


class HarnessValidationError(HarnessError, ValueError):
    """Raised when an immutable harness contract fails validation."""


class HarnessFingerprintError(HarnessError, ValueError):
    """Raised when harness plan or candidate-set fingerprint fails verification."""
