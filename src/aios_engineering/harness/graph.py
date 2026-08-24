"""Exact-snapshot static Python import graph supporting canonical H2."""
from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Sequence

from src.aios_engineering.harness import roles as roles_module
from src.aios_engineering.harness.contracts import (
    HarnessReceipt,
    RepositoryEvidenceRef,
    RepositorySnapshotRef,
    _validate_hex_40,
    _validate_hex_64,
    _validate_posix_path,
    _validate_task_id,
)
from src.aios_engineering.harness.errors import (
    HarnessError,
    HarnessFingerprintError,
    HarnessValidationError,
)
from src.aios_engineering.harness.fingerprint import canonical_json_bytes, compute_sha256
from src.aios_engineering.harness.ranking import RepositoryRankingResult
from src.aios_engineering.harness.roles import (
    ContentAnalysisStatus,
    RepositoryRoleSummary,
    RepositoryRoleSummaryResult,
)


H2_IMPORT_GRAPH_POLICY_VERSION: str = "h2-import-graph-v1"
DEPENDENCY_GRAPH_SCHEMA_VERSION: str = "1"

MAX_H2_IMPORT_GRAPH_SELECTED_ITEMS: int = 32
MAX_H2_IMPORT_GRAPH_IMPORT_EDGES_PER_FILE: int = 128
MAX_H2_IMPORT_GRAPH_TOTAL_IMPORT_EDGES: int = 1024
MAX_H2_IMPORT_GRAPH_MODULE_EXPRESSION_LENGTH: int = 256
MAX_H2_IMPORT_GRAPH_IMPORTED_NAME_LENGTH: int = 128
MAX_H2_IMPORT_GRAPH_RELATIVE_LEVEL: int = 64
MAX_H2_IMPORT_GRAPH_TOTAL_BODY_BYTES: int = 4_194_304


class RepositoryDependencyGraphError(HarnessError):
    """Base error for deterministic H2 static-import graph failures."""


class RepositoryDependencyGraphBoundError(RepositoryDependencyGraphError):
    """Raised when an H2 static-import graph resource bound would be exceeded."""


class RepositoryDependencyGraphConsistencyError(RepositoryDependencyGraphError):
    """Raised when exact H2/H3 evidence contradicts static-import re-analysis."""


class ImportDependencyKind(str, Enum):
    """Closed static Python import dependency kinds."""

    IMPORT_MODULE = "IMPORT_MODULE"
    IMPORT_FROM = "IMPORT_FROM"


class ImportResolutionStatus(str, Enum):
    """Closed deterministic internal-resolution outcomes."""

    INTERNAL_SELECTED = "INTERNAL_SELECTED"
    INTERNAL_UNSELECTED = "INTERNAL_UNSELECTED"
    EXTERNAL_OR_UNRESOLVED = "EXTERNAL_OR_UNRESOLVED"
    AMBIGUOUS_INTERNAL = "AMBIGUOUS_INTERNAL"


def _validate_bounded_text(
    value: Any,
    field_name: str,
    maximum_length: int,
    *,
    allow_empty: bool,
) -> str:
    if type(value) is not str or (not allow_empty and not value):
        qualifier = "a string" if allow_empty else "a non-empty string"
        raise HarnessValidationError(f"{field_name} must be {qualifier}: got {value!r}")
    if len(value) > maximum_length:
        raise RepositoryDependencyGraphBoundError(
            f"{field_name} length ({len(value)}) exceeds hard limit ({maximum_length})"
        )
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise HarnessValidationError(f"{field_name} must not contain control characters")
    return value


def _edge_payload(
    *,
    source_path: str,
    source_blob_sha: str,
    kind: ImportDependencyKind,
    module_expression: str,
    imported_name: str | None,
    relative_level: int,
    line_number: int,
    column_offset: int,
    resolution_status: ImportResolutionStatus,
    target_path: str | None,
    target_blob_sha: str | None,
    target_selected: bool | None,
) -> dict[str, Any]:
    return {
        "column_offset": column_offset,
        "imported_name": imported_name,
        "kind": kind.value,
        "line_number": line_number,
        "module_expression": module_expression,
        "policy_version": H2_IMPORT_GRAPH_POLICY_VERSION,
        "relative_level": relative_level,
        "resolution_status": resolution_status.value,
        "source_blob_sha": source_blob_sha,
        "source_path": source_path,
        "target_blob_sha": target_blob_sha,
        "target_path": target_path,
        "target_selected": target_selected,
    }


def _compute_edge_fingerprint(
    *,
    source_path: str,
    source_blob_sha: str,
    kind: ImportDependencyKind,
    module_expression: str,
    imported_name: str | None,
    relative_level: int,
    line_number: int,
    column_offset: int,
    resolution_status: ImportResolutionStatus,
    target_path: str | None,
    target_blob_sha: str | None,
    target_selected: bool | None,
) -> str:
    return compute_sha256(
        canonical_json_bytes(
            _edge_payload(
                source_path=source_path,
                source_blob_sha=source_blob_sha,
                kind=kind,
                module_expression=module_expression,
                imported_name=imported_name,
                relative_level=relative_level,
                line_number=line_number,
                column_offset=column_offset,
                resolution_status=resolution_status,
                target_path=target_path,
                target_blob_sha=target_blob_sha,
                target_selected=target_selected,
            )
        )
    )


