"""Canonical bounded H2 structural and engineering-experience graph composition."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any, BinaryIO, Sequence

from src.aios_engineering.harness.contracts import (
    HarnessReceipt,
    RepositorySnapshotRef,
    _validate_hex_40,
    _validate_hex_64,
    _validate_posix_path,
    _validate_task_id,
)
from src.aios_engineering.harness.discovery import RepositoryDiscoveryResult
from src.aios_engineering.harness.errors import (
    HarnessError,
    HarnessFingerprintError,
    HarnessValidationError,
)
from src.aios_engineering.harness.experience import (
    ControlPlaneSnapshotRef,
    ExperienceArtifactKind,
    ExperienceArtifactRef,
    ExperienceSurface,
    RepositoryExperienceManifest,
)
from src.aios_engineering.harness.fingerprint import canonical_json_bytes, compute_sha256
from src.aios_engineering.harness.graph import (
    ImportResolutionStatus,
    RepositoryDependencyGraphResult,
    RepositoryImportDependency,
)
from src.aios_engineering.harness.ranking import RepositoryRankingResult
from src.aios_engineering.harness.roles import (
    PythonSymbolKind,
    PythonSymbolSummary,
    RepositoryRoleSummaryResult,
)


H2_STRUCTURAL_EXPERIENCE_GRAPH_POLICY_VERSION: str = "h2-structural-experience-v1"
STRUCTURAL_EXPERIENCE_GRAPH_SCHEMA_VERSION: str = "1"

# All graph, parser, body, and serialization surfaces are finite.
MAX_H2_GRAPH_COMPONENTS: int = 512
MAX_H2_GRAPH_SYMBOLS: int = 4096
MAX_H2_GRAPH_STRUCTURAL_EDGES: int = 16_384
MAX_H2_GRAPH_EXPERIENCE_ARTIFACTS: int = 4096
MAX_H2_GRAPH_EXPERIENCE_BLOB_BYTES: int = 512 * 1024
MAX_H2_GRAPH_TOTAL_EXPERIENCE_BYTES: int = 16 * 1024 * 1024
MAX_H2_GRAPH_TASKS: int = 4096
MAX_H2_GRAPH_REVIEW_FINDINGS: int = 8192
MAX_H2_GRAPH_EXECUTORS: int = 256
MAX_H2_GRAPH_INVARIANTS: int = 4096
MAX_H2_GRAPH_EXPERIENCE_EDGES: int = 32_768
MAX_H2_GRAPH_UNRESOLVED_RECORDS: int = 16_384
MAX_H2_GRAPH_MACHINE_MARKER_BYTES: int = 64 * 1024
MAX_H2_GRAPH_FINGERPRINT_PAYLOAD_BYTES: int = 64 * 1024 * 1024
MAX_H2_GRAPH_GIT_SCALAR_BYTES: int = 4096

_GIT_READ_CHUNK_BYTES: int = 64 * 1024
_MAX_GRAPH_TEXT: int = 4096
_MAX_INVARIANT_ID: int = 128
_MAX_EXECUTOR_ID: int = 64
_MAX_FINDING_TITLE: int = 256
_DECIMAL_BYTES_RE = re.compile(rb"\A(?:0|[1-9][0-9]*)\Z")
_TASK_PATH_RE = re.compile(r"\A\.ai/tasks/TASK-([0-9]+)\.md\Z")
_RESULT_PATH_RE = re.compile(r"\A\.ai/results/RESULT-([0-9]+)\.md\Z")
_REVIEW_PATH_RE = re.compile(r"\A\.ai/reviews/REVIEW-([0-9]+)\.md\Z")
_TASK_ID_RE = re.compile(r"\ATASK-([0-9]+)\Z")
_EXECUTOR_RE = re.compile(r"\A[a-z][a-z0-9_-]{0,63}\Z", re.ASCII)
_INVARIANT_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z", re.ASCII)
_FINDING_HEADING_RE = re.compile(
    r"^###\s+(B[1-9][0-9]*)\s+(?:—|-)\s+([^\r\n]+?)\s*$",
    re.MULTILINE,
)
_REVIEW_MANIFEST_RE = re.compile(
    r"^## Review Manifest[ \t]*\n(?:[ \t]*\n)*```[^\r\n]*\n(.*?)^```[ \t]*$",
    re.MULTILINE | re.DOTALL,
)

_GIT_CHILD_ENVIRONMENT_ALLOWLIST: tuple[str, ...] = (
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "WINDIR",
    "TEMP",
    "TMP",
    "TMPDIR",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
)


class RepositoryStructuralExperienceGraphError(HarnessError):
    """Base error for canonical H2 graph construction."""


class RepositoryStructuralExperienceGraphGitError(RepositoryStructuralExperienceGraphError):
    """An exact local Git object or snapshot could not be verified."""


class RepositoryStructuralExperienceGraphBoundError(RepositoryStructuralExperienceGraphError):
    """A canonical H2 graph hard bound was exceeded."""


class RepositoryStructuralExperienceGraphConsistencyError(
    RepositoryStructuralExperienceGraphError
):
    """Contradictory upstream or explicit machine evidence was supplied."""


class StructuralComponentKind(str, Enum):
    PYTHON_PACKAGE = "PYTHON_PACKAGE"
    STANDALONE_PYTHON_MODULE = "STANDALONE_PYTHON_MODULE"


class H2GraphNodeKind(str, Enum):
    FILE = "FILE"
    SYMBOL = "SYMBOL"
    COMPONENT = "COMPONENT"
    TASK = "TASK"
    REVIEW_FINDING = "REVIEW_FINDING"
    EXECUTOR = "EXECUTOR"
    INVARIANT = "INVARIANT"


class H2GraphRelation(str, Enum):
    CONTAINS_SYMBOL = "CONTAINS_SYMBOL"
    BELONGS_TO_COMPONENT = "BELONGS_TO_COMPONENT"
    FILE_BELONGS_TO_COMPONENT = "FILE_BELONGS_TO_COMPONENT"
    COMPONENT_IMPORTS_COMPONENT = "COMPONENT_IMPORTS_COMPONENT"
    TASK_TOUCHES_COMPONENT = "TASK_TOUCHES_COMPONENT"
    TASK_EXECUTED_BY_EXECUTOR = "TASK_EXECUTED_BY_EXECUTOR"
    TASK_HAS_REVIEW_FINDING = "TASK_HAS_REVIEW_FINDING"
    REVIEW_FINDING_RELATES_TO_COMPONENT = "REVIEW_FINDING_RELATES_TO_COMPONENT"
    TASK_REFERENCES_INVARIANT = "TASK_REFERENCES_INVARIANT"
    INVARIANT_RELATES_TO_COMPONENT = "INVARIANT_RELATES_TO_COMPONENT"


class H2ExperienceParseStatus(str, Enum):
    PARSED = "PARSED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NO_MACHINE_EVIDENCE = "NO_MACHINE_EVIDENCE"
    PATH_NOT_IN_STRUCTURAL_GRAPH = "PATH_NOT_IN_STRUCTURAL_GRAPH"
    MALFORMED_MACHINE_EVIDENCE = "MALFORMED_MACHINE_EVIDENCE"
    TASK_ID_MISMATCH = "TASK_ID_MISMATCH"
    AMBIGUOUS_COMPONENT = "AMBIGUOUS_COMPONENT"
    BODY_BOUND_EXCEEDED = "BODY_BOUND_EXCEEDED"
    UNSUPPORTED_ARTIFACT_KIND = "UNSUPPORTED_ARTIFACT_KIND"


def _bounded_text(value: Any, field_name: str, maximum: int = _MAX_GRAPH_TEXT) -> str:
    if type(value) is not str or not value:
        raise HarnessValidationError(f"{field_name} must be an exact non-empty string")
    if len(value) > maximum:
        raise RepositoryStructuralExperienceGraphBoundError(
            f"{field_name} length exceeds hard limit ({maximum})"
        )
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise HarnessValidationError(f"{field_name} must not contain control characters")
    return value


def _bounded_fingerprint(payload: Any) -> str:
    encoded = canonical_json_bytes(payload)
    if len(encoded) > MAX_H2_GRAPH_FINGERPRINT_PAYLOAD_BYTES:
        raise RepositoryStructuralExperienceGraphBoundError(
            "canonical graph fingerprint payload exceeds hard limit "
            f"({MAX_H2_GRAPH_FINGERPRINT_PAYLOAD_BYTES})"
        )
    return compute_sha256(encoded)


def _component_payload(kind: StructuralComponentKind, path: str) -> dict[str, str]:
    return {"kind": kind.value, "path": path, "policy_version": H2_STRUCTURAL_EXPERIENCE_GRAPH_POLICY_VERSION}


@dataclass(frozen=True)
class StructuralComponent:
    component_id: str
    kind: StructuralComponentKind
    path: str
    component_fingerprint: str

    def __post_init__(self) -> None:
        if type(self.kind) is not StructuralComponentKind:
            raise HarnessValidationError("kind must be an exact StructuralComponentKind")
        _validate_posix_path(self.path)
        expected_id = f"component:{self.kind.value}:{self.path}"
        if self.component_id != expected_id:
            raise HarnessValidationError("component_id does not match canonical kind/path identity")
        _validate_hex_64(self.component_fingerprint, "component_fingerprint")
        expected = _bounded_fingerprint(_component_payload(self.kind, self.path))
        if self.component_fingerprint != expected:
            raise HarnessFingerprintError("structural component fingerprint mismatch")

    @classmethod
    def create(cls, kind: StructuralComponentKind, path: str) -> "StructuralComponent":
        _validate_posix_path(path)
        return cls(
            component_id=f"component:{kind.value}:{path}",
            kind=kind,
            path=path,
            component_fingerprint=_bounded_fingerprint(_component_payload(kind, path)),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "component_fingerprint": self.component_fingerprint,
            "component_id": self.component_id,
            "kind": self.kind.value,
            "path": self.path,
        }


def _symbol_payload(
    *,
    file_path: str,
    blob_sha: str,
    kind: PythonSymbolKind,
    name: str,
    line_number: int,
    symbol_locator: str,
) -> dict[str, Any]:
    return {
        "blob_sha": blob_sha,
        "file_path": file_path,
        "kind": kind.value,
        "line_number": line_number,
        "name": name,
        "policy_version": H2_STRUCTURAL_EXPERIENCE_GRAPH_POLICY_VERSION,
        "symbol_locator": symbol_locator,
    }


@dataclass(frozen=True)
class StructuralSymbolRef:
    symbol_id: str
    file_path: str
    blob_sha: str
    kind: PythonSymbolKind
    name: str
    line_number: int
    symbol_locator: str
    symbol_fingerprint: str

    def __post_init__(self) -> None:
        _validate_posix_path(self.file_path)
        _validate_hex_40(self.blob_sha, "blob_sha")
        PythonSymbolSummary(
            kind=self.kind,
            name=self.name,
            line_number=self.line_number,
            symbol_locator=self.symbol_locator,
        )
        expected_id = f"symbol:{self.file_path}:{self.blob_sha}:{self.symbol_locator}"
        if self.symbol_id != expected_id:
            raise HarnessValidationError("symbol_id does not match exact file/blob/locator identity")
        _validate_hex_64(self.symbol_fingerprint, "symbol_fingerprint")
        expected = _bounded_fingerprint(
            _symbol_payload(
                file_path=self.file_path,
                blob_sha=self.blob_sha,
                kind=self.kind,
                name=self.name,
                line_number=self.line_number,
                symbol_locator=self.symbol_locator,
            )
        )
        if self.symbol_fingerprint != expected:
            raise HarnessFingerprintError("structural symbol fingerprint mismatch")

    @classmethod
    def create(
        cls, file_path: str, blob_sha: str, symbol: PythonSymbolSummary
    ) -> "StructuralSymbolRef":
        payload = _symbol_payload(
            file_path=file_path,
            blob_sha=blob_sha,
            kind=symbol.kind,
            name=symbol.name,
            line_number=symbol.line_number,
            symbol_locator=symbol.symbol_locator,
        )
        return cls(
            symbol_id=f"symbol:{file_path}:{blob_sha}:{symbol.symbol_locator}",
            file_path=file_path,
            blob_sha=blob_sha,
            kind=symbol.kind,
            name=symbol.name,
            line_number=symbol.line_number,
            symbol_locator=symbol.symbol_locator,
            symbol_fingerprint=_bounded_fingerprint(payload),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **_symbol_payload(
                file_path=self.file_path,
                blob_sha=self.blob_sha,
                kind=self.kind,
                name=self.name,
                line_number=self.line_number,
                symbol_locator=self.symbol_locator,
            ),
            "symbol_fingerprint": self.symbol_fingerprint,
            "symbol_id": self.symbol_id,
        }


def _node_payload(
    kind: H2GraphNodeKind, node_id: str, identity: str, evidence_fingerprint: str
) -> dict[str, str]:
    return {
        "evidence_fingerprint": evidence_fingerprint,
        "identity": identity,
        "kind": kind.value,
        "node_id": node_id,
        "policy_version": H2_STRUCTURAL_EXPERIENCE_GRAPH_POLICY_VERSION,
    }


@dataclass(frozen=True)
class H2GraphNode:
    node_id: str
    kind: H2GraphNodeKind
    identity: str
    evidence_fingerprint: str
    node_fingerprint: str

    def __post_init__(self) -> None:
        if type(self.kind) is not H2GraphNodeKind:
            raise HarnessValidationError("kind must be an exact H2GraphNodeKind")
        _bounded_text(self.node_id, "node_id")
        _bounded_text(self.identity, "identity")
        _validate_hex_64(self.evidence_fingerprint, "evidence_fingerprint")
        _validate_hex_64(self.node_fingerprint, "node_fingerprint")
        expected = _bounded_fingerprint(
            _node_payload(self.kind, self.node_id, self.identity, self.evidence_fingerprint)
        )
        if self.node_fingerprint != expected:
            raise HarnessFingerprintError("H2 graph node fingerprint mismatch")

    @classmethod
    def create(
        cls,
        *,
        node_id: str,
        kind: H2GraphNodeKind,
        identity: str,
        evidence_fingerprint: str,
    ) -> "H2GraphNode":
        return cls(
            node_id=node_id,
            kind=kind,
            identity=identity,
            evidence_fingerprint=evidence_fingerprint,
            node_fingerprint=_bounded_fingerprint(
                _node_payload(kind, node_id, identity, evidence_fingerprint)
            ),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            **_node_payload(self.kind, self.node_id, self.identity, self.evidence_fingerprint),
            "node_fingerprint": self.node_fingerprint,
        }


def _edge_payload(
    *,
    source_node_id: str,
    target_node_id: str,
    relation: H2GraphRelation,
    evidence_path: str,
    evidence_blob_sha: str,
    evidence_fingerprint: str,
) -> dict[str, str]:
    return {
        "evidence_blob_sha": evidence_blob_sha,
        "evidence_fingerprint": evidence_fingerprint,
        "evidence_path": evidence_path,
        "policy_version": H2_STRUCTURAL_EXPERIENCE_GRAPH_POLICY_VERSION,
        "relation": relation.value,
        "source_node_id": source_node_id,
        "target_node_id": target_node_id,
    }


@dataclass(frozen=True)
class H2GraphEdge:
    source_node_id: str
    target_node_id: str
    relation: H2GraphRelation
    evidence_path: str
    evidence_blob_sha: str
    evidence_fingerprint: str
    edge_fingerprint: str

    def __post_init__(self) -> None:
        _bounded_text(self.source_node_id, "source_node_id")
        _bounded_text(self.target_node_id, "target_node_id")
        if type(self.relation) is not H2GraphRelation:
            raise HarnessValidationError("relation must be an exact H2GraphRelation")
        _validate_posix_path(self.evidence_path)
        _validate_hex_40(self.evidence_blob_sha, "evidence_blob_sha")
        _validate_hex_64(self.evidence_fingerprint, "evidence_fingerprint")
        _validate_hex_64(self.edge_fingerprint, "edge_fingerprint")
        expected = _bounded_fingerprint(
            _edge_payload(
                source_node_id=self.source_node_id,
                target_node_id=self.target_node_id,
                relation=self.relation,
                evidence_path=self.evidence_path,
                evidence_blob_sha=self.evidence_blob_sha,
                evidence_fingerprint=self.evidence_fingerprint,
            )
        )
        if self.edge_fingerprint != expected:
            raise HarnessFingerprintError("H2 graph edge fingerprint mismatch")

    @classmethod
    def create(
        cls,
        *,
        source_node_id: str,
        target_node_id: str,
        relation: H2GraphRelation,
        evidence_path: str,
        evidence_blob_sha: str,
        evidence_fingerprint: str,
    ) -> "H2GraphEdge":
        payload = _edge_payload(
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            relation=relation,
            evidence_path=evidence_path,
            evidence_blob_sha=evidence_blob_sha,
            evidence_fingerprint=evidence_fingerprint,
        )
        return cls(
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            relation=relation,
            evidence_path=evidence_path,
            evidence_blob_sha=evidence_blob_sha,
            evidence_fingerprint=evidence_fingerprint,
            edge_fingerprint=_bounded_fingerprint(payload),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            **_edge_payload(
                source_node_id=self.source_node_id,
                target_node_id=self.target_node_id,
                relation=self.relation,
                evidence_path=self.evidence_path,
                evidence_blob_sha=self.evidence_blob_sha,
                evidence_fingerprint=self.evidence_fingerprint,
            ),
            "edge_fingerprint": self.edge_fingerprint,
        }


def _unresolved_payload(
    *,
    surface: str,
    artifact_kind: str,
    path: str,
    blob_sha: str,
    status: H2ExperienceParseStatus,
    subject: str,
) -> dict[str, str]:
    return {
        "artifact_kind": artifact_kind,
        "blob_sha": blob_sha,
        "path": path,
        "policy_version": H2_STRUCTURAL_EXPERIENCE_GRAPH_POLICY_VERSION,
        "status": status.value,
        "subject": subject,
        "surface": surface,
    }


@dataclass(frozen=True)
class H2UnresolvedExperienceRecord:
    surface: str
    artifact_kind: str
    path: str
    blob_sha: str
    status: H2ExperienceParseStatus
    subject: str
    record_fingerprint: str

    def __post_init__(self) -> None:
        _bounded_text(self.surface, "surface", 64)
        _bounded_text(self.artifact_kind, "artifact_kind", 64)
        _validate_posix_path(self.path)
        _validate_hex_40(self.blob_sha, "blob_sha")
        if type(self.status) is not H2ExperienceParseStatus:
            raise HarnessValidationError("status must be an exact H2ExperienceParseStatus")
        _bounded_text(self.subject, "subject")
        _validate_hex_64(self.record_fingerprint, "record_fingerprint")
        expected = _bounded_fingerprint(
            _unresolved_payload(
                surface=self.surface,
                artifact_kind=self.artifact_kind,
                path=self.path,
                blob_sha=self.blob_sha,
                status=self.status,
                subject=self.subject,
            )
        )
        if self.record_fingerprint != expected:
            raise HarnessFingerprintError("unresolved experience record fingerprint mismatch")

    @classmethod
    def create(
        cls,
        *,
        surface: str,
        artifact_kind: str,
        path: str,
        blob_sha: str,
        status: H2ExperienceParseStatus,
        subject: str,
    ) -> "H2UnresolvedExperienceRecord":
        payload = _unresolved_payload(
            surface=surface,
            artifact_kind=artifact_kind,
            path=path,
            blob_sha=blob_sha,
            status=status,
            subject=subject,
        )
        return cls(
            surface=surface,
            artifact_kind=artifact_kind,
            path=path,
            blob_sha=blob_sha,
            status=status,
            subject=subject,
            record_fingerprint=_bounded_fingerprint(payload),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            **_unresolved_payload(
                surface=self.surface,
                artifact_kind=self.artifact_kind,
                path=self.path,
                blob_sha=self.blob_sha,
                status=self.status,
                subject=self.subject,
            ),
            "record_fingerprint": self.record_fingerprint,
        }


def _result_payload(
    *,
    task_id: str,
    repository_snapshot: RepositorySnapshotRef,
    control_plane_snapshot: ControlPlaneSnapshotRef,
    discovery_fingerprint: str,
    candidate_set_fingerprint: str,
    experience_manifest_fingerprint: str,
    ranking_fingerprint: str,
    relevance_spec_fingerprint: str,
    role_summary_fingerprint: str,
    import_graph_fingerprint: str,
    components: Sequence[StructuralComponent],
    symbols: Sequence[StructuralSymbolRef],
    nodes: Sequence[H2GraphNode],
    edges: Sequence[H2GraphEdge],
    unresolved_records: Sequence[H2UnresolvedExperienceRecord],
    authority_created: bool,
) -> dict[str, Any]:
    return {
        "authority_created": authority_created,
        "candidate_set_fingerprint": candidate_set_fingerprint,
        "components": [item.to_dict() for item in components],
        "control_plane_snapshot": control_plane_snapshot.to_dict(),
        "discovery_fingerprint": discovery_fingerprint,
        "edges": [item.to_dict() for item in edges],
        "experience_manifest_fingerprint": experience_manifest_fingerprint,
        "import_graph_fingerprint": import_graph_fingerprint,
        "nodes": [item.to_dict() for item in nodes],
        "policy_version": H2_STRUCTURAL_EXPERIENCE_GRAPH_POLICY_VERSION,
        "ranking_fingerprint": ranking_fingerprint,
        "relevance_spec_fingerprint": relevance_spec_fingerprint,
        "repository_snapshot": repository_snapshot.to_dict(),
        "role_summary_fingerprint": role_summary_fingerprint,
        "schema_version": STRUCTURAL_EXPERIENCE_GRAPH_SCHEMA_VERSION,
        "symbols": [item.to_dict() for item in symbols],
        "task_id": task_id,
        "unresolved_records": [item.to_dict() for item in unresolved_records],
    }


_STRUCTURAL_RELATIONS = frozenset(
    {
        H2GraphRelation.CONTAINS_SYMBOL,
        H2GraphRelation.BELONGS_TO_COMPONENT,
        H2GraphRelation.FILE_BELONGS_TO_COMPONENT,
        H2GraphRelation.COMPONENT_IMPORTS_COMPONENT,
    }
)


@dataclass(frozen=True)
class RepositoryStructuralExperienceGraphResult:
    task_id: str
    repository_snapshot: RepositorySnapshotRef
    control_plane_snapshot: ControlPlaneSnapshotRef
    discovery_fingerprint: str
    candidate_set_fingerprint: str
    experience_manifest_fingerprint: str
    ranking_fingerprint: str
    relevance_spec_fingerprint: str
    role_summary_fingerprint: str
    import_graph_fingerprint: str
    components: tuple[StructuralComponent, ...]
    symbols: tuple[StructuralSymbolRef, ...]
    nodes: tuple[H2GraphNode, ...]
    edges: tuple[H2GraphEdge, ...]
    unresolved_records: tuple[H2UnresolvedExperienceRecord, ...]
    graph_fingerprint: str
    schema_version: str = STRUCTURAL_EXPERIENCE_GRAPH_SCHEMA_VERSION
    policy_version: str = H2_STRUCTURAL_EXPERIENCE_GRAPH_POLICY_VERSION
    authority_created: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != STRUCTURAL_EXPERIENCE_GRAPH_SCHEMA_VERSION:
            raise HarnessValidationError("invalid structural-experience schema version")
        if self.policy_version != H2_STRUCTURAL_EXPERIENCE_GRAPH_POLICY_VERSION:
            raise HarnessValidationError("invalid structural-experience policy version")
        _validate_task_id(self.task_id)
        if type(self.repository_snapshot) is not RepositorySnapshotRef:
            raise HarnessValidationError("repository_snapshot must be exact RepositorySnapshotRef")
        if type(self.control_plane_snapshot) is not ControlPlaneSnapshotRef:
            raise HarnessValidationError("control_plane_snapshot must be exact ControlPlaneSnapshotRef")
        for name, value in (
            ("discovery_fingerprint", self.discovery_fingerprint),
            ("candidate_set_fingerprint", self.candidate_set_fingerprint),
            ("experience_manifest_fingerprint", self.experience_manifest_fingerprint),
            ("ranking_fingerprint", self.ranking_fingerprint),
            ("relevance_spec_fingerprint", self.relevance_spec_fingerprint),
            ("role_summary_fingerprint", self.role_summary_fingerprint),
            ("import_graph_fingerprint", self.import_graph_fingerprint),
            ("graph_fingerprint", self.graph_fingerprint),
        ):
            _validate_hex_64(value, name)
        if self.authority_created is not False:
            raise HarnessValidationError("authority_created must be exactly False")
        for name, values, expected_type, maximum in (
            ("components", self.components, StructuralComponent, MAX_H2_GRAPH_COMPONENTS),
            ("symbols", self.symbols, StructuralSymbolRef, MAX_H2_GRAPH_SYMBOLS),
            ("nodes", self.nodes, H2GraphNode, MAX_H2_GRAPH_SYMBOLS + MAX_H2_GRAPH_TASKS + MAX_H2_GRAPH_REVIEW_FINDINGS + MAX_H2_GRAPH_INVARIANTS + MAX_H2_GRAPH_EXECUTORS + MAX_H2_GRAPH_COMPONENTS * 2),
            ("edges", self.edges, H2GraphEdge, MAX_H2_GRAPH_STRUCTURAL_EDGES + MAX_H2_GRAPH_EXPERIENCE_EDGES),
            ("unresolved_records", self.unresolved_records, H2UnresolvedExperienceRecord, MAX_H2_GRAPH_UNRESOLVED_RECORDS),
        ):
            if type(values) is not tuple:
                raise HarnessValidationError(f"{name} must be an exact tuple")
            if len(values) > maximum:
                raise RepositoryStructuralExperienceGraphBoundError(
                    f"{name} count exceeds hard limit ({maximum})"
                )
            if any(type(item) is not expected_type for item in values):
                raise HarnessValidationError(f"{name} contains an invalid value")
        if self.components != tuple(sorted(self.components, key=_component_order_key)):
            raise HarnessValidationError("components must use canonical order")
        if self.symbols != tuple(sorted(self.symbols, key=_symbol_order_key)):
            raise HarnessValidationError("symbols must use canonical order")
        if self.nodes != tuple(sorted(self.nodes, key=_node_order_key)):
            raise HarnessValidationError("nodes must use canonical order")
        if self.edges != tuple(sorted(self.edges, key=_graph_edge_order_key)):
            raise HarnessValidationError("edges must use canonical order")
        if self.unresolved_records != tuple(
            sorted(self.unresolved_records, key=_unresolved_order_key)
        ):
            raise HarnessValidationError("unresolved_records must use canonical order")

        for component in self.components:
            StructuralComponent(**{
                "component_id": component.component_id,
                "kind": component.kind,
                "path": component.path,
                "component_fingerprint": component.component_fingerprint,
            })
        for symbol in self.symbols:
            StructuralSymbolRef(
                symbol_id=symbol.symbol_id,
                file_path=symbol.file_path,
                blob_sha=symbol.blob_sha,
                kind=symbol.kind,
                name=symbol.name,
                line_number=symbol.line_number,
                symbol_locator=symbol.symbol_locator,
                symbol_fingerprint=symbol.symbol_fingerprint,
            )
        node_ids: set[str] = set()
        for node in self.nodes:
            H2GraphNode(
                node_id=node.node_id,
                kind=node.kind,
                identity=node.identity,
                evidence_fingerprint=node.evidence_fingerprint,
                node_fingerprint=node.node_fingerprint,
            )
            if node.node_id in node_ids:
                raise HarnessValidationError("duplicate graph node identity rejected")
            node_ids.add(node.node_id)
        structural_count = 0
        experience_count = 0
        edge_fingerprints: set[str] = set()
        for edge in self.edges:
            H2GraphEdge(
                source_node_id=edge.source_node_id,
                target_node_id=edge.target_node_id,
                relation=edge.relation,
                evidence_path=edge.evidence_path,
                evidence_blob_sha=edge.evidence_blob_sha,
                evidence_fingerprint=edge.evidence_fingerprint,
                edge_fingerprint=edge.edge_fingerprint,
            )
            if edge.source_node_id not in node_ids or edge.target_node_id not in node_ids:
                raise HarnessValidationError("every graph edge endpoint must exist")
            if edge.edge_fingerprint in edge_fingerprints:
                raise HarnessValidationError("duplicate exact graph edge rejected")
            edge_fingerprints.add(edge.edge_fingerprint)
            if edge.relation in _STRUCTURAL_RELATIONS:
                structural_count += 1
            else:
                experience_count += 1
        if structural_count > MAX_H2_GRAPH_STRUCTURAL_EDGES:
            raise RepositoryStructuralExperienceGraphBoundError("structural edge bound exceeded")
        if experience_count > MAX_H2_GRAPH_EXPERIENCE_EDGES:
            raise RepositoryStructuralExperienceGraphBoundError("experience edge bound exceeded")
        for record in self.unresolved_records:
            H2UnresolvedExperienceRecord(
                surface=record.surface,
                artifact_kind=record.artifact_kind,
                path=record.path,
                blob_sha=record.blob_sha,
                status=record.status,
                subject=record.subject,
                record_fingerprint=record.record_fingerprint,
            )

        expected = _bounded_fingerprint(
            _result_payload(
                task_id=self.task_id,
                repository_snapshot=self.repository_snapshot,
                control_plane_snapshot=self.control_plane_snapshot,
                discovery_fingerprint=self.discovery_fingerprint,
                candidate_set_fingerprint=self.candidate_set_fingerprint,
                experience_manifest_fingerprint=self.experience_manifest_fingerprint,
                ranking_fingerprint=self.ranking_fingerprint,
                relevance_spec_fingerprint=self.relevance_spec_fingerprint,
                role_summary_fingerprint=self.role_summary_fingerprint,
                import_graph_fingerprint=self.import_graph_fingerprint,
                components=self.components,
                symbols=self.symbols,
                nodes=self.nodes,
                edges=self.edges,
                unresolved_records=self.unresolved_records,
                authority_created=self.authority_created,
            )
        )
        if self.graph_fingerprint != expected:
            raise HarnessFingerprintError("combined structural-experience graph fingerprint mismatch")

    def to_dict(self) -> dict[str, Any]:
        return {
            **_result_payload(
                task_id=self.task_id,
                repository_snapshot=self.repository_snapshot,
                control_plane_snapshot=self.control_plane_snapshot,
                discovery_fingerprint=self.discovery_fingerprint,
                candidate_set_fingerprint=self.candidate_set_fingerprint,
                experience_manifest_fingerprint=self.experience_manifest_fingerprint,
                ranking_fingerprint=self.ranking_fingerprint,
                relevance_spec_fingerprint=self.relevance_spec_fingerprint,
                role_summary_fingerprint=self.role_summary_fingerprint,
                import_graph_fingerprint=self.import_graph_fingerprint,
                components=self.components,
                symbols=self.symbols,
                nodes=self.nodes,
                edges=self.edges,
                unresolved_records=self.unresolved_records,
                authority_created=self.authority_created,
            ),
            "graph_fingerprint": self.graph_fingerprint,
        }


def _component_order_key(item: StructuralComponent) -> tuple[str, str]:
    return (item.kind.value, item.path)


def _symbol_order_key(item: StructuralSymbolRef) -> tuple[Any, ...]:
    return (item.file_path, item.line_number, item.kind.value, item.name, item.blob_sha)


def _node_order_key(item: H2GraphNode) -> tuple[str, str]:
    return (item.kind.value, item.node_id)


def _graph_edge_order_key(item: H2GraphEdge) -> tuple[str, ...]:
    return (
        item.relation.value,
        item.source_node_id,
        item.target_node_id,
        item.evidence_path,
        item.evidence_blob_sha,
        item.evidence_fingerprint,
    )


def _unresolved_order_key(item: H2UnresolvedExperienceRecord) -> tuple[str, ...]:
    return (
        item.surface,
        item.artifact_kind,
        item.path,
        item.status.value,
        item.subject,
        item.blob_sha,
    )


def _revalidate_upstream_bindings(
    *,
    task_id: str,
    discovery: RepositoryDiscoveryResult,
    ranking: RepositoryRankingResult,
    roles: RepositoryRoleSummaryResult,
    import_graph: RepositoryDependencyGraphResult,
    experience_manifest: RepositoryExperienceManifest,
) -> None:
    """Fail closed on every upstream identity before any graph/body operation."""

    _validate_task_id(task_id)
    if type(discovery) is not RepositoryDiscoveryResult:
        raise HarnessValidationError("discovery must be exact RepositoryDiscoveryResult")
    RepositoryDiscoveryResult(
        snapshot=discovery.snapshot,
        evidence=discovery.evidence,
        exclusions=discovery.exclusions,
        candidate_set_fingerprint=discovery.candidate_set_fingerprint,
        discovery_fingerprint=discovery.discovery_fingerprint,
        schema_version=discovery.schema_version,
        policy_version=discovery.policy_version,
    )
    if type(ranking) is not RepositoryRankingResult:
        raise HarnessValidationError("ranking must be exact RepositoryRankingResult")
    RepositoryRankingResult(
        task_id=ranking.task_id,
        discovery_fingerprint=ranking.discovery_fingerprint,
        input_candidate_set_fingerprint=ranking.input_candidate_set_fingerprint,
        relevance_spec_fingerprint=ranking.relevance_spec_fingerprint,
        plan=ranking.plan,
        ranking_fingerprint=ranking.ranking_fingerprint,
        schema_version=ranking.schema_version,
        policy_version=ranking.policy_version,
    )
    if type(roles) is not RepositoryRoleSummaryResult:
        raise HarnessValidationError("roles must be exact RepositoryRoleSummaryResult")
    RepositoryRoleSummaryResult(
        task_id=roles.task_id,
        snapshot=roles.snapshot,
        ranking_fingerprint=roles.ranking_fingerprint,
        h2_plan_fingerprint=roles.h2_plan_fingerprint,
        summaries=roles.summaries,
        role_summary_fingerprint=roles.role_summary_fingerprint,
        schema_version=roles.schema_version,
        policy_version=roles.policy_version,
    )
    if type(import_graph) is not RepositoryDependencyGraphResult:
        raise HarnessValidationError("import_graph must be exact RepositoryDependencyGraphResult")
    RepositoryDependencyGraphResult(
        task_id=import_graph.task_id,
        snapshot=import_graph.snapshot,
        ranking_fingerprint=import_graph.ranking_fingerprint,
        h2_plan_fingerprint=import_graph.h2_plan_fingerprint,
        h3_role_summary_fingerprint=import_graph.h3_role_summary_fingerprint,
        source_summary_fingerprints=import_graph.source_summary_fingerprints,
        edges=import_graph.edges,
        graph_fingerprint=import_graph.graph_fingerprint,
        schema_version=import_graph.schema_version,
        policy_version=import_graph.policy_version,
    )
    if type(experience_manifest) is not RepositoryExperienceManifest:
        raise HarnessValidationError(
            "experience_manifest must be exact RepositoryExperienceManifest"
        )
    RepositoryExperienceManifest(
        repository_snapshot=experience_manifest.repository_snapshot,
        repository_discovery_fingerprint=experience_manifest.repository_discovery_fingerprint,
        repository_candidate_set_fingerprint=experience_manifest.repository_candidate_set_fingerprint,
        control_plane_snapshot=experience_manifest.control_plane_snapshot,
        control_plane_manifest_fingerprint=experience_manifest.control_plane_manifest_fingerprint,
        evidence=experience_manifest.evidence,
        combined_experience_fingerprint=experience_manifest.combined_experience_fingerprint,
        manifest_fingerprint=experience_manifest.manifest_fingerprint,
        schema_version=experience_manifest.schema_version,
        policy_version=experience_manifest.policy_version,
        authority_created=experience_manifest.authority_created,
    )

    snapshot = discovery.snapshot
    if task_id != ranking.task_id:
        raise RepositoryStructuralExperienceGraphConsistencyError(
            "graph-build task identity must equal ranking task identity"
        )
    if ranking.plan.snapshot != snapshot:
        raise RepositoryStructuralExperienceGraphConsistencyError(
            "ranking repository snapshot does not equal discovery snapshot"
        )
    if (
        ranking.discovery_fingerprint != discovery.discovery_fingerprint
        or ranking.input_candidate_set_fingerprint != discovery.candidate_set_fingerprint
    ):
        raise RepositoryStructuralExperienceGraphConsistencyError(
            "ranking identity is not exactly bound to supplied discovery"
        )
    if (
        roles.task_id != task_id
        or roles.snapshot != snapshot
        or roles.ranking_fingerprint != ranking.ranking_fingerprint
        or roles.h2_plan_fingerprint != ranking.plan.plan_fingerprint
    ):
        raise RepositoryStructuralExperienceGraphConsistencyError(
            "role summary identity is not exactly bound to supplied ranking"
        )
    expected_source_fingerprints = tuple(item.summary_fingerprint for item in roles.summaries)
    if (
        import_graph.task_id != task_id
        or import_graph.snapshot != snapshot
        or import_graph.ranking_fingerprint != ranking.ranking_fingerprint
        or import_graph.h2_plan_fingerprint != ranking.plan.plan_fingerprint
        or import_graph.h3_role_summary_fingerprint != roles.role_summary_fingerprint
        or import_graph.source_summary_fingerprints != expected_source_fingerprints
    ):
        raise RepositoryStructuralExperienceGraphConsistencyError(
            "import graph identity is not exactly bound to supplied ranking and roles"
        )
    if (
        experience_manifest.repository_snapshot != snapshot
        or experience_manifest.repository_discovery_fingerprint != discovery.discovery_fingerprint
        or experience_manifest.repository_candidate_set_fingerprint
        != discovery.candidate_set_fingerprint
    ):
        raise RepositoryStructuralExperienceGraphConsistencyError(
            "experience manifest is not exactly bound to structural repository discovery"
        )
    if type(experience_manifest.control_plane_snapshot) is not ControlPlaneSnapshotRef:
        raise RepositoryStructuralExperienceGraphConsistencyError(
            "exact control-plane snapshot is required"
        )


def _validate_repository_root(repository_root: Path | str) -> Path:
    if not isinstance(repository_root, (str, os.PathLike)):
        raise HarnessValidationError("repo_root must be a filesystem path")
    try:
        root = Path(repository_root).resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise HarnessValidationError("repo_root must resolve to an existing directory") from exc
    if not root.is_dir():
        raise HarnessValidationError("repo_root must be a directory")
    return root


def _read_bounded_output(stream: BinaryIO, limit: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = stream.read(min(_GIT_READ_CHUNK_BYTES, limit - total + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise RepositoryStructuralExperienceGraphBoundError(
                f"local Git output exceeds hard limit ({limit})"
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _open_git_process(root: Path, command: Sequence[str]) -> subprocess.Popen[bytes]:
    environment = {
        name: value
        for name in _GIT_CHILD_ENVIRONMENT_ALLOWLIST
        if (value := os.environ.get(name)) is not None
    }
    environment["GIT_NO_LAZY_FETCH"] = "1"
    try:
        return subprocess.Popen(
            ["git", "--no-replace-objects", "-C", os.fspath(root), *command],
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=environment,
        )
    except OSError as exc:
        raise RepositoryStructuralExperienceGraphGitError(
            f"unable to start local Git command {command[0]!r}"
        ) from exc


def _abort_process(process: subprocess.Popen[bytes]) -> None:
    try:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    except OSError:
        pass


def _run_git_output(root: Path, command: Sequence[str], limit: int) -> bytes:
    process = _open_git_process(root, command)
    if process.stdout is None:
        _abort_process(process)
        raise RepositoryStructuralExperienceGraphGitError("local Git stdout is unavailable")
    try:
        output = _read_bounded_output(process.stdout, limit)
        return_code = process.wait()
    except Exception:
        _abort_process(process)
        raise
    finally:
        process.stdout.close()
    if return_code != 0:
        raise RepositoryStructuralExperienceGraphGitError(
            f"local Git command {command[0]!r} failed with exit code {return_code}"
        )
    return output


def _decode_git_line(output: bytes, field_name: str) -> str:
    if not output.endswith(b"\n") or output.count(b"\n") != 1 or b"\r" in output:
        raise RepositoryStructuralExperienceGraphGitError(
            f"local Git returned malformed {field_name} output"
        )
    try:
        return output[:-1].decode("ascii", errors="strict")
    except UnicodeDecodeError as exc:
        raise RepositoryStructuralExperienceGraphGitError(
            f"local Git returned non-ASCII {field_name} output"
        ) from exc


def _verify_snapshot(root: Path, commit_sha: str, tree_sha: str, surface: str) -> None:
    commit = _decode_git_line(
        _run_git_output(
            root,
            ["rev-parse", "--verify", f"{commit_sha}^{{commit}}"],
            MAX_H2_GRAPH_GIT_SCALAR_BYTES,
        ),
        f"{surface} commit SHA",
    )
    tree = _decode_git_line(
        _run_git_output(
            root,
            ["rev-parse", f"{commit_sha}^{{tree}}"],
            MAX_H2_GRAPH_GIT_SCALAR_BYTES,
        ),
        f"{surface} tree SHA",
    )
    if commit != commit_sha or tree != tree_sha:
        raise RepositoryStructuralExperienceGraphGitError(
            f"local Git {surface} snapshot does not equal exact supplied identity"
        )


def _read_experience_blob(root: Path, artifact: ExperienceArtifactRef) -> bytes:
    object_type = _decode_git_line(
        _run_git_output(
            root,
            ["cat-file", "-t", artifact.blob_sha],
            MAX_H2_GRAPH_GIT_SCALAR_BYTES,
        ),
        "experience object type",
    )
    if object_type != "blob":
        raise RepositoryStructuralExperienceGraphGitError("experience object is not a blob")
    size_output = _run_git_output(
        root,
        ["cat-file", "-s", artifact.blob_sha],
        MAX_H2_GRAPH_GIT_SCALAR_BYTES,
    )
    if (
        not size_output.endswith(b"\n")
        or size_output.count(b"\n") != 1
        or b"\r" in size_output
        or not _DECIMAL_BYTES_RE.fullmatch(size_output[:-1])
    ):
        raise RepositoryStructuralExperienceGraphGitError("malformed Git blob size output")
    size = int(size_output[:-1].decode("ascii"))
    if size > MAX_H2_GRAPH_EXPERIENCE_BLOB_BYTES:
        raise RepositoryStructuralExperienceGraphBoundError(
            "experience blob exceeds per-artifact body hard limit"
        )
    body = _run_git_output(root, ["cat-file", "blob", artifact.blob_sha], size)
    if len(body) != size:
        raise RepositoryStructuralExperienceGraphGitError(
            "experience blob body length does not equal preflight size"
        )
    actual = hashlib.sha1(b"blob " + str(size).encode("ascii") + b"\0" + body).hexdigest()
    if actual != artifact.blob_sha:
        raise RepositoryStructuralExperienceGraphGitError(
            "experience body Git blob SHA does not equal manifest identity"
        )
    return body


def _canonical_task_id(prefix: str, digits: str) -> str:
    if not digits or int(digits) <= 0:
        raise RepositoryStructuralExperienceGraphConsistencyError(
            f"{prefix} path does not contain a positive task identity"
        )
    task_id = f"TASK-{digits}"
    _validate_task_id(task_id)
    return task_id


def _task_id_from_path(path: str) -> str:
    match = _TASK_PATH_RE.fullmatch(path)
    if match is None:
        raise RepositoryStructuralExperienceGraphConsistencyError(
            "TASK experience path is not canonical .ai/tasks/TASK-NNN.md"
        )
    return _canonical_task_id("TASK", match.group(1))


def _result_task_id_from_path(path: str) -> str:
    match = _RESULT_PATH_RE.fullmatch(path)
    if match is None:
        raise RepositoryStructuralExperienceGraphConsistencyError(
            "RESULT experience path is not canonical .ai/results/RESULT-NNN.md"
        )
    return _canonical_task_id("RESULT", match.group(1))


def _review_task_id_from_path(path: str) -> str:
    match = _REVIEW_PATH_RE.fullmatch(path)
    if match is None:
        raise RepositoryStructuralExperienceGraphConsistencyError(
            "REVIEW experience path is not canonical .ai/reviews/REVIEW-NNN.md"
        )
    return _canonical_task_id("REVIEW", match.group(1))


def _strict_json(payload: str, marker: str) -> Any:
    encoded = payload.encode("utf-8")
    if len(encoded) > MAX_H2_GRAPH_MACHINE_MARKER_BYTES:
        raise RepositoryStructuralExperienceGraphBoundError(
            f"{marker} payload exceeds machine-marker hard limit"
        )

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        return json.loads(payload, object_pairs_hook=reject_duplicate_keys)
    except (json.JSONDecodeError, UnicodeError, ValueError) as exc:
        raise RepositoryStructuralExperienceGraphConsistencyError(
            f"malformed explicit {marker} machine evidence"
        ) from exc


def _marker_payload(text: str, marker: str) -> str | None:
    prefix = marker + ":"
    values = [line[len(prefix) :].strip() for line in text.splitlines() if line.startswith(prefix)]
    if len(values) > 1:
        raise RepositoryStructuralExperienceGraphConsistencyError(
            f"multiple {marker} markers are forbidden"
        )
    if not values:
        return None
    if not values[0]:
        raise RepositoryStructuralExperienceGraphConsistencyError(
            f"empty explicit {marker} machine evidence"
        )
    return values[0]


def _parse_allowed_paths(text: str) -> tuple[str, ...] | None:
    payload = _marker_payload(text, "EXECUTOR_ALLOWED_PATHS_JSON")
    if payload is None:
        return None
    parsed = _strict_json(payload, "EXECUTOR_ALLOWED_PATHS_JSON")
    if type(parsed) is not list or any(type(item) is not str for item in parsed):
        raise RepositoryStructuralExperienceGraphConsistencyError(
            "EXECUTOR_ALLOWED_PATHS_JSON must be a strict JSON array of paths"
        )
    paths = tuple(parsed)
    if len(set(paths)) != len(paths):
        raise RepositoryStructuralExperienceGraphConsistencyError(
            "duplicate EXECUTOR_ALLOWED_PATHS_JSON paths are forbidden"
        )
    for path in paths:
        _validate_posix_path(path)
    return paths


def _parse_invariants(text: str) -> tuple[tuple[str, str], ...] | None:
    payload = _marker_payload(text, "H2_INVARIANT_REFS_JSON")
    if payload is None:
        return None
    parsed = _strict_json(payload, "H2_INVARIANT_REFS_JSON")
    if type(parsed) is not list:
        raise RepositoryStructuralExperienceGraphConsistencyError(
            "H2_INVARIANT_REFS_JSON must be a strict JSON array"
        )
    records: list[tuple[str, str]] = []
    for item in parsed:
        if type(item) is not dict or set(item) != {"invariant_id", "component_path"}:
            raise RepositoryStructuralExperienceGraphConsistencyError(
                "H2 invariant records require exactly invariant_id and component_path"
            )
        invariant_id = item["invariant_id"]
        component_path = item["component_path"]
        if type(invariant_id) is not str or not _INVARIANT_RE.fullmatch(invariant_id):
            raise RepositoryStructuralExperienceGraphConsistencyError(
                "invariant_id must be a bounded explicit token"
            )
        if len(invariant_id) > _MAX_INVARIANT_ID or type(component_path) is not str:
            raise RepositoryStructuralExperienceGraphConsistencyError(
                "invalid bounded H2 invariant record"
            )
        _validate_posix_path(component_path)
        records.append((invariant_id, component_path))
    if len(set(records)) != len(records):
        raise RepositoryStructuralExperienceGraphConsistencyError(
            "duplicate exact H2 invariant records are forbidden"
        )
    return tuple(records)


def _parse_result_manifest(text: str, expected_task_id: str) -> tuple[str, str] | None:
    heading_count = len(re.findall(r"^## Review Manifest[ \t]*$", text, re.MULTILINE))
    matches = list(_REVIEW_MANIFEST_RE.finditer(text))
    if heading_count == 0:
        return None
    if heading_count != 1 or len(matches) != 1:
        raise RepositoryStructuralExperienceGraphConsistencyError(
            "RESULT Review Manifest must be one closed fenced block"
        )
    fields: dict[str, str] = {}
    for line in matches[0].group(1).splitlines():
        if not line.strip():
            continue
        scalar = re.fullmatch(r"([A-Z][A-Z0-9_]*)[ \t]*(?::|=)[ \t]*([^\s][^\r\n]*?)\s*", line)
        if scalar is None:
            raise RepositoryStructuralExperienceGraphConsistencyError(
                "Review Manifest contains a non-scalar line"
            )
        key, value = scalar.groups()
        if key in fields:
            raise RepositoryStructuralExperienceGraphConsistencyError(
                "Review Manifest contains duplicate scalar fields"
            )
        fields[key] = value
    task_id = fields.get("TASK_ID")
    executor_id = fields.get("EXECUTOR_ID")
    if task_id is None or executor_id is None:
        raise RepositoryStructuralExperienceGraphConsistencyError(
            "Review Manifest requires TASK_ID and EXECUTOR_ID"
        )
    if not _TASK_ID_RE.fullmatch(task_id) or task_id != expected_task_id:
        raise RepositoryStructuralExperienceGraphConsistencyError(
            "RESULT Review Manifest TASK_ID does not match RESULT path"
        )
    if not _EXECUTOR_RE.fullmatch(executor_id) or len(executor_id) > _MAX_EXECUTOR_ID:
        raise RepositoryStructuralExperienceGraphConsistencyError(
            "Review Manifest EXECUTOR_ID is not a bounded executor token"
        )
    return task_id, executor_id


def _parse_review_findings(text: str) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    matches = list(_FINDING_HEADING_RE.finditer(text))
    findings: list[tuple[str, str, tuple[str, ...]]] = []
    seen_numbers: set[str] = set()
    for position, match in enumerate(matches):
        number, title = match.groups()
        if number in seen_numbers:
            raise RepositoryStructuralExperienceGraphConsistencyError(
                "duplicate REVIEW finding number is forbidden"
            )
        seen_numbers.add(number)
        title = title.strip()
        _bounded_text(title, "review finding title", _MAX_FINDING_TITLE)
        section_end = matches[position + 1].start() if position + 1 < len(matches) else len(text)
        section = text[match.end() : section_end]
        paths: list[str] = []
        for line in section.splitlines():
            if line.startswith("H2_COMPONENT_PATH:"):
                path = line[len("H2_COMPONENT_PATH:") :].strip()
                if not path:
                    raise RepositoryStructuralExperienceGraphConsistencyError(
                        "empty H2_COMPONENT_PATH finding evidence"
                    )
                _validate_posix_path(path)
                paths.append(path)
        if len(set(paths)) != len(paths):
            raise RepositoryStructuralExperienceGraphConsistencyError(
                "duplicate finding component path evidence is forbidden"
            )
        findings.append((number, title, tuple(paths)))
    return tuple(findings)


def _artifact_evidence_fingerprint(artifact: ExperienceArtifactRef) -> str:
    return _bounded_fingerprint(
        {
            "artifact": artifact.to_dict(),
            "policy_version": H2_STRUCTURAL_EXPERIENCE_GRAPH_POLICY_VERSION,
        }
    )


def _node_evidence(identity: str) -> str:
    return _bounded_fingerprint(
        {"identity": identity, "policy_version": H2_STRUCTURAL_EXPERIENCE_GRAPH_POLICY_VERSION}
    )


def _file_node_id(path: str, blob_sha: str) -> str:
    return f"file:{path}:{blob_sha}"


def _task_node_id(task_id: str) -> str:
    return f"task:{task_id}"


def _executor_node_id(executor_id: str) -> str:
    return f"executor:{executor_id}"


def _invariant_node_id(invariant_id: str) -> str:
    return f"invariant:{invariant_id}"


def _component_for_python_path(
    path: str, discovery_paths: frozenset[str]
) -> tuple[StructuralComponentKind, str]:
    pure_path = PurePosixPath(path)
    parent = pure_path.parent
    if str(parent) != ".":
        directories = list(parent.parents)
        directories.insert(0, parent)
        for directory in directories:
            directory_text = directory.as_posix()
            if directory_text == ".":
                continue
            if f"{directory_text}/__init__.py" in discovery_paths:
                return StructuralComponentKind.PYTHON_PACKAGE, directory_text
    return StructuralComponentKind.STANDALONE_PYTHON_MODULE, path


def _add_node(nodes: dict[str, H2GraphNode], node: H2GraphNode) -> None:
    existing = nodes.get(node.node_id)
    if existing is not None and existing != node:
        raise RepositoryStructuralExperienceGraphConsistencyError(
            "contradictory duplicate graph node identity"
        )
    nodes[node.node_id] = node


def _add_edge(edges: dict[str, H2GraphEdge], edge: H2GraphEdge) -> None:
    existing = edges.get(edge.edge_fingerprint)
    if existing is not None and existing != edge:
        raise RepositoryStructuralExperienceGraphConsistencyError(
            "contradictory duplicate graph edge fingerprint"
        )
    edges[edge.edge_fingerprint] = edge


def _add_unresolved(
    records: dict[str, H2UnresolvedExperienceRecord],
    record: H2UnresolvedExperienceRecord,
) -> None:
    existing = records.get(record.record_fingerprint)
    if existing is not None and existing != record:
        raise RepositoryStructuralExperienceGraphConsistencyError(
            "contradictory duplicate unresolved record fingerprint"
        )
    records[record.record_fingerprint] = record
    if len(records) > MAX_H2_GRAPH_UNRESOLVED_RECORDS:
        raise RepositoryStructuralExperienceGraphBoundError("unresolved record bound exceeded")


def build_repository_structural_experience_graph(
    repo_root: Path | str,
    discovery: RepositoryDiscoveryResult,
    ranking: RepositoryRankingResult,
    roles: RepositoryRoleSummaryResult,
    import_graph: RepositoryDependencyGraphResult,
    experience_manifest: RepositoryExperienceManifest,
    *,
    task_id: str | None = None,
) -> tuple[RepositoryStructuralExperienceGraphResult, HarnessReceipt]:
    """Compose exact reviewed H1/H2 evidence into one canonical zero-authority graph."""

    graph_task_id = ranking.task_id if task_id is None else task_id
    _revalidate_upstream_bindings(
        task_id=graph_task_id,
        discovery=discovery,
        ranking=ranking,
        roles=roles,
        import_graph=import_graph,
        experience_manifest=experience_manifest,
    )
    if len(experience_manifest.evidence) > MAX_H2_GRAPH_EXPERIENCE_ARTIFACTS:
        raise RepositoryStructuralExperienceGraphBoundError(
            "experience artifact count exceeds hard limit"
        )

    root = _validate_repository_root(repo_root)
    _verify_snapshot(
        root,
        discovery.snapshot.repository_commit_sha,
        discovery.snapshot.repository_tree_sha,
        "repository",
    )
    _verify_snapshot(
        root,
        experience_manifest.control_plane_snapshot.control_commit_sha,
        experience_manifest.control_plane_snapshot.control_tree_sha,
        "control-plane",
    )

    discovery_paths = frozenset(item.path for item in discovery.evidence)
    components_by_id: dict[str, StructuralComponent] = {}
    file_to_component: dict[str, StructuralComponent] = {}
    symbols: list[StructuralSymbolRef] = []
    nodes: dict[str, H2GraphNode] = {}
    edges: dict[str, H2GraphEdge] = {}
    unresolved: dict[str, H2UnresolvedExperienceRecord] = {}

    # H2.R1 consumes the reviewed role-summary symbols; source is never reparsed here.
    for summary in roles.summaries:
        if not summary.path.endswith(".py"):
            continue
        kind, component_path = _component_for_python_path(summary.path, discovery_paths)
        component = StructuralComponent.create(kind, component_path)
        components_by_id.setdefault(component.component_id, component)
        file_to_component[summary.path] = component
        if len(components_by_id) > MAX_H2_GRAPH_COMPONENTS:
            raise RepositoryStructuralExperienceGraphBoundError("component bound exceeded")

        file_id = _file_node_id(summary.path, summary.blob_sha)
        _add_node(
            nodes,
            H2GraphNode.create(
                node_id=file_id,
                kind=H2GraphNodeKind.FILE,
                identity=f"{summary.path}@{summary.blob_sha}",
                evidence_fingerprint=summary.summary_fingerprint,
            ),
        )
        _add_node(
            nodes,
            H2GraphNode.create(
                node_id=component.component_id,
                kind=H2GraphNodeKind.COMPONENT,
                identity=f"{component.kind.value}:{component.path}",
                evidence_fingerprint=component.component_fingerprint,
            ),
        )
        _add_edge(
            edges,
            H2GraphEdge.create(
                source_node_id=file_id,
                target_node_id=component.component_id,
                relation=H2GraphRelation.FILE_BELONGS_TO_COMPONENT,
                evidence_path=summary.path,
                evidence_blob_sha=summary.blob_sha,
                evidence_fingerprint=summary.summary_fingerprint,
            ),
        )
        for symbol_summary in summary.symbols:
            symbol = StructuralSymbolRef.create(summary.path, summary.blob_sha, symbol_summary)
            symbols.append(symbol)
            if len(symbols) > MAX_H2_GRAPH_SYMBOLS:
                raise RepositoryStructuralExperienceGraphBoundError("symbol bound exceeded")
            _add_node(
                nodes,
                H2GraphNode.create(
                    node_id=symbol.symbol_id,
                    kind=H2GraphNodeKind.SYMBOL,
                    identity=f"{symbol.file_path}@{symbol.blob_sha}#{symbol.symbol_locator}",
                    evidence_fingerprint=symbol.symbol_fingerprint,
                ),
            )
            for relation, source, target in (
                (H2GraphRelation.CONTAINS_SYMBOL, file_id, symbol.symbol_id),
                (H2GraphRelation.BELONGS_TO_COMPONENT, symbol.symbol_id, component.component_id),
            ):
                _add_edge(
                    edges,
                    H2GraphEdge.create(
                        source_node_id=source,
                        target_node_id=target,
                        relation=relation,
                        evidence_path=summary.path,
                        evidence_blob_sha=summary.blob_sha,
                        evidence_fingerprint=summary.summary_fingerprint,
                    ),
                )

    def map_component(path: str) -> StructuralComponent | None:
        direct = file_to_component.get(path)
        if direct is not None:
            return direct
        for component in components_by_id.values():
            if path == component.path:
                return component
        if path in discovery_paths and path.endswith(".py"):
            kind, component_path = _component_for_python_path(path, discovery_paths)
            return components_by_id.get(f"component:{kind.value}:{component_path}")
        return None

    # Bind the already-reviewed import graph. Ambiguous and unresolved targets never link.
    for import_edge in import_graph.edges:
        source_component = map_component(import_edge.source_path)
        target_component = (
            map_component(import_edge.target_path)
            if import_edge.target_path is not None
            and import_edge.resolution_status
            in {ImportResolutionStatus.INTERNAL_SELECTED, ImportResolutionStatus.INTERNAL_UNSELECTED}
            else None
        )
        if source_component is not None and target_component is not None:
            _add_edge(
                edges,
                H2GraphEdge.create(
                    source_node_id=source_component.component_id,
                    target_node_id=target_component.component_id,
                    relation=H2GraphRelation.COMPONENT_IMPORTS_COMPONENT,
                    evidence_path=import_edge.source_path,
                    evidence_blob_sha=import_edge.source_blob_sha,
                    evidence_fingerprint=import_edge.edge_fingerprint,
                ),
            )
        elif import_edge.resolution_status is ImportResolutionStatus.AMBIGUOUS_INTERNAL:
            _add_unresolved(
                unresolved,
                H2UnresolvedExperienceRecord.create(
                    surface="IMPORT_GRAPH",
                    artifact_kind="IMPORT_DEPENDENCY",
                    path=import_edge.source_path,
                    blob_sha=import_edge.source_blob_sha,
                    status=H2ExperienceParseStatus.AMBIGUOUS_COMPONENT,
                    subject=import_edge.module_expression,
                ),
            )
        elif import_edge.target_path is not None:
            _add_unresolved(
                unresolved,
                H2UnresolvedExperienceRecord.create(
                    surface="IMPORT_GRAPH",
                    artifact_kind="IMPORT_DEPENDENCY",
                    path=import_edge.source_path,
                    blob_sha=import_edge.source_blob_sha,
                    status=H2ExperienceParseStatus.PATH_NOT_IN_STRUCTURAL_GRAPH,
                    subject=import_edge.target_path,
                ),
            )

    task_ids: set[str] = set()
    finding_ids: set[str] = set()
    executor_ids: set[str] = set()
    invariant_ids: set[str] = set()
    total_body_bytes = 0

    def add_task_node(canonical_task_id: str) -> str:
        task_ids.add(canonical_task_id)
        if len(task_ids) > MAX_H2_GRAPH_TASKS:
            raise RepositoryStructuralExperienceGraphBoundError("task node bound exceeded")
        node_id = _task_node_id(canonical_task_id)
        _add_node(
            nodes,
            H2GraphNode.create(
                node_id=node_id,
                kind=H2GraphNodeKind.TASK,
                identity=canonical_task_id,
                evidence_fingerprint=_node_evidence(canonical_task_id),
            ),
        )
        return node_id

    def account(
        artifact: ExperienceArtifactRef,
        status: H2ExperienceParseStatus,
        subject: str,
    ) -> None:
        _add_unresolved(
            unresolved,
            H2UnresolvedExperienceRecord.create(
                surface=artifact.surface.value,
                artifact_kind=artifact.artifact_kind.value,
                path=artifact.path,
                blob_sha=artifact.blob_sha,
                status=status,
                subject=subject,
            ),
        )

    def add_invariants(
        artifact: ExperienceArtifactRef,
        records: tuple[tuple[str, str], ...],
        task_node_id: str | None,
    ) -> int:
        emitted = 0
        evidence_fingerprint = _artifact_evidence_fingerprint(artifact)
        for invariant_id, component_path in records:
            invariant_ids.add(invariant_id)
            if len(invariant_ids) > MAX_H2_GRAPH_INVARIANTS:
                raise RepositoryStructuralExperienceGraphBoundError("invariant node bound exceeded")
            invariant_node_id = _invariant_node_id(invariant_id)
            _add_node(
                nodes,
                H2GraphNode.create(
                    node_id=invariant_node_id,
                    kind=H2GraphNodeKind.INVARIANT,
                    identity=invariant_id,
                    evidence_fingerprint=_node_evidence(invariant_id),
                ),
            )
            if task_node_id is not None:
                _add_edge(
                    edges,
                    H2GraphEdge.create(
                        source_node_id=task_node_id,
                        target_node_id=invariant_node_id,
                        relation=H2GraphRelation.TASK_REFERENCES_INVARIANT,
                        evidence_path=artifact.path,
                        evidence_blob_sha=artifact.blob_sha,
                        evidence_fingerprint=evidence_fingerprint,
                    ),
                )
                emitted += 1
            component = map_component(component_path)
            if component is None:
                account(
                    artifact,
                    H2ExperienceParseStatus.PATH_NOT_IN_STRUCTURAL_GRAPH,
                    f"invariant:{invariant_id}:{component_path}",
                )
            else:
                _add_edge(
                    edges,
                    H2GraphEdge.create(
                        source_node_id=invariant_node_id,
                        target_node_id=component.component_id,
                        relation=H2GraphRelation.INVARIANT_RELATES_TO_COMPONENT,
                        evidence_path=artifact.path,
                        evidence_blob_sha=artifact.blob_sha,
                        evidence_fingerprint=evidence_fingerprint,
                    ),
                )
                emitted += 1
        return emitted

    for artifact in experience_manifest.evidence:
        body = _read_experience_blob(root, artifact)
        total_body_bytes += len(body)
        if total_body_bytes > MAX_H2_GRAPH_TOTAL_EXPERIENCE_BYTES:
            raise RepositoryStructuralExperienceGraphBoundError(
                "aggregate experience body hard limit exceeded"
            )
        try:
            text = body.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise RepositoryStructuralExperienceGraphConsistencyError(
                "experience body is not strict UTF-8"
            ) from exc

        evidence_fingerprint = _artifact_evidence_fingerprint(artifact)
        emitted = 0
        invariant_records = _parse_invariants(text)
        if (
            artifact.artifact_kind is ExperienceArtifactKind.RESULT
            and invariant_records is not None
        ):
            raise RepositoryStructuralExperienceGraphConsistencyError(
                "H2_INVARIANT_REFS_JSON is forbidden in RESULT artifacts"
            )

        if artifact.artifact_kind is ExperienceArtifactKind.TASK:
            canonical_task_id = _task_id_from_path(artifact.path)
            task_node_id = add_task_node(canonical_task_id)
            allowed_paths = _parse_allowed_paths(text)
            if allowed_paths is not None:
                for allowed_path in allowed_paths:
                    component = map_component(allowed_path)
                    if component is None:
                        account(
                            artifact,
                            H2ExperienceParseStatus.PATH_NOT_IN_STRUCTURAL_GRAPH,
                            allowed_path,
                        )
                    else:
                        _add_edge(
                            edges,
                            H2GraphEdge.create(
                                source_node_id=task_node_id,
                                target_node_id=component.component_id,
                                relation=H2GraphRelation.TASK_TOUCHES_COMPONENT,
                                evidence_path=artifact.path,
                                evidence_blob_sha=artifact.blob_sha,
                                evidence_fingerprint=evidence_fingerprint,
                            ),
                        )
                        emitted += 1
            if invariant_records is not None:
                emitted += add_invariants(artifact, invariant_records, task_node_id)

        elif artifact.artifact_kind is ExperienceArtifactKind.RESULT:
            expected_task_id = _result_task_id_from_path(artifact.path)
            result_evidence = _parse_result_manifest(text, expected_task_id)
            if result_evidence is not None:
                canonical_task_id, executor_id = result_evidence
                task_node_id = add_task_node(canonical_task_id)
                executor_ids.add(executor_id)
                if len(executor_ids) > MAX_H2_GRAPH_EXECUTORS:
                    raise RepositoryStructuralExperienceGraphBoundError(
                        "executor node bound exceeded"
                    )
                executor_node_id = _executor_node_id(executor_id)
                _add_node(
                    nodes,
                    H2GraphNode.create(
                        node_id=executor_node_id,
                        kind=H2GraphNodeKind.EXECUTOR,
                        identity=executor_id,
                        evidence_fingerprint=_node_evidence(executor_id),
                    ),
                )
                _add_edge(
                    edges,
                    H2GraphEdge.create(
                        source_node_id=task_node_id,
                        target_node_id=executor_node_id,
                        relation=H2GraphRelation.TASK_EXECUTED_BY_EXECUTOR,
                        evidence_path=artifact.path,
                        evidence_blob_sha=artifact.blob_sha,
                        evidence_fingerprint=evidence_fingerprint,
                    ),
                )
                emitted += 1

        elif artifact.artifact_kind is ExperienceArtifactKind.REVIEW:
            canonical_task_id = _review_task_id_from_path(artifact.path)
            task_node_id = add_task_node(canonical_task_id)
            for number, title, component_paths in _parse_review_findings(text):
                title_fingerprint = _bounded_fingerprint({"title": title})
                finding_node_id = (
                    f"review-finding:{canonical_task_id}:{number}:{title_fingerprint}"
                )
                finding_ids.add(finding_node_id)
                if len(finding_ids) > MAX_H2_GRAPH_REVIEW_FINDINGS:
                    raise RepositoryStructuralExperienceGraphBoundError(
                        "review finding node bound exceeded"
                    )
                _add_node(
                    nodes,
                    H2GraphNode.create(
                        node_id=finding_node_id,
                        kind=H2GraphNodeKind.REVIEW_FINDING,
                        identity=f"{canonical_task_id}:{number}:{title_fingerprint}",
                        evidence_fingerprint=evidence_fingerprint,
                    ),
                )
                _add_edge(
                    edges,
                    H2GraphEdge.create(
                        source_node_id=task_node_id,
                        target_node_id=finding_node_id,
                        relation=H2GraphRelation.TASK_HAS_REVIEW_FINDING,
                        evidence_path=artifact.path,
                        evidence_blob_sha=artifact.blob_sha,
                        evidence_fingerprint=evidence_fingerprint,
                    ),
                )
                emitted += 1
                for component_path in component_paths:
                    component = map_component(component_path)
                    if component is None:
                        account(
                            artifact,
                            H2ExperienceParseStatus.PATH_NOT_IN_STRUCTURAL_GRAPH,
                            f"{number}:{component_path}",
                        )
                    else:
                        _add_edge(
                            edges,
                            H2GraphEdge.create(
                                source_node_id=finding_node_id,
                                target_node_id=component.component_id,
                                relation=H2GraphRelation.REVIEW_FINDING_RELATES_TO_COMPONENT,
                                evidence_path=artifact.path,
                                evidence_blob_sha=artifact.blob_sha,
                                evidence_fingerprint=evidence_fingerprint,
                            ),
                        )
                        emitted += 1
            if invariant_records is not None:
                emitted += add_invariants(artifact, invariant_records, None)

        elif artifact.artifact_kind in {
            ExperienceArtifactKind.DECISION,
            ExperienceArtifactKind.LEARNING,
        }:
            if invariant_records is not None:
                emitted += add_invariants(artifact, invariant_records, None)
        else:
            account(
                artifact,
                H2ExperienceParseStatus.UNSUPPORTED_ARTIFACT_KIND,
                "artifact",
            )

        account(
            artifact,
            H2ExperienceParseStatus.PARSED
            if emitted
            else H2ExperienceParseStatus.NO_MACHINE_EVIDENCE,
            "artifact",
        )

    components_tuple = tuple(sorted(components_by_id.values(), key=_component_order_key))
    symbols_tuple = tuple(sorted(symbols, key=_symbol_order_key))
    nodes_tuple = tuple(sorted(nodes.values(), key=_node_order_key))
    edges_tuple = tuple(sorted(edges.values(), key=_graph_edge_order_key))
    unresolved_tuple = tuple(sorted(unresolved.values(), key=_unresolved_order_key))
    structural_count = sum(edge.relation in _STRUCTURAL_RELATIONS for edge in edges_tuple)
    experience_count = len(edges_tuple) - structural_count
    if structural_count > MAX_H2_GRAPH_STRUCTURAL_EDGES:
        raise RepositoryStructuralExperienceGraphBoundError("structural edge bound exceeded")
    if experience_count > MAX_H2_GRAPH_EXPERIENCE_EDGES:
        raise RepositoryStructuralExperienceGraphBoundError("experience edge bound exceeded")

    payload = _result_payload(
        task_id=graph_task_id,
        repository_snapshot=discovery.snapshot,
        control_plane_snapshot=experience_manifest.control_plane_snapshot,
        discovery_fingerprint=discovery.discovery_fingerprint,
        candidate_set_fingerprint=discovery.candidate_set_fingerprint,
        experience_manifest_fingerprint=experience_manifest.manifest_fingerprint,
        ranking_fingerprint=ranking.ranking_fingerprint,
        relevance_spec_fingerprint=ranking.relevance_spec_fingerprint,
        role_summary_fingerprint=roles.role_summary_fingerprint,
        import_graph_fingerprint=import_graph.graph_fingerprint,
        components=components_tuple,
        symbols=symbols_tuple,
        nodes=nodes_tuple,
        edges=edges_tuple,
        unresolved_records=unresolved_tuple,
        authority_created=False,
    )
    result = RepositoryStructuralExperienceGraphResult(
        task_id=graph_task_id,
        repository_snapshot=discovery.snapshot,
        control_plane_snapshot=experience_manifest.control_plane_snapshot,
        discovery_fingerprint=discovery.discovery_fingerprint,
        candidate_set_fingerprint=discovery.candidate_set_fingerprint,
        experience_manifest_fingerprint=experience_manifest.manifest_fingerprint,
        ranking_fingerprint=ranking.ranking_fingerprint,
        relevance_spec_fingerprint=ranking.relevance_spec_fingerprint,
        role_summary_fingerprint=roles.role_summary_fingerprint,
        import_graph_fingerprint=import_graph.graph_fingerprint,
        components=components_tuple,
        symbols=symbols_tuple,
        nodes=nodes_tuple,
        edges=edges_tuple,
        unresolved_records=unresolved_tuple,
        graph_fingerprint=_bounded_fingerprint(payload),
    )
    input_fingerprint = _bounded_fingerprint(
        {
            "candidate_set_fingerprint": discovery.candidate_set_fingerprint,
            "control_plane_snapshot": experience_manifest.control_plane_snapshot.to_dict(),
            "discovery_fingerprint": discovery.discovery_fingerprint,
            "experience_manifest_fingerprint": experience_manifest.manifest_fingerprint,
            "import_graph_fingerprint": import_graph.graph_fingerprint,
            "operation": "h2_repository_structural_experience_graph",
            "policy_version": H2_STRUCTURAL_EXPERIENCE_GRAPH_POLICY_VERSION,
            "ranking_fingerprint": ranking.ranking_fingerprint,
            "repository_snapshot": discovery.snapshot.to_dict(),
            "role_summary_fingerprint": roles.role_summary_fingerprint,
            "schema_version": STRUCTURAL_EXPERIENCE_GRAPH_SCHEMA_VERSION,
            "task_id": graph_task_id,
        }
    )
    receipt = HarnessReceipt(
        task_id=graph_task_id,
        repository_commit_sha=discovery.snapshot.repository_commit_sha,
        input_fingerprint=input_fingerprint,
        output_fingerprint=result.graph_fingerprint,
        generator_version=H2_STRUCTURAL_EXPERIENCE_GRAPH_POLICY_VERSION,
        candidate_count=len(experience_manifest.evidence),
        selected_count=len(experience_manifest.evidence),
        excluded_count=0,
    )
    return result, receipt


__all__ = [
    "H2_STRUCTURAL_EXPERIENCE_GRAPH_POLICY_VERSION",
    "STRUCTURAL_EXPERIENCE_GRAPH_SCHEMA_VERSION",
    "MAX_H2_GRAPH_COMPONENTS",
    "MAX_H2_GRAPH_SYMBOLS",
    "MAX_H2_GRAPH_STRUCTURAL_EDGES",
    "MAX_H2_GRAPH_EXPERIENCE_ARTIFACTS",
    "MAX_H2_GRAPH_EXPERIENCE_BLOB_BYTES",
    "MAX_H2_GRAPH_TOTAL_EXPERIENCE_BYTES",
    "MAX_H2_GRAPH_TASKS",
    "MAX_H2_GRAPH_REVIEW_FINDINGS",
    "MAX_H2_GRAPH_EXECUTORS",
    "MAX_H2_GRAPH_INVARIANTS",
    "MAX_H2_GRAPH_EXPERIENCE_EDGES",
    "MAX_H2_GRAPH_UNRESOLVED_RECORDS",
    "MAX_H2_GRAPH_MACHINE_MARKER_BYTES",
    "MAX_H2_GRAPH_FINGERPRINT_PAYLOAD_BYTES",
    "StructuralComponentKind",
    "H2GraphNodeKind",
    "H2GraphRelation",
    "H2ExperienceParseStatus",
    "StructuralComponent",
    "StructuralSymbolRef",
    "H2GraphNode",
    "H2GraphEdge",
    "H2UnresolvedExperienceRecord",
    "RepositoryStructuralExperienceGraphError",
    "RepositoryStructuralExperienceGraphGitError",
    "RepositoryStructuralExperienceGraphBoundError",
    "RepositoryStructuralExperienceGraphConsistencyError",
    "RepositoryStructuralExperienceGraphResult",
    "build_repository_structural_experience_graph",
]
