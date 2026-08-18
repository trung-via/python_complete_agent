from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.aios_m10_real_dispatch_proof as proof
from src.aios_bridge.continuity.dispatch import (
    CapacityState,
    DispatchActorKind,
    DispatchStatus,
)
from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.runtime_dispatch import ObservationSource, RuntimeCapacityRecord


FP_ANTIGRAVITY = "a" * 64
FP_CODEX = "b" * 64
POLICY_FP = "c" * 64
REQUEST_FP = "d" * 64
RESULT_FP = "e" * 64
TASK_BLOB = "f" * 40


def _candidate(actor: str) -> dict:
    runnable = actor == "codex"
    state = "AVAILABLE" if runnable else "QUOTA_EXHAUSTED"
    return {
        "actor_id": actor,
        "compatible": True,
        "effective_state": state,
        "freshness": "FRESH",
        "reasons": ["ELIGIBLE"] if runnable else ["CAPACITY_QUOTA_EXHAUSTED"],
        "record_fingerprint": FP_CODEX if runnable else FP_ANTIGRAVITY,
        "runnable": runnable,
        "stored_state": state,
    }


def valid_receipt(*, overrides: dict[str, str] | None = None, candidates=None) -> str:
    values = {
        "TASK_ID": "TASK-039",
        "ACTION": "RUN",
        "AUTHORIZED_ARTIFACT_PATH": ".ai/tasks/TASK-039.md",
        "AUTHORIZED_ARTIFACT_BLOB_SHA": TASK_BLOB,
        "POLICY_FINGERPRINT": POLICY_FP,
        "CAPACITY_OBSERVATION_FINGERPRINTS": json.dumps(
            {"antigravity": FP_ANTIGRAVITY, "codex": FP_CODEX},
            sort_keys=True,
            separators=(",", ":"),
        ),
        "DISPATCH_REQUEST_FINGERPRINT": REQUEST_FP,
        "DISPATCH_RESULT_FINGERPRINT": RESULT_FP,
        "STATUS": "SELECTED",
        "SELECTED_EXECUTOR": "codex",
        "HUMAN_APPROVAL_REQUIRED": "YES",
        "AUTHORIZATION_CHANGED": "NO",
        "LEASE_CHANGED": "NO",
    }
    values.update(overrides or {})
    rows = [_candidate("antigravity"), _candidate("codex")] if candidates is None else candidates
    lines = ["[DISPATCH RECOMMENDATION]"]
    lines.extend(f"{key}: {values[key]}" for key in proof._REQUIRED_SCALARS)
    lines.extend(
        "CANDIDATE_EVIDENCE: "
        + json.dumps(row, sort_keys=True, separators=(",", ":"))
        for row in rows
    )
    lines.append("Human must explicitly use the existing approval flow to accept any recommendation.")
    return "\n".join(lines) + "\n"


def _write_external_receipt(root: Path, payload: bytes | None = None) -> Path:
    path = root / "dispatch" / "proofs" / "TASK-039" / "recommendation.txt"
    path.parent.mkdir(parents=True)
    path.write_bytes(payload if payload is not None else valid_receipt().encode("utf-8"))
    return path


def _record(
    actor: str,
    state: CapacityState,
    *,
    observed: int = 100,
    ttl: int = 100,
    source: ObservationSource = ObservationSource.HUMAN_DECLARED,
) -> RuntimeCapacityRecord:
    return RuntimeCapacityRecord(
        actor_kind=DispatchActorKind.EXECUTOR,
        actor_id=actor,
        capacity_state=state,
        observed_at_epoch_seconds=observed,
        ttl_seconds=ttl,
        observation_source=source,
    )


def _valid_auth() -> dict[str, str]:
    return {
        "task_id": "TASK-039",
        "action": "RUN",
        "branch": "ai/task-039",
        "executor_id": "codex",
        "status": "ACTIVE",
        "artifact_path": ".ai/tasks/TASK-039.md",
        "artifact_blob_sha": TASK_BLOB,
        "lease_id": "lease-task-039-abcdef123456",
        "lease_fingerprint": "1" * 64,
        "workspace_id": "2" * 64,
        "execution_fingerprint": "3" * 64,
    }


