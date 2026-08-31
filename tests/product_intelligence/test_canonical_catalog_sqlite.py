"""Focused regressions for TASK-120 canonical catalog SQLite durability."""

from contextlib import closing
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
import sqlite3
from unittest.mock import patch

import pytest

import src.product_intelligence.canonical_catalog_sqlite as storage_module
from src.product_intelligence import (
    SQLITE_CATALOG_STORAGE_VERSION,
    CanonicalCatalogCodecError,
    CanonicalCatalogIntegrityError,
    CanonicalCatalogStorageError,
    CatalogRegistrationStatus,
    EntityResolutionResult,
    FamilyMergeDecision,
    MultiObservationResolutionGraph,
    ProductRelationship,
    ResolutionEvidence,
    SellableVariantDecision,
    SourceObservationIdentity,
    create_canonical_family,
    create_canonical_sellable_variant,
    create_family_merge_decision_record,
    create_family_merge_proposal,
    create_sellable_variant_decision_record,
    create_sellable_variant_proposal,
    create_sqlite_canonical_catalog,
    encode_canonical_catalog,
    group_resolution_graph,
    load_sqlite_canonical_catalog,
    register_sqlite_canonical_family,
    register_sqlite_canonical_variant,
)


def _family(prefix: str, family_id: str):
    names = ("a", "b", "c")
    members = {
        name: SourceObservationIdentity(
            source_pack_id=f"pack-{prefix}-{name}",
            platform="test-market",
            source_product_id=f"{prefix}-{name}",
            product_url=f"https://market.example/{prefix}/{name}",
            observed_at=datetime(2026, 8, 31, tzinfo=timezone.utc),
        )
        for name in names
    }
    pairwise_results = []
    for left_name, right_name in combinations(names, 2):
        relationship = (
            ProductRelationship.EXACT_VARIANT_MATCH
            if (left_name, right_name) == ("a", "b")
            else ProductRelationship.SAME_PRODUCT_FAMILY
        )
        code = f"{prefix}-{left_name}-{right_name}"
        pairwise_results.append(
            EntityResolutionResult(
                relationship=relationship,
                confidence=0.98,
                left=members[right_name],
                right=members[left_name],
                reasons=(code,),
                evidence=(ResolutionEvidence(code, "retained"),),
            )
        )
    graph = MultiObservationResolutionGraph(
        observations=tuple(reversed(tuple(members.values()))),
        pairwise_results=tuple(reversed(pairwise_results)),
        conflicts=(),
    )
    proposal = create_family_merge_proposal(
        graph,
        group_resolution_graph(graph).groups[0],
    )
    decision = create_family_merge_decision_record(
        proposal,
        decision=FamilyMergeDecision.APPROVE,
        actor="family reviewer",
        decided_at=datetime(2026, 8, 31, 1, tzinfo=timezone.utc),
    )
    return create_canonical_family(decision, family_id=family_id)


def _variant(family, variant_id: str):
    proposal = create_sellable_variant_proposal(family, family.members[:2])
    decision = create_sellable_variant_decision_record(
        proposal,
        decision=SellableVariantDecision.APPROVE,
        actor="variant reviewer",
        decided_at=datetime(2026, 8, 31, 2, tzinfo=timezone.utc),
    )
    return create_canonical_sellable_variant(decision, variant_id=variant_id)


def _payload(path: Path) -> bytes:
    with closing(sqlite3.connect(path)) as connection:
        value = connection.execute(
            "SELECT payload FROM canonical_catalog_snapshot WHERE singleton = 1"
        ).fetchone()[0]
    assert type(value) is bytes
    return value


