"""Bounded local discovery of persisted Product Source Pack evidence."""

from collections.abc import Iterable as _Iterable
from dataclasses import dataclass as _dataclass
import os as _os
import stat as _stat

from src.product_intelligence.entity_resolution import (
    SourceObservationIdentity as _SourceObservationIdentity,
)
from src.product_source.models import ProductSourcePack as _ProductSourcePack
from src.product_source.serialization import (
    deserialize_product_source_pack as _deserialize_product_source_pack,
)


_MANIFEST_BASENAME = "source_pack.json"
_MAX_CONFIGURED_ROOTS = 32
_MAX_DISCOVERED_MANIFESTS = 1024
_MAX_VISITED_DIRECTORIES = 4096


class SourceEvidenceIntakeError(ValueError):
    """Raised when source-evidence intake cannot safely produce an inventory."""


@_dataclass(frozen=True)
class SourceEvidenceInventory:
    """Immutable, index-aligned persisted paths and typed source packs."""

    manifest_paths: tuple[str, ...]
    source_packs: tuple[_ProductSourcePack, ...]

    def __post_init__(self) -> None:
        if type(self.manifest_paths) is not tuple or type(self.source_packs) is not tuple:
            raise SourceEvidenceIntakeError("inventory values must be exact tuples")
        if len(self.manifest_paths) != len(self.source_packs):
            raise SourceEvidenceIntakeError("inventory paths and packs must be aligned")
        if any(type(path) is not str for path in self.manifest_paths):
            raise SourceEvidenceIntakeError("inventory manifest paths must be exact strings")
        if any(not isinstance(pack, _ProductSourcePack) for pack in self.source_packs):
            raise SourceEvidenceIntakeError(
                "inventory source packs must be ProductSourcePack values"
            )


def _canonical_path(path: str) -> str:
    try:
        return _os.path.realpath(_os.path.abspath(path))
    except (OSError, ValueError, TypeError) as exc:
        raise SourceEvidenceIntakeError("filesystem path cannot be resolved safely") from exc


def _path_key(path: str) -> tuple[str, str]:
    return (_os.path.normcase(path), path)


def _retain_path_representative(
    paths_by_key: dict[str, str], canonical_path: str
) -> None:
    filesystem_key = _os.path.normcase(canonical_path)
    current = paths_by_key.get(filesystem_key)
    if current is None or _path_key(canonical_path) < _path_key(current):
        paths_by_key[filesystem_key] = canonical_path


def _is_within(path: str, root: str) -> bool:
    try:
        common = _os.path.commonpath((path, root))
        return _os.path.normcase(common) == _os.path.normcase(root)
    except (OSError, ValueError) as exc:
        raise SourceEvidenceIntakeError(
            "filesystem path cannot be bounded to a configured root"
        ) from exc


