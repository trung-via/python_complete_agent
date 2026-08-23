"""Deterministic, bounded discovery of evidence from one exact local Git snapshot."""
from __future__ import annotations

from dataclasses import dataclass
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
    _validate_reason_code,
    _validate_task_id,
)
from src.aios_engineering.harness.errors import (
    HarnessFingerprintError,
    HarnessValidationError,
    RepositoryDiscoveryBoundError,
    RepositoryDiscoveryGitError,
)
from src.aios_engineering.harness.fingerprint import (
    canonical_json_bytes,
    compute_candidate_set_fingerprint,
    compute_sha256,
)


H1_DISCOVERY_POLICY_VERSION: str = "h1-v1"
DISCOVERY_SCHEMA_VERSION: str = "1"

# These limits are deliberately finite and enforced during stream consumption.
MAX_DISCOVERY_ENTRIES: int = 100_000
MAX_DISCOVERY_STREAM_BYTES: int = 64 * 1024 * 1024
MAX_GIT_TREE_RECORD_BYTES: int = 4096
MAX_GIT_SCALAR_OUTPUT_BYTES: int = 4096
_GIT_READ_CHUNK_BYTES: int = 64 * 1024

DISCOVERED_GIT_BLOB: str = "DISCOVERED_GIT_BLOB"
NON_REGULAR_GIT_MODE: str = "NON_REGULAR_GIT_MODE"
UNSUPPORTED_GIT_OBJECT_TYPE: str = "UNSUPPORTED_GIT_OBJECT_TYPE"

REGULAR_GIT_MODES: frozenset[str] = frozenset({"100644", "100755"})
CONTRACT_PATH_PREFIXES: tuple[str, ...] = (
    ".ai/context/",
    ".ai/decisions/",
    ".ai/reviews/",
    ".ai/tasks/",
)
TEST_PATH_PREFIXES: tuple[str, ...] = ("test/", "tests/")
DOCUMENTATION_PATH_PREFIXES: tuple[str, ...] = ("docs/",)
DOCUMENTATION_EXTENSIONS: frozenset[str] = frozenset({".md", ".rst"})
CONFIGURATION_PATH_PREFIXES: tuple[str, ...] = (
    ".github/workflows/",
    "config/",
    "configs/",
)
CONFIGURATION_FILENAMES: frozenset[str] = frozenset(
    {
        ".editorconfig",
        ".gitattributes",
        ".gitignore",
        ".pre-commit-config.yaml",
        "cargo.toml",
        "dockerfile",
        "go.mod",
        "makefile",
        "package-lock.json",
        "package.json",
        "pdm.lock",
        "poetry.lock",
        "pyproject.toml",
        "pytest.ini",
        "requirements-dev.txt",
        "requirements.in",
        "requirements.txt",
        "setup.cfg",
        "tox.ini",
        "tsconfig.json",
        "uv.lock",
    }
)
SOURCE_PATH_PREFIXES: tuple[str, ...] = ("app/", "lib/", "scripts/", "src/")
SOURCE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".bash",
        ".c",
        ".cc",
        ".cpp",
        ".cs",
        ".dart",
        ".ex",
        ".exs",
        ".go",
        ".h",
        ".hpp",
        ".java",
        ".js",
        ".jsx",
        ".kt",
        ".kts",
        ".lua",
        ".php",
        ".ps1",
        ".psm1",
        ".py",
        ".r",
        ".rb",
        ".rs",
        ".scala",
        ".sh",
        ".sql",
        ".swift",
        ".ts",
        ".tsx",
        ".zsh",
    }
)

_EXACT_SHA_RE = re.compile(r"\A[0-9a-f]{40}\Z")
_GIT_MODE_RE = re.compile(rb"\A[0-7]{6}\Z")
_GIT_OBJECT_TYPE_RE = re.compile(rb"\A[a-z][a-z0-9_-]{0,31}\Z")
_GIT_OBJECT_SHA_RE = re.compile(rb"\A[0-9a-f]{40}\Z")