@dataclass(frozen=True)
class RepositoryImportDependency:
    """One immutable, fingerprint-bound static import edge."""

    source_path: str
    source_blob_sha: str
    kind: ImportDependencyKind
    module_expression: str
    imported_name: str | None
    relative_level: int
    line_number: int
    column_offset: int
    resolution_status: ImportResolutionStatus
    target_path: str | None
    target_blob_sha: str | None
    target_selected: bool | None
    edge_fingerprint: str

    def __post_init__(self) -> None:
        _validate_posix_path(self.source_path)
        _validate_hex_40(self.source_blob_sha, "source_blob_sha")
        if type(self.kind) is not ImportDependencyKind:
            raise HarnessValidationError(
                f"kind must be an exact ImportDependencyKind value: got {self.kind!r}"
            )
        _validate_bounded_text(
            self.module_expression,
            "module_expression",
            MAX_H2_IMPORT_GRAPH_MODULE_EXPRESSION_LENGTH,
            allow_empty=self.kind is ImportDependencyKind.IMPORT_FROM,
        )
        if self.imported_name is not None:
            _validate_bounded_text(
                self.imported_name,
                "imported_name",
                MAX_H2_IMPORT_GRAPH_IMPORTED_NAME_LENGTH,
                allow_empty=False,
            )
        if self.kind is ImportDependencyKind.IMPORT_MODULE:
            if self.imported_name is not None or self.relative_level != 0:
                raise HarnessValidationError(
                    "IMPORT_MODULE edges require imported_name=None and relative_level=0"
                )
        elif self.imported_name is None:
            raise HarnessValidationError("IMPORT_FROM edges require imported_name")

        if type(self.relative_level) is not int or not (
            0 <= self.relative_level <= MAX_H2_IMPORT_GRAPH_RELATIVE_LEVEL
        ):
            raise HarnessValidationError(
                "relative_level must be an exact integer between 0 and "
                f"{MAX_H2_IMPORT_GRAPH_RELATIVE_LEVEL}: got {self.relative_level!r}"
            )
        if type(self.line_number) is not int or self.line_number <= 0:
            raise HarnessValidationError(
                f"line_number must be an exact positive integer: got {self.line_number!r}"
            )
        if type(self.column_offset) is not int or self.column_offset < 0:
            raise HarnessValidationError(
                "column_offset must be an exact non-negative integer: "
                f"got {self.column_offset!r}"
            )
        if type(self.resolution_status) is not ImportResolutionStatus:
            raise HarnessValidationError(
                "resolution_status must be an exact ImportResolutionStatus value: "
                f"got {self.resolution_status!r}"
            )

        resolved = self.resolution_status in {
            ImportResolutionStatus.INTERNAL_SELECTED,
            ImportResolutionStatus.INTERNAL_UNSELECTED,
        }
        if resolved:
            if self.target_path is None or self.target_blob_sha is None:
                raise HarnessValidationError(
                    "resolved internal edges require exact target path and blob SHA"
                )
            _validate_posix_path(self.target_path)
            _validate_hex_40(self.target_blob_sha, "target_blob_sha")
            if type(self.target_selected) is not bool:
                raise HarnessValidationError(
                    "resolved internal edges require an exact boolean target_selected"
                )
            expected_selected = (
                self.resolution_status is ImportResolutionStatus.INTERNAL_SELECTED
            )
            if self.target_selected is not expected_selected:
                raise HarnessValidationError(
                    "internal resolution status must match target_selected"
                )
        elif (
            self.target_path is not None
            or self.target_blob_sha is not None
            or self.target_selected is not None
        ):
            raise HarnessValidationError(
                "unresolved or ambiguous edges require all target fields to be null"
            )

        _validate_hex_64(self.edge_fingerprint, "edge_fingerprint")
        expected_fingerprint = _compute_edge_fingerprint(
            source_path=self.source_path,
            source_blob_sha=self.source_blob_sha,
            kind=self.kind,
            module_expression=self.module_expression,
            imported_name=self.imported_name,
            relative_level=self.relative_level,
            line_number=self.line_number,
            column_offset=self.column_offset,
            resolution_status=self.resolution_status,
            target_path=self.target_path,
            target_blob_sha=self.target_blob_sha,
            target_selected=self.target_selected,
        )
        if self.edge_fingerprint != expected_fingerprint:
            raise HarnessFingerprintError(
                "Import dependency edge fingerprint mismatch: "
                f"expected {expected_fingerprint}, got {self.edge_fingerprint}"
            )

    @classmethod
    def create(
        cls,
        *,
        source_path: str,
        source_blob_sha: str,
        kind: ImportDependencyKind,
        module_expression: str,
        imported_name: str | None,
        relative_level: int,
        line_number: int,
        column_offset: int,
        resolution_status: ImportResolutionStatus,
        target_path: str | None = None,
        target_blob_sha: str | None = None,
        target_selected: bool | None = None,
    ) -> "RepositoryImportDependency":
        """Create one edge with its canonical H2 static-import fingerprint."""

        fingerprint = _compute_edge_fingerprint(
            source_path=source_path,
            source_blob_sha=source_blob_sha,
            kind=kind,
            module_expression=module_expression,
            imported_name=imported_name,
            relative_level=relative_level,
            line_number=line_number,
            column_offset=column_offset,
            resolution_status=resolution_status,
            target_path=target_path,
            target_blob_sha=target_blob_sha,
            target_selected=target_selected,
        )
        return cls(
            source_path=source_path,
            source_blob_sha=source_blob_sha,
            kind=kind,
            module_expression=module_expression,
            imported_name=imported_name,
            relative_level=relative_level,
            line_number=line_number,
            column_offset=column_offset,
            resolution_status=resolution_status,
            target_path=target_path,
            target_blob_sha=target_blob_sha,
            target_selected=target_selected,
            edge_fingerprint=fingerprint,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **_edge_payload(
                source_path=self.source_path,
                source_blob_sha=self.source_blob_sha,
                kind=self.kind,
                module_expression=self.module_expression,
                imported_name=self.imported_name,
                relative_level=self.relative_level,
                line_number=self.line_number,
                column_offset=self.column_offset,
                resolution_status=self.resolution_status,
                target_path=self.target_path,
                target_blob_sha=self.target_blob_sha,
                target_selected=self.target_selected,
            ),
            "edge_fingerprint": self.edge_fingerprint,
        }


