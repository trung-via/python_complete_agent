"""Bounded H1 engineering-experience inventory over exact Git provenance."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import os
from pathlib import Path
import re
import subprocess
from typing import Any, BinaryIO, Sequence

from src.aios_engineering.harness.contracts import (
    RepositoryEvidenceRef,
    RepositorySnapshotRef,
    _validate_hex_40,
    _validate_hex_64,
    _validate_posix_path,
)
from src.aios_engineering.harness.discovery import RepositoryDiscoveryResult
from src.aios_engineering.harness.errors import (
    HarnessError,
    HarnessFingerprintError,
    HarnessValidationError,
)
from src.aios_engineering.harness.fingerprint import canonical_json_bytes, compute_sha256


H1_EXPERIENCE_POLICY_VERSION: str = "h1-experience-v1"
EXPERIENCE_SCHEMA_VERSION: str = "1"

# Every input is finite and enforced before a complete result is emitted.
MAX_CONTROL_TREE_ENTRIES: int = 100_000
MAX_CONTROL_GIT_STREAM_BYTES: int = 64 * 1024 * 1024
MAX_CONTROL_GIT_TREE_RECORD_BYTES: int = 4096
MAX_CONTROL_GIT_SCALAR_OUTPUT_BYTES: int = 4096
MAX_EXPERIENCE_EVIDENCE_COUNT: int = 25_000
MAX_EXPERIENCE_FINGERPRINT_PAYLOAD_BYTES: int = 64 * 1024 * 1024
_GIT_READ_CHUNK_BYTES: int = 64 * 1024

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

REGULAR_GIT_MODES: frozenset[str] = frozenset({"100644", "100755"})
TASK_PATH_PREFIX: str = ".ai/tasks/"
RESULT_PATH_PREFIX: str = ".ai/results/"
REVIEW_PATH_PREFIX: str = ".ai/reviews/"
DECISION_PATH_PREFIX: str = ".ai/decisions/"
LEARNING_PATH_PREFIXES: tuple[str, ...] = (
    ".ai/findings/",
    ".ai/knowledge/",
    ".ai/learning/",
    ".ai/lessons/",
    ".ai/skills/",
)

_EXACT_SHA_RE = re.compile(r"\A[0-9a-f]{40}\Z")
_GIT_MODE_RE = re.compile(rb"\A[0-7]{6}\Z")
_GIT_OBJECT_TYPE_RE = re.compile(rb"\A[a-z][a-z0-9_-]{0,31}\Z")
_GIT_OBJECT_SHA_RE = re.compile(rb"\A[0-9a-f]{40}\Z")


class ExperienceManifestError(HarnessError):
    """Base error for exact local experience-manifest discovery."""


class ExperienceManifestGitError(ExperienceManifestError):
    """Raised when required local Git objects cannot produce an exact snapshot."""


class ExperienceManifestBoundError(ExperienceManifestError):
    """Raised when an H1 experience discovery hard bound is exceeded."""


class ExperienceArtifactKind(str, Enum):
    """Path-identity classes allowed in the bounded H1 experience inventory."""

    TASK = "TASK"
    RESULT = "RESULT"
    REVIEW = "REVIEW"
    DECISION = "DECISION"
    LEARNING = "LEARNING"


class ExperienceSurface(str, Enum):
    """Independently frozen evidence surfaces combined by canonical H1."""

    REPOSITORY = "REPOSITORY"
    CONTROL_PLANE = "CONTROL_PLANE"


@dataclass(frozen=True)
class ControlPlaneSnapshotRef:
    """Exact immutable control-plane Git commit/tree binding."""

    control_commit_sha: str
    control_tree_sha: str
    schema_version: str = EXPERIENCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != EXPERIENCE_SCHEMA_VERSION:
            raise HarnessValidationError(
                f"schema_version must be {EXPERIENCE_SCHEMA_VERSION!r}: got {self.schema_version!r}"
            )
        _validate_hex_40(self.control_commit_sha, "control_commit_sha")
        _validate_hex_40(self.control_tree_sha, "control_tree_sha")

    def to_dict(self) -> dict[str, str]:
        return {
            "control_commit_sha": self.control_commit_sha,
            "control_tree_sha": self.control_tree_sha,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class ExperienceArtifactRef:
    """One exact regular Git blob classified only by explicit path identity."""

    surface: ExperienceSurface
    path: str
    blob_sha: str
    artifact_kind: ExperienceArtifactKind

    def __post_init__(self) -> None:
        if not isinstance(self.surface, ExperienceSurface):
            raise HarnessValidationError(f"surface must be ExperienceSurface: got {self.surface!r}")
        _validate_posix_path(self.path)
        _validate_hex_40(self.blob_sha, "blob_sha")
        if not isinstance(self.artifact_kind, ExperienceArtifactKind):
            raise HarnessValidationError(
                f"artifact_kind must be ExperienceArtifactKind: got {self.artifact_kind!r}"
            )
        expected_kind = classify_experience_artifact(self.path)
        if expected_kind is not self.artifact_kind:
            raise HarnessValidationError(
                f"artifact_kind does not match explicit path identity for {self.path!r}"
            )
        if self.surface is ExperienceSurface.REPOSITORY and self.artifact_kind not in {
            ExperienceArtifactKind.RESULT,
            ExperienceArtifactKind.LEARNING,
        }:
            raise HarnessValidationError(
                "repository experience evidence is limited to RESULT and explicit LEARNING paths"
            )

    def to_dict(self) -> dict[str, str]:
        return {
            "artifact_kind": self.artifact_kind.value,
            "blob_sha": self.blob_sha,
            "path": self.path,
            "surface": self.surface.value,
        }


@dataclass(frozen=True)
class ControlPlaneExperienceManifest:
    """Fingerprint-verified experience evidence from one exact control snapshot."""

    snapshot: ControlPlaneSnapshotRef
    evidence: tuple[ExperienceArtifactRef, ...]
    manifest_fingerprint: str
    schema_version: str = EXPERIENCE_SCHEMA_VERSION
    policy_version: str = H1_EXPERIENCE_POLICY_VERSION

    def __post_init__(self) -> None:
        _validate_versions(self.schema_version, self.policy_version)
        if not isinstance(self.snapshot, ControlPlaneSnapshotRef):
            raise HarnessValidationError(
                f"snapshot must be ControlPlaneSnapshotRef: got {self.snapshot!r}"
            )
        _validate_experience_evidence(self.evidence, allowed_surface=ExperienceSurface.CONTROL_PLANE)
        _validate_hex_64(self.manifest_fingerprint, "manifest_fingerprint")
        expected = _compute_control_manifest_fingerprint(
            snapshot=self.snapshot,
            evidence=self.evidence,
            schema_version=self.schema_version,
            policy_version=self.policy_version,
        )
        if self.manifest_fingerprint != expected:
            raise HarnessFingerprintError(
                "Control-plane manifest fingerprint mismatch: "
                f"expected {expected}, got {self.manifest_fingerprint}"
            )

    @classmethod
    def create(
        cls,
        snapshot: ControlPlaneSnapshotRef,
        evidence: tuple[ExperienceArtifactRef, ...],
    ) -> "ControlPlaneExperienceManifest":
        if type(evidence) is not tuple:
            raise HarnessValidationError("evidence must be an exact tuple")
        ordered_evidence = tuple(sorted(evidence, key=_experience_order_key))
        fingerprint = _compute_control_manifest_fingerprint(
            snapshot=snapshot,
            evidence=ordered_evidence,
            schema_version=EXPERIENCE_SCHEMA_VERSION,
            policy_version=H1_EXPERIENCE_POLICY_VERSION,
        )
        return cls(
            snapshot=snapshot,
            evidence=ordered_evidence,
            manifest_fingerprint=fingerprint,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence": [item.to_dict() for item in self.evidence],
            "manifest_fingerprint": self.manifest_fingerprint,
            "policy_version": self.policy_version,
            "schema_version": self.schema_version,
            "snapshot": self.snapshot.to_dict(),
        }


@dataclass(frozen=True)
class RepositoryExperienceManifest:
    """Immutable repository/control-plane dual-provenance H1 manifest."""

    repository_snapshot: RepositorySnapshotRef
    repository_discovery_fingerprint: str
    repository_candidate_set_fingerprint: str
    control_plane_snapshot: ControlPlaneSnapshotRef
    control_plane_manifest_fingerprint: str
    evidence: tuple[ExperienceArtifactRef, ...]
    combined_experience_fingerprint: str
    manifest_fingerprint: str
    schema_version: str = EXPERIENCE_SCHEMA_VERSION
    policy_version: str = H1_EXPERIENCE_POLICY_VERSION
    authority_created: bool = False

    def __post_init__(self) -> None:
        _validate_versions(self.schema_version, self.policy_version)
        if not isinstance(self.repository_snapshot, RepositorySnapshotRef):
            raise HarnessValidationError(
                f"repository_snapshot must be RepositorySnapshotRef: got {self.repository_snapshot!r}"
            )
        if not isinstance(self.control_plane_snapshot, ControlPlaneSnapshotRef):
            raise HarnessValidationError(
                "control_plane_snapshot must be ControlPlaneSnapshotRef: "
                f"got {self.control_plane_snapshot!r}"
            )
        _validate_hex_64(self.repository_discovery_fingerprint, "repository_discovery_fingerprint")
        _validate_hex_64(
            self.repository_candidate_set_fingerprint,
            "repository_candidate_set_fingerprint",
        )
        _validate_hex_64(
            self.control_plane_manifest_fingerprint,
            "control_plane_manifest_fingerprint",
        )
        _validate_experience_evidence(self.evidence)
        _validate_hex_64(self.combined_experience_fingerprint, "combined_experience_fingerprint")
        _validate_hex_64(self.manifest_fingerprint, "manifest_fingerprint")
        if self.authority_created is not False:
            raise HarnessValidationError("authority_created must be exactly False")

        expected_combined = _compute_combined_experience_fingerprint(
            repository_snapshot=self.repository_snapshot,
            repository_discovery_fingerprint=self.repository_discovery_fingerprint,
            repository_candidate_set_fingerprint=self.repository_candidate_set_fingerprint,
            control_plane_snapshot=self.control_plane_snapshot,
            control_plane_manifest_fingerprint=self.control_plane_manifest_fingerprint,
            evidence=self.evidence,
        )
        if self.combined_experience_fingerprint != expected_combined:
            raise HarnessFingerprintError(
                "Combined experience fingerprint mismatch: "
                f"expected {expected_combined}, got {self.combined_experience_fingerprint}"
            )
        expected_manifest = _compute_repository_manifest_fingerprint(
            combined_experience_fingerprint=self.combined_experience_fingerprint,
            schema_version=self.schema_version,
            policy_version=self.policy_version,
            authority_created=self.authority_created,
        )
        if self.manifest_fingerprint != expected_manifest:
            raise HarnessFingerprintError(
                "Repository experience manifest fingerprint mismatch: "
                f"expected {expected_manifest}, got {self.manifest_fingerprint}"
            )

    @classmethod
    def create(
        cls,
        repository_discovery: RepositoryDiscoveryResult,
        control_plane_manifest: ControlPlaneExperienceManifest,
    ) -> "RepositoryExperienceManifest":
        if not isinstance(repository_discovery, RepositoryDiscoveryResult):
            raise HarnessValidationError(
                "repository_discovery must be an already-frozen RepositoryDiscoveryResult"
            )
        if not isinstance(control_plane_manifest, ControlPlaneExperienceManifest):
            raise HarnessValidationError(
                "control_plane_manifest must be ControlPlaneExperienceManifest"
            )
        repository_evidence = _select_repository_experience(repository_discovery.evidence)
        combined_evidence = tuple(
            sorted((*repository_evidence, *control_plane_manifest.evidence), key=_experience_order_key)
        )
        _validate_experience_evidence(combined_evidence)
        combined_fingerprint = _compute_combined_experience_fingerprint(
            repository_snapshot=repository_discovery.snapshot,
            repository_discovery_fingerprint=repository_discovery.discovery_fingerprint,
            repository_candidate_set_fingerprint=repository_discovery.candidate_set_fingerprint,
            control_plane_snapshot=control_plane_manifest.snapshot,
            control_plane_manifest_fingerprint=control_plane_manifest.manifest_fingerprint,
            evidence=combined_evidence,
        )
        manifest_fingerprint = _compute_repository_manifest_fingerprint(
            combined_experience_fingerprint=combined_fingerprint,
            schema_version=EXPERIENCE_SCHEMA_VERSION,
            policy_version=H1_EXPERIENCE_POLICY_VERSION,
            authority_created=False,
        )
        return cls(
            repository_snapshot=repository_discovery.snapshot,
            repository_discovery_fingerprint=repository_discovery.discovery_fingerprint,
            repository_candidate_set_fingerprint=repository_discovery.candidate_set_fingerprint,
            control_plane_snapshot=control_plane_manifest.snapshot,
            control_plane_manifest_fingerprint=control_plane_manifest.manifest_fingerprint,
            evidence=combined_evidence,
            combined_experience_fingerprint=combined_fingerprint,
            manifest_fingerprint=manifest_fingerprint,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "authority_created": self.authority_created,
            "combined_experience_fingerprint": self.combined_experience_fingerprint,
            "control_plane_manifest_fingerprint": self.control_plane_manifest_fingerprint,
            "control_plane_snapshot": self.control_plane_snapshot.to_dict(),
            "evidence": [item.to_dict() for item in self.evidence],
            "manifest_fingerprint": self.manifest_fingerprint,
            "policy_version": self.policy_version,
            "repository_candidate_set_fingerprint": self.repository_candidate_set_fingerprint,
            "repository_discovery_fingerprint": self.repository_discovery_fingerprint,
            "repository_snapshot": self.repository_snapshot.to_dict(),
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class _ControlGitTreeEntry:
    path: str
    object_sha: str
    git_mode: str
    object_type: str


def classify_experience_artifact(path: str) -> ExperienceArtifactKind | None:
    """Classify experience solely through conservative exact path-prefix identity."""

    _validate_posix_path(path)
    if path.startswith(TASK_PATH_PREFIX):
        return ExperienceArtifactKind.TASK
    if path.startswith(RESULT_PATH_PREFIX):
        return ExperienceArtifactKind.RESULT
    if path.startswith(REVIEW_PATH_PREFIX):
        return ExperienceArtifactKind.REVIEW
    if path.startswith(DECISION_PATH_PREFIX):
        return ExperienceArtifactKind.DECISION
    if path.startswith(LEARNING_PATH_PREFIXES):
        return ExperienceArtifactKind.LEARNING
    return None


def _validate_versions(schema_version: str, policy_version: str) -> None:
    if schema_version != EXPERIENCE_SCHEMA_VERSION:
        raise HarnessValidationError(
            f"schema_version must be {EXPERIENCE_SCHEMA_VERSION!r}: got {schema_version!r}"
        )
    if policy_version != H1_EXPERIENCE_POLICY_VERSION:
        raise HarnessValidationError(
            f"policy_version must be {H1_EXPERIENCE_POLICY_VERSION!r}: got {policy_version!r}"
        )


def _experience_order_key(
    item: ExperienceArtifactRef,
) -> tuple[str, str, str, str]:
    return (item.surface.value, item.path, item.blob_sha, item.artifact_kind.value)


def _validate_experience_evidence(
    evidence: tuple[ExperienceArtifactRef, ...],
    *,
    allowed_surface: ExperienceSurface | None = None,
) -> None:
    if type(evidence) is not tuple:
        raise HarnessValidationError("evidence must be an exact tuple")
    if len(evidence) > MAX_EXPERIENCE_EVIDENCE_COUNT:
        raise ExperienceManifestBoundError(
            "experience evidence count "
            f"({len(evidence)}) exceeds hard limit ({MAX_EXPERIENCE_EVIDENCE_COUNT})"
        )
    if any(not isinstance(item, ExperienceArtifactRef) for item in evidence):
        raise HarnessValidationError("every evidence item must be ExperienceArtifactRef")
    if evidence != tuple(sorted(evidence, key=_experience_order_key)):
        raise HarnessValidationError("experience evidence must be in deterministic canonical order")

    seen_paths: set[tuple[ExperienceSurface, str]] = set()
    for item in evidence:
        if allowed_surface is not None and item.surface is not allowed_surface:
            raise HarnessValidationError(
                f"evidence surface must be {allowed_surface.value}: got {item.surface.value}"
            )
        path_identity = (item.surface, item.path)
        if path_identity in seen_paths:
            raise HarnessValidationError(
                f"duplicate or conflicting same-surface path rejected: {item.surface.value}:{item.path}"
            )
        seen_paths.add(path_identity)


def _bounded_payload_fingerprint(payload: Any) -> str:
    payload_bytes = canonical_json_bytes(payload)
    if len(payload_bytes) > MAX_EXPERIENCE_FINGERPRINT_PAYLOAD_BYTES:
        raise ExperienceManifestBoundError(
            "experience fingerprint payload bytes "
            f"({len(payload_bytes)}) exceed hard limit "
            f"({MAX_EXPERIENCE_FINGERPRINT_PAYLOAD_BYTES})"
        )
    return compute_sha256(payload_bytes)


def _compute_control_manifest_fingerprint(
    *,
    snapshot: ControlPlaneSnapshotRef,
    evidence: Sequence[ExperienceArtifactRef],
    schema_version: str,
    policy_version: str,
) -> str:
    return _bounded_payload_fingerprint(
        {
            "evidence": [item.to_dict() for item in evidence],
            "policy_version": policy_version,
            "schema_version": schema_version,
            "snapshot": snapshot.to_dict(),
        }
    )


def _compute_combined_experience_fingerprint(
    *,
    repository_snapshot: RepositorySnapshotRef,
    repository_discovery_fingerprint: str,
    repository_candidate_set_fingerprint: str,
    control_plane_snapshot: ControlPlaneSnapshotRef,
    control_plane_manifest_fingerprint: str,
    evidence: Sequence[ExperienceArtifactRef],
) -> str:
    return _bounded_payload_fingerprint(
        {
            "control_plane_manifest_fingerprint": control_plane_manifest_fingerprint,
            "control_plane_snapshot": control_plane_snapshot.to_dict(),
            "evidence": [item.to_dict() for item in evidence],
            "repository_candidate_set_fingerprint": repository_candidate_set_fingerprint,
            "repository_discovery_fingerprint": repository_discovery_fingerprint,
            "repository_snapshot": repository_snapshot.to_dict(),
        }
    )


def _compute_repository_manifest_fingerprint(
    *,
    combined_experience_fingerprint: str,
    schema_version: str,
    policy_version: str,
    authority_created: bool,
) -> str:
    return _bounded_payload_fingerprint(
        {
            "authority_created": authority_created,
            "combined_experience_fingerprint": combined_experience_fingerprint,
            "policy_version": policy_version,
            "schema_version": schema_version,
        }
    )


def _select_repository_experience(
    repository_evidence: Sequence[RepositoryEvidenceRef],
) -> tuple[ExperienceArtifactRef, ...]:
    selected: list[ExperienceArtifactRef] = []
    for item in repository_evidence:
        if not isinstance(item, RepositoryEvidenceRef):
            raise HarnessValidationError(
                "repository discovery evidence must contain RepositoryEvidenceRef values"
            )
        kind = classify_experience_artifact(item.path)
        if kind not in {ExperienceArtifactKind.RESULT, ExperienceArtifactKind.LEARNING}:
            continue
        if len(selected) >= MAX_EXPERIENCE_EVIDENCE_COUNT:
            raise ExperienceManifestBoundError(
                "experience evidence count exceeds hard limit "
                f"({MAX_EXPERIENCE_EVIDENCE_COUNT})"
            )
        selected.append(
            ExperienceArtifactRef(
                surface=ExperienceSurface.REPOSITORY,
                path=item.path,
                blob_sha=item.blob_sha,
                artifact_kind=kind,
            )
        )
    return tuple(sorted(selected, key=_experience_order_key))


def _parse_control_tree_record(
    record: bytes,
    *,
    max_record_bytes: int | None = None,
) -> _ControlGitTreeEntry:
    record_limit = (
        MAX_CONTROL_GIT_TREE_RECORD_BYTES if max_record_bytes is None else max_record_bytes
    )
    if type(record) is not bytes:
        raise HarnessValidationError("Git tree record must be bytes")
    if not record:
        raise HarnessValidationError("Git tree record must not be empty")
    if len(record) > record_limit:
        raise ExperienceManifestBoundError(
            f"Git tree record bytes ({len(record)}) exceed hard limit ({record_limit})"
        )

    metadata, separator, path_bytes = record.partition(b"\t")
    if not separator or not path_bytes:
        raise HarnessValidationError("malformed Git tree record framing")
    metadata_parts = metadata.split(b" ")
    if len(metadata_parts) != 3 or any(not part for part in metadata_parts):
        raise HarnessValidationError("malformed Git tree record metadata")
    mode_bytes, type_bytes, object_sha_bytes = metadata_parts
    if not _GIT_MODE_RE.fullmatch(mode_bytes):
        raise HarnessValidationError(f"malformed Git tree mode: {mode_bytes!r}")
    if not _GIT_OBJECT_TYPE_RE.fullmatch(type_bytes):
        raise HarnessValidationError(f"malformed Git object type: {type_bytes!r}")
    if not _GIT_OBJECT_SHA_RE.fullmatch(object_sha_bytes):
        raise HarnessValidationError(f"malformed Git object SHA: {object_sha_bytes!r}")
    try:
        path = path_bytes.decode("utf-8", errors="strict")
        object_sha = object_sha_bytes.decode("ascii", errors="strict")
        git_mode = mode_bytes.decode("ascii", errors="strict")
        object_type = type_bytes.decode("ascii", errors="strict")
    except UnicodeDecodeError as exc:
        raise HarnessValidationError(
            "Git tree metadata and paths must use canonical UTF-8/ASCII"
        ) from exc
    _validate_posix_path(path)
    return _ControlGitTreeEntry(
        path=path,
        object_sha=object_sha,
        git_mode=git_mode,
        object_type=object_type,
    )


def _read_control_tree_stream(
    stream: BinaryIO,
    *,
    max_entries: int | None = None,
    max_stream_bytes: int | None = None,
    max_record_bytes: int | None = None,
) -> tuple[_ControlGitTreeEntry, ...]:
    """Consume NUL-framed local Git output while enforcing every hard bound."""

    entry_limit = MAX_CONTROL_TREE_ENTRIES if max_entries is None else max_entries
    stream_limit = (
        MAX_CONTROL_GIT_STREAM_BYTES if max_stream_bytes is None else max_stream_bytes
    )
    record_limit = (
        MAX_CONTROL_GIT_TREE_RECORD_BYTES if max_record_bytes is None else max_record_bytes
    )
    for name, value in (
        ("max_entries", entry_limit),
        ("max_stream_bytes", stream_limit),
        ("max_record_bytes", record_limit),
    ):
        if type(value) is not int or value <= 0:
            raise HarnessValidationError(f"{name} must be a positive integer")

    entries: list[_ControlGitTreeEntry] = []
    record_buffer = bytearray()
    stream_bytes = 0
    while True:
        remaining = stream_limit - stream_bytes
        chunk = stream.read(min(_GIT_READ_CHUNK_BYTES, remaining + 1))
        if not chunk:
            break
        if type(chunk) is not bytes:
            raise HarnessValidationError("Git tree stream must produce bytes")
        stream_bytes += len(chunk)
        if stream_bytes > stream_limit:
            raise ExperienceManifestBoundError(
                f"Git tree stream bytes exceed hard limit ({stream_limit})"
            )
        cursor = 0
        while cursor < len(chunk):
            terminator = chunk.find(b"\0", cursor)
            if terminator < 0:
                fragment = chunk[cursor:]
                if len(record_buffer) + len(fragment) > record_limit:
                    raise ExperienceManifestBoundError(
                        f"Git tree record bytes exceed hard limit ({record_limit})"
                    )
                record_buffer.extend(fragment)
                break
            fragment = chunk[cursor:terminator]
            if len(record_buffer) + len(fragment) > record_limit:
                raise ExperienceManifestBoundError(
                    f"Git tree record bytes exceed hard limit ({record_limit})"
                )
            record_buffer.extend(fragment)
            if len(entries) >= entry_limit:
                raise ExperienceManifestBoundError(
                    f"Git tree entry count exceeds hard limit ({entry_limit})"
                )
            entries.append(
                _parse_control_tree_record(
                    bytes(record_buffer),
                    max_record_bytes=record_limit,
                )
            )
            record_buffer.clear()
            cursor = terminator + 1
    if record_buffer:
        raise HarnessValidationError("Git tree stream ended with an unterminated record")
    return tuple(entries)


def _read_bounded_git_output(stream: BinaryIO, limit: int) -> bytes:
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
            raise ExperienceManifestBoundError(
                f"local Git scalar output exceeds hard limit ({limit})"
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _open_control_git_process(
    repository_root: Path,
    command: Sequence[str],
) -> subprocess.Popen[bytes]:
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
        raise ExperienceManifestGitError(
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


def _run_control_git_scalar(repository_root: Path, command: Sequence[str]) -> bytes:
    process = _open_control_git_process(repository_root, command)
    if process.stdout is None:
        _abort_process(process)
        raise ExperienceManifestGitError("local Git stdout pipe was not created")
    try:
        output = _read_bounded_git_output(
            process.stdout,
            MAX_CONTROL_GIT_SCALAR_OUTPUT_BYTES,
        )
        return_code = process.wait()
    except Exception:
        _abort_process(process)
        raise
    finally:
        process.stdout.close()
    if return_code != 0:
        raise ExperienceManifestGitError(
            f"local Git plumbing command {command[0]!r} failed with exit code {return_code}"
        )
    return output


def _run_control_git_tree(
    repository_root: Path,
    control_commit_sha: str,
) -> tuple[_ControlGitTreeEntry, ...]:
    command = ["ls-tree", "-r", "-z", "--full-tree", control_commit_sha, "--"]
    process = _open_control_git_process(repository_root, command)
    if process.stdout is None:
        _abort_process(process)
        raise ExperienceManifestGitError("local Git stdout pipe was not created")
    try:
        entries = _read_control_tree_stream(process.stdout)
        return_code = process.wait()
    except Exception:
        _abort_process(process)
        raise
    finally:
        process.stdout.close()
    if return_code != 0:
        raise ExperienceManifestGitError(
            "local Git plumbing command 'ls-tree' failed "
            f"with exit code {return_code}"
        )
    return entries


def _decode_git_line(output: bytes, field_name: str) -> str:
    if not output.endswith(b"\n") or output.count(b"\n") != 1 or b"\r" in output:
        raise HarnessValidationError(f"local Git returned malformed {field_name} output")
    try:
        return output[:-1].decode("ascii", errors="strict")
    except UnicodeDecodeError as exc:
        raise HarnessValidationError(
            f"local Git returned non-ASCII {field_name} output"
        ) from exc


def _resolve_control_snapshot(
    repository_root: Path,
    control_commit_sha: str,
) -> ControlPlaneSnapshotRef:
    object_type = _decode_git_line(
        _run_control_git_scalar(repository_root, ["cat-file", "-t", control_commit_sha]),
        "commit object type",
    )
    if object_type != "commit":
        raise ExperienceManifestGitError(
            f"exact object {control_commit_sha} is not a commit object"
        )
    control_tree_sha = _decode_git_line(
        _run_control_git_scalar(
            repository_root,
            ["rev-parse", "--verify", f"{control_commit_sha}^{{tree}}"],
        ),
        "tree SHA",
    )
    _validate_hex_40(control_tree_sha, "control_tree_sha")
    return ControlPlaneSnapshotRef(
        control_commit_sha=control_commit_sha,
        control_tree_sha=control_tree_sha,
    )


def _convert_control_tree_entries(
    entries: Sequence[_ControlGitTreeEntry],
) -> tuple[ExperienceArtifactRef, ...]:
    evidence: list[ExperienceArtifactRef] = []
    seen_paths: set[str] = set()
    for entry in entries:
        if entry.path in seen_paths:
            raise HarnessValidationError(
                f"duplicate or conflicting control Git tree path rejected: {entry.path}"
            )
        seen_paths.add(entry.path)
        kind = classify_experience_artifact(entry.path)
        if (
            kind is None
            or entry.git_mode not in REGULAR_GIT_MODES
            or entry.object_type != "blob"
        ):
            continue
        if len(evidence) >= MAX_EXPERIENCE_EVIDENCE_COUNT:
            raise ExperienceManifestBoundError(
                "experience evidence count exceeds hard limit "
                f"({MAX_EXPERIENCE_EVIDENCE_COUNT})"
            )
        evidence.append(
            ExperienceArtifactRef(
                surface=ExperienceSurface.CONTROL_PLANE,
                path=entry.path,
                blob_sha=entry.object_sha,
                artifact_kind=kind,
            )
        )
    return tuple(sorted(evidence, key=_experience_order_key))


def _validate_repository_root(repository_root: str | os.PathLike[str]) -> Path:
    if not isinstance(repository_root, (str, os.PathLike)):
        raise HarnessValidationError("repository_root must be a filesystem path")
    try:
        root = Path(repository_root).resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise HarnessValidationError(
            f"repository_root must resolve to an existing directory: {repository_root!r}"
        ) from exc
    if not root.is_dir():
        raise HarnessValidationError(
            f"repository_root must be a directory: {repository_root!r}"
        )
    return root


def discover_control_plane_experience(
    repository_root: str | os.PathLike[str],
    control_commit_sha: str,
) -> ControlPlaneExperienceManifest:
    """Discover classified H1 evidence from one exact local control commit."""

    if not isinstance(control_commit_sha, str) or not _EXACT_SHA_RE.fullmatch(
        control_commit_sha
    ):
        raise HarnessValidationError(
            "control_commit_sha must be an exact lowercase 40-hex commit identity"
        )
    root = _validate_repository_root(repository_root)
    snapshot = _resolve_control_snapshot(root, control_commit_sha)
    entries = _run_control_git_tree(root, control_commit_sha)
    evidence = _convert_control_tree_entries(entries)
    return ControlPlaneExperienceManifest.create(snapshot, evidence)


def build_repository_experience_manifest(
    repository_discovery: RepositoryDiscoveryResult,
    control_plane_manifest: ControlPlaneExperienceManifest,
) -> RepositoryExperienceManifest:
    """Bind already-frozen repository discovery to exact control experience."""

    return RepositoryExperienceManifest.create(
        repository_discovery,
        control_plane_manifest,
    )


__all__ = [
    "DECISION_PATH_PREFIX",
    "EXPERIENCE_SCHEMA_VERSION",
    "ExperienceArtifactKind",
    "ExperienceArtifactRef",
    "ExperienceManifestBoundError",
    "ExperienceManifestError",
    "ExperienceManifestGitError",
    "ExperienceSurface",
    "H1_EXPERIENCE_POLICY_VERSION",
    "LEARNING_PATH_PREFIXES",
    "MAX_CONTROL_GIT_STREAM_BYTES",
    "MAX_CONTROL_GIT_TREE_RECORD_BYTES",
    "MAX_CONTROL_TREE_ENTRIES",
    "MAX_EXPERIENCE_EVIDENCE_COUNT",
    "MAX_EXPERIENCE_FINGERPRINT_PAYLOAD_BYTES",
    "RESULT_PATH_PREFIX",
    "REVIEW_PATH_PREFIX",
    "TASK_PATH_PREFIX",
    "ControlPlaneExperienceManifest",
    "ControlPlaneSnapshotRef",
    "RepositoryExperienceManifest",
    "build_repository_experience_manifest",
    "classify_experience_artifact",
    "discover_control_plane_experience",
]