def test_receipt_parser_accepts_exact_bridge_receipt():
    parsed = proof.parse_recommendation_receipt(valid_receipt())
    assert parsed["scalars"]["SELECTED_EXECUTOR"] == "codex"
    assert list(parsed["candidate_evidence"]) == ["antigravity", "codex"]


@pytest.mark.parametrize("key", proof._REQUIRED_SCALARS)
def test_receipt_parser_rejects_missing_required_scalar(key):
    text = "\n".join(
        line for line in valid_receipt().splitlines() if not line.startswith(f"{key}:")
    )
    with pytest.raises(ContinuityStateValidationError):
        proof.parse_recommendation_receipt(text)


@pytest.mark.parametrize("key", proof._REQUIRED_SCALARS)
def test_receipt_parser_rejects_duplicate_required_scalar(key):
    text = valid_receipt() + f"{key}: duplicate\n"
    with pytest.raises(ContinuityStateValidationError):
        proof.parse_recommendation_receipt(text)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("TASK_ID", "TASK-038"),
        ("ACTION", "FIX"),
        ("AUTHORIZED_ARTIFACT_PATH", ".ai/tasks/TASK-038.md"),
        ("AUTHORIZED_ARTIFACT_BLOB_SHA", "x" * 40),
        ("POLICY_FINGERPRINT", "C" * 64),
        ("DISPATCH_REQUEST_FINGERPRINT", "short"),
        ("DISPATCH_RESULT_FINGERPRINT", "f" * 63),
        ("STATUS", "WAIT"),
        ("SELECTED_EXECUTOR", "antigravity"),
        ("HUMAN_APPROVAL_REQUIRED", "NO"),
        ("AUTHORIZATION_CHANGED", "YES"),
        ("LEASE_CHANGED", "YES"),
    ],
)
def test_receipt_parser_rejects_wrong_scalar_semantics(key, value):
    with pytest.raises(ContinuityStateValidationError):
        proof.parse_recommendation_receipt(valid_receipt(overrides={key: value}))


@pytest.mark.parametrize(
    "mapping",
    [
        "[]",
        "not-json",
        json.dumps({"antigravity": FP_ANTIGRAVITY}),
        json.dumps({"antigravity": FP_ANTIGRAVITY, "codex": "bad"}),
        json.dumps(
            {"antigravity": FP_ANTIGRAVITY, "codex": FP_CODEX, "third": "3" * 64}
        ),
    ],
)
def test_receipt_parser_rejects_malformed_capacity_mapping(mapping):
    with pytest.raises(ContinuityStateValidationError):
        proof.parse_recommendation_receipt(
            valid_receipt(overrides={"CAPACITY_OBSERVATION_FINGERPRINTS": mapping})
        )


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [_candidate("antigravity")],
        [_candidate("antigravity"), _candidate("antigravity")],
        [_candidate("codex"), _candidate("antigravity")],
    ],
)
def test_receipt_parser_rejects_missing_duplicate_or_unsorted_candidates(rows):
    with pytest.raises(ContinuityStateValidationError):
        proof.parse_recommendation_receipt(valid_receipt(candidates=rows))


@pytest.mark.parametrize(
    "mutation",
    [
        lambda row: row.pop("reasons"),
        lambda row: row.update(extra=True),
        lambda row: row.update(freshness="EXPIRED"),
        lambda row: row.update(stored_state="AVAILABLE"),
        lambda row: row.update(record_fingerprint="9" * 64),
        lambda row: row.update(compatible=False),
        lambda row: row.update(runnable=True),
        lambda row: row.update(reasons=["ELIGIBLE"]),
    ],
)
def test_receipt_parser_rejects_wrong_candidate_evidence(mutation):
    first = _candidate("antigravity")
    mutation(first)
    with pytest.raises(ContinuityStateValidationError):
        proof.parse_recommendation_receipt(
            valid_receipt(candidates=[first, _candidate("codex")])
        )


def test_exact_receipt_reader_preserves_bom_and_bytes(tmp_path):
    raw = b"\xef\xbb\xbf" + valid_receipt().encode("utf-8")
    path = _write_external_receipt(tmp_path, raw)
    info = proof.read_exact_external_receipt(tmp_path)
    assert info["bytes"] == raw
    assert info["text"].startswith("[DISPATCH RECOMMENDATION]")
    assert info["path"] == path