def _result_payload(
    *,
    schema_version: str,
    policy_version: str,
    task_id: str,
    snapshot: RepositorySnapshotRef,
    ranking_fingerprint: str,
    h2_plan_fingerprint: str,
    h3_role_summary_fingerprint: str,
    source_summary_fingerprints: Sequence[str],
    edges: Sequence[RepositoryImportDependency],
) -> dict[str, Any]:
    return {
        "edges": [edge.to_dict() for edge in edges],
        "h2_plan_fingerprint": h2_plan_fingerprint,
        "h3_role_summary_fingerprint": h3_role_summary_fingerprint,
        "policy_version": policy_version,
        "ranking_fingerprint": ranking_fingerprint,
        "schema_version": schema_version,
        "snapshot": snapshot.to_dict(),
        "source_summary_fingerprints": list(source_summary_fingerprints),
        "task_id": task_id,
    }


def _compute_graph_fingerprint(
    *,
    schema_version: str,
    policy_version: str,
    task_id: str,
    snapshot: RepositorySnapshotRef,
    ranking_fingerprint: str,
    h2_plan_fingerprint: str,
    h3_role_summary_fingerprint: str,
    source_summary_fingerprints: Sequence[str],
    edges: Sequence[RepositoryImportDependency],
) -> str:
    return compute_sha256(
        canonical_json_bytes(
            _result_payload(
                schema_version=schema_version,
                policy_version=policy_version,
                task_id=task_id,
                snapshot=snapshot,
                ranking_fingerprint=ranking_fingerprint,
                h2_plan_fingerprint=h2_plan_fingerprint,
                h3_role_summary_fingerprint=h3_role_summary_fingerprint,
                source_summary_fingerprints=source_summary_fingerprints,
                edges=edges,
            )
        )
    )


def _edge_identity(edge: RepositoryImportDependency) -> tuple[Any, ...]:
    return (
        edge.source_path,
        edge.source_blob_sha,
        edge.kind,
        edge.module_expression,
        edge.imported_name,
        edge.relative_level,
        edge.line_number,
        edge.column_offset,
        edge.resolution_status,
        edge.target_path,
        edge.target_blob_sha,
        edge.target_selected,
    )


def _edge_order_key(edge: RepositoryImportDependency) -> tuple[Any, ...]:
    return (
        edge.line_number,
        edge.column_offset,
        edge.kind.value,
        edge.module_expression,
        edge.imported_name is not None,
        edge.imported_name or "",
        edge.target_path is not None,
        edge.target_path or "",
    )