def _is_alias(stat_result: _os.stat_result) -> bool:
    reparse_flag = getattr(_stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    file_attributes = getattr(stat_result, "st_file_attributes", 0)
    return _stat.S_ISLNK(stat_result.st_mode) or bool(
        reparse_flag and file_attributes & reparse_flag
    )


def _resolve_roots(roots: _Iterable[str]) -> tuple[str, ...]:
    if isinstance(roots, (str, bytes)):
        raise SourceEvidenceIntakeError("roots must be an iterable, not str or bytes")
    try:
        supplied_roots = tuple(roots)
    except (TypeError, OSError) as exc:
        raise SourceEvidenceIntakeError("roots must be an iterable of path strings") from exc
    except Exception as exc:
        raise SourceEvidenceIntakeError("roots could not be materialized safely") from exc

    if len(supplied_roots) > _MAX_CONFIGURED_ROOTS:
        raise SourceEvidenceIntakeError("configured root limit exceeded")

    canonical_by_key: dict[str, str] = {}
    for root in supplied_roots:
        if type(root) is not str or not root:
            raise SourceEvidenceIntakeError(
                "each root must be an exact non-empty str"
            )
        canonical_root = _canonical_path(root)
        try:
            if not _os.path.exists(canonical_root):
                raise SourceEvidenceIntakeError("configured root does not exist")
            if not _os.path.isdir(canonical_root):
                raise SourceEvidenceIntakeError("configured root is not a directory")
        except OSError as exc:
            raise SourceEvidenceIntakeError(
                "configured root cannot be inspected safely"
            ) from exc
        _retain_path_representative(canonical_by_key, canonical_root)

    return tuple(sorted(canonical_by_key.values(), key=_path_key))


def _discover_manifests(roots: tuple[str, ...]) -> tuple[str, ...]:
    manifests_by_key: dict[str, str] = {}
    visited_directory_keys: set[str] = set()

    def fail_walk(error: OSError) -> None:
        raise SourceEvidenceIntakeError(
            "configured root cannot be scanned safely"
        ) from error

    for root in roots:
        try:
            walker = _os.walk(root, topdown=True, onerror=fail_walk, followlinks=False)
            for directory, child_directories, filenames in walker:
                canonical_directory = _canonical_path(directory)
                if not _is_within(canonical_directory, root):
                    raise SourceEvidenceIntakeError(
                        "discovered directory escapes its configured root"
                    )

                directory_key = _os.path.normcase(canonical_directory)
                if directory_key not in visited_directory_keys:
                    visited_directory_keys.add(directory_key)
                    if len(visited_directory_keys) > _MAX_VISITED_DIRECTORIES:
                        raise SourceEvidenceIntakeError("directory scan limit exceeded")

                safe_child_directories: list[str] = []
                for name in child_directories:
                    child_path = _os.path.join(directory, name)
                    try:
                        child_stat = _os.lstat(child_path)
                    except OSError as exc:
                        raise SourceEvidenceIntakeError(
                            "discovered directory cannot be inspected safely"
                        ) from exc
                    if not _is_alias(child_stat):
                        safe_child_directories.append(name)
                child_directories[:] = safe_child_directories

                for name in filenames:
                    if name != _MANIFEST_BASENAME:
                        continue
                    candidate = _os.path.join(directory, name)
                    try:
                        candidate_stat = _os.lstat(candidate)
                    except OSError as exc:
                        raise SourceEvidenceIntakeError(
                            "manifest candidate cannot be inspected safely"
                        ) from exc
                    if _is_alias(candidate_stat):
                        raise SourceEvidenceIntakeError(
                            "source_pack.json filesystem aliases are not permitted"
                        )
                    if not _stat.S_ISREG(candidate_stat.st_mode):
                        continue

                    canonical_manifest = _canonical_path(candidate)
                    if not _is_within(canonical_manifest, root):
                        raise SourceEvidenceIntakeError(
                            "manifest candidate escapes its configured root"
                        )
                    _retain_path_representative(manifests_by_key, canonical_manifest)
                    if len(manifests_by_key) > _MAX_DISCOVERED_MANIFESTS:
                        raise SourceEvidenceIntakeError("manifest limit exceeded")
        except SourceEvidenceIntakeError:
            raise
        except OSError as exc:
            raise SourceEvidenceIntakeError(
                "configured root cannot be scanned safely"
            ) from exc

    return tuple(sorted(manifests_by_key.values(), key=_path_key))


def intake_product_source_evidence(roots: _Iterable[str]) -> SourceEvidenceInventory:
    """Discover and strictly rehydrate local manifests beneath explicit roots."""

    manifest_paths = _discover_manifests(_resolve_roots(roots))
    packs: list[_ProductSourcePack] = []
    identities: set[_SourceObservationIdentity] = set()
    for manifest_path in manifest_paths:
        pack = _deserialize_product_source_pack(manifest_path)
        identity = _SourceObservationIdentity.from_pack(pack)
        if identity in identities:
            raise SourceEvidenceIntakeError(
                "duplicate exact SourceObservationIdentity in intake batch"
            )
        identities.add(identity)
        packs.append(pack)

    return SourceEvidenceInventory(
        manifest_paths=manifest_paths,
        source_packs=tuple(packs),
    )


__all__ = [
    "SourceEvidenceIntakeError",
    "SourceEvidenceInventory",
    "intake_product_source_evidence",
]