def test_exact_receipt_reader_does_not_use_latest_or_fuzzy_fallback(tmp_path):
    other = tmp_path / "dispatch" / "proofs" / "TASK-039" / "latest.txt"
    other.parent.mkdir(parents=True)
    other.write_text(valid_receipt(), encoding="utf-8")
    with pytest.raises(ContinuityStateValidationError):
        proof.read_exact_external_receipt(tmp_path)


@pytest.mark.parametrize(
    "payload",
    [b"", b"nul\x00byte", b"x" * (proof.MAX_RECEIPT_BYTES + 1)],
    ids=["empty", "nul", "oversized"],
)
def test_exact_receipt_reader_rejects_empty_nul_or_oversized(tmp_path, payload):
    _write_external_receipt(tmp_path, payload)
    with pytest.raises(ContinuityStateValidationError):
        proof.read_exact_external_receipt(tmp_path)


def test_exact_receipt_reader_rejects_non_regular_leaf(tmp_path):
    path = tmp_path / "dispatch" / "proofs" / "TASK-039" / "recommendation.txt"
    path.mkdir(parents=True)
    with pytest.raises(ContinuityStateValidationError):
        proof.read_exact_external_receipt(tmp_path)


def test_exact_receipt_reader_rejects_traversal_even_if_constant_is_tampered(tmp_path, monkeypatch):
    monkeypatch.setattr(proof, "EXTERNAL_RECEIPT_REL", "../recommendation.txt")
    with pytest.raises(ContinuityStateValidationError):
        proof.read_exact_external_receipt(tmp_path)


def test_exact_receipt_reader_rejects_symlink_leaf(tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text(valid_receipt(), encoding="utf-8")
    path = tmp_path / "dispatch" / "proofs" / "TASK-039" / "recommendation.txt"
    path.parent.mkdir(parents=True)
    try:
        path.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    with pytest.raises(ContinuityStateValidationError):
        proof.read_exact_external_receipt(tmp_path)


def test_exact_receipt_reader_rejects_symlink_parent_and_outside_resolution(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    dispatch = tmp_path / "dispatch"
    try:
        dispatch.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    with pytest.raises(ContinuityStateValidationError):
        proof.read_exact_external_receipt(tmp_path)


def test_capacity_record_accepts_exact_fresh_human_observation():
    record = _record("codex", CapacityState.AVAILABLE)
    assert (
        proof.validate_capacity_record(
            record,
            actor_id="codex",
            expected_state=CapacityState.AVAILABLE,
            expected_fingerprint=record.record_fingerprint,
            now_epoch_seconds=150,
        )
        is record
    )


@pytest.mark.parametrize(
    ("record", "now", "expected_state", "expected_fp"),
    [
        (None, 150, CapacityState.AVAILABLE, FP_CODEX),
        (_record("codex", CapacityState.AVAILABLE, observed=100, ttl=10), 111, CapacityState.AVAILABLE, None),
        (_record("codex", CapacityState.AVAILABLE, observed=200), 199, CapacityState.AVAILABLE, None),
        (_record("codex", CapacityState.QUOTA_EXHAUSTED), 150, CapacityState.AVAILABLE, None),
        (
            _record(
                "codex",
                CapacityState.AVAILABLE,
                source=ObservationSource.ADAPTER_REPORTED,
            ),
            150,
            CapacityState.AVAILABLE,
            None,
        ),
    ],
)
def test_capacity_record_rejects_missing_expired_future_wrong_state_or_source(
    record, now, expected_state, expected_fp
):
    fingerprint = expected_fp or (record.record_fingerprint if record else FP_CODEX)
    with pytest.raises(ContinuityStateValidationError):
        proof.validate_capacity_record(
            record,
            actor_id="codex",
            expected_state=expected_state,
            expected_fingerprint=fingerprint,
            now_epoch_seconds=now,
        )


def test_capacity_record_rejects_receipt_fingerprint_mismatch():
    record = _record("codex", CapacityState.AVAILABLE)
    with pytest.raises(ContinuityStateValidationError):
        proof.validate_capacity_record(
            record,
            actor_id="codex",
            expected_state=CapacityState.AVAILABLE,
            expected_fingerprint="9" * 64,
            now_epoch_seconds=150,
        )


def test_causal_ordering_accepts_equality():
    proof.validate_causal_ordering({"antigravity": 10, "codex": 10}, 10, 10)


def test_causal_ordering_rejects_capacity_after_receipt():
    with pytest.raises(ContinuityStateValidationError):
        proof.validate_causal_ordering({"antigravity": 11, "codex": 9}, 10, 12)


def test_causal_ordering_rejects_receipt_after_authorization():
    with pytest.raises(ContinuityStateValidationError):
        proof.validate_causal_ordering({"antigravity": 8, "codex": 9}, 10, 9)


def test_authorization_accepts_exact_active_direct_run():
    snapshot = proof.validate_authorization(_valid_auth(), TASK_BLOB)
    assert snapshot["executor_id"] == "codex"
    assert "approved_at" not in snapshot


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "CONSUMED"),
        ("task_id", "TASK-038"),
        ("action", "FIX"),
        ("branch", "ai/task-038"),
        ("executor_id", "antigravity"),
        ("artifact_path", ".ai/tasks/TASK-038.md"),
        ("artifact_blob_sha", "0" * 40),
        ("lease_id", ""),
        ("lease_fingerprint", ""),
        ("workspace_id", ""),
        ("execution_fingerprint", ""),
    ],
)
def test_authorization_rejects_nonactive_or_wrong_binding(field, value):
    auth = _valid_auth()
    auth[field] = value
    with pytest.raises(ContinuityStateValidationError):
        proof.validate_authorization(auth, TASK_BLOB)


