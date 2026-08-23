"""Exact-snapshot H3 artifact roles and bounded Python symbol intelligence."""
from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import Enum
import os
from pathlib import Path
import re
import subprocess
from typing import Any, BinaryIO, Sequence

from src.aios_engineering.harness.contracts import (
    EvidenceKind,
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


H3_ROLE_POLICY_VERSION: str = "h3-v1"
ROLE_SUMMARY_SCHEMA_VERSION: str = "1"

MAX_H3_SELECTED_ITEMS: int = 32
MAX_H3_BLOB_BYTES: int = 262_144
MAX_H3_TOTAL_BODY_BYTES: int = 4_194_304
MAX_H3_SYMBOLS_PER_FILE: int = 128
MAX_H3_SYMBOL_NAME_LENGTH: int = 128
MAX_H3_GIT_SCALAR_BYTES: int = 4096

_GIT_READ_CHUNK_BYTES: int = 64 * 1024
_DECIMAL_BYTES_RE = re.compile(rb"\A(?:0|[1-9][0-9]*)\Z")

# Match the H1 closed child boundary. In particular, no caller-controlled
# GIT_* value or provider credential is inherited by local Git plumbing.
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


class RepositoryRoleSummaryError(HarnessError):
    """Base error for exact-snapshot H3 role summarization failures."""


class RepositoryRoleSummaryGitError(RepositoryRoleSummaryError):
    """Raised when required local Git object plumbing fails closed."""


class RepositoryRoleSummaryBoundError(RepositoryRoleSummaryError):
    """Raised when bounded local Git output violates an H3 hard limit."""


class ArtifactRole(str, Enum):
    """One deterministic primary role for a selected H2 artifact."""

    CONTRACT_ARTIFACT = "CONTRACT_ARTIFACT"
    TEST_ARTIFACT = "TEST_ARTIFACT"
    DOCUMENTATION_ARTIFACT = "DOCUMENTATION_ARTIFACT"
    CONFIGURATION_ARTIFACT = "CONFIGURATION_ARTIFACT"
    PACKAGE_EXPORT_SURFACE = "PACKAGE_EXPORT_SURFACE"
    EXECUTABLE_ENTRYPOINT = "EXECUTABLE_ENTRYPOINT"
    SOURCE_IMPLEMENTATION = "SOURCE_IMPLEMENTATION"
    OTHER_ARTIFACT = "OTHER_ARTIFACT"


class ContentAnalysisStatus(str, Enum):
    """Closed accounting status for selected artifact content analysis."""

    PARSED = "PARSED"
    NOT_PYTHON = "NOT_PYTHON"
    CONTENT_BOUND_EXCEEDED = "CONTENT_BOUND_EXCEEDED"
    DECODE_REJECTED = "DECODE_REJECTED"
    SYNTAX_REJECTED = "SYNTAX_REJECTED"


class PythonSymbolKind(str, Enum):
    """Supported top-level Python AST symbol kinds."""

    CLASS = "CLASS"
    FUNCTION = "FUNCTION"
    ASYNC_FUNCTION = "ASYNC_FUNCTION"


def _symbol_locator(kind: PythonSymbolKind, name: str, line_number: int) -> str:
    return f"{kind.value.lower()}:{name}@L{line_number}"


@dataclass(frozen=True)
class PythonSymbolSummary:
    """Bounded, non-executing summary of one top-level Python AST symbol."""

    kind: PythonSymbolKind
    name: str
    line_number: int
    symbol_locator: str

    def __post_init__(self) -> None:
        if type(self.kind) is not PythonSymbolKind:
            raise HarnessValidationError(
                f"kind must be an exact PythonSymbolKind value: got {self.kind!r}"
            )
        if type(self.name) is not str or not self.name or not self.name.isidentifier():
            raise HarnessValidationError(
                f"Python symbol name must be a non-empty identifier: got {self.name!r}"
            )
        if len(self.name) > MAX_H3_SYMBOL_NAME_LENGTH:
            raise HarnessValidationError(
                f"Python symbol name length ({len(self.name)}) exceeds hard limit "
                f"({MAX_H3_SYMBOL_NAME_LENGTH})"
            )
        if type(self.line_number) is not int or self.line_number <= 0:
            raise HarnessValidationError(
                f"line_number must be an exact positive integer: got {self.line_number!r}"
            )
        expected_locator = _symbol_locator(self.kind, self.name, self.line_number)
        if self.symbol_locator != expected_locator:
            raise HarnessValidationError(
                f"symbol_locator must equal deterministic locator {expected_locator!r}"
            )
        if len(self.symbol_locator) > 256 or any(
            ord(character) < 32 or ord(character) == 127
            for character in self.symbol_locator
        ):
            raise HarnessValidationError("symbol_locator must be bounded and control-character free")
        if (
            self.symbol_locator.startswith("/")
            or "\\" in self.symbol_locator
            or (
                len(self.symbol_locator) >= 2
                and self.symbol_locator[1] == ":"
            )
        ):
            raise HarnessValidationError("symbol_locator must not have absolute path semantics")

    @classmethod
    def create(
        cls,
        kind: PythonSymbolKind,
        name: str,
        line_number: int,
    ) -> "PythonSymbolSummary":
        """Create one symbol with its deterministic bounded locator."""

        return cls(
            kind=kind,
            name=name,
            line_number=line_number,
            symbol_locator=_symbol_locator(kind, name, line_number),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "line_number": self.line_number,
            "name": self.name,
            "symbol_locator": self.symbol_locator,
        }


def _summary_payload(
    *,
    path: str,
    blob_sha: str,
    evidence_kind: EvidenceKind,
    h2_priority: int,
    artifact_role: ArtifactRole,
    analysis_status: ContentAnalysisStatus,
    blob_size_bytes: int,
    symbols: Sequence[PythonSymbolSummary],
) -> dict[str, Any]:
    return {
        "analysis_status": analysis_status.value,
        "artifact_role": artifact_role.value,
        "blob_sha": blob_sha,
        "blob_size_bytes": blob_size_bytes,
        "evidence_kind": evidence_kind.value,
        "h2_priority": h2_priority,
        "path": path,
        "policy_version": H3_ROLE_POLICY_VERSION,
        "symbols": [symbol.to_dict() for symbol in symbols],
    }


def _compute_summary_fingerprint(
    *,
    path: str,
    blob_sha: str,
    evidence_kind: EvidenceKind,
    h2_priority: int,
    artifact_role: ArtifactRole,
    analysis_status: ContentAnalysisStatus,
    blob_size_bytes: int,
    symbols: Sequence[PythonSymbolSummary],
) -> str:
    return compute_sha256(
        canonical_json_bytes(
            _summary_payload(
                path=path,
                blob_sha=blob_sha,
                evidence_kind=evidence_kind,
                h2_priority=h2_priority,
                artifact_role=artifact_role,
                analysis_status=analysis_status,
                blob_size_bytes=blob_size_bytes,
                symbols=symbols,
            )
        )
    )


@dataclass(frozen=True)
class RepositoryRoleSummary:
    """Immutable H3 accounting record for one exact H2 selected artifact."""

    path: str
    blob_sha: str
    evidence_kind: EvidenceKind
    h2_priority: int
    artifact_role: ArtifactRole
    analysis_status: ContentAnalysisStatus
    blob_size_bytes: int
    symbols: tuple[PythonSymbolSummary, ...]
    summary_fingerprint: str

    def __post_init__(self) -> None:
        _validate_posix_path(self.path)
        _validate_hex_40(self.blob_sha, "blob_sha")
        if type(self.evidence_kind) is not EvidenceKind:
            raise HarnessValidationError(
                f"evidence_kind must be an exact EvidenceKind value: got {self.evidence_kind!r}"
            )
        if type(self.h2_priority) is not int or not (1 <= self.h2_priority <= 1000):
            raise HarnessValidationError(
                f"h2_priority must be an exact integer between 1 and 1000: {self.h2_priority!r}"
            )
        if type(self.artifact_role) is not ArtifactRole:
            raise HarnessValidationError(
                f"artifact_role must be an exact ArtifactRole value: got {self.artifact_role!r}"
            )
        if type(self.analysis_status) is not ContentAnalysisStatus:
            raise HarnessValidationError(
                "analysis_status must be an exact ContentAnalysisStatus value: "
                f"got {self.analysis_status!r}"
            )
        if type(self.blob_size_bytes) is not int or self.blob_size_bytes < 0:
            raise HarnessValidationError(
                f"blob_size_bytes must be an exact non-negative integer: {self.blob_size_bytes!r}"
            )
        if type(self.symbols) is not tuple:
            raise HarnessValidationError("symbols must be an exact tuple")
        if len(self.symbols) > MAX_H3_SYMBOLS_PER_FILE:
            raise HarnessValidationError(
                f"symbol count ({len(self.symbols)}) exceeds hard limit "
                f"({MAX_H3_SYMBOLS_PER_FILE})"
            )
        for symbol in self.symbols:
            if type(symbol) is not PythonSymbolSummary:
                raise HarnessValidationError(
                    f"symbols must contain exact PythonSymbolSummary values: got {symbol!r}"
                )
            PythonSymbolSummary(
                kind=symbol.kind,
                name=symbol.name,
                line_number=symbol.line_number,
                symbol_locator=symbol.symbol_locator,
            )

        is_python = _is_python_path(self.path)
        if self.analysis_status is ContentAnalysisStatus.NOT_PYTHON and is_python:
            raise HarnessValidationError("Python paths cannot use NOT_PYTHON analysis status")
        if self.analysis_status is not ContentAnalysisStatus.NOT_PYTHON and not is_python:
            raise HarnessValidationError("non-Python paths must use NOT_PYTHON analysis status")
        if self.analysis_status is not ContentAnalysisStatus.PARSED and self.symbols:
            raise HarnessValidationError("non-PARSED summaries must contain zero symbols")
        if (
            self.analysis_status is ContentAnalysisStatus.PARSED
            and self.blob_size_bytes > MAX_H3_BLOB_BYTES
        ):
            raise HarnessValidationError("oversized Python blobs cannot use PARSED analysis status")

        _validate_hex_64(self.summary_fingerprint, "summary_fingerprint")
        expected_fingerprint = _compute_summary_fingerprint(
            path=self.path,
            blob_sha=self.blob_sha,
            evidence_kind=self.evidence_kind,
            h2_priority=self.h2_priority,
            artifact_role=self.artifact_role,
            analysis_status=self.analysis_status,
            blob_size_bytes=self.blob_size_bytes,
            symbols=self.symbols,
        )
        if self.summary_fingerprint != expected_fingerprint:
            raise HarnessFingerprintError(
                "Role summary fingerprint mismatch: "
                f"expected {expected_fingerprint}, got {self.summary_fingerprint}"
            )

    @classmethod
    def create(
        cls,
        *,
        evidence: RepositoryEvidenceRef,
        artifact_role: ArtifactRole,
        analysis_status: ContentAnalysisStatus,
        blob_size_bytes: int,
        symbols: tuple[PythonSymbolSummary, ...],
    ) -> "RepositoryRoleSummary":
        """Create one immutable summary preserving the exact H2 evidence identity."""

        if type(evidence) is not RepositoryEvidenceRef:
            raise HarnessValidationError(
                f"evidence must be an exact RepositoryEvidenceRef: got {evidence!r}"
            )
        summary_fingerprint = _compute_summary_fingerprint(
            path=evidence.path,
            blob_sha=evidence.blob_sha,
            evidence_kind=evidence.evidence_kind,
            h2_priority=evidence.priority,
            artifact_role=artifact_role,
            analysis_status=analysis_status,
            blob_size_bytes=blob_size_bytes,
            symbols=symbols,
        )
        return cls(
            path=evidence.path,
            blob_sha=evidence.blob_sha,
            evidence_kind=evidence.evidence_kind,
            h2_priority=evidence.priority,
            artifact_role=artifact_role,
            analysis_status=analysis_status,
            blob_size_bytes=blob_size_bytes,
            symbols=symbols,
            summary_fingerprint=summary_fingerprint,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **_summary_payload(
                path=self.path,
                blob_sha=self.blob_sha,
                evidence_kind=self.evidence_kind,
                h2_priority=self.h2_priority,
                artifact_role=self.artifact_role,
                analysis_status=self.analysis_status,
                blob_size_bytes=self.blob_size_bytes,
                symbols=self.symbols,
            ),
            "summary_fingerprint": self.summary_fingerprint,
        }


def _result_payload(
    *,
    schema_version: str,
    policy_version: str,
    task_id: str,
    snapshot: RepositorySnapshotRef,
    ranking_fingerprint: str,
    h2_plan_fingerprint: str,
    summaries: Sequence[RepositoryRoleSummary],
) -> dict[str, Any]:
    return {
        "h2_plan_fingerprint": h2_plan_fingerprint,
        "policy_version": policy_version,
        "ranking_fingerprint": ranking_fingerprint,
        "schema_version": schema_version,
        "snapshot": snapshot.to_dict(),
        "summaries": [summary.to_dict() for summary in summaries],
        "task_id": task_id,
    }


def _compute_result_fingerprint(
    *,
    schema_version: str,
    policy_version: str,
    task_id: str,
    snapshot: RepositorySnapshotRef,
    ranking_fingerprint: str,
    h2_plan_fingerprint: str,
    summaries: Sequence[RepositoryRoleSummary],
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
                summaries=summaries,
            )
        )
    )


