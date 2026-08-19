from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import inspect
import json
from pathlib import Path
import sys
import threading

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import aios_bridge.runtime_paid_api_grant as runtime_paid_api_grant
from aios_bridge.continuity.dispatch import DispatchActorKind
from aios_bridge.continuity.errors import ContinuityStateValidationError
from aios_bridge.continuity.state import BrainOperation, MAX_SERIALIZED_BYTES
from aios_bridge.paid_api_grant import PaidApiGrant
from aios_bridge.runtime_paid_api_grant import AtomicPaidApiGrantStore


WORKSPACE_ID = "a" * 64
OTHER_WORKSPACE_ID = "b" * 64
TASK_ID = "TASK-051"
NOW = 1_000
OPERATIONS = tuple(BrainOperation)


def _grant(**overrides: object) -> PaidApiGrant:
    values: dict[str, object] = {
        "schema_version": "1",
        "grant_id": "human:grant-051",
        "task_id": TASK_ID,
        "actor_kind": DispatchActorKind.BRAIN,
        "brain_id": "review-brain",
        "provider_id": "provider-one",
        "model_id": "model-one",
        "brain_operation": OPERATIONS[0],
        "authorized_artifact_path": ".ai/proposals/TASK-051.md",
        "authorized_artifact_blob_sha": "c" * 40,
        "max_input_tokens": 4_096,
        "max_output_tokens": 1_024,
        "max_calls": 1,
        "expires_at_epoch_seconds": NOW + 100,
        "workspace_id": WORKSPACE_ID,
    }
    values.update(overrides)
    return PaidApiGrant(**values)


def _state_path(root: Path, grant: PaidApiGrant, state: str) -> Path:
    grant_key = hashlib.sha256(grant.grant_id.encode("utf-8")).hexdigest()
    return root.resolve() / grant.task_id / state / f"{grant_key}.json"


def _write_state(root: Path, namespace_grant: PaidApiGrant, state: str, payload: bytes) -> Path:
    path = _state_path(root, namespace_grant, state)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def test_activate_persists_exact_canonical_bytes_under_hashed_colon_grant_key(
    tmp_path: Path,
) -> None:
    grant = _grant()
    store = AtomicPaidApiGrantStore(tmp_path, WORKSPACE_ID)

    activated = store.activate(grant, now_epoch_seconds=NOW)

    expected_key = hashlib.sha256(grant.grant_id.encode("utf-8")).hexdigest()
    active_path = _state_path(tmp_path, grant, "active")
    assert active_path.name == f"{expected_key}.json"
    assert grant.grant_id not in active_path.name
    assert active_path.read_bytes() == grant.to_canonical_json().encode("utf-8")
    assert activated == grant
    assert store.load_active(grant.task_id, grant.grant_id) == grant
    assert store.load_consumed(grant.task_id, grant.grant_id) is None


@pytest.mark.parametrize(
    "workspace_id",
    ["a" * 63, "A" * 64, True, None],
)
def test_store_rejects_malformed_workspace(
    tmp_path: Path,
    workspace_id: object,
) -> None:
    with pytest.raises(ContinuityStateValidationError):
        AtomicPaidApiGrantStore(tmp_path, workspace_id)  # type: ignore[arg-type]


def test_activate_rejects_grant_for_another_workspace(tmp_path: Path) -> None:
    store = AtomicPaidApiGrantStore(tmp_path, WORKSPACE_ID)
    grant = _grant(workspace_id=OTHER_WORKSPACE_ID)

    with pytest.raises(ContinuityStateValidationError):
        store.activate(grant, now_epoch_seconds=NOW)


@pytest.mark.parametrize("now", [True, -1, 1.5, "1000", None])
def test_runtime_methods_reject_invalid_time(tmp_path: Path, now: object) -> None:
    store = AtomicPaidApiGrantStore(tmp_path, WORKSPACE_ID)
    grant = _grant()

    with pytest.raises(ContinuityStateValidationError):
        store.activate(grant, now_epoch_seconds=now)  # type: ignore[arg-type]
    assert store.load_active(grant.task_id, grant.grant_id) is None