def test_authorization_rejects_missing_payload():
    with pytest.raises(ContinuityStateValidationError):
        proof.validate_authorization(None, TASK_BLOB)


@pytest.mark.parametrize(
    "field",
    ["failover_source_lease", "failover_proof", "failover_proof_fingerprint", "hot_handoff"],
)
def test_authorization_rejects_failover_or_hot_handoff_metadata(field):
    auth = _valid_auth()
    auth[field] = {}
    with pytest.raises(ContinuityStateValidationError):
        proof.validate_authorization(auth, TASK_BLOB)


def test_authorization_rejects_wrong_optional_base_main_sha():
    auth = _valid_auth()
    auth["base_main_sha"] = "0" * 40
    with pytest.raises(ContinuityStateValidationError):
        proof.validate_authorization(auth, TASK_BLOB)


class _FakeLease:
    def __init__(self, auth, *, executor_id="codex"):
        self.task_id = auth["task_id"]
        self.executor_id = executor_id
        self.operation = SimpleNamespace(value=auth["action"])
        self.lease_id = auth["lease_id"]
        self.workspace_id = auth["workspace_id"]
        self.execution_fingerprint = auth["execution_fingerprint"]
        self._fingerprint = auth["lease_fingerprint"]

    def fingerprint(self):
        return self._fingerprint

    def to_dict(self):
        return {"lease_id": self.lease_id}


def test_active_lease_requires_existing_store_binding(monkeypatch):
    auth = _valid_auth()
    lease = _FakeLease(auth)
    monkeypatch.setattr(proof, "reconstruct_expected_executor_lease", lambda value: lease)

    def reject(_lease):
        raise ContinuityStateValidationError("not active")

    monkeypatch.setattr(proof, "get_lease_store", lambda: SimpleNamespace(require_active=reject))
    with pytest.raises(ContinuityStateValidationError):
        proof.validate_active_lease(auth)


def test_active_lease_rejects_semantic_mismatch(monkeypatch):
    auth = _valid_auth()
    lease = _FakeLease(auth, executor_id="antigravity")
    monkeypatch.setattr(proof, "reconstruct_expected_executor_lease", lambda value: lease)
    monkeypatch.setattr(
        proof, "get_lease_store", lambda: SimpleNamespace(require_active=lambda value: None)
    )
    with pytest.raises(ContinuityStateValidationError):
        proof.validate_active_lease(auth)


def test_active_lease_accepts_exact_authorization_bound_lease(monkeypatch):
    auth = _valid_auth()
    lease = _FakeLease(auth)
    monkeypatch.setattr(proof, "reconstruct_expected_executor_lease", lambda value: lease)
    monkeypatch.setattr(
        proof, "get_lease_store", lambda: SimpleNamespace(require_active=lambda value: None)
    )
    assert proof.validate_active_lease(auth) is lease


