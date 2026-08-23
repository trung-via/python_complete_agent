"""AIOS Engineering Harness foundation and local repository discovery."""
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
    RepositoryDiscoveryBoundError,
    RepositoryDiscoveryError,
    RepositoryDiscoveryGitError,
)
from src.aios_engineering.harness.discovery import (
    H1_DISCOVERY_POLICY_VERSION,
    MAX_DISCOVERY_ENTRIES,
    MAX_DISCOVERY_STREAM_BYTES,
    MAX_GIT_TREE_RECORD_BYTES,
    RepositoryDiscoveryExclusion,
    RepositoryDiscoveryResult,
    classify_evidence_kind,
    discover_repository_snapshot,
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
    "RepositoryDiscoveryBoundError",
    "RepositoryDiscoveryError",
    "RepositoryDiscoveryGitError",
    "H1_DISCOVERY_POLICY_VERSION",
    "MAX_DISCOVERY_ENTRIES",
    "MAX_DISCOVERY_STREAM_BYTES",
    "MAX_GIT_TREE_RECORD_BYTES",
    "RepositoryDiscoveryExclusion",
    "RepositoryDiscoveryResult",
    "classify_evidence_kind",
    "discover_repository_snapshot",
    "canonical_json_bytes",
    "compute_candidate_set_fingerprint",
    "compute_plan_fingerprint",
    "compute_sha256",
]