@dataclass(frozen=True)
class RepositoryDependencyGraphResult:
    """Immutable static-import graph supporting canonical H2."""

    task_id: str
    snapshot: RepositorySnapshotRef
    ranking_fingerprint: str
    h2_plan_fingerprint: str
    h3_role_summary_fingerprint: str
    source_summary_fingerprints: tuple[str, ...]
    edges: tuple[RepositoryImportDependency, ...]
    graph_fingerprint: str
    schema_version: str = DEPENDENCY_GRAPH_SCHEMA_VERSION
    policy_version: str = H2_IMPORT_GRAPH_POLICY_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DEPENDENCY_GRAPH_SCHEMA_VERSION:
            raise HarnessValidationError(
                f"schema_version must be {DEPENDENCY_GRAPH_SCHEMA_VERSION!r}: "
                f"got {self.schema_version!r}"
            )
        if self.policy_version != H2_IMPORT_GRAPH_POLICY_VERSION:
            raise HarnessValidationError(
                f"policy_version must be {H2_IMPORT_GRAPH_POLICY_VERSION!r}: "
                f"got {self.policy_version!r}"
            )
        _validate_task_id(self.task_id)
        if type(self.snapshot) is not RepositorySnapshotRef:
            raise HarnessValidationError(
                f"snapshot must be an exact RepositorySnapshotRef: got {self.snapshot!r}"
            )
        RepositorySnapshotRef(
            repository_commit_sha=self.snapshot.repository_commit_sha,
            repository_tree_sha=self.snapshot.repository_tree_sha,
            schema_version=self.snapshot.schema_version,
        )
        _validate_hex_64(self.ranking_fingerprint, "ranking_fingerprint")
        _validate_hex_64(self.h2_plan_fingerprint, "h2_plan_fingerprint")
        _validate_hex_64(
            self.h3_role_summary_fingerprint,
            "h3_role_summary_fingerprint",
        )
        if type(self.source_summary_fingerprints) is not tuple:
            raise HarnessValidationError("source_summary_fingerprints must be an exact tuple")
        if len(self.source_summary_fingerprints) > MAX_H2_IMPORT_GRAPH_SELECTED_ITEMS:
            raise RepositoryDependencyGraphBoundError(
                "source summary count exceeds the H2 static-import graph hard limit "
                f"({MAX_H2_IMPORT_GRAPH_SELECTED_ITEMS})"
            )
        for fingerprint in self.source_summary_fingerprints:
            _validate_hex_64(fingerprint, "source_summary_fingerprint")

        if type(self.edges) is not tuple:
            raise HarnessValidationError("edges must be an exact tuple")
        if len(self.edges) > MAX_H2_IMPORT_GRAPH_TOTAL_IMPORT_EDGES:
            raise RepositoryDependencyGraphBoundError(
                f"total import edge count exceeds hard limit ({MAX_H2_IMPORT_GRAPH_TOTAL_IMPORT_EDGES})"
            )
        seen_edges: set[tuple[Any, ...]] = set()
        closed_sources: set[tuple[str, str]] = set()
        current_source: tuple[str, str] | None = None
        current_edges: list[RepositoryImportDependency] = []

        def validate_current_group() -> None:
            if len(current_edges) > MAX_H2_IMPORT_GRAPH_IMPORT_EDGES_PER_FILE:
                raise RepositoryDependencyGraphBoundError(
                    "per-file import edge count exceeds hard limit "
                    f"({MAX_H2_IMPORT_GRAPH_IMPORT_EDGES_PER_FILE})"
                )
            if current_edges != sorted(current_edges, key=_edge_order_key):
                raise HarnessValidationError(
                    "dependency edges within one source must use deterministic H2 ordering"
                )

        for edge in self.edges:
            if type(edge) is not RepositoryImportDependency:
                raise HarnessValidationError(
                    "edges must contain exact RepositoryImportDependency values: "
                    f"got {edge!r}"
                )
            RepositoryImportDependency(
                source_path=edge.source_path,
                source_blob_sha=edge.source_blob_sha,
                kind=edge.kind,
                module_expression=edge.module_expression,
                imported_name=edge.imported_name,
                relative_level=edge.relative_level,
                line_number=edge.line_number,
                column_offset=edge.column_offset,
                resolution_status=edge.resolution_status,
                target_path=edge.target_path,
                target_blob_sha=edge.target_blob_sha,
                target_selected=edge.target_selected,
                edge_fingerprint=edge.edge_fingerprint,
            )
            identity = _edge_identity(edge)
            if identity in seen_edges:
                raise HarnessValidationError("duplicate exact dependency edge identity rejected")
            seen_edges.add(identity)

            source = (edge.source_path, edge.source_blob_sha)
            if source != current_source:
                if current_source is not None:
                    validate_current_group()
                    closed_sources.add(current_source)
                if source in closed_sources:
                    raise HarnessValidationError(
                        "dependency edges for one source must form one contiguous group"
                    )
                current_source = source
                current_edges = []
            current_edges.append(edge)
        if current_source is not None:
            validate_current_group()

        _validate_hex_64(self.graph_fingerprint, "graph_fingerprint")
        expected_fingerprint = _compute_graph_fingerprint(
            schema_version=self.schema_version,
            policy_version=self.policy_version,
            task_id=self.task_id,
            snapshot=self.snapshot,
            ranking_fingerprint=self.ranking_fingerprint,
            h2_plan_fingerprint=self.h2_plan_fingerprint,
            h3_role_summary_fingerprint=self.h3_role_summary_fingerprint,
            source_summary_fingerprints=self.source_summary_fingerprints,
            edges=self.edges,
        )
        if self.graph_fingerprint != expected_fingerprint:
            raise HarnessFingerprintError(
                "Dependency graph fingerprint mismatch: "
                f"expected {expected_fingerprint}, got {self.graph_fingerprint}"
            )

    @classmethod
    def create(
        cls,
        ranking: RepositoryRankingResult,
        roles: RepositoryRoleSummaryResult,
        edges: tuple[RepositoryImportDependency, ...],
    ) -> "RepositoryDependencyGraphResult":
        """Create a graph after exact upstream and edge-semantic revalidation."""

        _revalidate_upstream_bindings(ranking, roles)
        if type(edges) is not tuple:
            raise HarnessValidationError("edges must be an exact tuple")

        alias_index, candidates_by_path = _build_alias_index(ranking)
        selected_positions = {
            (evidence.path, evidence.blob_sha): position
            for position, evidence in enumerate(ranking.plan.selected_evidence)
        }
        previous_source_position = -1
        for edge in edges:
            if type(edge) is not RepositoryImportDependency:
                raise HarnessValidationError(
                    "edges must contain exact RepositoryImportDependency values"
                )
            source_identity = (edge.source_path, edge.source_blob_sha)
            if source_identity not in selected_positions:
                raise HarnessValidationError(
                    "every dependency edge source must be exact H2 selected evidence"
                )
            source_position = selected_positions[source_identity]
            if source_position < previous_source_position:
                raise HarnessValidationError(
                    "dependency graph must preserve H2 selected source order"
                )
            previous_source_position = source_position
            summary = roles.summaries[source_position]
            if (
                not edge.source_path.endswith(".py")
                or summary.analysis_status is not ContentAnalysisStatus.PARSED
            ):
                raise HarnessValidationError(
                    "dependency edges may originate only from selected PARSED Python sources"
                )
            expected_resolution = _resolve_import(
                source_path=edge.source_path,
                kind=edge.kind,
                module_expression=edge.module_expression,
                relative_level=edge.relative_level,
                alias_index=alias_index,
                candidates_by_path=candidates_by_path,
            )
            actual_resolution = (
                edge.resolution_status,
                edge.target_path,
                edge.target_blob_sha,
                edge.target_selected,
            )
            if actual_resolution != expected_resolution:
                raise HarnessValidationError(
                    "dependency edge resolution does not match the H2 import alias policy"
                )

        source_summary_fingerprints = tuple(
            summary.summary_fingerprint for summary in roles.summaries
        )
        graph_fingerprint = _compute_graph_fingerprint(
            schema_version=DEPENDENCY_GRAPH_SCHEMA_VERSION,
            policy_version=H2_IMPORT_GRAPH_POLICY_VERSION,
            task_id=ranking.task_id,
            snapshot=ranking.plan.snapshot,
            ranking_fingerprint=ranking.ranking_fingerprint,
            h2_plan_fingerprint=ranking.plan.plan_fingerprint,
            h3_role_summary_fingerprint=roles.role_summary_fingerprint,
            source_summary_fingerprints=source_summary_fingerprints,
            edges=edges,
        )
        return cls(
            task_id=ranking.task_id,
            snapshot=ranking.plan.snapshot,
            ranking_fingerprint=ranking.ranking_fingerprint,
            h2_plan_fingerprint=ranking.plan.plan_fingerprint,
            h3_role_summary_fingerprint=roles.role_summary_fingerprint,
            source_summary_fingerprints=source_summary_fingerprints,
            edges=edges,
            graph_fingerprint=graph_fingerprint,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **_result_payload(
                schema_version=self.schema_version,
                policy_version=self.policy_version,
                task_id=self.task_id,
                snapshot=self.snapshot,
                ranking_fingerprint=self.ranking_fingerprint,
                h2_plan_fingerprint=self.h2_plan_fingerprint,
                h3_role_summary_fingerprint=self.h3_role_summary_fingerprint,
                source_summary_fingerprints=self.source_summary_fingerprints,
                edges=self.edges,
            ),
            "graph_fingerprint": self.graph_fingerprint,
        }