def _write_witness(root: Path, payload=proof.EXPECTED_EXECUTOR_STAGE_BYTES) -> Path:
    path = root / proof.EXECUTOR_STAGE_PATH
    path.parent.mkdir(parents=True)
    path.write_bytes(payload)
    return path


def test_executor_witness_accepts_exact_bytes(tmp_path):
    _write_witness(tmp_path)
    info = proof.read_executor_stage(tmp_path)
    assert info["size_bytes"] == len(proof.EXPECTED_EXECUTOR_STAGE_BYTES)


@pytest.mark.parametrize(
    "payload",
    [
        proof.EXPECTED_EXECUTOR_STAGE_BYTES[:-1],
        proof.EXPECTED_EXECUTOR_STAGE_BYTES + b"\n",
        proof.EXPECTED_EXECUTOR_STAGE_BYTES.replace(b"codex", b"other", 1),
        b"\xff",
    ],
)
def test_executor_witness_rejects_missing_newline_extra_newline_tamper_or_non_utf8(
    tmp_path, payload
):
    _write_witness(tmp_path, payload)
    with pytest.raises(ContinuityStateValidationError):
        proof.read_executor_stage(tmp_path)


def test_executor_witness_rejects_missing_exact_path_even_if_nearby_exists(tmp_path):
    nearby = tmp_path / "proofs" / "TASK-039-M10" / "executor-stage-latest.txt"
    nearby.parent.mkdir(parents=True)
    nearby.write_bytes(proof.EXPECTED_EXECUTOR_STAGE_BYTES)
    with pytest.raises(ContinuityStateValidationError):
        proof.read_executor_stage(tmp_path)


def test_executor_witness_rejects_path_traversal(monkeypatch, tmp_path):
    monkeypatch.setattr(proof, "EXECUTOR_STAGE_PATH", "../executor-stage.txt")
    with pytest.raises(ContinuityStateValidationError):
        proof.read_executor_stage(tmp_path)


def test_executor_witness_rejects_symlink(tmp_path):
    outside = tmp_path / "outside-stage.txt"
    outside.write_bytes(proof.EXPECTED_EXECUTOR_STAGE_BYTES)
    path = tmp_path / proof.EXECUTOR_STAGE_PATH
    path.parent.mkdir(parents=True)
    try:
        path.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    with pytest.raises(ContinuityStateValidationError):
        proof.read_executor_stage(tmp_path)


def _fake_dispatch(parsed, *, request_fp=REQUEST_FP, result_fp=RESULT_FP):
    reason_exhausted = SimpleNamespace(value="CAPACITY_QUOTA_EXHAUSTED")
    reason_eligible = SimpleNamespace(value="ELIGIBLE")
    evaluations = (
        SimpleNamespace(
            actor_id="antigravity",
            compatible=True,
            runnable=False,
            reasons=(reason_exhausted,),
        ),
        SimpleNamespace(
            actor_id="codex", compatible=True, runnable=True, reasons=(reason_eligible,)
        ),
    )
    evidence = tuple(
        SimpleNamespace(actor_id=actor, to_dict=lambda row=row: {
            key: value
            for key, value in row.items()
            if key not in {"compatible", "reasons", "runnable"}
        })
        for actor, row in parsed["candidate_evidence"].items()
    )
    request = SimpleNamespace(fingerprint=lambda: request_fp)
    result = SimpleNamespace(
        fingerprint=lambda: result_fp,
        status=DispatchStatus.SELECTED,
        selected_actor_id="codex",
        actor_kind=DispatchActorKind.EXECUTOR,
        evaluations=evaluations,
    )
    return request, result, evidence


def test_recomputed_dispatch_accepts_exact_request_result_and_evidence():
    parsed = proof.parse_recommendation_receipt(valid_receipt())
    proof.validate_recomputed_dispatch(*_fake_dispatch(parsed), parsed)


@pytest.mark.parametrize(("request_fp", "result_fp"), [("0" * 64, RESULT_FP), (REQUEST_FP, "0" * 64)])
def test_recomputed_dispatch_rejects_request_or_result_fingerprint_mismatch(
    request_fp, result_fp
):
    parsed = proof.parse_recommendation_receipt(valid_receipt())
    with pytest.raises(ContinuityStateValidationError):
        proof.validate_recomputed_dispatch(
            *_fake_dispatch(parsed, request_fp=request_fp, result_fp=result_fp), parsed
        )