@dataclass(frozen=True)
class RepositoryRoleSummaryResult:
    """Fingerprint-verified H3 result bound to an exact H2 ranking and snapshot."""

    task_id: str
    snapshot: RepositorySnapshotRef
    ranking_fingerprint: str
    h2_plan_fingerprint: str
    summaries: tuple[RepositoryRoleSummary, ...]
    role_summary_fingerprint: str
    schema_version: str = ROLE_SUMMARY_SCHEMA_VERSION
    policy_version: str = H3_ROLE_POLICY_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != ROLE_SUMMARY_SCHEMA_VERSION:
            raise HarnessValidationError(
                f"schema_version must be {ROLE_SUMMARY_SCHEMA_VERSION!r}: "
                f"got {self.schema_version!r}"
            )
        if self.policy_version != H3_ROLE_POLICY_VERSION:
            raise HarnessValidationError(
                f"policy_version must be {H3_ROLE_POLICY_VERSION!r}: got {self.policy_version!r}"
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
        if type(self.summaries) is not tuple:
            raise HarnessValidationError("summaries must be an exact tuple")
        if len(self.summaries) > MAX_H3_SELECTED_ITEMS:
            raise HarnessValidationError(
                f"summary count ({len(self.summaries)}) exceeds hard limit "
                f"({MAX_H3_SELECTED_ITEMS})"
            )
        seen_identities: set[tuple[str, str]] = set()
        for summary in self.summaries:
            if type(summary) is not RepositoryRoleSummary:
                raise HarnessValidationError(
                    f"summaries must contain exact RepositoryRoleSummary values: got {summary!r}"
                )
            RepositoryRoleSummary(
                path=summary.path,
                blob_sha=summary.blob_sha,
                evidence_kind=summary.evidence_kind,
                h2_priority=summary.h2_priority,
                artifact_role=summary.artifact_role,
                analysis_status=summary.analysis_status,
                blob_size_bytes=summary.blob_size_bytes,
                symbols=summary.symbols,
                summary_fingerprint=summary.summary_fingerprint,
            )
            identity = (summary.path, summary.blob_sha)
            if identity in seen_identities:
                raise HarnessValidationError(
                    f"duplicate role summary identity rejected: {summary.path} ({summary.blob_sha})"
                )
            seen_identities.add(identity)

        _validate_hex_64(self.role_summary_fingerprint, "role_summary_fingerprint")
        expected_fingerprint = _compute_result_fingerprint(
            schema_version=self.schema_version,
            policy_version=self.policy_version,
            task_id=self.task_id,
            snapshot=self.snapshot,
            ranking_fingerprint=self.ranking_fingerprint,
            h2_plan_fingerprint=self.h2_plan_fingerprint,
            summaries=self.summaries,
        )
        if self.role_summary_fingerprint != expected_fingerprint:
            raise HarnessFingerprintError(
                "Role result fingerprint mismatch: "
                f"expected {expected_fingerprint}, got {self.role_summary_fingerprint}"
            )

    @classmethod
    def create(
        cls,
        ranking: RepositoryRankingResult,
        summaries: tuple[RepositoryRoleSummary, ...],
    ) -> "RepositoryRoleSummaryResult":
        """Create a result after exact H2 input/order/identity revalidation."""

        _revalidate_ranking(ranking)
        if type(summaries) is not tuple:
            raise HarnessValidationError("summaries must be an exact tuple")
        selected_evidence = ranking.plan.selected_evidence
        if len(summaries) != len(selected_evidence):
            raise HarnessValidationError(
                "summary count must equal the H2 selected evidence count"
            )
        for evidence, summary in zip(selected_evidence, summaries):
            if type(summary) is not RepositoryRoleSummary:
                raise HarnessValidationError(
                    f"summaries must contain exact RepositoryRoleSummary values: got {summary!r}"
                )
            if (
                summary.path != evidence.path
                or summary.blob_sha != evidence.blob_sha
                or summary.evidence_kind is not evidence.evidence_kind
                or summary.h2_priority != evidence.priority
            ):
                raise HarnessValidationError(
                    "role summaries must preserve exact H2 path/blob/kind/priority order"
                )

        role_summary_fingerprint = _compute_result_fingerprint(
            schema_version=ROLE_SUMMARY_SCHEMA_VERSION,
            policy_version=H3_ROLE_POLICY_VERSION,
            task_id=ranking.task_id,
            snapshot=ranking.plan.snapshot,
            ranking_fingerprint=ranking.ranking_fingerprint,
            h2_plan_fingerprint=ranking.plan.plan_fingerprint,
            summaries=summaries,
        )
        return cls(
            task_id=ranking.task_id,
            snapshot=ranking.plan.snapshot,
            ranking_fingerprint=ranking.ranking_fingerprint,
            h2_plan_fingerprint=ranking.plan.plan_fingerprint,
            summaries=summaries,
            role_summary_fingerprint=role_summary_fingerprint,
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
                summaries=self.summaries,
            ),
            "role_summary_fingerprint": self.role_summary_fingerprint,
        }


