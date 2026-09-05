"""TASK-138 regressions for bounded local source-evidence intake."""

import ast
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone
import inspect
import os
from pathlib import Path

import pytest

import src.product_intelligence as product_intelligence
from src.product_intelligence import source_evidence_intake
from src.product_intelligence.entity_resolution_graph import resolve_multi_observations
from src.product_intelligence.source_evidence_intake import (
    SourceEvidenceIntakeError,
    SourceEvidenceInventory,
    intake_product_source_evidence,
)
from src.product_source.models import ProductFact, ProductSourcePack
from src.product_source.serialization import serialize_source_pack


def _pack(
    source_pack_id: str,
    *,
    source_product_id: str | None = None,
    observed_hour: int = 1,
) -> ProductSourcePack:
    return ProductSourcePack(
        source_pack_id=source_pack_id,
        platform="test-market",
        product_url=f"https://market.example/items/{source_pack_id}",
        observed_at=datetime(
            2026,
            9,
            1,
            observed_hour,
            tzinfo=timezone(timedelta(hours=7)),
        ),
        collector="task-138-test",
        title=f"Observed {source_pack_id}",
        source_product_id=source_product_id,
        brand="Example",
        facts=(ProductFact("color", "red", "specifications", "table"),),
    )


def _persist(root: Path, relative_dir: str, pack: ProductSourcePack) -> str:
    return serialize_source_pack(pack, str(root / relative_dir))


def test_public_surface_is_exact_and_inventory_is_frozen():
    expected = {
        "SourceEvidenceIntakeError",
        "SourceEvidenceInventory",
        "intake_product_source_evidence",
    }
    assert source_evidence_intake.__all__ == [
        "SourceEvidenceIntakeError",
        "SourceEvidenceInventory",
        "intake_product_source_evidence",
    ]
    assert {
        name for name in vars(source_evidence_intake) if not name.startswith("_")
    } == expected
    assert [field.name for field in fields(SourceEvidenceInventory)] == [
        "manifest_paths",
        "source_packs",
    ]
    assert product_intelligence.SourceEvidenceIntakeError is SourceEvidenceIntakeError
    assert product_intelligence.SourceEvidenceInventory is SourceEvidenceInventory
    assert (
        product_intelligence.intake_product_source_evidence
        is intake_product_source_evidence
    )
    assert all(product_intelligence.__all__.count(name) == 1 for name in expected)

    inventory = SourceEvidenceInventory((), ())
    with pytest.raises(FrozenInstanceError):
        inventory.manifest_paths = ("changed",)


def test_recursive_exact_name_discovery_is_canonical_aligned_and_deterministic(
    tmp_path,
):
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    path_z = _persist(left, "nested/z", _pack("z"))
    path_a = _persist(right, "a", _pack("a"))
    (left / "nested" / "not_source_pack.json").write_text("{}", encoding="utf-8")
    (right / "source_pack.JSON").write_text("{}", encoding="utf-8")

    forward = intake_product_source_evidence((str(left), str(right)))
    reverse = intake_product_source_evidence((str(right), str(left)))
    expected_paths = tuple(
        sorted(
            (os.path.realpath(path_z), os.path.realpath(path_a)),
            key=lambda path: (os.path.normcase(path), path),
        )
    )

    assert forward == reverse
    assert forward.manifest_paths == expected_paths
    assert all(os.path.isabs(path) for path in forward.manifest_paths)
    assert tuple(pack.source_pack_id for pack in forward.source_packs) == tuple(
        "z" if path == os.path.realpath(path_z) else "a"
        for path in expected_paths
    )
    assert all(type(pack) is ProductSourcePack for pack in forward.source_packs)


def test_overlapping_and_equivalent_roots_collapse_canonical_manifest(tmp_path):
    root = tmp_path / "root"
    nested = root / "nested"
    nested.mkdir(parents=True)
    path = _persist(root, "nested/evidence", _pack("one"))

    inventory = intake_product_source_evidence(
        (str(nested / ".."), str(root), str(root / "nested"))
    )

    assert inventory.manifest_paths == (os.path.realpath(path),)
    assert len(inventory.source_packs) == 1


def test_case_equivalent_root_spelling_is_independent_of_root_order(
    tmp_path, monkeypatch
):
    mixed_case_root = tmp_path / "CaseRoot"
    lower_case_root = tmp_path / "caseroot"
    _persist(mixed_case_root, "evidence", _pack("one"))
    if not lower_case_root.exists():
        _persist(lower_case_root, "evidence", _pack("one"))

    monkeypatch.setattr(
        source_evidence_intake._os.path,
        "normcase",
        lambda path: os.fspath(path).replace("\\", "/").casefold(),
    )

    forward = intake_product_source_evidence(
        (str(mixed_case_root), str(lower_case_root))
    )
    reverse = intake_product_source_evidence(
        (str(lower_case_root), str(mixed_case_root))
    )

    assert forward == reverse
    assert len(forward.manifest_paths) == 1


def test_empty_input_and_empty_roots_return_empty_inventory(tmp_path):
    assert intake_product_source_evidence(()) == SourceEvidenceInventory((), ())
    assert intake_product_source_evidence((str(tmp_path),)) == SourceEvidenceInventory(
        (), ()
    )