@dataclass(frozen=True)
class RepositoryDiscoveryExclusion:
    """Immutable accounting record for a tracked entry that is not evidence."""

    path: str
    object_sha: str
    git_mode: str
    object_type: str
    reason_code: str

    def __post_init__(self) -> None:
        _validate_posix_path(self.path)
        _validate_hex_40(self.object_sha, "object_sha")
        if not isinstance(self.git_mode, str) or not re.fullmatch(r"[0-7]{6}", self.git_mode):
            raise HarnessValidationError(f"git_mode must be exact six-digit octal metadata: {self.git_mode!r}")
        if (
            not isinstance(self.object_type, str)
            or not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", self.object_type)
        ):
            raise HarnessValidationError(f"object_type must be a bounded lowercase Git type: {self.object_type!r}")
        _validate_reason_code(self.reason_code, "reason_code")
        if self.reason_code not in {NON_REGULAR_GIT_MODE, UNSUPPORTED_GIT_OBJECT_TYPE}:
            raise HarnessValidationError(f"unsupported discovery exclusion reason: {self.reason_code!r}")

    def to_dict(self) -> dict[str, str]:
        return {
            "git_mode": self.git_mode,
            "object_sha": self.object_sha,
            "object_type": self.object_type,
            "path": self.path,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True)
class RepositoryDiscoveryResult:
    """Immutable, fingerprint-verified evidence inventory for an exact snapshot."""

    snapshot: RepositorySnapshotRef
    evidence: tuple[RepositoryEvidenceRef, ...]
    exclusions: tuple[RepositoryDiscoveryExclusion, ...]
    candidate_set_fingerprint: str
    discovery_fingerprint: str
    schema_version: str = DISCOVERY_SCHEMA_VERSION
    policy_version: str = H1_DISCOVERY_POLICY_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DISCOVERY_SCHEMA_VERSION:
            raise HarnessValidationError(
                f"schema_version must be {DISCOVERY_SCHEMA_VERSION!r}: got {self.schema_version!r}"
            )
        if self.policy_version != H1_DISCOVERY_POLICY_VERSION:
            raise HarnessValidationError(
                f"policy_version must be {H1_DISCOVERY_POLICY_VERSION!r}: got {self.policy_version!r}"
            )
        if not isinstance(self.snapshot, RepositorySnapshotRef):
            raise HarnessValidationError(f"snapshot must be RepositorySnapshotRef: got {self.snapshot!r}")
        if type(self.evidence) is not tuple:
            raise HarnessValidationError("evidence must be an exact tuple")
        if type(self.exclusions) is not tuple:
            raise HarnessValidationError("exclusions must be an exact tuple")
        if any(not isinstance(item, RepositoryEvidenceRef) for item in self.evidence):
            raise HarnessValidationError("every evidence item must be RepositoryEvidenceRef")
        if any(not isinstance(item, RepositoryDiscoveryExclusion) for item in self.exclusions):
            raise HarnessValidationError("every exclusion item must be RepositoryDiscoveryExclusion")

        if self.evidence != tuple(sorted(self.evidence, key=lambda item: item.path)):
            raise HarnessValidationError("evidence must be in deterministic canonical path order")
        if self.exclusions != tuple(sorted(self.exclusions, key=_exclusion_order_key)):
            raise HarnessValidationError("exclusions must be in deterministic canonical order")

        seen_paths: set[str] = set()
        for item in (*self.evidence, *self.exclusions):
            if item.path in seen_paths:
                raise HarnessValidationError(f"duplicate or ambiguous discovery path rejected: {item.path}")
            seen_paths.add(item.path)

        _validate_hex_64(self.candidate_set_fingerprint, "candidate_set_fingerprint")
        _validate_hex_64(self.discovery_fingerprint, "discovery_fingerprint")
        expected_candidate_fingerprint = compute_candidate_set_fingerprint(self.evidence)
        if self.candidate_set_fingerprint != expected_candidate_fingerprint:
            raise HarnessFingerprintError(
                "Candidate set fingerprint mismatch: "
                f"expected {expected_candidate_fingerprint}, got {self.candidate_set_fingerprint}"
            )
        expected_discovery_fingerprint = _compute_discovery_fingerprint(
            schema_version=self.schema_version,
            policy_version=self.policy_version,
            snapshot=self.snapshot,
            evidence=self.evidence,
            exclusions=self.exclusions,
            candidate_set_fingerprint=self.candidate_set_fingerprint,
        )
        if self.discovery_fingerprint != expected_discovery_fingerprint:
            raise HarnessFingerprintError(
                "Discovery fingerprint mismatch: "
                f"expected {expected_discovery_fingerprint}, got {self.discovery_fingerprint}"
            )

    @classmethod
    def create(
        cls,
        snapshot: RepositorySnapshotRef,
        evidence: Sequence[RepositoryEvidenceRef],
        exclusions: Sequence[RepositoryDiscoveryExclusion] = (),
    ) -> "RepositoryDiscoveryResult":
        """Create a canonically ordered and fingerprint-verified result."""

        evidence_items = tuple(evidence)
        exclusion_items = tuple(exclusions)
        if any(not isinstance(item, RepositoryEvidenceRef) for item in evidence_items):
            raise HarnessValidationError("every evidence item must be RepositoryEvidenceRef")
        if any(not isinstance(item, RepositoryDiscoveryExclusion) for item in exclusion_items):
            raise HarnessValidationError("every exclusion item must be RepositoryDiscoveryExclusion")
        evidence_tuple = tuple(sorted(evidence_items, key=lambda item: item.path))
        exclusion_tuple = tuple(sorted(exclusion_items, key=_exclusion_order_key))
        candidate_fingerprint = compute_candidate_set_fingerprint(evidence_tuple)
        discovery_fingerprint = _compute_discovery_fingerprint(
            schema_version=DISCOVERY_SCHEMA_VERSION,
            policy_version=H1_DISCOVERY_POLICY_VERSION,
            snapshot=snapshot,
            evidence=evidence_tuple,
            exclusions=exclusion_tuple,
            candidate_set_fingerprint=candidate_fingerprint,
        )
        return cls(
            snapshot=snapshot,
            evidence=evidence_tuple,
            exclusions=exclusion_tuple,
            candidate_set_fingerprint=candidate_fingerprint,
            discovery_fingerprint=discovery_fingerprint,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_set_fingerprint": self.candidate_set_fingerprint,
            "discovery_fingerprint": self.discovery_fingerprint,
            "evidence": [item.to_dict() for item in self.evidence],
            "exclusions": [item.to_dict() for item in self.exclusions],
            "policy_version": self.policy_version,
            "schema_version": self.schema_version,
            "snapshot": self.snapshot.to_dict(),
        }