def test_public_surface_and_create_load_reopen_exact_v1_blob(tmp_path):
    path = tmp_path / "catalog.sqlite"
    created = create_sqlite_canonical_catalog(path)

    assert SQLITE_CATALOG_STORAGE_VERSION == 1
    assert storage_module.__all__ == [
        "CanonicalCatalogStorageError",
        "SQLITE_CATALOG_STORAGE_VERSION",
        "create_sqlite_canonical_catalog",
        "load_sqlite_canonical_catalog",
        "register_sqlite_canonical_family",
        "register_sqlite_canonical_variant",
    ]
    forbidden = ("save", "replace", "upsert", "payload", "raw_sql", "connection")
    assert not any(
        fragment in exported.lower()
        for exported in storage_module.__all__
        for fragment in forbidden
    )
    assert created.families == () and created.variants == ()
    assert load_sqlite_canonical_catalog(path) == created
    with closing(sqlite3.connect(path)) as connection:
        objects = connection.execute(
            "SELECT type, name FROM sqlite_schema WHERE name NOT LIKE 'sqlite_%'"
        ).fetchall()
        row = connection.execute(
            "SELECT singleton, storage_version, payload, typeof(payload) "
            "FROM canonical_catalog_snapshot"
        ).fetchone()
    assert objects == [("table", "canonical_catalog_snapshot")]
    assert row == (1, 1, encode_canonical_catalog(created), "blob")
    with closing(sqlite3.connect(path)) as connection:
        for statement in (
            "UPDATE canonical_catalog_snapshot SET singleton = 2",
            "UPDATE canonical_catalog_snapshot SET storage_version = 2",
            "UPDATE canonical_catalog_snapshot SET payload = 'text'",
        ):
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(statement)
            connection.rollback()

    original = path.read_bytes()
    with pytest.raises(CanonicalCatalogStorageError):
        create_sqlite_canonical_catalog(path)
    assert path.read_bytes() == original


def test_missing_load_never_creates_and_corrupt_file_fails_as_storage(tmp_path):
    missing = tmp_path / "missing.sqlite"
    with pytest.raises(CanonicalCatalogStorageError):
        load_sqlite_canonical_catalog(missing)
    assert not missing.exists()

    corrupt = tmp_path / "corrupt.sqlite"
    corrupt.write_bytes(b"not a SQLite database")
    with pytest.raises(CanonicalCatalogStorageError):
        load_sqlite_canonical_catalog(corrupt)
    assert corrupt.read_bytes() == b"not a SQLite database"


def test_family_and_variant_insert_reopen_and_exact_no_write(tmp_path):
    path = tmp_path / "catalog.sqlite"
    create_sqlite_canonical_catalog(path)
    family = _family("one", "family-1")
    family_result = register_sqlite_canonical_family(path, family)
    assert family_result.status is CatalogRegistrationStatus.INSERTED
    assert load_sqlite_canonical_catalog(path) == family_result.catalog

    family_payload = _payload(path)
    family_noop = register_sqlite_canonical_family(path, family)
    assert family_noop.status is CatalogRegistrationStatus.ALREADY_PRESENT
    assert _payload(path) == family_payload

    variant = _variant(family, "variant-1")
    variant_result = register_sqlite_canonical_variant(path, variant)
    assert variant_result.status is CatalogRegistrationStatus.INSERTED
    reopened = load_sqlite_canonical_catalog(path)
    assert reopened == variant_result.catalog
    assert encode_canonical_catalog(reopened) == _payload(path)

    variant_payload = _payload(path)
    variant_noop = register_sqlite_canonical_variant(path, variant)
    assert variant_noop.status is CatalogRegistrationStatus.ALREADY_PRESENT
    assert _payload(path) == variant_payload


def test_registration_delegates_once_to_catalog_and_codec_authorities(tmp_path):
    path = tmp_path / "catalog.sqlite"
    create_sqlite_canonical_catalog(path)
    family = _family("one", "family-1")

    with (
        patch.object(
            storage_module,
            "decode_canonical_catalog",
            wraps=storage_module.decode_canonical_catalog,
        ) as decode,
        patch.object(
            storage_module,
            "register_canonical_family",
            wraps=storage_module.register_canonical_family,
        ) as register,
        patch.object(
            storage_module,
            "encode_canonical_catalog",
            wraps=storage_module.encode_canonical_catalog,
        ) as encode,
    ):
        result = storage_module.register_sqlite_canonical_family(path, family)

    assert result.status is CatalogRegistrationStatus.INSERTED
    decode.assert_called_once()
    register.assert_called_once()
    encode.assert_called_once_with(result.catalog)


