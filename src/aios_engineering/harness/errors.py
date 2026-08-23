"""AIOS Engineering Harness errors."""
from __future__ import annotations


class HarnessError(Exception):
    """Base exception for all AIOS Engineering Harness errors."""


class HarnessValidationError(HarnessError, ValueError):
    """Raised when an immutable harness contract fails validation."""


class HarnessFingerprintError(HarnessError, ValueError):
    """Raised when harness plan or candidate-set fingerprint fails verification."""


class RepositoryDiscoveryError(HarnessError):
    """Base error for deterministic local repository discovery failures."""


class RepositoryDiscoveryGitError(RepositoryDiscoveryError):
    """Raised when required local Git plumbing cannot produce an exact snapshot."""


class RepositoryDiscoveryBoundError(RepositoryDiscoveryError):
    """Raised when a hard repository discovery resource bound is exceeded."""