@dataclass(frozen=True)
class _CandidateMetadata:
    path: str
    blob_sha: str
    selected: bool
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class _ImportRecord:
    kind: ImportDependencyKind
    module_expression: str
    imported_name: str | None
    relative_level: int
    line_number: int
    column_offset: int


def _revalidate_upstream_bindings(
    ranking: RepositoryRankingResult,
    roles: RepositoryRoleSummaryResult,
) -> None:
    roles_module._revalidate_ranking(ranking)
    if len(ranking.plan.selected_evidence) > MAX_H2_IMPORT_GRAPH_SELECTED_ITEMS:
        raise RepositoryDependencyGraphBoundError(
            "H2 selected evidence count exceeds the static-import graph hard limit "
            f"({MAX_H2_IMPORT_GRAPH_SELECTED_ITEMS})"
        )
    if type(roles) is not RepositoryRoleSummaryResult:
        raise HarnessValidationError(
            f"roles must be an exact RepositoryRoleSummaryResult: got {roles!r}"
        )
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

    if ranking.task_id != roles.task_id:
        raise HarnessValidationError("H2 and H3 task_id bindings must match exactly")
    if ranking.plan.snapshot != roles.snapshot:
        raise HarnessValidationError("H2 and H3 snapshot bindings must match exactly")
    if ranking.ranking_fingerprint != roles.ranking_fingerprint:
        raise HarnessValidationError("H2 and H3 ranking fingerprints must match exactly")
    if ranking.plan.plan_fingerprint != roles.h2_plan_fingerprint:
        raise HarnessValidationError("H2 plan and H3 plan fingerprints must match exactly")
    if len(ranking.plan.selected_evidence) != len(roles.summaries):
        raise HarnessValidationError(
            "H2 selected evidence and H3 summary counts must match exactly"
        )
    for evidence, summary in zip(ranking.plan.selected_evidence, roles.summaries):
        if (
            evidence.path != summary.path
            or evidence.blob_sha != summary.blob_sha
            or evidence.evidence_kind is not summary.evidence_kind
            or evidence.priority != summary.h2_priority
        ):
            raise HarnessValidationError(
                "H2 selected evidence and H3 summaries must preserve exact positional "
                "path/blob/kind/priority bindings"
            )