@pytest.mark.parametrize(
    "roots",
    [
        "single-root",
        b"single-root",
        None,
        7,
        [""],
        [Path("pathlike-is-not-an-exact-string")],
        [7],
    ],
)
def test_invalid_root_input_fails_closed(roots):
    with pytest.raises(SourceEvidenceIntakeError):
        intake_product_source_evidence(roots)


def test_missing_and_non_directory_roots_fail_closed(tmp_path):
    file_root = tmp_path / "file"
    file_root.write_text("not a directory", encoding="utf-8")
    for root in (tmp_path / "missing", file_root):
        with pytest.raises(SourceEvidenceIntakeError):
            intake_product_source_evidence((str(root),))


def test_roots_are_materialized_once(tmp_path):
    class _OneShotRoots:
        calls = 0

        def __iter__(self):
            self.calls += 1
            if self.calls > 1:
                raise AssertionError("roots were iterated more than once")
            yield str(tmp_path)

    roots = _OneShotRoots()
    assert intake_product_source_evidence(roots) == SourceEvidenceInventory((), ())
    assert roots.calls == 1


def test_manifest_symlink_fails_closed(tmp_path):
    outside = tmp_path / "outside"
    root = tmp_path / "root"
    root.mkdir()
    target = Path(_persist(outside, "pack", _pack("outside")))
    alias = root / "source_pack.json"
    try:
        alias.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"filesystem does not permit symlink creation: {exc}")

    with pytest.raises(SourceEvidenceIntakeError):
        intake_product_source_evidence((str(root),))


def test_configured_root_and_manifest_limits_fail_before_rehydration(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(source_evidence_intake, "_MAX_CONFIGURED_ROOTS", 1)
    with pytest.raises(SourceEvidenceIntakeError, match="configured root limit"):
        intake_product_source_evidence((str(tmp_path), str(tmp_path)))

    _persist(tmp_path, "a", _pack("a"))
    _persist(tmp_path, "b", _pack("b"))
    monkeypatch.setattr(source_evidence_intake, "_MAX_CONFIGURED_ROOTS", 32)
    monkeypatch.setattr(source_evidence_intake, "_MAX_DISCOVERED_MANIFESTS", 1)

    calls = []
    monkeypatch.setattr(
        source_evidence_intake,
        "_deserialize_product_source_pack",
        lambda path: calls.append(path),
    )
    with pytest.raises(SourceEvidenceIntakeError, match="manifest limit"):
        intake_product_source_evidence((str(tmp_path),))
    assert calls == []


def test_decoder_called_once_per_ordered_manifest_and_failure_propagates(
    tmp_path, monkeypatch
):
    _persist(tmp_path, "a", _pack("a"))
    _persist(tmp_path, "b", _pack("b"))
    original = source_evidence_intake._deserialize_product_source_pack
    calls = []

    def recording_decoder(path):
        calls.append(path)
        return original(path)

    monkeypatch.setattr(
        source_evidence_intake, "_deserialize_product_source_pack", recording_decoder
    )
    inventory = intake_product_source_evidence((str(tmp_path),))
    assert calls == list(inventory.manifest_paths)

    marker = RuntimeError("decoder-owned-failure")

    def failing_decoder(path):
        raise marker

    monkeypatch.setattr(
        source_evidence_intake, "_deserialize_product_source_pack", failing_decoder
    )
    with pytest.raises(RuntimeError) as caught:
        intake_product_source_evidence((str(tmp_path),))
    assert caught.value is marker


def test_duplicate_detection_uses_only_exact_observation_identity(tmp_path):
    duplicate_root = tmp_path / "duplicates"
    duplicate = _pack("same", source_product_id="listing")
    _persist(duplicate_root, "a", duplicate)
    _persist(duplicate_root, "b", duplicate)
    with pytest.raises(SourceEvidenceIntakeError, match="duplicate exact"):
        intake_product_source_evidence((str(duplicate_root),))

    distinct_root = tmp_path / "distinct"
    _persist(
        distinct_root,
        "a",
        _pack("shared-id", source_product_id="listing", observed_hour=1),
    )
    _persist(
        distinct_root,
        "b",
        _pack("shared-id", source_product_id="listing", observed_hour=2),
    )
    inventory = intake_product_source_evidence((str(distinct_root),))
    assert len(inventory.source_packs) == 2


def test_inventory_is_directly_consumable_by_m3_and_has_task_135_path_shape(
    tmp_path,
):
    _persist(tmp_path, "a", _pack("a", observed_hour=1))
    _persist(tmp_path, "b", _pack("b", observed_hour=2))
    inventory = intake_product_source_evidence((str(tmp_path),))

    graph = resolve_multi_observations(inventory.source_packs)
    assert graph.observations
    assert type(inventory.manifest_paths) is tuple
    assert all(type(path) is str and path for path in inventory.manifest_paths)


def test_intake_has_no_downstream_or_forbidden_side_effect_calls():
    source = inspect.getsource(source_evidence_intake)
    tree = ast.parse(source)
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    forbidden = {
        "open",
        "deserialize_source_pack",
        "resolve_multi_observations",
        "answer_persisted_grounded_question",
        "sqlite3",
        "system",
        "popen",
    }
    assert called.isdisjoint(forbidden)