def test_require_and_consume_reject_bool_time(tmp_path: Path) -> None:
    store = AtomicPaidApiGrantStore(tmp_path, WORKSPACE_ID)
    grant = _grant()
    store.activate(grant, now_epoch_seconds=NOW)

    with pytest.raises(ContinuityStateValidationError):
        store.require_active(grant, now_epoch_seconds=True)
    with pytest.raises(ContinuityStateValidationError):
        store.consume(grant, now_epoch_seconds=True)


@pytest.mark.parametrize("now", [NOW + 100, NOW + 101])
def test_activate_rejects_expiry_equality_and_already_expired(
    tmp_path: Path,
    now: int,
) -> None:
    grant = _grant(expires_at_epoch_seconds=NOW + 100)
    store = AtomicPaidApiGrantStore(tmp_path, WORKSPACE_ID)

    with pytest.raises(ContinuityStateValidationError):
        store.activate(grant, now_epoch_seconds=now)
    assert store.load_active(grant.task_id, grant.grant_id) is None


@pytest.mark.parametrize(
    "case",
    [
        "empty",
        "oversized",
        "invalid_utf8",
        "malformed_json",
        "wrong_workspace",
        "wrong_task",
        "wrong_grant",
        "forged_fingerprint",
    ],
)
def test_strict_load_rejects_invalid_active_state(tmp_path: Path, case: str) -> None:
    namespace_grant = _grant()
    store = AtomicPaidApiGrantStore(tmp_path, WORKSPACE_ID)

    if case == "empty":
        payload = b""
    elif case == "oversized":
        payload = b"x" * (MAX_SERIALIZED_BYTES + 1)
    elif case == "invalid_utf8":
        payload = b"\xff"
    elif case == "malformed_json":
        payload = b"{"
    elif case == "wrong_workspace":
        payload = _grant(workspace_id=OTHER_WORKSPACE_ID).to_canonical_json().encode("utf-8")
    elif case == "wrong_task":
        payload = _grant(task_id="TASK-999").to_canonical_json().encode("utf-8")
    elif case == "wrong_grant":
        payload = _grant(grant_id="other:grant").to_canonical_json().encode("utf-8")
    else:
        forged = namespace_grant.to_dict()
        forged["grant_fingerprint"] = "0" * 64
        payload = json.dumps(
            forged,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    _write_state(tmp_path, namespace_grant, "active", payload)
    with pytest.raises(ContinuityStateValidationError):
        store.load_active(namespace_grant.task_id, namespace_grant.grant_id)


def test_absent_requested_state_validates_corrupt_sibling(tmp_path: Path) -> None:
    grant = _grant()
    store = AtomicPaidApiGrantStore(tmp_path, WORKSPACE_ID)
    _write_state(tmp_path, grant, "consumed", b"")

    with pytest.raises(ContinuityStateValidationError):
        store.load_active(grant.task_id, grant.grant_id)


@pytest.mark.parametrize("state", ["active", "consumed"])
def test_strict_load_rejects_state_path_directory(tmp_path: Path, state: str) -> None:
    grant = _grant()
    store = AtomicPaidApiGrantStore(tmp_path, WORKSPACE_ID)
    _state_path(tmp_path, grant, state).mkdir(parents=True)

    loader = store.load_active if state == "active" else store.load_consumed
    with pytest.raises(ContinuityStateValidationError):
        loader(grant.task_id, grant.grant_id)


def test_active_and_consumed_dual_state_is_corruption(tmp_path: Path) -> None:
    grant = _grant()
    store = AtomicPaidApiGrantStore(tmp_path, WORKSPACE_ID)
    payload = grant.to_canonical_json().encode("utf-8")
    _write_state(tmp_path, grant, "active", payload)
    _write_state(tmp_path, grant, "consumed", payload)

    with pytest.raises(ContinuityStateValidationError):
        store.load_active(grant.task_id, grant.grant_id)
    with pytest.raises(ContinuityStateValidationError):
        store.load_consumed(grant.task_id, grant.grant_id)


def test_duplicate_activation_does_not_delete_preexisting_state(tmp_path: Path) -> None:
    grant = _grant()
    store = AtomicPaidApiGrantStore(tmp_path, WORKSPACE_ID)
    store.activate(grant, now_epoch_seconds=NOW)
    active_path = _state_path(tmp_path, grant, "active")
    before = active_path.read_bytes()

    with pytest.raises(ContinuityStateValidationError):
        store.activate(grant, now_epoch_seconds=NOW)

    assert active_path.read_bytes() == before


def test_activation_after_consumed_history_is_rejected(tmp_path: Path) -> None:
    grant = _grant()
    store = AtomicPaidApiGrantStore(tmp_path, WORKSPACE_ID)
    store.activate(grant, now_epoch_seconds=NOW)
    store.consume(grant, now_epoch_seconds=NOW)

    with pytest.raises(ContinuityStateValidationError):
        store.activate(grant, now_epoch_seconds=NOW)

    assert store.load_consumed(grant.task_id, grant.grant_id) == grant
    assert store.load_active(grant.task_id, grant.grant_id) is None


def test_require_active_requires_exact_semantics(tmp_path: Path) -> None:
    grant = _grant()
    store = AtomicPaidApiGrantStore(tmp_path, WORKSPACE_ID)
    store.activate(grant, now_epoch_seconds=NOW)
    assert store.require_active(grant, now_epoch_seconds=NOW) == grant

    mismatches: list[PaidApiGrant] = [
        _grant(provider_id="provider-two"),
        _grant(model_id="model-two"),
        _grant(authorized_artifact_path=".ai/proposals/OTHER.md"),
        _grant(authorized_artifact_blob_sha="d" * 40),
        _grant(max_input_tokens=4_095),
        _grant(max_output_tokens=1_023),
        _grant(expires_at_epoch_seconds=NOW + 101),
    ]
    if len(OPERATIONS) > 1:
        mismatches.append(_grant(brain_operation=OPERATIONS[1]))

    for mismatch in mismatches:
        with pytest.raises(ContinuityStateValidationError):
            store.require_active(mismatch, now_epoch_seconds=NOW)


def test_expired_active_fails_require_and_consume_without_state_change(tmp_path: Path) -> None:
    grant = _grant(expires_at_epoch_seconds=NOW + 1)
    store = AtomicPaidApiGrantStore(tmp_path, WORKSPACE_ID)
    store.activate(grant, now_epoch_seconds=NOW)

    with pytest.raises(ContinuityStateValidationError):
        store.require_active(grant, now_epoch_seconds=NOW + 1)
    with pytest.raises(ContinuityStateValidationError):
        store.consume(grant, now_epoch_seconds=NOW + 1)

    assert store.load_active(grant.task_id, grant.grant_id) == grant
    assert store.load_consumed(grant.task_id, grant.grant_id) is None


def test_consume_atomically_transitions_to_terminal_state_and_rejects_replay(
    tmp_path: Path,
) -> None:
    grant = _grant()
    store = AtomicPaidApiGrantStore(tmp_path, WORKSPACE_ID)
    store.activate(grant, now_epoch_seconds=NOW)

    consumed = store.consume(grant, now_epoch_seconds=NOW)

    assert consumed == grant
    assert store.load_consumed(grant.task_id, grant.grant_id) == grant
    assert store.load_active(grant.task_id, grant.grant_id) is None
    with pytest.raises(ContinuityStateValidationError):
        store.consume(grant, now_epoch_seconds=NOW)
    with pytest.raises(ContinuityStateValidationError):
        store.require_active(grant, now_epoch_seconds=NOW)


def test_concurrent_activation_has_exactly_one_winner(tmp_path: Path) -> None:
    grant = _grant()
    store = AtomicPaidApiGrantStore(tmp_path, WORKSPACE_ID)
    barrier = threading.Barrier(2)

    def attempt() -> PaidApiGrant | None:
        barrier.wait()
        try:
            return store.activate(grant, now_epoch_seconds=NOW)
        except ContinuityStateValidationError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))

    assert results.count(grant) == 1
    assert results.count(None) == 1
    assert store.load_active(grant.task_id, grant.grant_id) == grant