def _candidate_aliases(path: str) -> tuple[str, ...]:
    if not path.endswith(".py"):
        return ()
    canonical_alias = path[:-3].replace("/", ".")
    if canonical_alias.endswith(".__init__"):
        canonical_alias = canonical_alias.removesuffix(".__init__")
    aliases = {canonical_alias} if canonical_alias else set()
    if path.startswith("src/") and canonical_alias.startswith("src."):
        source_layout_alias = canonical_alias[4:]
        if source_layout_alias:
            aliases.add(source_layout_alias)
    return tuple(sorted(aliases))


def _build_alias_index(
    ranking: RepositoryRankingResult,
) -> tuple[
    dict[str, tuple[_CandidateMetadata, ...]],
    dict[str, _CandidateMetadata],
]:
    candidates_by_path: dict[str, _CandidateMetadata] = {}
    ordered_candidates: list[_CandidateMetadata] = []
    for selected, evidence_values in (
        (True, ranking.plan.selected_evidence),
        (False, tuple(item.evidence for item in ranking.plan.excluded_evidence)),
    ):
        for evidence in evidence_values:
            if type(evidence) is not RepositoryEvidenceRef:
                raise HarnessValidationError(
                    "H2 candidate metadata must contain exact RepositoryEvidenceRef values"
                )
            if evidence.path in candidates_by_path:
                raise HarnessValidationError(
                    f"duplicate H2 candidate path rejected: {evidence.path}"
                )
            metadata = _CandidateMetadata(
                path=evidence.path,
                blob_sha=evidence.blob_sha,
                selected=selected,
                aliases=_candidate_aliases(evidence.path),
            )
            candidates_by_path[evidence.path] = metadata
            ordered_candidates.append(metadata)

    mutable_index: dict[str, list[_CandidateMetadata]] = {}
    for candidate in ordered_candidates:
        for alias in candidate.aliases:
            mutable_index.setdefault(alias, []).append(candidate)
    alias_index = {
        alias: tuple(
            sorted(
                candidates,
                key=lambda item: (item.path, item.blob_sha, not item.selected),
            )
        )
        for alias, candidates in mutable_index.items()
    }
    return alias_index, candidates_by_path


def _source_package_aliases(
    source_path: str,
    candidates_by_path: dict[str, _CandidateMetadata],
) -> tuple[str, ...]:
    source = candidates_by_path.get(source_path)
    if source is None or not source.selected:
        raise HarnessValidationError("relative import source must be exact selected metadata")
    is_package_init = source_path.rsplit("/", 1)[-1] == "__init__.py"
    package_aliases: set[str] = set()
    for alias in source.aliases:
        if is_package_init:
            package_alias = alias
        elif "." in alias:
            package_alias = alias.rsplit(".", 1)[0]
        else:
            continue
        if package_alias:
            package_aliases.add(package_alias)
    return tuple(sorted(package_aliases))


def _collapse_resolution_candidates(
    module_aliases: Sequence[str],
    alias_index: dict[str, tuple[_CandidateMetadata, ...]],
) -> tuple[ImportResolutionStatus, str | None, str | None, bool | None]:
    matches = {
        (candidate.path, candidate.blob_sha, candidate.selected)
        for module_alias in module_aliases
        for candidate in alias_index.get(module_alias, ())
    }
    if not matches:
        return (
            ImportResolutionStatus.EXTERNAL_OR_UNRESOLVED,
            None,
            None,
            None,
        )
    if len(matches) > 1:
        return (ImportResolutionStatus.AMBIGUOUS_INTERNAL, None, None, None)
    target_path, target_blob_sha, target_selected = next(iter(matches))
    status = (
        ImportResolutionStatus.INTERNAL_SELECTED
        if target_selected
        else ImportResolutionStatus.INTERNAL_UNSELECTED
    )
    return status, target_path, target_blob_sha, target_selected


