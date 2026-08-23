"""AIOS Engineering Harness Foundation (H0)."""
from __future__ import annotations

from src.aios_engineering.harness.contracts import (
    EvidenceKind,
    HarnessEvidenceExclusion,
    HarnessExtensionPoint,
    HarnessIntelligencePlan,
    HarnessReceipt,
    RepositoryEvidenceRef,
    RepositorySnapshotRef,
)
from src.aios_engineering.harness.errors import (
    HarnessError,
    HarnessFingerprintError,
    HarnessValidationError,
)
from src.aios_engineering.harness.fingerprint import (
    canonical_json_bytes,
    compute_candidate_set_fingerprint,
    compute_plan_fingerprint,
    compute_sha256,
)

__all__ = [
    "EvidenceKind",
    "HarnessEvidenceExclusion",
    "HarnessExtensionPoint",
    "HarnessIntelligencePlan",
    "HarnessReceipt",
    "RepositoryEvidenceRef",
    "RepositorySnapshotRef",
    "HarnessError",
    "HarnessFingerprintError",
    "HarnessValidationError",
    "canonical_json_bytes",
    "compute_candidate_set_fingerprint",
    "compute_plan_fingerprint",
    "compute_sha256",
]