def test_concurrent_consume_has_exactly_one_winner(tmp_path: Path) -> None:
    grant = _grant()
    store = AtomicPaidApiGrantStore(tmp_path, WORKSPACE_ID)
    store.activate(grant, now_epoch_seconds=NOW)
    barrier = threading.Barrier(2)

    def attempt() -> PaidApiGrant | None:
        barrier.wait()
        try:
            return store.consume(grant, now_epoch_seconds=NOW)
        except ContinuityStateValidationError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))

    assert results.count(grant) == 1
    assert results.count(None) == 1
    assert store.load_active(grant.task_id, grant.grant_id) is None
    assert store.load_consumed(grant.task_id, grant.grant_id) == grant


def test_failed_fresh_activation_cleans_only_its_new_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    grant = _grant()
    store = AtomicPaidApiGrantStore(tmp_path, WORKSPACE_ID)

    def fail_fsync(_fd: int) -> None:
        raise OSError("injected fsync failure")

    monkeypatch.setattr(runtime_paid_api_grant.os, "fsync", fail_fsync)
    with pytest.raises(ContinuityStateValidationError):
        store.activate(grant, now_epoch_seconds=NOW)

    assert not _state_path(tmp_path, grant, "active").exists()
    assert not _state_path(tmp_path, grant, "consumed").exists()