def _revalidate_ranking(ranking: RepositoryRankingResult) -> None:
    if type(ranking) is not RepositoryRankingResult:
        raise HarnessValidationError(
            f"ranking must be an exact RepositoryRankingResult: got {ranking!r}"
        )
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
    if ranking.task_id != ranking.plan.task_id:
        raise HarnessValidationError("ranking task_id must equal ranking plan task_id")
    if len(ranking.plan.selected_evidence) > MAX_H3_SELECTED_ITEMS:
        raise HarnessValidationError(
            f"H2 selected evidence count exceeds H3 hard limit ({MAX_H3_SELECTED_ITEMS})"
        )


def _validate_repository_root(repository_root: Path | str) -> Path:
    if not isinstance(repository_root, (str, os.PathLike)):
        raise HarnessValidationError("repo_root must be a filesystem path")
    try:
        root = Path(repository_root).resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise HarnessValidationError(
            f"repo_root must resolve to an existing directory: {repository_root!r}"
        ) from exc
    if not root.is_dir():
        raise HarnessValidationError(f"repo_root must be a directory: {repository_root!r}")
    return root


def _read_bounded_output(stream: BinaryIO, limit: int) -> bytes:
    if type(limit) is not int or limit < 0:
        raise HarnessValidationError("local Git output limit must be a non-negative integer")
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = stream.read(min(_GIT_READ_CHUNK_BYTES, limit - total + 1))
        if not chunk:
            break
        if type(chunk) is not bytes:
            raise HarnessValidationError("local Git output must be bytes")
        total += len(chunk)
        if total > limit:
            raise RepositoryRoleSummaryBoundError(
                f"local Git output exceeds hard limit ({limit})"
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _open_git_process(repository_root: Path, command: Sequence[str]) -> subprocess.Popen[bytes]:
    argv = ["git", "--no-replace-objects", "-C", os.fspath(repository_root), *command]
    child_environment = {
        name: value
        for name in _GIT_CHILD_ENVIRONMENT_ALLOWLIST
        if (value := os.environ.get(name)) is not None
    }
    child_environment["GIT_NO_LAZY_FETCH"] = "1"
    try:
        return subprocess.Popen(
            argv,
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=child_environment,
        )
    except OSError as exc:
        raise RepositoryRoleSummaryGitError(
            f"unable to start local Git plumbing command {command[0]!r}"
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


def _run_git_output(
    repository_root: Path,
    command: Sequence[str],
    *,
    output_limit: int,
) -> bytes:
    process = _open_git_process(repository_root, command)
    if process.stdout is None:
        _abort_process(process)
        raise RepositoryRoleSummaryGitError("local Git stdout pipe was not created")
    try:
        output = _read_bounded_output(process.stdout, output_limit)
        return_code = process.wait()
    except Exception:
        _abort_process(process)
        raise
    finally:
        process.stdout.close()
    if return_code != 0:
        raise RepositoryRoleSummaryGitError(
            f"local Git plumbing command {command[0]!r} failed with exit code {return_code}"
        )
    return output


def _run_git_scalar(repository_root: Path, command: Sequence[str]) -> bytes:
    return _run_git_output(
        repository_root,
        command,
        output_limit=MAX_H3_GIT_SCALAR_BYTES,
    )


def _decode_git_line(output: bytes, field_name: str) -> str:
    if not output.endswith(b"\n") or output.count(b"\n") != 1 or b"\r" in output:
        raise RepositoryRoleSummaryGitError(
            f"local Git returned malformed {field_name} output"
        )
    try:
        return output[:-1].decode("ascii", errors="strict")
    except UnicodeDecodeError as exc:
        raise RepositoryRoleSummaryGitError(
            f"local Git returned non-ASCII {field_name} output"
        ) from exc


def _verify_exact_snapshot(repository_root: Path, snapshot: RepositorySnapshotRef) -> None:
    resolved_commit = _decode_git_line(
        _run_git_scalar(
            repository_root,
            ["rev-parse", "--verify", f"{snapshot.repository_commit_sha}^{{commit}}"],
        ),
        "commit SHA",
    )
    _validate_hex_40(resolved_commit, "resolved repository_commit_sha")
    if resolved_commit != snapshot.repository_commit_sha:
        raise RepositoryRoleSummaryGitError(
            "local Git resolved commit does not equal the exact H2 commit identity"
        )

    resolved_tree = _decode_git_line(
        _run_git_scalar(
            repository_root,
            ["rev-parse", f"{snapshot.repository_commit_sha}^{{tree}}"],
        ),
        "tree SHA",
    )
    _validate_hex_40(resolved_tree, "resolved repository_tree_sha")
    if resolved_tree != snapshot.repository_tree_sha:
        raise RepositoryRoleSummaryGitError(
            "local Git commit tree does not equal the exact H2 tree identity"
        )


def _read_blob_size(repository_root: Path, blob_sha: str) -> int:
    object_type = _decode_git_line(
        _run_git_scalar(repository_root, ["cat-file", "-t", blob_sha]),
        "blob object type",
    )
    if object_type != "blob":
        raise RepositoryRoleSummaryGitError(
            f"exact selected object {blob_sha} is not a blob"
        )
    size_bytes = _run_git_scalar(repository_root, ["cat-file", "-s", blob_sha])
    if (
        not size_bytes.endswith(b"\n")
        or size_bytes.count(b"\n") != 1
        or b"\r" in size_bytes
        or not _DECIMAL_BYTES_RE.fullmatch(size_bytes[:-1])
    ):
        raise RepositoryRoleSummaryGitError("local Git returned malformed blob size output")
    return int(size_bytes[:-1].decode("ascii", errors="strict"))


def _read_blob_body(repository_root: Path, blob_sha: str, blob_size_bytes: int) -> bytes:
    body = _run_git_output(
        repository_root,
        ["cat-file", "blob", blob_sha],
        output_limit=blob_size_bytes,
    )
    if len(body) != blob_size_bytes:
        raise RepositoryRoleSummaryGitError(
            "local Git blob body length does not equal its exact preflight size"
        )
    return body


def _is_python_path(path: str) -> bool:
    return path.endswith(".py")


def _is_main_guard(test: ast.expr) -> bool:
    if not isinstance(test, ast.Compare):
        return False
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        return False
    if len(test.comparators) != 1:
        return False
    left = test.left
    right = test.comparators[0]

    def is_name(node: ast.expr) -> bool:
        return isinstance(node, ast.Name) and node.id == "__name__"

    def is_main_value(node: ast.expr) -> bool:
        return isinstance(node, ast.Constant) and node.value == "__main__"

    return (is_name(left) and is_main_value(right)) or (
        is_main_value(left) and is_name(right)
    )


def _extract_python_symbols(tree: ast.Module) -> tuple[PythonSymbolSummary, ...]:
    symbols: list[PythonSymbolSummary] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            kind = PythonSymbolKind.CLASS
        elif isinstance(node, ast.AsyncFunctionDef):
            kind = PythonSymbolKind.ASYNC_FUNCTION
        elif isinstance(node, ast.FunctionDef):
            kind = PythonSymbolKind.FUNCTION
        else:
            continue
        if len(node.name) > MAX_H3_SYMBOL_NAME_LENGTH:
            continue
        symbols.append(PythonSymbolSummary.create(kind, node.name, node.lineno))
        if len(symbols) == MAX_H3_SYMBOLS_PER_FILE:
            break
    return tuple(symbols)


def _classify_artifact_role(
    evidence: RepositoryEvidenceRef,
    *,
    has_python_main_guard: bool,
) -> ArtifactRole:
    if evidence.evidence_kind is EvidenceKind.CONTRACT:
        return ArtifactRole.CONTRACT_ARTIFACT
    if evidence.evidence_kind is EvidenceKind.TEST:
        return ArtifactRole.TEST_ARTIFACT
    if evidence.evidence_kind is EvidenceKind.DOCUMENTATION:
        return ArtifactRole.DOCUMENTATION_ARTIFACT
    if evidence.evidence_kind is EvidenceKind.CONFIGURATION:
        return ArtifactRole.CONFIGURATION_ARTIFACT
    if evidence.evidence_kind is EvidenceKind.SOURCE:
        basename = evidence.path.rsplit("/", 1)[-1]
        if basename == "__init__.py":
            return ArtifactRole.PACKAGE_EXPORT_SURFACE
        if basename in {"main.py", "cli.py"} or has_python_main_guard:
            return ArtifactRole.EXECUTABLE_ENTRYPOINT
        return ArtifactRole.SOURCE_IMPLEMENTATION
    return ArtifactRole.OTHER_ARTIFACT


def _analyze_selected_evidence(
    repository_root: Path,
    evidence: RepositoryEvidenceRef,
    aggregate_body_bytes: int,
) -> tuple[RepositoryRoleSummary, int]:
    blob_size_bytes = _read_blob_size(repository_root, evidence.blob_sha)
    symbols: tuple[PythonSymbolSummary, ...] = ()
    has_python_main_guard = False

    if not _is_python_path(evidence.path):
        analysis_status = ContentAnalysisStatus.NOT_PYTHON
    elif blob_size_bytes > MAX_H3_BLOB_BYTES:
        analysis_status = ContentAnalysisStatus.CONTENT_BOUND_EXCEEDED
    elif aggregate_body_bytes + blob_size_bytes > MAX_H3_TOTAL_BODY_BYTES:
        analysis_status = ContentAnalysisStatus.CONTENT_BOUND_EXCEEDED
    else:
        body = _read_blob_body(repository_root, evidence.blob_sha, blob_size_bytes)
        aggregate_body_bytes += blob_size_bytes
        try:
            source = body.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            analysis_status = ContentAnalysisStatus.DECODE_REJECTED
        else:
            try:
                tree = ast.parse(source, filename=evidence.path, mode="exec")
            except (SyntaxError, ValueError, TypeError, MemoryError, RecursionError):
                analysis_status = ContentAnalysisStatus.SYNTAX_REJECTED
            else:
                analysis_status = ContentAnalysisStatus.PARSED
                symbols = _extract_python_symbols(tree)
                has_python_main_guard = any(
                    isinstance(node, ast.If) and _is_main_guard(node.test)
                    for node in tree.body
                )

    artifact_role = _classify_artifact_role(
        evidence,
        has_python_main_guard=has_python_main_guard,
    )
    summary = RepositoryRoleSummary.create(
        evidence=evidence,
        artifact_role=artifact_role,
        analysis_status=analysis_status,
        blob_size_bytes=blob_size_bytes,
        symbols=symbols,
    )
    return summary, aggregate_body_bytes


def summarize_repository_roles(
    repo_root: Path | str,
    ranking: RepositoryRankingResult,
) -> tuple[RepositoryRoleSummaryResult, HarnessReceipt]:
    """Summarize exactly the H2-selected blobs from one exact local Git snapshot."""

    _revalidate_ranking(ranking)
    root = _validate_repository_root(repo_root)
    _verify_exact_snapshot(root, ranking.plan.snapshot)

    summaries: list[RepositoryRoleSummary] = []
    aggregate_body_bytes = 0
    for evidence in ranking.plan.selected_evidence:
        summary, aggregate_body_bytes = _analyze_selected_evidence(
            root,
            evidence,
            aggregate_body_bytes,
        )
        summaries.append(summary)

    summaries_tuple = tuple(summaries)
    result = RepositoryRoleSummaryResult.create(ranking, summaries_tuple)
    input_fingerprint = compute_sha256(
        canonical_json_bytes(
            {
                "h2_plan_fingerprint": ranking.plan.plan_fingerprint,
                "operation": "repository_role_summary",
                "policy_version": H3_ROLE_POLICY_VERSION,
                "ranking_fingerprint": ranking.ranking_fingerprint,
                "schema_version": ROLE_SUMMARY_SCHEMA_VERSION,
                "snapshot": ranking.plan.snapshot.to_dict(),
                "task_id": ranking.task_id,
            }
        )
    )
    receipt = HarnessReceipt(
        task_id=ranking.task_id,
        repository_commit_sha=ranking.plan.snapshot.repository_commit_sha,
        input_fingerprint=input_fingerprint,
        output_fingerprint=result.role_summary_fingerprint,
        generator_version=H3_ROLE_POLICY_VERSION,
        candidate_count=len(ranking.plan.selected_evidence),
        selected_count=len(result.summaries),
        excluded_count=0,
    )
    return result, receipt


__all__ = [
    "ArtifactRole",
    "ContentAnalysisStatus",
    "H3_ROLE_POLICY_VERSION",
    "MAX_H3_BLOB_BYTES",
    "MAX_H3_GIT_SCALAR_BYTES",
    "MAX_H3_SELECTED_ITEMS",
    "MAX_H3_SYMBOLS_PER_FILE",
    "MAX_H3_SYMBOL_NAME_LENGTH",
    "MAX_H3_TOTAL_BODY_BYTES",
    "PythonSymbolKind",
    "PythonSymbolSummary",
    "ROLE_SUMMARY_SCHEMA_VERSION",
    "RepositoryRoleSummary",
    "RepositoryRoleSummaryBoundError",
    "RepositoryRoleSummaryError",
    "RepositoryRoleSummaryGitError",
    "RepositoryRoleSummaryResult",
    "summarize_repository_roles",
]