def _resolve_import(
    *,
    source_path: str,
    kind: ImportDependencyKind,
    module_expression: str,
    relative_level: int,
    alias_index: dict[str, tuple[_CandidateMetadata, ...]],
    candidates_by_path: dict[str, _CandidateMetadata],
) -> tuple[ImportResolutionStatus, str | None, str | None, bool | None]:
    if kind is ImportDependencyKind.IMPORT_MODULE or relative_level == 0:
        if not module_expression:
            return (
                ImportResolutionStatus.EXTERNAL_OR_UNRESOLVED,
                None,
                None,
                None,
            )
        return _collapse_resolution_candidates((module_expression,), alias_index)

    module_aliases: list[str] = []
    remove_segments = relative_level - 1
    for package_alias in _source_package_aliases(source_path, candidates_by_path):
        segments = package_alias.split(".")
        if remove_segments >= len(segments):
            continue
        base_segments = segments[: len(segments) - remove_segments]
        if module_expression:
            base_segments.extend(module_expression.split("."))
        resolved_alias = ".".join(base_segments)
        if resolved_alias:
            module_aliases.append(resolved_alias)
    return _collapse_resolution_candidates(tuple(sorted(set(module_aliases))), alias_index)


def _import_record_order_key(record: _ImportRecord) -> tuple[Any, ...]:
    return (
        record.line_number,
        record.column_offset,
        record.kind.value,
        record.module_expression,
        record.imported_name is not None,
        record.imported_name or "",
    )


def _extract_import_records(tree: ast.Module) -> tuple[_ImportRecord, ...]:
    records: list[_ImportRecord] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                record = _ImportRecord(
                    kind=ImportDependencyKind.IMPORT_MODULE,
                    module_expression=alias.name,
                    imported_name=None,
                    relative_level=0,
                    line_number=node.lineno,
                    column_offset=node.col_offset,
                )
                _validate_bounded_text(
                    record.module_expression,
                    "module_expression",
                    MAX_H2_IMPORT_GRAPH_MODULE_EXPRESSION_LENGTH,
                    allow_empty=False,
                )
                records.append(record)
        elif isinstance(node, ast.ImportFrom):
            module_expression = node.module or ""
            if type(node.level) is not int or node.level < 0:
                raise HarnessValidationError(
                    "AST relative import level must be an exact non-negative integer"
                )
            if node.level > MAX_H2_IMPORT_GRAPH_RELATIVE_LEVEL:
                raise RepositoryDependencyGraphBoundError(
                    f"relative import level exceeds hard limit ({MAX_H2_IMPORT_GRAPH_RELATIVE_LEVEL})"
                )
            _validate_bounded_text(
                module_expression,
                "module_expression",
                MAX_H2_IMPORT_GRAPH_MODULE_EXPRESSION_LENGTH,
                allow_empty=True,
            )
            for alias in node.names:
                _validate_bounded_text(
                    alias.name,
                    "imported_name",
                    MAX_H2_IMPORT_GRAPH_IMPORTED_NAME_LENGTH,
                    allow_empty=False,
                )
                records.append(
                    _ImportRecord(
                        kind=ImportDependencyKind.IMPORT_FROM,
                        module_expression=module_expression,
                        imported_name=alias.name,
                        relative_level=node.level,
                        line_number=node.lineno,
                        column_offset=node.col_offset,
                    )
                )
        if len(records) > MAX_H2_IMPORT_GRAPH_IMPORT_EDGES_PER_FILE:
            raise RepositoryDependencyGraphBoundError(
                "per-file import edge count exceeds hard limit "
                f"({MAX_H2_IMPORT_GRAPH_IMPORT_EDGES_PER_FILE})"
            )
    records.sort(key=_import_record_order_key)
    return tuple(records)


def _read_parsed_python_tree(
    repository_root: Path,
    evidence: RepositoryEvidenceRef,
    summary: RepositoryRoleSummary,
    aggregate_body_bytes: int,
) -> tuple[ast.Module, int]:
    blob_size_bytes = roles_module._read_blob_size(repository_root, evidence.blob_sha)
    if blob_size_bytes != summary.blob_size_bytes:
        raise RepositoryDependencyGraphConsistencyError(
            "H3 PARSED blob size contradicts exact H2 static-import Git preflight size"
        )
    if blob_size_bytes > roles_module.MAX_H3_BLOB_BYTES:
        raise RepositoryDependencyGraphConsistencyError(
            "H3 PARSED blob exceeds the locked H3 per-blob body bound"
        )
    if aggregate_body_bytes + blob_size_bytes > MAX_H2_IMPORT_GRAPH_TOTAL_BODY_BYTES:
        raise RepositoryDependencyGraphBoundError(
            "H2 static-import aggregate body bytes exceed hard limit "
            f"({MAX_H2_IMPORT_GRAPH_TOTAL_BODY_BYTES})"
        )

    body = roles_module._read_blob_body(repository_root, evidence.blob_sha, blob_size_bytes)
    try:
        source = body.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise RepositoryDependencyGraphConsistencyError(
            "H3 PARSED source no longer decodes as strict UTF-8"
        ) from exc
    try:
        tree = ast.parse(source, filename=evidence.path, mode="exec")
    except (SyntaxError, ValueError) as exc:
        raise RepositoryDependencyGraphConsistencyError(
            "H3 PARSED source no longer parses as a Python module"
        ) from exc
    return tree, aggregate_body_bytes + blob_size_bytes