@dataclass(frozen=True)
class _GitTreeEntry:
    path: str
    object_sha: str
    git_mode: str
    object_type: str


def classify_evidence_kind(path: str) -> EvidenceKind:
    """Classify one canonical path using locked H1 precedence and path-only rules."""

    _validate_posix_path(path)
    lower_path = path.lower()
    filename = lower_path.rsplit("/", 1)[-1]
    extension = Path(filename).suffix

    if path.startswith(CONTRACT_PATH_PREFIXES):
        return EvidenceKind.CONTRACT
    if path.startswith(TEST_PATH_PREFIXES):
        return EvidenceKind.TEST
    if (
        path.startswith(DOCUMENTATION_PATH_PREFIXES)
        or filename.startswith("readme")
        or filename.startswith("changelog")
        or extension in DOCUMENTATION_EXTENSIONS
    ):
        return EvidenceKind.DOCUMENTATION
    if path.startswith(CONFIGURATION_PATH_PREFIXES) or filename in CONFIGURATION_FILENAMES:
        return EvidenceKind.CONFIGURATION
    if path.startswith(SOURCE_PATH_PREFIXES) or extension in SOURCE_EXTENSIONS:
        return EvidenceKind.SOURCE
    return EvidenceKind.OTHER


def _exclusion_order_key(item: RepositoryDiscoveryExclusion) -> tuple[str, str, str, str, str]:
    return (item.path, item.git_mode, item.object_type, item.object_sha, item.reason_code)