def test_domain_and_codec_errors_remain_distinct_and_do_not_commit(tmp_path):
    path = tmp_path / "catalog.sqlite"
    create_sqlite_canonical_catalog(path)
    family = _family("one", "family-1")
    register_sqlite_canonical_family(path, family)
    committed = _payload(path)

    conflicting = _family("two", "family-1")
    with pytest.raises(CanonicalCatalogIntegrityError):
        register_sqlite_canonical_family(path, conflicting)
    assert _payload(path) == committed

    with closing(sqlite3.connect(path)) as connection:
        with connection:
            connection.execute(
                "UPDATE canonical_catalog_snapshot SET payload = ?",
                (sqlite3.Binary(b"{}"),),
            )
    invalid_payload = _payload(path)
    with pytest.raises(CanonicalCatalogCodecError):
        load_sqlite_canonical_catalog(path)
    with pytest.raises(CanonicalCatalogCodecError):
        register_sqlite_canonical_family(path, family)
    assert _payload(path) == invalid_payload


@pytest.mark.parametrize(
    "damage",
    [
        "extra_table",
        "extra_view",
        "extra_trigger",
        "extra_index",
        "zero_rows",
        "multiple_rows",
        "version",
        "singleton",
        "text",
    ],
)
def test_strict_v1_layout_and_row_contract_fail_closed(tmp_path, damage):
    path = tmp_path / f"{damage}.sqlite"
    create_sqlite_canonical_catalog(path)
    with closing(sqlite3.connect(path)) as connection:
        with connection:
            if damage == "extra_table":
                connection.execute("CREATE TABLE extra(value INTEGER)")
            elif damage == "extra_view":
                connection.execute(
                    "CREATE VIEW extra_view AS SELECT singleton "
                    "FROM canonical_catalog_snapshot"
                )
            elif damage == "extra_trigger":
                connection.execute(
                    "CREATE TRIGGER extra_trigger AFTER UPDATE "
                    "ON canonical_catalog_snapshot BEGIN SELECT 1; END"
                )
            elif damage == "extra_index":
                connection.execute(
                    "CREATE INDEX extra_index "
                    "ON canonical_catalog_snapshot(storage_version)"
                )
            elif damage == "zero_rows":
                connection.execute("DELETE FROM canonical_catalog_snapshot")
            else:
                connection.execute("PRAGMA ignore_check_constraints = ON")
                if damage == "multiple_rows":
                    payload = connection.execute(
                        "SELECT payload FROM canonical_catalog_snapshot"
                    ).fetchone()[0]
                    connection.execute(
                        "INSERT INTO canonical_catalog_snapshot "
                        "(singleton, storage_version, payload) VALUES (2, 1, ?)",
                        (sqlite3.Binary(payload),),
                    )
                elif damage == "version":
                    connection.execute(
                        "UPDATE canonical_catalog_snapshot SET storage_version = 2"
                    )
                elif damage == "singleton":
                    connection.execute(
                        "UPDATE canonical_catalog_snapshot SET singleton = 2"
                    )
                else:
                    connection.execute(
                        "UPDATE canonical_catalog_snapshot SET payload = 'text'"
                    )

    damaged = path.read_bytes()
    with pytest.raises(CanonicalCatalogStorageError):
        load_sqlite_canonical_catalog(path)
    assert path.read_bytes() == damaged


def test_failed_commit_rolls_back_previous_snapshot_and_success_is_atomic(tmp_path):
    path = tmp_path / "catalog.sqlite"
    empty = create_sqlite_canonical_catalog(path)
    family = _family("one", "family-1")

    with patch.object(
        storage_module,
        "_commit_transaction",
        side_effect=sqlite3.OperationalError("injected commit failure"),
    ):
        with pytest.raises(CanonicalCatalogStorageError):
            register_sqlite_canonical_family(path, family)
    assert load_sqlite_canonical_catalog(path) == empty

    result = register_sqlite_canonical_family(path, family)
    assert result.status is CatalogRegistrationStatus.INSERTED
    assert load_sqlite_canonical_catalog(path) == result.catalog
    assert _payload(path) == encode_canonical_catalog(result.catalog)


def test_competing_writer_fails_closed_without_stale_read_or_retry(tmp_path):
    path = tmp_path / "catalog.sqlite"
    empty = create_sqlite_canonical_catalog(path)
    family = _family("one", "family-1")

    competing = sqlite3.connect(path, timeout=0, isolation_level=None)
    competing.execute("BEGIN IMMEDIATE")
    try:
        with pytest.raises(CanonicalCatalogStorageError):
            register_sqlite_canonical_family(path, family)
    finally:
        competing.execute("ROLLBACK")
        competing.close()
    assert load_sqlite_canonical_catalog(path) == empty