def build_repository_dependency_graph(
    repo_root: Path | str,
    ranking: RepositoryRankingResult,
    roles: RepositoryRoleSummaryResult,
) -> tuple[RepositoryDependencyGraphResult, HarnessReceipt]:
    """Build one exact H2/H3-bound static import graph using local Git blobs only."""

    # The complete H2/H3 cross-binding gate intentionally precedes all Git plumbing.
    _revalidate_upstream_bindings(ranking, roles)
    alias_index, candidates_by_path = _build_alias_index(ranking)
    repository_root = roles_module._validate_repository_root(repo_root)
    roles_module._verify_exact_snapshot(repository_root, ranking.plan.snapshot)

    edges: list[RepositoryImportDependency] = []
    aggregate_body_bytes = 0
    for evidence, summary in zip(ranking.plan.selected_evidence, roles.summaries):
        if (
            not evidence.path.endswith(".py")
            or summary.analysis_status is not ContentAnalysisStatus.PARSED
        ):
            continue
        tree, aggregate_body_bytes = _read_parsed_python_tree(
            repository_root,
            evidence,
            summary,
            aggregate_body_bytes,
        )
        records = _extract_import_records(tree)
        if len(edges) + len(records) > MAX_H2_IMPORT_GRAPH_TOTAL_IMPORT_EDGES:
            raise RepositoryDependencyGraphBoundError(
                f"total import edge count exceeds hard limit ({MAX_H2_IMPORT_GRAPH_TOTAL_IMPORT_EDGES})"
            )

        source_edges: list[RepositoryImportDependency] = []
        for record in records:
            status, target_path, target_blob_sha, target_selected = _resolve_import(
                source_path=evidence.path,
                kind=record.kind,
                module_expression=record.module_expression,
                relative_level=record.relative_level,
                alias_index=alias_index,
                candidates_by_path=candidates_by_path,
            )
            source_edges.append(
                RepositoryImportDependency.create(
                    source_path=evidence.path,
                    source_blob_sha=evidence.blob_sha,
                    kind=record.kind,
                    module_expression=record.module_expression,
                    imported_name=record.imported_name,
                    relative_level=record.relative_level,
                    line_number=record.line_number,
                    column_offset=record.column_offset,
                    resolution_status=status,
                    target_path=target_path,
                    target_blob_sha=target_blob_sha,
                    target_selected=target_selected,
                )
            )
        source_edges.sort(key=_edge_order_key)
        seen_source_edges: set[tuple[Any, ...]] = set()
        for edge in source_edges:
            identity = _edge_identity(edge)
            if identity in seen_source_edges:
                raise HarnessValidationError(
                    "duplicate exact dependency edge identity rejected"
                )
            seen_source_edges.add(identity)
        edges.extend(source_edges)

    edges_tuple = tuple(edges)
    result = RepositoryDependencyGraphResult.create(ranking, roles, edges_tuple)
    source_summary_fingerprints = tuple(
        summary.summary_fingerprint for summary in roles.summaries
    )
    input_fingerprint = compute_sha256(
        canonical_json_bytes(
            {
                "h2_plan_fingerprint": ranking.plan.plan_fingerprint,
                "h3_role_summary_fingerprint": roles.role_summary_fingerprint,
                "operation": "h2_repository_import_dependency_graph",
                "policy_version": H2_IMPORT_GRAPH_POLICY_VERSION,
                "ranking_fingerprint": ranking.ranking_fingerprint,
                "schema_version": DEPENDENCY_GRAPH_SCHEMA_VERSION,
                "snapshot": ranking.plan.snapshot.to_dict(),
                "source_summary_fingerprints": list(source_summary_fingerprints),
                "task_id": ranking.task_id,
            }
        )
    )
    receipt = HarnessReceipt(
        task_id=ranking.task_id,
        repository_commit_sha=ranking.plan.snapshot.repository_commit_sha,
        input_fingerprint=input_fingerprint,
        output_fingerprint=result.graph_fingerprint,
        generator_version=H2_IMPORT_GRAPH_POLICY_VERSION,
        candidate_count=len(roles.summaries),
        selected_count=len(roles.summaries),
        excluded_count=0,
    )
    return result, receipt


__all__ = [
    "DEPENDENCY_GRAPH_SCHEMA_VERSION",
    "H2_IMPORT_GRAPH_POLICY_VERSION",
    "ImportDependencyKind",
    "ImportResolutionStatus",
    "MAX_H2_IMPORT_GRAPH_IMPORTED_NAME_LENGTH",
    "MAX_H2_IMPORT_GRAPH_IMPORT_EDGES_PER_FILE",
    "MAX_H2_IMPORT_GRAPH_MODULE_EXPRESSION_LENGTH",
    "MAX_H2_IMPORT_GRAPH_RELATIVE_LEVEL",
    "MAX_H2_IMPORT_GRAPH_SELECTED_ITEMS",
    "MAX_H2_IMPORT_GRAPH_TOTAL_BODY_BYTES",
    "MAX_H2_IMPORT_GRAPH_TOTAL_IMPORT_EDGES",
    "RepositoryDependencyGraphBoundError",
    "RepositoryDependencyGraphConsistencyError",
    "RepositoryDependencyGraphError",
    "RepositoryDependencyGraphResult",
    "RepositoryImportDependency",
    "build_repository_dependency_graph",
]