def test_proof_fingerprint_is_deterministic_and_verifies():
    semantic = {"z": [2, 1], "a": {"value": True}}
    first, canonical = proof.compute_canonical_semantic_proof_fingerprint(semantic)
    second, canonical_again = proof.compute_canonical_semantic_proof_fingerprint(
        {"a": {"value": True}, "z": [2, 1]}
    )
    assert first == second
    assert canonical == canonical_again
    assert proof.verify_proof_fingerprint_integrity(
        {**semantic, "proof_fingerprint": first}
    ) == first


def test_proof_fingerprint_rejects_semantic_tamper_retaining_old_fingerprint():
    semantic = {"task_id": "TASK-039", "selected_executor": "codex"}
    fingerprint, _ = proof.compute_canonical_semantic_proof_fingerprint(semantic)
    tampered = {**semantic, "selected_executor": "antigravity", "proof_fingerprint": fingerprint}
    with pytest.raises(ContinuityStateValidationError):
        proof.verify_proof_fingerprint_integrity(tampered)


def test_receipt_copy_is_byte_exact_and_rejects_drift(tmp_path):
    raw = b"\xef\xbb\xbfexact\r\nbytes\r\n"
    proof._copy_receipt_fail_closed(tmp_path, raw)
    destination = tmp_path / proof.RECEIPT_COPY_PATH
    assert destination.read_bytes() == raw
    proof._copy_receipt_fail_closed(tmp_path, raw)
    with pytest.raises(ContinuityStateValidationError):
        proof._copy_receipt_fail_closed(tmp_path, b"different")


def test_exact_task_control_requires_blob_stability_policy_and_receipt_binding(monkeypatch):
    marker = "DISPATCH_EXECUTOR_POLICY_JSON: " + json.dumps(
        proof._EXPECTED_POLICY, sort_keys=True, separators=(",", ":")
    )
    policy = proof.parse_executor_dispatch_policy_marker(marker)
    parsed = proof.parse_recommendation_receipt(
        valid_receipt(
            overrides={
                "AUTHORIZED_ARTIFACT_BLOB_SHA": TASK_BLOB,
                "POLICY_FINGERPRINT": policy.fingerprint(),
            }
        )
    )
    blobs = iter([TASK_BLOB, TASK_BLOB])
    monkeypatch.setattr(proof, "load_config", lambda: {})
    monkeypatch.setattr(proof, "fetch_control", lambda cfg: None)
    monkeypatch.setattr(proof, "get_remote_blob_sha", lambda cfg, path: next(blobs))
    monkeypatch.setattr(proof, "read_remote_file", lambda cfg, path: marker)
    blob, content, loaded_policy = proof.load_exact_task_control(parsed)
    assert blob == TASK_BLOB
    assert content == marker
    assert loaded_policy.fingerprint() == policy.fingerprint()


def test_exact_task_control_rejects_blob_drift(monkeypatch):
    parsed = proof.parse_recommendation_receipt(valid_receipt())
    blobs = iter([TASK_BLOB, "0" * 40])
    monkeypatch.setattr(proof, "load_config", lambda: {})
    monkeypatch.setattr(proof, "fetch_control", lambda cfg: None)
    monkeypatch.setattr(proof, "get_remote_blob_sha", lambda cfg, path: next(blobs))
    monkeypatch.setattr(proof, "read_remote_file", lambda cfg, path: "content")
    with pytest.raises(ContinuityStateValidationError):
        proof.load_exact_task_control(parsed)


def test_real_verifier_calls_existing_dispatcher_exactly_once_by_construction():
    tree = ast.parse(inspect.getsource(proof.verify_real_dispatch_proof))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "dispatch_executor"
    ]
    assert len(calls) == 1


def test_verifier_has_no_authority_capacity_lease_or_executor_mutation_calls():
    tree = ast.parse(inspect.getsource(proof))
    forbidden_names = {
        "approve",
        "handoff",
        "save_authorization",
        "save_authorization_record",
        "acquire",
        "release",
        "cmd_recommend",
        "cmd_capacity_set",
        "invoke_executor",
        "invoke_brain",
        "publish",
        "commit",
        "push",
    }
    called = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            called.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            called.add(node.func.attr)
    assert called.isdisjoint(forbidden_names)
