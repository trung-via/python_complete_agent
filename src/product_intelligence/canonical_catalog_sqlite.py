"""Durable SQLite boundary for one canonical catalog snapshot.

TASK-120 owns only the filesystem, SQLite layout, and transaction boundary.  The
catalog payload remains opaque here: TASK-119 alone encodes and decodes it, and
TASK-118 alone decides family and variant registration semantics.
"""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Callable, TypeVar

from src.product_intelligence.canonical_catalog import (
    CanonicalCatalogState,
    CatalogRegistrationResult,
    CatalogRegistrationStatus,
    create_empty_canonical_catalog,
    register_canonical_family,
    register_canonical_variant,
)
from src.product_intelligence.canonical_catalog_codec import (
    decode_canonical_catalog,
    encode_canonical_catalog,
)
from src.product_intelligence.canonical_family import CanonicalProductFamily
from src.product_intelligence.canonical_variant import CanonicalSellableVariant


SQLITE_CATALOG_STORAGE_VERSION = 1


class CanonicalCatalogStorageError(RuntimeError):
    """Raised for catalog path, SQLite, layout, lock, or transaction failures."""


_TABLE_NAME = "canonical_catalog_snapshot"
_CREATE_SCHEMA_SQL = """CREATE TABLE canonical_catalog_snapshot (
    singleton INTEGER NOT NULL PRIMARY KEY CHECK (singleton = 1),
    storage_version INTEGER NOT NULL CHECK (storage_version = 1),
    payload BLOB NOT NULL CHECK (typeof(payload) = 'blob')
) WITHOUT ROWID"""
_EXPECTED_COLUMNS = (
    (0, "singleton", "INTEGER", 1, None, 1, 0),
    (1, "storage_version", "INTEGER", 1, None, 0, 0),
    (2, "payload", "BLOB", 1, None, 0, 0),
)

_RegistrationValue = TypeVar(
    "_RegistrationValue", CanonicalProductFamily, CanonicalSellableVariant
)


def create_sqlite_canonical_catalog(
    database_path: os.PathLike[str] | str,
) -> CanonicalCatalogState:
    """Atomically create and publish one empty V1 canonical catalog store."""

    path = _absolute_path(database_path)
    temporary_path: Path | None = None
    connection: sqlite3.Connection | None = None
    transaction_started = False
    try:
        if os.path.lexists(path):
            raise CanonicalCatalogStorageError("database path already exists")

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        os.close(descriptor)
        temporary_path = Path(temporary_name)

        connection = _connect_path(temporary_path)
        _configure_writer(connection)
        connection.execute("BEGIN IMMEDIATE")
        transaction_started = True
        connection.execute(_CREATE_SCHEMA_SQL)
        catalog = create_empty_canonical_catalog()
        payload = encode_canonical_catalog(catalog)
        connection.execute(
            "INSERT INTO canonical_catalog_snapshot "
            "(singleton, storage_version, payload) VALUES (1, ?, ?)",
            (SQLITE_CATALOG_STORAGE_VERSION, sqlite3.Binary(payload)),
        )
        _commit_transaction(connection)
        transaction_started = False
        connection.close()
        connection = None

        # A same-filesystem hard link publishes the completed database atomically
        # and, unlike replace, fails if another creator won the target path.
        os.link(temporary_path, path)
        return catalog
    except CanonicalCatalogStorageError:
        if transaction_started and connection is not None:
            _rollback_best_effort(connection)
        raise
    except (OSError, sqlite3.Error) as exc:
        if transaction_started and connection is not None:
            _rollback_best_effort(connection)
        raise CanonicalCatalogStorageError(
            "canonical catalog database could not be created"
        ) from exc
    finally:
        if connection is not None:
            _close_best_effort(connection)
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def load_sqlite_canonical_catalog(
    database_path: os.PathLike[str] | str,
) -> CanonicalCatalogState:
    """Load one pre-existing, strictly valid V1 canonical catalog store."""

    path = _require_existing_path(database_path)
    connection: sqlite3.Connection | None = None
    try:
        connection = _connect_existing(path, mode="ro")
        catalog, _ = _load_snapshot(connection)
        return catalog
    except CanonicalCatalogStorageError:
        raise
    except sqlite3.Error as exc:
        raise CanonicalCatalogStorageError(
            "canonical catalog database could not be loaded"
        ) from exc
    finally:
        if connection is not None:
            _close_best_effort(connection)


def register_sqlite_canonical_family(
    database_path: os.PathLike[str] | str,
    family: CanonicalProductFamily,
) -> CatalogRegistrationResult:
    """Durably register one exact family through TASK-118 semantics."""

    return _register_sqlite_value(
        database_path,
        family,
        register_canonical_family,
    )


def register_sqlite_canonical_variant(
    database_path: os.PathLike[str] | str,
    variant: CanonicalSellableVariant,
) -> CatalogRegistrationResult:
    """Durably register one exact variant through TASK-118 semantics."""

    return _register_sqlite_value(
        database_path,
        variant,
        register_canonical_variant,
    )


