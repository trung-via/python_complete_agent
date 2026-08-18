"""Fail-closed hot local handoff checkpoint primitives (ADR-023 / M9.1).

This module deliberately has no lease or Bridge lifecycle integration.  It only
captures and verifies exact, local Git-workspace evidence at a quiescent point.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
from typing import Any, Iterable, Sequence

from .errors import ContinuityStateValidationError


HOT_HANDOFF_SCHEMA_VERSION = "1"
_TASK_ID_PATTERN = re.compile(r"^TASK-\d+$")
_ACTOR_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:[a-z0-9_.-]*[a-z0-9])?$")
_BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
_HEX_64_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_PATTERN = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_FORBIDDEN_PAYLOAD_COMPONENTS = {
    ".git",
    ".ai",
    ".env",
    "cookies",
    "credentials",
    "secrets",
    "sessions",
    "transcripts",
}
_OPERATION_MARKERS = (
    "MERGE_HEAD",
    "CHERRY_PICK_HEAD",
    "REVERT_HEAD",
    "rebase-apply",
    "rebase-merge",
)


class HotHandoffCheckpointError(ContinuityStateValidationError):
    """Raised when checkpoint capture or verification cannot prove exact safety."""


@dataclass(frozen=True, order=True)
class WorkspaceFileManifestEntry:
    """Exact byte evidence for one regular workspace file."""

    path: str
    size_bytes: int
    sha256: str

    def __post_init__(self) -> None:
        _validate_normalized_manifest_path(self.path)
        if isinstance(self.size_bytes, bool) or not isinstance(self.size_bytes, int) or self.size_bytes < 0:
            raise HotHandoffCheckpointError("manifest size_bytes must be a non-negative integer")
        _validate_sha256(self.sha256, "manifest sha256")

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "sha256": self.sha256, "size_bytes": self.size_bytes}

    @classmethod
    def from_dict(cls, data: Any) -> WorkspaceFileManifestEntry:
        if not isinstance(data, dict):
            raise HotHandoffCheckpointError("manifest entry must be an object")
        expected = {"path", "sha256", "size_bytes"}
        if set(data) != expected:
            raise HotHandoffCheckpointError(
                f"manifest entry fields must be exactly {sorted(expected)}, got {sorted(data)}"
            )
        return cls(path=data["path"], size_bytes=data["size_bytes"], sha256=data["sha256"])


# Public contract name for the required untracked-file evidence.
UntrackedFileManifestEntry = WorkspaceFileManifestEntry


@dataclass(frozen=True)
class HotHandoffCheckpoint:
    """Immutable, content-addressed evidence for an exact dirty workspace state."""

    schema_version: str
    task_id: str
    target_branch: str
    workspace_id: str
    source_executor_id: str
    source_lease_fingerprint: str
    source_execution_fingerprint: str
    head_sha: str
    allowed_paths: tuple[str, ...]
    status_porcelain_v2_sha256: str
    tracked_diff_sha256: str
    tracked_file_manifest: tuple[WorkspaceFileManifestEntry, ...]
    untracked_file_manifest: tuple[UntrackedFileManifestEntry, ...]
    checkpoint_fingerprint: str

    def __post_init__(self) -> None:
        if self.schema_version != HOT_HANDOFF_SCHEMA_VERSION:
            raise HotHandoffCheckpointError(
                f"unsupported checkpoint schema_version {self.schema_version!r}"
            )
        if not isinstance(self.task_id, str) or not _TASK_ID_PATTERN.fullmatch(self.task_id):
            raise HotHandoffCheckpointError("task_id must match exact case-sensitive '^TASK-\\d+$'")
        _validate_branch(self.target_branch)
        _validate_sha256(self.workspace_id, "workspace_id")
        if not isinstance(self.source_executor_id, str) or not _ACTOR_ID_PATTERN.fullmatch(
            self.source_executor_id
        ):
            raise HotHandoffCheckpointError("source_executor_id must be a canonical lowercase identifier")
        _validate_sha256(self.source_lease_fingerprint, "source_lease_fingerprint")
        _validate_sha256(self.source_execution_fingerprint, "source_execution_fingerprint")
        if not isinstance(self.head_sha, str) or not _GIT_SHA_PATTERN.fullmatch(self.head_sha):
            raise HotHandoffCheckpointError("head_sha must be an exact lowercase Git object ID")
        _validate_sha256(self.status_porcelain_v2_sha256, "status_porcelain_v2_sha256")
        _validate_sha256(self.tracked_diff_sha256, "tracked_diff_sha256")

        allowed = _coerce_allowed_paths(self.allowed_paths)
        if allowed != self.allowed_paths:
            object.__setattr__(self, "allowed_paths", allowed)

        tracked = _coerce_manifest(self.tracked_file_manifest, "tracked_file_manifest")
        untracked = _coerce_manifest(self.untracked_file_manifest, "untracked_file_manifest")
        if tracked != self.tracked_file_manifest:
            object.__setattr__(self, "tracked_file_manifest", tracked)
        if untracked != self.untracked_file_manifest:
            object.__setattr__(self, "untracked_file_manifest", untracked)
        overlap = {item.path for item in tracked} & {item.path for item in untracked}
        if overlap:
            raise HotHandoffCheckpointError(f"tracked and untracked manifests overlap: {sorted(overlap)}")

        _validate_sha256(self.checkpoint_fingerprint, "checkpoint_fingerprint")
        expected = self.compute_fingerprint()
        if self.checkpoint_fingerprint != expected:
            raise HotHandoffCheckpointError(
                "checkpoint_fingerprint does not match canonical semantic checkpoint fields"
            )

    def semantic_dict(self) -> dict[str, Any]:
        """Return all fingerprint-bound fields, excluding the fingerprint itself."""
        return {
            "allowed_paths": list(self.allowed_paths),
            "head_sha": self.head_sha,
            "schema_version": self.schema_version,
            "source_execution_fingerprint": self.source_execution_fingerprint,
            "source_executor_id": self.source_executor_id,
            "source_lease_fingerprint": self.source_lease_fingerprint,
            "status_porcelain_v2_sha256": self.status_porcelain_v2_sha256,
            "target_branch": self.target_branch,
            "task_id": self.task_id,
            "tracked_diff_sha256": self.tracked_diff_sha256,
            "tracked_file_manifest": [item.to_dict() for item in self.tracked_file_manifest],
            "untracked_file_manifest": [item.to_dict() for item in self.untracked_file_manifest],
            "workspace_id": self.workspace_id,
        }

    def compute_fingerprint(self) -> str:
        return _sha256(_canonical_json(self.semantic_dict()).encode("utf-8"))

    def to_dict(self) -> dict[str, Any]:
        return {**self.semantic_dict(), "checkpoint_fingerprint": self.checkpoint_fingerprint}

    def to_canonical_json(self) -> str:
        return _canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, data: Any) -> HotHandoffCheckpoint:
        if not isinstance(data, dict):
            raise HotHandoffCheckpointError("HotHandoffCheckpoint root must be an object")
        expected = {
            "allowed_paths",
            "checkpoint_fingerprint",
            "head_sha",
            "schema_version",
            "source_execution_fingerprint",
            "source_executor_id",
            "source_lease_fingerprint",
            "status_porcelain_v2_sha256",
            "target_branch",
            "task_id",
            "tracked_diff_sha256",
            "tracked_file_manifest",
            "untracked_file_manifest",
            "workspace_id",
        }
        if set(data) != expected:
            missing = sorted(expected - set(data))
            extra = sorted(set(data) - expected)
            raise HotHandoffCheckpointError(
                f"checkpoint fields mismatch; missing={missing}, extra={extra}"
            )
        if not isinstance(data["allowed_paths"], (list, tuple)):
            raise HotHandoffCheckpointError("allowed_paths must be an ordered list")
        if not isinstance(data["tracked_file_manifest"], (list, tuple)):
            raise HotHandoffCheckpointError("tracked_file_manifest must be an ordered list")
        if not isinstance(data["untracked_file_manifest"], (list, tuple)):
            raise HotHandoffCheckpointError("untracked_file_manifest must be an ordered list")
        return cls(
            schema_version=data["schema_version"],
            task_id=data["task_id"],
            target_branch=data["target_branch"],
            workspace_id=data["workspace_id"],
            source_executor_id=data["source_executor_id"],
            source_lease_fingerprint=data["source_lease_fingerprint"],
            source_execution_fingerprint=data["source_execution_fingerprint"],
            head_sha=data["head_sha"],
            allowed_paths=tuple(data["allowed_paths"]),
            status_porcelain_v2_sha256=data["status_porcelain_v2_sha256"],
            tracked_diff_sha256=data["tracked_diff_sha256"],
            tracked_file_manifest=tuple(
                WorkspaceFileManifestEntry.from_dict(item) for item in data["tracked_file_manifest"]
            ),
            untracked_file_manifest=tuple(
                UntrackedFileManifestEntry.from_dict(item) for item in data["untracked_file_manifest"]
            ),
            checkpoint_fingerprint=data["checkpoint_fingerprint"],
        )

    @classmethod
    def from_json(cls, value: str | bytes) -> HotHandoffCheckpoint:
        if isinstance(value, bytes):
            try:
                value = value.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise HotHandoffCheckpointError("checkpoint JSON must be UTF-8") from exc
        if not isinstance(value, str):
            raise HotHandoffCheckpointError("checkpoint JSON must be str or bytes")
        try:
            data = json.loads(value)
        except (TypeError, ValueError) as exc:
            raise HotHandoffCheckpointError(f"malformed checkpoint JSON: {exc}") from exc
        return cls.from_dict(data)


@dataclass(frozen=True)
class _WorkspaceEvidence:
    head_sha: str
    branch: str
    status_sha256: str
    tracked_diff_sha256: str
    tracked_manifest: tuple[WorkspaceFileManifestEntry, ...]
    untracked_manifest: tuple[UntrackedFileManifestEntry, ...]


def capture_hot_handoff_checkpoint(
    worktree: str | os.PathLike[str],
    checkpoint_dir: str | os.PathLike[str],
    *,
    task_id: str,
    target_branch: str,
    workspace_id: str,
    source_executor_id: str,
    source_lease_fingerprint: str,
    source_execution_fingerprint: str,
    allowed_paths: Sequence[str | os.PathLike[str]],
) -> HotHandoffCheckpoint:
    """Inspect, bind, and persist exact workspace evidence without mutating Git state."""
    root = _repository_root(worktree)
    normalized_allowed = _normalize_allowed_paths(root, allowed_paths)
    storage = _validate_external_storage(root, checkpoint_dir)
    evidence = _inspect_workspace(root, target_branch, normalized_allowed)

    semantic = {
        "schema_version": HOT_HANDOFF_SCHEMA_VERSION,
        "task_id": task_id,
        "target_branch": target_branch,
        "workspace_id": workspace_id,
        "source_executor_id": source_executor_id,
        "source_lease_fingerprint": source_lease_fingerprint,
        "source_execution_fingerprint": source_execution_fingerprint,
        "head_sha": evidence.head_sha,
        "allowed_paths": normalized_allowed,
        "status_porcelain_v2_sha256": evidence.status_sha256,
        "tracked_diff_sha256": evidence.tracked_diff_sha256,
        "tracked_file_manifest": evidence.tracked_manifest,
        "untracked_file_manifest": evidence.untracked_manifest,
    }
    fingerprint_payload = {
        **semantic,
        "allowed_paths": list(normalized_allowed),
        "tracked_file_manifest": [item.to_dict() for item in evidence.tracked_manifest],
        "untracked_file_manifest": [item.to_dict() for item in evidence.untracked_manifest],
    }
    checkpoint = HotHandoffCheckpoint(
        **semantic,
        checkpoint_fingerprint=_sha256(_canonical_json(fingerprint_payload).encode("utf-8")),
    )
    _persist_checkpoint(storage, checkpoint)
    return checkpoint


def verify_hot_handoff_checkpoint(
    checkpoint: HotHandoffCheckpoint,
    worktree: str | os.PathLike[str],
    *,
    workspace_id: str,
    allowed_paths: Sequence[str | os.PathLike[str]],
    checkpoint_dir: str | os.PathLike[str] | None = None,
) -> None:
    """Fail unless the current workspace exactly equals the immutable checkpoint."""
    if not isinstance(checkpoint, HotHandoffCheckpoint):
        raise HotHandoffCheckpointError("checkpoint must be a HotHandoffCheckpoint instance")
    if checkpoint.checkpoint_fingerprint != checkpoint.compute_fingerprint():
        raise HotHandoffCheckpointError("checkpoint fingerprint tamper detected")
    _validate_sha256(workspace_id, "workspace_id")
    if workspace_id != checkpoint.workspace_id:
        raise HotHandoffCheckpointError("workspace_id mismatch")

    root = _repository_root(worktree)
    normalized_allowed = _normalize_allowed_paths(root, allowed_paths)
    if normalized_allowed != checkpoint.allowed_paths:
        raise HotHandoffCheckpointError("allowed_paths mismatch")

    if checkpoint_dir is not None:
        storage = _validate_external_storage(root, checkpoint_dir)
        persisted_path = storage / f"{checkpoint.checkpoint_fingerprint}.json"
        try:
            persisted_bytes = persisted_path.read_bytes()
        except OSError as exc:
            raise HotHandoffCheckpointError("persisted checkpoint evidence is missing or unreadable") from exc
        expected_bytes = (checkpoint.to_canonical_json() + "\n").encode("utf-8")
        if persisted_bytes != expected_bytes:
            raise HotHandoffCheckpointError("persisted checkpoint evidence mismatch")

    evidence = _inspect_workspace(
        root,
        checkpoint.target_branch,
        normalized_allowed,
        require_dirty=False,
    )
    comparisons = {
        "head_sha": (evidence.head_sha, checkpoint.head_sha),
        "branch": (evidence.branch, checkpoint.target_branch),
        "status_porcelain_v2_sha256": (
            evidence.status_sha256,
            checkpoint.status_porcelain_v2_sha256,
        ),
        "tracked_diff_sha256": (evidence.tracked_diff_sha256, checkpoint.tracked_diff_sha256),
        "tracked_file_manifest": (evidence.tracked_manifest, checkpoint.tracked_file_manifest),
        "untracked_file_manifest": (evidence.untracked_manifest, checkpoint.untracked_file_manifest),
    }
    drifted = [name for name, (actual, expected) in comparisons.items() if actual != expected]
    if drifted:
        raise HotHandoffCheckpointError(f"workspace checkpoint mismatch: {', '.join(drifted)}")


# Short aliases make the primitive convenient without introducing a CLI lifecycle.
capture_checkpoint = capture_hot_handoff_checkpoint
verify_checkpoint = verify_hot_handoff_checkpoint


def _inspect_workspace(
    root: Path,
    target_branch: str,
    allowed_paths: tuple[str, ...],
    *,
    require_dirty: bool = True,
) -> _WorkspaceEvidence:
    first = _inspect_workspace_once(root, target_branch, allowed_paths, require_dirty=require_dirty)
    second = _inspect_workspace_once(root, target_branch, allowed_paths, require_dirty=require_dirty)
    if first != second:
        raise HotHandoffCheckpointError("workspace changed during checkpoint inspection")
    return first


def _inspect_workspace_once(
    root: Path,
    target_branch: str,
    allowed_paths: tuple[str, ...],
    *,
    require_dirty: bool,
) -> _WorkspaceEvidence:
    _reject_git_operation_in_progress(root)
    branch = _git_text(root, "symbolic-ref", "--quiet", "--short", "HEAD", failure="detached HEAD")
    _validate_branch(target_branch)
    if branch != target_branch:
        raise HotHandoffCheckpointError(
            f"branch mismatch: expected {target_branch!r}, observed {branch!r}"
        )
    head_sha = _git_text(root, "rev-parse", "--verify", "HEAD", failure="unable to resolve HEAD")
    if not _GIT_SHA_PATTERN.fullmatch(head_sha):
        raise HotHandoffCheckpointError("Git returned an unsupported HEAD object ID")

    status_bytes = _git_bytes(
        root,
        "-c",
        "core.quotepath=false",
        "status",
        "--porcelain=v2",
        "-z",
        "--untracked-files=all",
    )
    tracked_paths, untracked_paths = _parse_status(status_bytes)
    changed_paths = tuple(sorted(set(tracked_paths) | set(untracked_paths)))
    if require_dirty and not changed_paths:
        raise HotHandoffCheckpointError("hot-handoff checkpoint requires unpublished dirty workspace state")
    for path in changed_paths:
        _validate_payload_path(root, path, allowed_paths)

    tracked_manifest = tuple(_manifest_entry(root, path) for path in sorted(tracked_paths) if (root / path).exists())
    untracked_manifest = tuple(_manifest_entry(root, path) for path in sorted(untracked_paths))
    for path in tracked_paths:
        _validate_tracked_index_mode(root, path)

    diff_bytes = _git_bytes(
        root,
        "-c",
        "core.quotepath=false",
        "diff",
        "--binary",
        "--full-index",
        "--no-ext-diff",
        "--no-textconv",
        "--no-renames",
        "--",
    )
    return _WorkspaceEvidence(
        head_sha=head_sha,
        branch=branch,
        status_sha256=_sha256(status_bytes),
        tracked_diff_sha256=_sha256(diff_bytes),
        tracked_manifest=tracked_manifest,
        untracked_manifest=untracked_manifest,
    )


def _parse_status(status_bytes: bytes) -> tuple[tuple[str, ...], tuple[str, ...]]:
    try:
        records = status_bytes.split(b"\0")
        tracked: list[str] = []
        untracked: list[str] = []
        index = 0
        while index < len(records):
            raw = records[index]
            index += 1
            if not raw:
                continue
            record = raw.decode("utf-8", "strict")
            kind = record[0]
            if kind == "?":
                untracked.append(record[2:])
                continue
            if kind == "!":
                continue
            if kind == "u":
                raise HotHandoffCheckpointError("unmerged/conflicted Git state is unsupported")
            if kind not in {"1", "2"}:
                raise HotHandoffCheckpointError(f"unsupported porcelain-v2 record: {kind!r}")
            fields = record.split(" ", 8 if kind == "1" else 9)
            minimum = 9 if kind == "1" else 10
            if len(fields) != minimum:
                raise HotHandoffCheckpointError("malformed porcelain-v2 status record")
            xy = fields[1]
            submodule_state = fields[2]
            path = fields[-1]
            if len(xy) != 2:
                raise HotHandoffCheckpointError("malformed porcelain-v2 XY state")
            if xy[0] != ".":
                raise HotHandoffCheckpointError("staged changes are unsupported")
            if xy[1] not in {"M", "D", "T"}:
                raise HotHandoffCheckpointError(f"unsupported unstaged Git state: {xy!r}")
            if kind == "2":
                if index < len(records):
                    index += 1  # consume original path before rejecting rename/copy state
                raise HotHandoffCheckpointError("rename/copy Git state is unsupported")
            if submodule_state != "N...":
                raise HotHandoffCheckpointError("submodule state is unsupported")
            if xy[1] == "T":
                raise HotHandoffCheckpointError("tracked file type changes are unsupported")
            tracked.append(path)
    except UnicodeDecodeError as exc:
        raise HotHandoffCheckpointError("non-UTF-8 repository paths are unsupported") from exc
    if len(tracked) != len(set(tracked)) or len(untracked) != len(set(untracked)):
        raise HotHandoffCheckpointError("duplicate paths in Git status evidence")
    return tuple(sorted(tracked)), tuple(sorted(untracked))


def _normalize_allowed_paths(
    root: Path,
    allowed_paths: Sequence[str | os.PathLike[str]],
) -> tuple[str, ...]:
    if isinstance(allowed_paths, (str, bytes, os.PathLike)) or not isinstance(allowed_paths, Sequence):
        raise HotHandoffCheckpointError("allowed_paths must be a non-empty ordered sequence")
    normalized: list[str] = []
    for raw in allowed_paths:
        if not isinstance(raw, (str, os.PathLike)):
            raise HotHandoffCheckpointError("each allowed path must be a string or PathLike")
        value = os.fspath(raw)
        if not isinstance(value, str) or not value:
            raise HotHandoffCheckpointError("allowed paths must be non-empty text paths")
        if "\\" in value:
            raise HotHandoffCheckpointError("allowed paths must use repository-relative POSIX separators")
        pure = PurePosixPath(value)
        if pure.is_absolute() or re.match(r"^[A-Za-z]:", value):
            raise HotHandoffCheckpointError("absolute allowed paths are forbidden")
        if any(part in {"", ".", ".."} for part in value.split("/")):
            raise HotHandoffCheckpointError("allowed paths may not contain empty, '.' or '..' segments")
        normalized_path = pure.as_posix()
        _reject_forbidden_payload_path(normalized_path)
        candidate = root.joinpath(*pure.parts)
        _ensure_no_symlink_component(root, candidate, include_leaf=True)
        resolved = candidate.resolve(strict=False)
        if not _is_within(resolved, root):
            raise HotHandoffCheckpointError("allowed path escapes repository root")
        normalized.append(normalized_path)
    if not normalized:
        raise HotHandoffCheckpointError("allowed_paths must not be empty")
    if len(normalized) != len(set(normalized)):
        raise HotHandoffCheckpointError("allowed_paths contains duplicates")
    return tuple(sorted(normalized))


def _coerce_allowed_paths(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise HotHandoffCheckpointError("allowed_paths must be a tuple or list")
    items = tuple(value)
    for item in items:
        _validate_normalized_manifest_path(item)
        _reject_forbidden_payload_path(item)
    if not items or items != tuple(sorted(set(items))):
        raise HotHandoffCheckpointError("allowed_paths must be non-empty, unique, and sorted")
    return items


def _coerce_manifest(value: Any, field_name: str) -> tuple[WorkspaceFileManifestEntry, ...]:
    if not isinstance(value, (tuple, list)):
        raise HotHandoffCheckpointError(f"{field_name} must be a tuple or list")
    items = tuple(value)
    if any(not isinstance(item, WorkspaceFileManifestEntry) for item in items):
        raise HotHandoffCheckpointError(f"{field_name} entries must be WorkspaceFileManifestEntry")
    if items != tuple(sorted(items, key=lambda item: item.path)):
        raise HotHandoffCheckpointError(f"{field_name} must be deterministically path-sorted")
    if len({item.path for item in items}) != len(items):
        raise HotHandoffCheckpointError(f"{field_name} contains duplicate paths")
    return items


def _validate_payload_path(root: Path, relative: str, allowed_paths: tuple[str, ...]) -> None:
    _validate_normalized_manifest_path(relative)
    _reject_forbidden_payload_path(relative)
    if not any(relative == scope or relative.startswith(scope + "/") for scope in allowed_paths):
        raise HotHandoffCheckpointError(f"changed path is outside allowed scope: {relative!r}")
    candidate = root.joinpath(*PurePosixPath(relative).parts)
    _ensure_no_symlink_component(root, candidate, include_leaf=True)
    if not _is_within(candidate.resolve(strict=False), root):
        raise HotHandoffCheckpointError(f"changed path escapes repository root: {relative!r}")


def _validate_normalized_manifest_path(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise HotHandoffCheckpointError("manifest path must be non-empty repository-relative POSIX text")
    if value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise HotHandoffCheckpointError("manifest path must be repository-relative")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts) or PurePosixPath(value).as_posix() != value:
        raise HotHandoffCheckpointError("manifest path must be normalized and traversal-free")
    return value


def _reject_forbidden_payload_path(relative: str) -> None:
    components = [component.lower() for component in PurePosixPath(relative).parts]
    if any(component in _FORBIDDEN_PAYLOAD_COMPONENTS for component in components):
        raise HotHandoffCheckpointError(f"runtime/secret/session payload path is forbidden: {relative!r}")
    if any(component.startswith(".env.") for component in components):
        raise HotHandoffCheckpointError(f"environment-secret payload path is forbidden: {relative!r}")


def _manifest_entry(root: Path, relative: str) -> WorkspaceFileManifestEntry:
    path = root.joinpath(*PurePosixPath(relative).parts)
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise HotHandoffCheckpointError(f"workspace payload is missing or unreadable: {relative!r}") from exc
    if stat.S_ISLNK(mode):
        raise HotHandoffCheckpointError(f"symlink payload is unsupported: {relative!r}")
    if not stat.S_ISREG(mode):
        raise HotHandoffCheckpointError(f"special/non-regular payload is unsupported: {relative!r}")
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise HotHandoffCheckpointError(f"workspace payload is unreadable: {relative!r}") from exc
    _reject_binary_payload(payload, relative)
    return WorkspaceFileManifestEntry(path=relative, size_bytes=len(payload), sha256=_sha256(payload))


def _reject_binary_payload(payload: bytes, relative: str) -> None:
    if b"\0" in payload:
        raise HotHandoffCheckpointError(f"binary payload is unsupported: {relative!r}")
    try:
        payload.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise HotHandoffCheckpointError(f"non-UTF-8/binary payload is unsupported: {relative!r}") from exc


def _validate_tracked_index_mode(root: Path, relative: str) -> None:
    result = _git_bytes(root, "ls-files", "--stage", "-z", "--", relative)
    if not result:
        raise HotHandoffCheckpointError(f"tracked status path is absent from index: {relative!r}")
    records = [item for item in result.split(b"\0") if item]
    if len(records) != 1:
        raise HotHandoffCheckpointError(f"ambiguous index stages for tracked path: {relative!r}")
    try:
        metadata, indexed_path = records[0].split(b"\t", 1)
        mode = metadata.split(b" ", 1)[0]
        decoded_path = indexed_path.decode("utf-8", "strict")
    except (ValueError, UnicodeDecodeError) as exc:
        raise HotHandoffCheckpointError("malformed Git index evidence") from exc
    if decoded_path != relative or mode not in {b"100644", b"100755"}:
        raise HotHandoffCheckpointError(f"symlink/submodule/special tracked state is unsupported: {relative!r}")


def _reject_git_operation_in_progress(root: Path) -> None:
    for marker in _OPERATION_MARKERS:
        marker_path = _git_text(
            root,
            "rev-parse",
            "--git-path",
            marker,
            failure=f"cannot inspect Git operation marker {marker}",
        )
        path = Path(marker_path)
        if not path.is_absolute():
            path = root / path
        if path.exists():
            raise HotHandoffCheckpointError(f"Git operation in progress ({marker})")


def _repository_root(worktree: str | os.PathLike[str]) -> Path:
    try:
        requested = Path(worktree).resolve(strict=True)
    except (OSError, TypeError) as exc:
        raise HotHandoffCheckpointError("worktree must identify an existing repository directory") from exc
    if not requested.is_dir():
        raise HotHandoffCheckpointError("worktree must identify a directory")
    root_text = _git_text(requested, "rev-parse", "--show-toplevel", failure="not a Git worktree")
    root = Path(root_text).resolve(strict=True)
    if requested != root:
        raise HotHandoffCheckpointError("worktree must identify the repository root exactly")
    return root


def _validate_external_storage(root: Path, checkpoint_dir: str | os.PathLike[str]) -> Path:
    try:
        storage = Path(checkpoint_dir).resolve(strict=False)
    except (OSError, TypeError) as exc:
        raise HotHandoffCheckpointError("checkpoint_dir is invalid") from exc
    if storage == root or _is_within(storage, root):
        raise HotHandoffCheckpointError("checkpoint storage must resolve outside the repository worktree")
    try:
        storage.mkdir(parents=True, exist_ok=True)
        storage = storage.resolve(strict=True)
    except OSError as exc:
        raise HotHandoffCheckpointError("checkpoint storage cannot be created safely") from exc
    if not storage.is_dir() or storage == root or _is_within(storage, root):
        raise HotHandoffCheckpointError("checkpoint storage must be an external directory")
    return storage


def _persist_checkpoint(storage: Path, checkpoint: HotHandoffCheckpoint) -> Path:
    destination = storage / f"{checkpoint.checkpoint_fingerprint}.json"
    content = (checkpoint.to_canonical_json() + "\n").encode("utf-8")
    try:
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    except FileExistsError:
        try:
            existing = destination.read_bytes()
        except OSError as exc:
            raise HotHandoffCheckpointError("existing checkpoint evidence is unreadable") from exc
        if existing != content:
            raise HotHandoffCheckpointError("existing content-addressed checkpoint evidence differs")
        return destination
    except OSError as exc:
        raise HotHandoffCheckpointError("checkpoint evidence could not be persisted") from exc
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            destination.chmod(stat.S_IREAD)
        except OSError:
            pass
    except Exception:
        try:
            destination.unlink()
        except OSError:
            pass
        raise
    return destination


def _ensure_no_symlink_component(root: Path, candidate: Path, *, include_leaf: bool) -> None:
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise HotHandoffCheckpointError("path escapes repository root") from exc
    parts = relative.parts if include_leaf else relative.parts[:-1]
    current = root
    for part in parts:
        current = current / part
        try:
            if current.is_symlink():
                raise HotHandoffCheckpointError(f"symlink path component is unsupported: {current}")
        except OSError as exc:
            raise HotHandoffCheckpointError(f"cannot inspect path component safely: {current}") from exc


def _is_within(candidate: Path, parent: Path) -> bool:
    try:
        candidate.relative_to(parent)
        return True
    except ValueError:
        return False


def _validate_sha256(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not _HEX_64_PATTERN.fullmatch(value):
        raise HotHandoffCheckpointError(f"{field_name} must be an exact lowercase SHA-256 hex string")
    return value


def _validate_branch(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not _BRANCH_PATTERN.fullmatch(value)
        or ".." in value
        or "//" in value
        or value.endswith(("/", ".", ".lock"))
        or value.startswith(".")
    ):
        raise HotHandoffCheckpointError(f"target_branch is not a safe canonical Git branch: {value!r}")
    return value


def _git_bytes(root: Path, *arguments: str) -> bytes:
    environment = os.environ.copy()
    environment.update({"GIT_OPTIONAL_LOCKS": "0", "LC_ALL": "C", "LANG": "C"})
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=root,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise HotHandoffCheckpointError("Git executable could not be invoked") from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise HotHandoffCheckpointError(f"Git inspection failed: {detail or arguments[0]}")
    return result.stdout


def _git_text(root: Path, *arguments: str, failure: str) -> str:
    environment = os.environ.copy()
    environment.update({"GIT_OPTIONAL_LOCKS": "0", "LC_ALL": "C", "LANG": "C"})
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=root,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise HotHandoffCheckpointError("Git executable could not be invoked") from exc
    if result.returncode != 0:
        raise HotHandoffCheckpointError(failure)
    try:
        return result.stdout.decode("utf-8", "strict").strip()
    except UnicodeDecodeError as exc:
        raise HotHandoffCheckpointError("Git text output is not valid UTF-8") from exc


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


__all__ = [
    "HOT_HANDOFF_SCHEMA_VERSION",
    "HotHandoffCheckpoint",
    "HotHandoffCheckpointError",
    "UntrackedFileManifestEntry",
    "WorkspaceFileManifestEntry",
    "capture_checkpoint",
    "capture_hot_handoff_checkpoint",
    "verify_checkpoint",
    "verify_hot_handoff_checkpoint",
]