def test_serialized_size_is_checked_before_state_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    grant = _grant()
    store = AtomicPaidApiGrantStore(tmp_path, WORKSPACE_ID)
    monkeypatch.setattr(
        PaidApiGrant,
        "to_canonical_json",
        lambda _self: "x" * (MAX_SERIALIZED_BYTES + 1),
    )

    with pytest.raises(ContinuityStateValidationError):
        store.activate(grant, now_epoch_seconds=NOW)
    assert not _state_path(tmp_path, grant, "active").exists()


def test_consumed_destination_collision_is_not_overwritten(tmp_path: Path) -> None:
    grant = _grant()
    store = AtomicPaidApiGrantStore(tmp_path, WORKSPACE_ID)
    store.activate(grant, now_epoch_seconds=NOW)
    colliding = _grant(provider_id="provider-collision")
    consumed_path = _write_state(
        tmp_path,
        grant,
        "consumed",
        colliding.to_canonical_json().encode("utf-8"),
    )
    before = consumed_path.read_bytes()

    with pytest.raises(ContinuityStateValidationError):
        store.consume(grant, now_epoch_seconds=NOW)

    assert consumed_path.read_bytes() == before
    assert _state_path(tmp_path, grant, "active").exists()


def test_post_move_verification_failure_never_recreates_active(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    grant = _grant()
    store = AtomicPaidApiGrantStore(tmp_path, WORKSPACE_ID)
    store.activate(grant, now_epoch_seconds=NOW)
    original_strict_read = store._strict_read_state

    def fail_consumed_read(
        path: Path,
        *,
        task_id: str,
        grant_id: str,
    ) -> PaidApiGrant:
        if path.parent.name == "consumed":
            raise ContinuityStateValidationError("injected post-move failure")
        return original_strict_read(path, task_id=task_id, grant_id=grant_id)

    monkeypatch.setattr(store, "_strict_read_state", fail_consumed_read)
    with pytest.raises(ContinuityStateValidationError, match="post-move"):
        store.consume(grant, now_epoch_seconds=NOW)

    assert not _state_path(tmp_path, grant, "active").exists()
    assert _state_path(tmp_path, grant, "consumed").read_bytes() == (
        grant.to_canonical_json().encode("utf-8")
    )


def test_store_has_no_forbidden_runtime_integrations() -> None:
    source = inspect.getsource(runtime_paid_api_grant)
    for forbidden in (
        "os.environ",
        "os.getenv",
        "subprocess",
        "socket",
        "ModelGateway",
        "ProviderAdapter",
        "runtime_dispatch",
    ):
        assert forbidden not in source


def test_store_uses_only_caller_supplied_external_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    external_root = tmp_path / "external runtime" / "grants"
    unrelated_cwd = tmp_path / "unrelated-cwd"
    unrelated_cwd.mkdir()
    monkeypatch.chdir(unrelated_cwd)
    grant = _grant()

    store = AtomicPaidApiGrantStore(external_root, WORKSPACE_ID)
    store.activate(grant, now_epoch_seconds=NOW)

    assert store.grant_root == external_root.resolve()
    assert _state_path(external_root, grant, "active").exists()
    assert list(unrelated_cwd.iterdir()) == []