def _register_sqlite_value(
    database_path: os.PathLike[str] | str,
    value: _RegistrationValue,
    register: Callable[
        [CanonicalCatalogState, _RegistrationValue], CatalogRegistrationResult
    ],
) -> CatalogRegistrationResult:
    path = _require_existing_path(database_path)
    connection: sqlite3.Connection | None = None
    transaction_started = False
    try:
        connection = _connect_existing(path, mode="rw")
        _configure_writer(connection)
        # Reserve the single writer before reading the snapshot.  timeout=0 on
        # the connection makes competing-writer contention fail closed.
        connection.execute("BEGIN IMMEDIATE")
        transaction_started = True
        catalog, _ = _load_snapshot(connection)
        result = register(catalog, value)

        if result.status is CatalogRegistrationStatus.INSERTED:
            payload = encode_canonical_catalog(result.catalog)
            cursor = connection.execute(
                "UPDATE canonical_catalog_snapshot SET payload = ? "
                "WHERE singleton = 1 AND storage_version = ?",
                (sqlite3.Binary(payload), SQLITE_CATALOG_STORAGE_VERSION),
            )
            if cursor.rowcount != 1:
                raise CanonicalCatalogStorageError(
                    "canonical catalog singleton update was ambiguous"
                )
        elif result.status is not CatalogRegistrationStatus.ALREADY_PRESENT:
            raise CanonicalCatalogStorageError(
                "canonical catalog registration returned an unknown status"
            )

        _commit_transaction(connection)
        transaction_started = False
        return result
    except CanonicalCatalogStorageError:
        if transaction_started and connection is not None:
            _rollback_best_effort(connection)
        raise
    except (OSError, sqlite3.Error) as exc:
        if transaction_started and connection is not None:
            _rollback_best_effort(connection)
        raise CanonicalCatalogStorageError(
            "canonical catalog registration transaction failed"
        ) from exc
    except BaseException:
        if transaction_started and connection is not None:
            _rollback_best_effort(connection)
        raise
    finally:
        if connection is not None:
            _close_best_effort(connection)


def _load_snapshot(
    connection: sqlite3.Connection,
) -> tuple[CanonicalCatalogState, bytes]:
    integrity = connection.execute("PRAGMA integrity_check").fetchall()
    if integrity != [("ok",)]:
        raise CanonicalCatalogStorageError(
            "canonical catalog database failed SQLite integrity validation"
        )

    objects = connection.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_schema "
        "WHERE substr(name, 1, 7) != 'sqlite_' ORDER BY type, name"
    ).fetchall()
    expected_objects = [("table", _TABLE_NAME, _TABLE_NAME, _CREATE_SCHEMA_SQL)]
    if objects != expected_objects:
        raise CanonicalCatalogStorageError(
            "canonical catalog database has an invalid or ambiguous user schema"
        )

    columns = connection.execute(
        "PRAGMA table_xinfo(canonical_catalog_snapshot)"
    ).fetchall()
    if tuple(columns) != _EXPECTED_COLUMNS:
        raise CanonicalCatalogStorageError(
            "canonical catalog snapshot table has an invalid column contract"
        )

    rows = connection.execute(
        "SELECT singleton, storage_version, payload, typeof(payload) "
        "FROM canonical_catalog_snapshot LIMIT 2"
    ).fetchall()
    if len(rows) != 1:
        raise CanonicalCatalogStorageError(
            "canonical catalog database must contain exactly one snapshot row"
        )
    singleton, storage_version, payload, storage_type = rows[0]
    if type(singleton) is not int or singleton != 1:
        raise CanonicalCatalogStorageError("invalid canonical catalog singleton")
    if (
        type(storage_version) is not int
        or storage_version != SQLITE_CATALOG_STORAGE_VERSION
    ):
        raise CanonicalCatalogStorageError(
            "unsupported canonical catalog storage version"
        )
    if storage_type != "blob" or type(payload) is not bytes:
        raise CanonicalCatalogStorageError(
            "canonical catalog payload must be stored as an exact SQLite BLOB"
        )
    return decode_canonical_catalog(payload), payload


def _absolute_path(database_path: os.PathLike[str] | str) -> Path:
    try:
        raw_path = os.fspath(database_path)
        if not isinstance(raw_path, str) or not raw_path:
            raise TypeError
        return Path(os.path.abspath(raw_path))
    except (TypeError, ValueError, OSError) as exc:
        raise CanonicalCatalogStorageError(
            "database_path must identify one filesystem path"
        ) from exc


def _require_existing_path(database_path: os.PathLike[str] | str) -> Path:
    path = _absolute_path(database_path)
    if not os.path.lexists(path):
        raise CanonicalCatalogStorageError("canonical catalog database does not exist")
    return path


def _connect_path(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path, timeout=0.0, isolation_level=None)


def _connect_existing(path: Path, *, mode: str) -> sqlite3.Connection:
    # Path.as_uri quotes URI metacharacters, while mode=ro/rw prevents SQLite's
    # default implicit database creation behavior.
    uri = f"{path.as_uri()}?mode={mode}"
    return sqlite3.connect(
        uri,
        uri=True,
        timeout=0.0,
        isolation_level=None,
    )


def _configure_writer(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA synchronous = FULL")
    row = connection.execute("PRAGMA synchronous").fetchone()
    if row != (2,):
        raise CanonicalCatalogStorageError(
            "SQLite synchronous FULL durability could not be requested"
        )


def _commit_transaction(connection: sqlite3.Connection) -> None:
    connection.execute("COMMIT")


def _rollback_best_effort(connection: sqlite3.Connection) -> None:
    try:
        connection.execute("ROLLBACK")
    except sqlite3.Error:
        pass


def _close_best_effort(connection: sqlite3.Connection) -> None:
    try:
        connection.close()
    except sqlite3.Error:
        pass


__all__ = [
    "CanonicalCatalogStorageError",
    "SQLITE_CATALOG_STORAGE_VERSION",
    "create_sqlite_canonical_catalog",
    "load_sqlite_canonical_catalog",
    "register_sqlite_canonical_family",
    "register_sqlite_canonical_variant",
]
