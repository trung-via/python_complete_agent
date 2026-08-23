"""Immutable contracts for AIOS Engineering Harness Foundation (H0)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Sequence

from src.aios_engineering.harness.errors import HarnessFingerprintError, HarnessValidationError
from src.aios_engineering.harness.fingerprint import (
    compute_candidate_set_fingerprint,
    compute_plan_fingerprint,
)


MAX_SCHEMA_VERSION_LENGTH: int = 64
MAX_PATH_LENGTH: int = 1024
MAX_REASON_CODE_LENGTH: int = 64
MAX_SYMBOL_LOCATOR_LENGTH: int = 256
MAX_GENERATOR_VERSION_LENGTH: int = 64

_HEX_40_RE = re.compile(r"\A[0-9a-f]{40}\Z")
_HEX_64_RE = re.compile(r"\A[0-9a-f]{64}\Z")
_REASON_CODE_RE = re.compile(r"\A[A-Z0-9_:-]+\Z")


def _validate_task_id(val: Any) -> str:
    if not isinstance(val, str) or not val.startswith("TASK-"):
        raise HarnessValidationError(f"task_id must be canonical TASK-<positive digits>: got {val!r}")
    num_part = val[5:]
    if not num_part.isdigit() or int(num_part) <= 0:
        raise HarnessValidationError(f"task_id must be canonical TASK-<positive digits>: got {val!r}")
    return val


def _validate_hex_40(val: Any, field_name: str) -> str:
    if not isinstance(val, str) or not _HEX_40_RE.fullmatch(val):
        raise HarnessValidationError(f"{field_name} must be exact lowercase 40-hex SHA: got {val!r}")
    return val


def _validate_hex_64(val: Any, field_name: str) -> str:
    if not isinstance(val, str) or not _HEX_64_RE.fullmatch(val):
        raise HarnessValidationError(f"{field_name} must be exact lowercase 64-hex hash: got {val!r}")
    return val


def _validate_reason_code(val: Any, field_name: str = "reason_code") -> str:
    if not isinstance(val, str) or not _REASON_CODE_RE.fullmatch(val):
        raise HarnessValidationError(
            f"{field_name} must be non-empty uppercase ASCII token matching ^[A-Z0-9_:-]+$: got {val!r}"
        )
    if any(ord(c) < 32 or ord(c) == 127 for c in val):
        raise HarnessValidationError(f"{field_name} must not contain control characters: got {val!r}")
    if len(val) > MAX_REASON_CODE_LENGTH:
        raise HarnessValidationError(
            f"{field_name} length ({len(val)}) exceeds maximum allowed ({MAX_REASON_CODE_LENGTH})"
        )
    return val


def _validate_posix_path(val: Any) -> str:
    if not isinstance(val, str) or not val:
        raise HarnessValidationError(f"path must be non-empty string: got {val!r}")
    if len(val) > MAX_PATH_LENGTH:
        raise HarnessValidationError(f"path length ({len(val)}) exceeds maximum allowed ({MAX_PATH_LENGTH})")
    
    # Fail closed on backslashes or absolute indicators
    if chr(92) in val:
        raise HarnessValidationError(f"path must use POSIX forward slashes, backslash forbidden: {val!r}")
    if val.startswith("/") or (len(val) >= 2 and val[1] == ":"):
        raise HarnessValidationError(f"path must be repository-relative, absolute path forbidden: {val!r}")
    
    # Check control characters
    if any(ord(c) < 32 or ord(c) == 127 for c in val):
        raise HarnessValidationError(f"path must not contain control characters: {val!r}")
    
    segments = val.split("/")
    for seg in segments:
        if not seg:
            raise HarnessValidationError(f"path contains empty segment or trailing/leading slash: {val!r}")
        if seg == ".":
            raise HarnessValidationError(f"path contains invalid dot segment '.': {val!r}")
        if seg == "..":
            raise HarnessValidationError(f"path contains invalid parent traversal segment '..': {val!r}")
        if seg == ".git":
            raise HarnessValidationError(f"path must not reference .git namespace: {val!r}")
            
    return val


class EvidenceKind(str, Enum):
    """Explicit kind categorization for repository evidence."""
    SOURCE = "SOURCE"
    TEST = "TEST"
    DOCUMENTATION = "DOCUMENTATION"
    CONFIGURATION = "CONFIGURATION"
    CONTRACT = "CONTRACT"
    OTHER = "OTHER"


class HarnessExtensionPoint(str, Enum):
    """Explicit extension-point identities for future H-Series capabilities."""
    SKILL_COMPILER = "SKILL_COMPILER"
    SKILL_PRECEDENCE = "SKILL_PRECEDENCE"
    EXECUTOR_SPECIFIC_RENDERING = "EXECUTOR_SPECIFIC_RENDERING"


@dataclass(frozen=True)
class RepositorySnapshotRef:
    """Immutable exact Git repository snapshot binding."""
    repository_commit_sha: str
    repository_tree_sha: str
    schema_version: str = "1"

    def __post_init__(self) -> None:
        if not isinstance(self.schema_version, str) or not self.schema_version.strip():
            raise HarnessValidationError("schema_version must be a non-empty string")
        if len(self.schema_version) > MAX_SCHEMA_VERSION_LENGTH:
            raise HarnessValidationError(
                f"schema_version length ({len(self.schema_version)}) exceeds maximum allowed ({MAX_SCHEMA_VERSION_LENGTH})"
            )
        _validate_hex_40(self.repository_commit_sha, "repository_commit_sha")
        _validate_hex_40(self.repository_tree_sha, "repository_tree_sha")

    def to_dict(self) -> dict[str, str]:
        return {
            "repository_commit_sha": self.repository_commit_sha,
            "repository_tree_sha": self.repository_tree_sha,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class RepositoryEvidenceRef:
    """Immutable provenance-bearing repository evidence reference."""
    path: str
    blob_sha: str
    evidence_kind: EvidenceKind
    reason_code: str
    priority: int
    symbol_locator: str | None = None

    def __post_init__(self) -> None:
        _validate_posix_path(self.path)
        _validate_hex_40(self.blob_sha, "blob_sha")
        
        # Validate evidence_kind
        if not isinstance(self.evidence_kind, EvidenceKind):
            try:
                object.__setattr__(self, "evidence_kind", EvidenceKind(str(self.evidence_kind)))
            except ValueError:
                raise HarnessValidationError(f"Invalid evidence_kind: {self.evidence_kind!r}")
        
        _validate_reason_code(self.reason_code, "reason_code")
        
        # Priority must be exact int, not bool, in range 0..1000
        if type(self.priority) is not int:
            raise HarnessValidationError(f"priority must be an integer (bool forbidden): got {self.priority!r}")
        if not (0 <= self.priority <= 1000):
            raise HarnessValidationError(f"priority must be between 0 and 1000: got {self.priority}")
        
        # symbol_locator validation
        if self.symbol_locator is not None:
            if not isinstance(self.symbol_locator, str) or not self.symbol_locator.strip():
                raise HarnessValidationError("symbol_locator if provided must be a non-empty string")
            if len(self.symbol_locator) > MAX_SYMBOL_LOCATOR_LENGTH:
                raise HarnessValidationError(
                    f"symbol_locator length ({len(self.symbol_locator)}) exceeds maximum allowed ({MAX_SYMBOL_LOCATOR_LENGTH})"
                )
            if any(ord(c) < 32 or ord(c) == 127 for c in self.symbol_locator):
                raise HarnessValidationError("symbol_locator must not contain control characters")
            if self.symbol_locator.startswith("/") or chr(92) in self.symbol_locator or (len(self.symbol_locator) >= 2 and self.symbol_locator[1] == ":"):
                raise HarnessValidationError("symbol_locator must not have absolute path semantics")

    def to_dict(self) -> dict[str, Any]:
        return {
            "blob_sha": self.blob_sha,
            "evidence_kind": self.evidence_kind.value,
            "path": self.path,
            "priority": self.priority,
            "reason_code": self.reason_code,
            "symbol_locator": self.symbol_locator,
        }


@dataclass(frozen=True)
class HarnessEvidenceExclusion:
    """Immutable record for deterministic candidate exclusion."""
    evidence: RepositoryEvidenceRef
    reason_code: str

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, RepositoryEvidenceRef):
            raise HarnessValidationError(f"evidence must be RepositoryEvidenceRef: got {self.evidence!r}")
        _validate_reason_code(self.reason_code, "exclusion reason_code")

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence": self.evidence.to_dict(),
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True)
class HarnessIntelligencePlan:
    """Immutable advisory harness intelligence plan bound to a snapshot and task."""
    task_id: str
    snapshot: RepositorySnapshotRef
    selected_evidence: tuple[RepositoryEvidenceRef, ...]
    excluded_evidence: tuple[HarnessEvidenceExclusion, ...]
    candidate_set_fingerprint: str
    plan_fingerprint: str
    schema_version: str = "1"

    def __post_init__(self) -> None:
        if not isinstance(self.schema_version, str) or not self.schema_version.strip():
            raise HarnessValidationError("schema_version must be a non-empty string")
        if len(self.schema_version) > MAX_SCHEMA_VERSION_LENGTH:
            raise HarnessValidationError(
                f"schema_version length ({len(self.schema_version)}) exceeds maximum allowed ({MAX_SCHEMA_VERSION_LENGTH})"
            )
        _validate_task_id(self.task_id)
        if not isinstance(self.snapshot, RepositorySnapshotRef):
            raise HarnessValidationError(f"snapshot must be RepositorySnapshotRef: got {self.snapshot!r}")
        
        # Ensure tuples
        if not isinstance(self.selected_evidence, tuple):
            object.__setattr__(self, "selected_evidence", tuple(self.selected_evidence))
        if not isinstance(self.excluded_evidence, tuple):
            object.__setattr__(self, "excluded_evidence", tuple(self.excluded_evidence))
            
        for item in self.selected_evidence:
            if not isinstance(item, RepositoryEvidenceRef):
                raise HarnessValidationError(f"selected item must be RepositoryEvidenceRef: got {item!r}")
        for ex in self.excluded_evidence:
            if not isinstance(ex, HarnessEvidenceExclusion):
                raise HarnessValidationError(f"excluded item must be HarnessEvidenceExclusion: got {ex!r}")
        
        # Duplicate identity and conflict check
        seen_identities: set[tuple[Any, ...]] = set()
        seen_locators: dict[tuple[str, str | None], str] = {}
        
        all_items: list[tuple[str, RepositoryEvidenceRef]] = []
        for item in self.selected_evidence:
            all_items.append(("selected", item))
        for ex in self.excluded_evidence:
            all_items.append(("excluded", ex.evidence))
            
        for origin, ev in all_items:
            identity_key = (
                ev.path,
                ev.blob_sha,
                ev.evidence_kind.value,
                ev.reason_code,
                ev.priority,
                ev.symbol_locator,
            )
            if identity_key in seen_identities:
                raise HarnessValidationError(f"Duplicate exact evidence identity rejected: {ev.path} ({ev.blob_sha})")
            seen_identities.add(identity_key)
            
            locator_key = (ev.path, ev.symbol_locator)
            if locator_key in seen_locators:
                existing_blob = seen_locators[locator_key]
                if existing_blob != ev.blob_sha:
                    raise HarnessValidationError(
                        f"Conflicting blob SHA for same path/symbol {ev.path} ({ev.symbol_locator}): "
                        f"{existing_blob} != {ev.blob_sha}"
                    )
            else:
                seen_locators[locator_key] = ev.blob_sha
                
        # Validate and verify fingerprints
        _validate_hex_64(self.candidate_set_fingerprint, "candidate_set_fingerprint")
        _validate_hex_64(self.plan_fingerprint, "plan_fingerprint")
        
        expected_candidate_fp = compute_candidate_set_fingerprint(
            self.selected_evidence,
            self.excluded_evidence,
        )
        if self.candidate_set_fingerprint != expected_candidate_fp:
            raise HarnessFingerprintError(
                f"Candidate set fingerprint mismatch: expected {expected_candidate_fp}, got {self.candidate_set_fingerprint}"
            )
            
        expected_plan_fp = compute_plan_fingerprint(
            self.task_id,
            self.snapshot,
            self.selected_evidence,
            self.excluded_evidence,
            self.candidate_set_fingerprint,
            self.schema_version,
        )
        if self.plan_fingerprint != expected_plan_fp:
            raise HarnessFingerprintError(
                f"Plan fingerprint mismatch: expected {expected_plan_fp}, got {self.plan_fingerprint}"
            )

    @classmethod
    def create(
        cls,
        task_id: str,
        snapshot: RepositorySnapshotRef,
        selected_evidence: Sequence[RepositoryEvidenceRef],
        excluded_evidence: Sequence[HarnessEvidenceExclusion] = (),
        schema_version: str = "1",
    ) -> HarnessIntelligencePlan:
        """Pure factory constructing an immutable plan with deterministically verified fingerprints."""
        selected_tuple = tuple(selected_evidence)
        excluded_tuple = tuple(excluded_evidence)
        candidate_fp = compute_candidate_set_fingerprint(selected_tuple, excluded_tuple)
        plan_fp = compute_plan_fingerprint(
            task_id=task_id,
            snapshot=snapshot,
            selected_evidence=selected_tuple,
            excluded_evidence=excluded_tuple,
            candidate_set_fingerprint=candidate_fp,
            schema_version=schema_version,
        )
        return cls(
            task_id=task_id,
            snapshot=snapshot,
            selected_evidence=selected_tuple,
            excluded_evidence=excluded_tuple,
            candidate_set_fingerprint=candidate_fp,
            plan_fingerprint=plan_fp,
            schema_version=schema_version,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_set_fingerprint": self.candidate_set_fingerprint,
            "excluded_evidence": [ex.to_dict() for ex in self.excluded_evidence],
            "plan_fingerprint": self.plan_fingerprint,
            "schema_version": self.schema_version,
            "selected_evidence": [item.to_dict() for item in self.selected_evidence],
            "snapshot": self.snapshot.to_dict(),
            "task_id": self.task_id,
        }


@dataclass(frozen=True)
class HarnessReceipt:
    """Immutable safe local audit receipt proving zero execution authority and zero side effects."""
    task_id: str
    repository_commit_sha: str
    input_fingerprint: str
    output_fingerprint: str
    generator_version: str
    candidate_count: int
    selected_count: int
    excluded_count: int
    schema_version: str = "1"
    authority_created: bool = False
    network_used: bool = False
    llm_used: bool = False
    paid_api_used: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.schema_version, str) or not self.schema_version.strip():
            raise HarnessValidationError("schema_version must be a non-empty string")
        if len(self.schema_version) > MAX_SCHEMA_VERSION_LENGTH:
            raise HarnessValidationError(
                f"schema_version length ({len(self.schema_version)}) exceeds maximum allowed ({MAX_SCHEMA_VERSION_LENGTH})"
            )
        _validate_task_id(self.task_id)
        _validate_hex_40(self.repository_commit_sha, "repository_commit_sha")
        _validate_hex_64(self.input_fingerprint, "input_fingerprint")
        _validate_hex_64(self.output_fingerprint, "output_fingerprint")
        
        if not isinstance(self.generator_version, str) or not self.generator_version.strip():
            raise HarnessValidationError("generator_version must be a non-empty string")
        if len(self.generator_version) > MAX_GENERATOR_VERSION_LENGTH:
            raise HarnessValidationError(
                f"generator_version length ({len(self.generator_version)}) exceeds maximum allowed ({MAX_GENERATOR_VERSION_LENGTH})"
            )
            
        # Count validations
        for name, count_val in [
            ("candidate_count", self.candidate_count),
            ("selected_count", self.selected_count),
            ("excluded_count", self.excluded_count),
        ]:
            if type(count_val) is not int:
                raise HarnessValidationError(f"{name} must be an integer (bool forbidden): got {count_val!r}")
            if count_val < 0:
                raise HarnessValidationError(f"{name} must be non-negative: got {count_val}")
                
        if self.candidate_count != (self.selected_count + self.excluded_count):
            raise HarnessValidationError(
                f"candidate_count ({self.candidate_count}) must equal "
                f"selected_count ({self.selected_count}) + excluded_count ({self.excluded_count})"
            )
            
        # Strict zero-authority invariants
        if self.authority_created is not False:
            raise HarnessValidationError(f"authority_created must be False: got {self.authority_created!r}")
        if self.network_used is not False:
            raise HarnessValidationError(f"network_used must be False: got {self.network_used!r}")
        if self.llm_used is not False:
            raise HarnessValidationError(f"llm_used must be False: got {self.llm_used!r}")
        if self.paid_api_used is not False:
            raise HarnessValidationError(f"paid_api_used must be False: got {self.paid_api_used!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "authority_created": self.authority_created,
            "candidate_count": self.candidate_count,
            "excluded_count": self.excluded_count,
            "generator_version": self.generator_version,
            "input_fingerprint": self.input_fingerprint,
            "llm_used": self.llm_used,
            "network_used": self.network_used,
            "output_fingerprint": self.output_fingerprint,
            "paid_api_used": self.paid_api_used,
            "repository_commit_sha": self.repository_commit_sha,
            "schema_version": self.schema_version,
            "selected_count": self.selected_count,
            "task_id": self.task_id,
        }