def _compute_discovery_fingerprint(
    *,
    schema_version: str,
    policy_version: str,
    snapshot: RepositorySnapshotRef,
    evidence: Sequence[RepositoryEvidenceRef],
    exclusions: Sequence[RepositoryDiscoveryExclusion],
    candidate_set_fingerprint: str,
) -> str:
    payload = {
        "candidate_set_fingerprint": candidate_set_fingerprint,
        "evidence": [item.to_dict() for item in evidence],
        "exclusions": [item.to_dict() for item in exclusions],
        "policy_version": policy_version,
        "schema_version": schema_version,
        "snapshot": snapshot.to_dict(),
    }
    return compute_sha256(canonical_json_bytes(payload))


def _parse_git_tree_record(record: bytes, *, max_record_bytes: int | None = None) -> _GitTreeEntry:
    record_limit = MAX_GIT_TREE_RECORD_BYTES if max_record_bytes is None else max_record_bytes
    if type(record) is not bytes:
        raise HarnessValidationError("Git tree record must be bytes")
    if not record:
        raise HarnessValidationError("Git tree record must not be empty")
    if len(record) > record_limit:
        raise RepositoryDiscoveryBoundError(
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
        object_type = type_bytes.decode("ascii", errors="strict")
        git_mode = mode_bytes.decode("ascii", errors="strict")
        object_sha = object_sha_bytes.decode("ascii", errors="strict")
    except UnicodeDecodeError as exc:
        raise HarnessValidationError("Git tree metadata and paths must use canonical UTF-8/ASCII") from exc
    _validate_posix_path(path)
    return _GitTreeEntry(
        path=path,
        object_sha=object_sha,
        git_mode=git_mode,
        object_type=object_type,
    )


def _read_git_tree_stream(
    stream: BinaryIO,
    *,
    max_entries: int | None = None,
    max_stream_bytes: int | None = None,
    max_record_bytes: int | None = None,
) -> tuple[_GitTreeEntry, ...]:
    """Read and parse a NUL-framed tree stream without whole-stream capture."""

    entry_limit = MAX_DISCOVERY_ENTRIES if max_entries is None else max_entries
    stream_limit = MAX_DISCOVERY_STREAM_BYTES if max_stream_bytes is None else max_stream_bytes
    record_limit = MAX_GIT_TREE_RECORD_BYTES if max_record_bytes is None else max_record_bytes
    for name, value in (
        ("max_entries", entry_limit),
        ("max_stream_bytes", stream_limit),
        ("max_record_bytes", record_limit),
    ):
        if type(value) is not int or value <= 0:
            raise HarnessValidationError(f"{name} must be a positive integer")

    entries: list[_GitTreeEntry] = []
    record_buffer = bytearray()
    stream_bytes = 0
    while True:
        remaining = stream_limit - stream_bytes
        read_size = min(_GIT_READ_CHUNK_BYTES, remaining + 1)
        chunk = stream.read(read_size)
        if not chunk:
            break
        if type(chunk) is not bytes:
            raise HarnessValidationError("Git tree stream must produce bytes")
        stream_bytes += len(chunk)
        if stream_bytes > stream_limit:
            raise RepositoryDiscoveryBoundError(
                f"Git tree stream bytes exceed hard limit ({stream_limit})"
            )

        cursor = 0
        while cursor < len(chunk):
            terminator = chunk.find(b"\0", cursor)
            if terminator < 0:
                fragment = chunk[cursor:]
                if len(record_buffer) + len(fragment) > record_limit:
                    raise RepositoryDiscoveryBoundError(
                        f"Git tree record bytes exceed hard limit ({record_limit})"
                    )
                record_buffer.extend(fragment)
                break

            fragment = chunk[cursor:terminator]
            if len(record_buffer) + len(fragment) > record_limit:
                raise RepositoryDiscoveryBoundError(
                    f"Git tree record bytes exceed hard limit ({record_limit})"
                )
            record_buffer.extend(fragment)
            if len(entries) >= entry_limit:
                raise RepositoryDiscoveryBoundError(
                    f"Git tree entry count exceeds hard limit ({entry_limit})"
                )
            entries.append(_parse_git_tree_record(bytes(record_buffer), max_record_bytes=record_limit))
            record_buffer.clear()
            cursor = terminator + 1

    if record_buffer:
        raise HarnessValidationError("Git tree stream ended with an unterminated record")
    return tuple(entries)


def _read_bounded_output(stream: BinaryIO, limit: int) -> bytes:
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
            raise RepositoryDiscoveryBoundError(f"local Git scalar output exceeds hard limit ({limit})")
        chunks.append(chunk)
    return b"".join(chunks)


def _open_git_process(repository_root: Path, command: Sequence[str]) -> subprocess.Popen[bytes]:
    argv = ["git", "--no-replace-objects", "-C", os.fspath(repository_root), *command]
    try:
        return subprocess.Popen(
            argv,
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        raise RepositoryDiscoveryGitError(f"unable to start local Git plumbing command {command[0]!r}") from exc


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


def _run_git_scalar(repository_root: Path, command: Sequence[str]) -> bytes:
    process = _open_git_process(repository_root, command)
    if process.stdout is None:
        _abort_process(process)
        raise RepositoryDiscoveryGitError("local Git stdout pipe was not created")
    try:
        output = _read_bounded_output(process.stdout, MAX_GIT_SCALAR_OUTPUT_BYTES)
        return_code = process.wait()
    except Exception:
        _abort_process(process)
        raise
    finally:
        process.stdout.close()
    if return_code != 0:
        raise RepositoryDiscoveryGitError(
            f"local Git plumbing command {command[0]!r} failed with exit code {return_code}"
        )
    return output


def _run_git_tree(repository_root: Path, repository_commit_sha: str) -> tuple[_GitTreeEntry, ...]:
    command = ["ls-tree", "-r", "-z", "--full-tree", repository_commit_sha, "--"]
    process = _open_git_process(repository_root, command)
    if process.stdout is None:
        _abort_process(process)
        raise RepositoryDiscoveryGitError("local Git stdout pipe was not created")
    try:
        entries = _read_git_tree_stream(process.stdout)
        return_code = process.wait()
    except Exception:
        _abort_process(process)
        raise
    finally:
        process.stdout.close()
    if return_code != 0:
        raise RepositoryDiscoveryGitError(
            f"local Git plumbing command 'ls-tree' failed with exit code {return_code}"
        )
    return entries


def _decode_git_line(output: bytes, field_name: str) -> str:
    if not output.endswith(b"\n") or output.count(b"\n") != 1 or b"\r" in output:
        raise HarnessValidationError(f"local Git returned malformed {field_name} output")
    try:
        return output[:-1].decode("ascii", errors="strict")
    except UnicodeDecodeError as exc:
        raise HarnessValidationError(f"local Git returned non-ASCII {field_name} output") from exc


def _resolve_snapshot(repository_root: Path, repository_commit_sha: str) -> RepositorySnapshotRef:
    object_type = _decode_git_line(
        _run_git_scalar(repository_root, ["cat-file", "-t", repository_commit_sha]),
        "commit object type",
    )
    if object_type != "commit":
        raise RepositoryDiscoveryGitError(
            f"exact object {repository_commit_sha} is not a commit object"
        )
    repository_tree_sha = _decode_git_line(
        _run_git_scalar(
            repository_root,
            ["rev-parse", "--verify", f"{repository_commit_sha}^{{tree}}"],
        ),
        "tree SHA",
    )
    _validate_hex_40(repository_tree_sha, "repository_tree_sha")
    return RepositorySnapshotRef(
        repository_commit_sha=repository_commit_sha,
        repository_tree_sha=repository_tree_sha,
    )


def _convert_tree_entries(
    entries: Sequence[_GitTreeEntry],
) -> tuple[tuple[RepositoryEvidenceRef, ...], tuple[RepositoryDiscoveryExclusion, ...]]:
    evidence: list[RepositoryEvidenceRef] = []
    exclusions: list[RepositoryDiscoveryExclusion] = []
    seen_paths: set[str] = set()
    for entry in entries:
        if entry.path in seen_paths:
            raise HarnessValidationError(f"duplicate or ambiguous Git tree path rejected: {entry.path}")
        seen_paths.add(entry.path)

        if entry.git_mode not in REGULAR_GIT_MODES:
            exclusions.append(
                RepositoryDiscoveryExclusion(
                    path=entry.path,
                    object_sha=entry.object_sha,
                    git_mode=entry.git_mode,
                    object_type=entry.object_type,
                    reason_code=NON_REGULAR_GIT_MODE,
                )
            )
        elif entry.object_type != "blob":
            exclusions.append(
                RepositoryDiscoveryExclusion(
                    path=entry.path,
                    object_sha=entry.object_sha,
                    git_mode=entry.git_mode,
                    object_type=entry.object_type,
                    reason_code=UNSUPPORTED_GIT_OBJECT_TYPE,
                )
            )
        else:
            evidence.append(
                RepositoryEvidenceRef(
                    path=entry.path,
                    blob_sha=entry.object_sha,
                    evidence_kind=classify_evidence_kind(entry.path),
                    reason_code=DISCOVERED_GIT_BLOB,
                    priority=0,
                    symbol_locator=None,
                )
            )
    return tuple(evidence), tuple(exclusions)


def _validate_repository_root(repository_root: str | os.PathLike[str]) -> Path:
    if not isinstance(repository_root, (str, os.PathLike)):
        raise HarnessValidationError("repository_root must be a filesystem path")
    try:
        root = Path(repository_root).resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise HarnessValidationError(f"repository_root must resolve to an existing directory: {repository_root!r}") from exc
    if not root.is_dir():
        raise HarnessValidationError(f"repository_root must be a directory: {repository_root!r}")
    return root


def discover_repository_snapshot(
    repository_root: str | os.PathLike[str],
    repository_commit_sha: str,
    *,
    task_id: str,
) -> tuple[RepositoryDiscoveryResult, HarnessReceipt]:
    """Discover tracked evidence from an exact commit using bounded local Git plumbing."""

    _validate_task_id(task_id)
    if not isinstance(repository_commit_sha, str) or not _EXACT_SHA_RE.fullmatch(repository_commit_sha):
        raise HarnessValidationError(
            "repository_commit_sha must be an exact lowercase 40-hex commit identity"
        )
    root = _validate_repository_root(repository_root)
    snapshot = _resolve_snapshot(root, repository_commit_sha)
    tree_entries = _run_git_tree(root, repository_commit_sha)
    evidence, exclusions = _convert_tree_entries(tree_entries)
    result = RepositoryDiscoveryResult.create(snapshot, evidence, exclusions)

    input_fingerprint = compute_sha256(
        canonical_json_bytes(
            {
                "operation": "repository_snapshot_discovery",
                "policy_version": H1_DISCOVERY_POLICY_VERSION,
                "snapshot": snapshot.to_dict(),
                "task_id": task_id,
            }
        )
    )
    output_fingerprint = compute_sha256(
        canonical_json_bytes({"discovery_fingerprint": result.discovery_fingerprint})
    )
    receipt = HarnessReceipt(
        task_id=task_id,
        repository_commit_sha=snapshot.repository_commit_sha,
        input_fingerprint=input_fingerprint,
        output_fingerprint=output_fingerprint,
        generator_version=H1_DISCOVERY_POLICY_VERSION,
        candidate_count=len(result.evidence) + len(result.exclusions),
        selected_count=len(result.evidence),
        excluded_count=len(result.exclusions),
    )
    return result, receipt


__all__ = [
    "CONFIGURATION_FILENAMES",
    "CONFIGURATION_PATH_PREFIXES",
    "CONTRACT_PATH_PREFIXES",
    "DISCOVERED_GIT_BLOB",
    "DOCUMENTATION_EXTENSIONS",
    "DOCUMENTATION_PATH_PREFIXES",
    "H1_DISCOVERY_POLICY_VERSION",
    "MAX_DISCOVERY_ENTRIES",
    "MAX_DISCOVERY_STREAM_BYTES",
    "MAX_GIT_TREE_RECORD_BYTES",
    "NON_REGULAR_GIT_MODE",
    "REGULAR_GIT_MODES",
    "RepositoryDiscoveryExclusion",
    "RepositoryDiscoveryResult",
    "SOURCE_EXTENSIONS",
    "SOURCE_PATH_PREFIXES",
    "TEST_PATH_PREFIXES",
    "UNSUPPORTED_GIT_OBJECT_TYPE",
    "classify_evidence_kind",
    "discover_repository_snapshot",
]
