"""TASK-039 / M10.3 real operational dispatch proof verifier.

This module is deliberately proof-only.  It consumes exact runtime evidence,
recomputes the existing M10.1 recommendation, validates Human authorization and
its active ExecutorLease, and emits only the locked TASK-039 proof artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
from typing import Any

REPO_DIR = Path(__file__).resolve().parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from bridge import (
    current_branch,
    fetch_control,
    get_active_authorization,
    get_auth_path,
    get_lease_store,
    get_remote_blob_sha,
    get_runtime_capacity_store,
    get_runtime_paths,
    load_config,
    read_remote_file,
    reconstruct_expected_executor_lease,
)
from src.aios_bridge.continuity.dispatch import (
    CapacityState,
    DispatchActorKind,
    DispatchStatus,
    dispatch_executor,
)
from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.runtime_dispatch import (
    ObservationSource,
    RuntimeCapacityRecord,
    build_executor_dispatch_request_from_runtime,
    classify_capacity_freshness,
    parse_executor_dispatch_policy_marker,
)


TASK_NUM = 39
TASK_ID = "TASK-039"
EXPECTED_BRANCH = "ai/task-039"
BASELINE_SHA = "ff5d78abd71086ecb814255d4a589370e5660332"
EXHAUSTED_EXECUTOR = "antigravity"
SELECTED_EXECUTOR = "codex"
ACTION = "RUN"
TASK_PATH = ".ai/tasks/TASK-039.md"
EXTERNAL_RECEIPT_REL = "dispatch/proofs/TASK-039/recommendation.txt"
RECEIPT_COPY_PATH = "proofs/TASK-039-M10/recommendation-receipt.txt"
EXECUTOR_STAGE_PATH = "proofs/TASK-039-M10/executor-stage.txt"
OUTPUT_PATH = "proofs/TASK-039-M10/PROOF.json"
SCHEMA_VERSION = "1"
MAX_RECEIPT_BYTES = 65536

EXPECTED_EXECUTOR_STAGE_CONTENT = (
    "TASK_ID: TASK-039\n"
    "STAGE: HUMAN_AUTHORIZED_EXECUTION\n"
    "EXECUTOR_ID: codex\n"
    "RECOMMENDED_EXECUTOR_ID: codex\n"
    "ACTION: RUN\n"
    "PAYLOAD_VERSION: 1\n"
)
EXPECTED_EXECUTOR_STAGE_BYTES = EXPECTED_EXECUTOR_STAGE_CONTENT.encode("utf-8")

_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_SCALARS = (
    "TASK_ID",
    "ACTION",
    "AUTHORIZED_ARTIFACT_PATH",
    "AUTHORIZED_ARTIFACT_BLOB_SHA",
    "POLICY_FINGERPRINT",
    "CAPACITY_OBSERVATION_FINGERPRINTS",
    "DISPATCH_REQUEST_FINGERPRINT",
    "DISPATCH_RESULT_FINGERPRINT",
    "STATUS",
    "SELECTED_EXECUTOR",
    "HUMAN_APPROVAL_REQUIRED",
    "AUTHORIZATION_CHANGED",
    "LEASE_CHANGED",
)
_CANDIDATE_FIELDS = {
    "actor_id",
    "compatible",
    "effective_state",
    "freshness",
    "reasons",
    "record_fingerprint",
    "runnable",
    "stored_state",
}
_EXPECTED_CAPACITY_STATES = {
    EXHAUSTED_EXECUTOR: CapacityState.QUOTA_EXHAUSTED,
    SELECTED_EXECUTOR: CapacityState.AVAILABLE,
}
_EXPECTED_POLICY = {
    "allow_paid_api": False,
    "candidates": [
        {
            "capacity_class": "SUBSCRIPTION",
            "executor_id": EXHAUSTED_EXECUTOR,
            "preference_rank": 0,
            "supported_capabilities": [
                "FILESYSTEM_WRITE",
                "LOCAL_GIT",
                "REPOSITORY_READ",
                "SHELL",
                "TEST_EXECUTION",
            ],
            "supported_operations": ["FIX", ACTION],
        },
        {
            "capacity_class": "SUBSCRIPTION",
            "executor_id": SELECTED_EXECUTOR,
            "preference_rank": 1,
            "supported_capabilities": [
                "FILESYSTEM_WRITE",
                "LOCAL_GIT",
                "REPOSITORY_READ",
                "SHELL",
                "TEST_EXECUTION",
            ],
            "supported_operations": ["FIX", ACTION],
        },
    ],
    "operation": ACTION,
    "required_capabilities": [
        "FILESYSTEM_WRITE",
        "LOCAL_GIT",
        "REPOSITORY_READ",
        "SHELL",
        "TEST_EXECUTION",
    ],
}


def _fail(message: str) -> None:
    raise ContinuityStateValidationError(message)


def compute_canonical_semantic_proof_fingerprint(
    semantic_proof: dict[str, Any],
) -> tuple[str, str]:
    canonical = json.dumps(
        semantic_proof, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest(), canonical


def verify_proof_fingerprint_integrity(proof_data: dict[str, Any]) -> str:
    if not isinstance(proof_data, dict):
        _fail("Proof data must be a dictionary")
    declared = proof_data.get("proof_fingerprint")
    if not isinstance(declared, str) or not _SHA256_RE.fullmatch(declared):
        _fail("Missing or invalid top-level proof_fingerprint")
    semantic = {key: value for key, value in proof_data.items() if key != "proof_fingerprint"}
    recomputed, _ = compute_canonical_semantic_proof_fingerprint(semantic)
    if declared != recomputed:
        _fail(
            f"Proof fingerprint mismatch: declared '{declared}', recomputed '{recomputed}'"
        )
    return declared


def _canonical_relative_parts(relative_path: str) -> tuple[str, ...]:
    if (
        not isinstance(relative_path, str)
        or not relative_path
        or os.path.isabs(relative_path)
        or Path(relative_path).is_absolute()
        or relative_path.startswith(("/", "\\"))
        or ":" in relative_path
    ):
        _fail(f"Path must be repository/runtime-relative: {relative_path!r}")
    parts = tuple(relative_path.replace("\\", "/").split("/"))
    if any(part in {"", ".", ".."} for part in parts):
        _fail(f"Path must be canonical without traversal: {relative_path!r}")
    return parts


def _safe_exact_path(root: Path, relative_path: str, *, context: str) -> Path:
    parts = _canonical_relative_parts(relative_path)
    root = root.resolve()
    current = root
    for part in parts:
        current = current / part
        if current.exists() or current.is_symlink():
            mode = os.lstat(current).st_mode
            if stat.S_ISLNK(mode):
                _fail(f"{context} path component must not be a symlink: {part}")
    try:
        current.resolve().relative_to(root)
    except ValueError as exc:
        raise ContinuityStateValidationError(
            f"{context} path escapes its required root"
        ) from exc
    return current


def read_exact_external_receipt(runtime_root: Path) -> dict[str, Any]:
    runtime_root = Path(runtime_root).resolve()
    path = _safe_exact_path(runtime_root, EXTERNAL_RECEIPT_REL, context="Receipt")
    expected_dir = (runtime_root / "dispatch" / "proofs" / TASK_ID).resolve()
    try:
        path.resolve().relative_to(expected_dir)
    except ValueError as exc:
        raise ContinuityStateValidationError(
            "Receipt does not resolve inside the exact TASK-039 runtime proof directory"
        ) from exc
    if path.name != "recommendation.txt" or not path.exists():
        _fail(f"Exact external recommendation receipt is missing: {path}")
    st = os.lstat(path)
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        _fail("External recommendation receipt must be a non-symlink regular file")
    with path.open("rb") as handle:
        raw = handle.read(MAX_RECEIPT_BYTES + 1)
    if not raw or len(raw) > MAX_RECEIPT_BYTES:
        _fail("External recommendation receipt is empty or oversized")
    if b"\x00" in raw:
        _fail("External recommendation receipt contains forbidden NUL bytes")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ContinuityStateValidationError(
            "External recommendation receipt is not valid UTF-8"
        ) from exc
    return {
        "bytes": raw,
        "text": text,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "st_mtime_ns": st.st_mtime_ns,
        "path": path,
    }


def _parse_json_object(raw: str, context: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ContinuityStateValidationError(f"Malformed {context} JSON: {exc}") from exc
    if not isinstance(value, dict):
        _fail(f"{context} must be a JSON object")
    return value


def parse_recommendation_receipt(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or not text:
        _fail("Recommendation receipt must be non-empty text")
    scalar_values: dict[str, list[str]] = {key: [] for key in _REQUIRED_SCALARS}
    candidate_rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        for key in _REQUIRED_SCALARS:
            prefix = f"{key}:"
            if line.startswith(prefix):
                scalar_values[key].append(line[len(prefix) :].strip())
        if line.startswith("CANDIDATE_EVIDENCE:"):
            candidate_rows.append(
                _parse_json_object(
                    line[len("CANDIDATE_EVIDENCE:") :].strip(),
                    "CANDIDATE_EVIDENCE",
                )
            )

    scalars: dict[str, str] = {}
    for key, values in scalar_values.items():
        if len(values) != 1:
            _fail(f"Receipt must contain exactly one {key}; found {len(values)}")
        if not values[0]:
            _fail(f"Receipt scalar {key} must not be empty")
        scalars[key] = values[0]

    if not _SHA1_RE.fullmatch(scalars["AUTHORIZED_ARTIFACT_BLOB_SHA"]):
        _fail("AUTHORIZED_ARTIFACT_BLOB_SHA must be exact lowercase 40-hex")
    for key in (
        "POLICY_FINGERPRINT",
        "DISPATCH_REQUEST_FINGERPRINT",
        "DISPATCH_RESULT_FINGERPRINT",
    ):
        if not _SHA256_RE.fullmatch(scalars[key]):
            _fail(f"{key} must be exact lowercase 64-hex")

    fingerprints = _parse_json_object(
        scalars["CAPACITY_OBSERVATION_FINGERPRINTS"],
        "CAPACITY_OBSERVATION_FINGERPRINTS",
    )
    expected_actors = {EXHAUSTED_EXECUTOR, SELECTED_EXECUTOR}
    if set(fingerprints) != expected_actors or any(
        not isinstance(value, str) or not _SHA256_RE.fullmatch(value)
        for value in fingerprints.values()
    ):
        _fail("Capacity fingerprint mapping must contain exact TASK-039 actors and 64-hex values")

    expected_scalars = {
        "TASK_ID": TASK_ID,
        "ACTION": ACTION,
        "AUTHORIZED_ARTIFACT_PATH": TASK_PATH,
        "STATUS": DispatchStatus.SELECTED.value,
        "SELECTED_EXECUTOR": SELECTED_EXECUTOR,
        "HUMAN_APPROVAL_REQUIRED": "YES",
        "AUTHORIZATION_CHANGED": "NO",
        "LEASE_CHANGED": "NO",
    }
    for key, expected in expected_scalars.items():
        if scalars[key] != expected:
            _fail(f"Receipt {key} mismatch: expected {expected!r}, got {scalars[key]!r}")

    if len(candidate_rows) != 2:
        _fail(f"Receipt must contain exactly two CANDIDATE_EVIDENCE rows; found {len(candidate_rows)}")
    actor_order = [row.get("actor_id") for row in candidate_rows]
    if actor_order != sorted(expected_actors):
        _fail("Candidate evidence actor IDs must be unique and in deterministic actor-id order")
    candidates: dict[str, dict[str, Any]] = {}
    for row in candidate_rows:
        if set(row) != _CANDIDATE_FIELDS:
            _fail("CANDIDATE_EVIDENCE fields must be exact")
        actor = row["actor_id"]
        state = _EXPECTED_CAPACITY_STATES[actor].value
        if row["stored_state"] != state or row["effective_state"] != state:
            _fail(f"Candidate evidence state mismatch for {actor}")
        if row["freshness"] != "FRESH":
            _fail(f"Candidate evidence must be FRESH for {actor}")
        if row["record_fingerprint"] != fingerprints[actor]:
            _fail(f"Candidate evidence fingerprint mismatch for {actor}")
        expected_runnable = actor == SELECTED_EXECUTOR
        expected_reasons = ["ELIGIBLE"] if expected_runnable else ["CAPACITY_QUOTA_EXHAUSTED"]
        if (
            type(row["compatible"]) is not bool
            or row["compatible"] is not True
            or type(row["runnable"]) is not bool
            or row["runnable"] is not expected_runnable
            or row["reasons"] != expected_reasons
        ):
            _fail(f"Candidate evaluation semantics mismatch for {actor}")
        candidates[actor] = row

    return {
        "scalars": scalars,
        "capacity_fingerprints": fingerprints,
        "candidate_evidence": candidates,
    }


def load_exact_task_control(parsed_receipt: dict[str, Any]) -> tuple[str, str, Any]:
    cfg = load_config()
    fetch_control(cfg)
    before_blob = get_remote_blob_sha(cfg, TASK_PATH)
    if not before_blob:
        _fail(f"Authoritative TASK control artifact is missing: {TASK_PATH}")
    content = read_remote_file(cfg, TASK_PATH)
    if not isinstance(content, str) or not content:
        _fail("Authoritative TASK control artifact is empty")
    after_blob = get_remote_blob_sha(cfg, TASK_PATH)
    if after_blob != before_blob:
        _fail("Authoritative TASK control artifact drifted while being read")
    receipt_blob = parsed_receipt["scalars"]["AUTHORIZED_ARTIFACT_BLOB_SHA"]
    if before_blob != receipt_blob:
        _fail("Authoritative TASK blob does not match recommendation receipt")
    policy = parse_executor_dispatch_policy_marker(content)
    if policy.to_dict() != _EXPECTED_POLICY:
        _fail("TASK-039 dispatch policy semantics do not match the locked policy")
    if policy.fingerprint() != parsed_receipt["scalars"]["POLICY_FINGERPRINT"]:
        _fail("TASK-039 policy fingerprint does not match recommendation receipt")
    return before_blob, content, policy


def validate_capacity_record(
    record: RuntimeCapacityRecord | None,
    *,
    actor_id: str,
    expected_state: CapacityState,
    expected_fingerprint: str,
    now_epoch_seconds: int,
) -> RuntimeCapacityRecord:
    if record is None:
        _fail(f"Missing exact runtime capacity record for {actor_id}")
    if record.actor_kind is not DispatchActorKind.EXECUTOR or record.actor_id != actor_id:
        _fail(f"Runtime capacity record namespace mismatch for {actor_id}")
    if record.observation_source is not ObservationSource.HUMAN_DECLARED:
        _fail(f"Runtime capacity source must be HUMAN_DECLARED for {actor_id}")
    if classify_capacity_freshness(record, now_epoch_seconds) != "FRESH":
        _fail(f"Runtime capacity evidence is not FRESH for {actor_id}")
    if record.capacity_state is not expected_state:
        _fail(f"Runtime capacity state mismatch for {actor_id}")
    if record.record_fingerprint != expected_fingerprint:
        _fail(f"Runtime capacity fingerprint mismatch for {actor_id}")
    return record


def validate_causal_ordering(
    capacity_mtimes: dict[str, int], receipt_mtime_ns: int, authorization_mtime_ns: int
) -> None:
    if set(capacity_mtimes) != {EXHAUSTED_EXECUTOR, SELECTED_EXECUTOR}:
        _fail("Causal ordering requires exact TASK-039 capacity actors")
    for actor, mtime in capacity_mtimes.items():
        if type(mtime) is not int or mtime > receipt_mtime_ns:
            _fail(f"Capacity record mtime is after recommendation receipt for {actor}")
    if receipt_mtime_ns > authorization_mtime_ns:
        _fail("Recommendation receipt mtime is after RUN authorization")


def validate_authorization(auth: Any, exact_task_blob: str) -> dict[str, Any]:
    if not isinstance(auth, dict) or auth.get("status") != "ACTIVE":
        _fail("TASK-039 does not have an exact ACTIVE authorization")
    required = (
        "task_id",
        "action",
        "branch",
        "executor_id",
        "status",
        "artifact_path",
        "artifact_blob_sha",
        "lease_id",
        "lease_fingerprint",
        "workspace_id",
        "execution_fingerprint",
    )
    for field in required:
        if not isinstance(auth.get(field), str) or not auth[field].strip():
            _fail(f"Authorization missing or malformed required field: {field}")
    expected = {
        "task_id": TASK_ID,
        "action": ACTION,
        "branch": EXPECTED_BRANCH,
        "executor_id": SELECTED_EXECUTOR,
        "status": "ACTIVE",
        "artifact_path": TASK_PATH,
        "artifact_blob_sha": exact_task_blob,
    }
    for field, value in expected.items():
        if auth.get(field) != value:
            _fail(f"Authorization {field} mismatch: expected {value!r}, got {auth.get(field)!r}")
    if auth.get("base_main_sha") is not None and auth["base_main_sha"] != BASELINE_SHA:
        _fail("Authorization base_main_sha does not match TASK-039 baseline")
    forbidden_metadata = {
        "failover_source_lease",
        "failover_proof",
        "failover_proof_fingerprint",
        "hot_handoff",
    }
    present = forbidden_metadata.intersection(auth)
    if present:
        _fail(f"TASK-039 direct RUN forbids failover/hot-handoff metadata: {sorted(present)}")
    snapshot_fields = (
        "task_id",
        "action",
        "branch",
        "executor_id",
        "status",
        "artifact_path",
        "artifact_blob_sha",
        "lease_id",
        "lease_fingerprint",
        "workspace_id",
        "execution_fingerprint",
    )
    snapshot = {field: auth[field] for field in snapshot_fields}
    if auth.get("base_main_sha") is not None:
        snapshot["base_main_sha"] = auth["base_main_sha"]
    return snapshot


def validate_active_lease(auth: dict[str, Any]) -> Any:
    lease = reconstruct_expected_executor_lease(auth)
    get_lease_store().require_active(lease)
    if (
        lease.task_id != TASK_ID
        or lease.executor_id != SELECTED_EXECUTOR
        or lease.operation.value != ACTION
        or lease.lease_id != auth["lease_id"]
        or lease.workspace_id != auth["workspace_id"]
        or lease.execution_fingerprint != auth["execution_fingerprint"]
        or lease.fingerprint() != auth["lease_fingerprint"]
    ):
        _fail("Active ExecutorLease does not exactly match TASK-039 authorization")
    return lease


def read_executor_stage(repo_root: Path) -> dict[str, Any]:
    path = _safe_exact_path(repo_root, EXECUTOR_STAGE_PATH, context="Executor witness")
    if not path.exists():
        _fail("Required TASK-039 executor witness is missing")
    st = os.lstat(path)
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        _fail("Executor witness must be a non-symlink regular file")
    raw = path.read_bytes()
    if b"\x00" in raw:
        _fail("Executor witness contains forbidden NUL bytes")
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContinuityStateValidationError("Executor witness is not strict UTF-8") from exc
    if raw != EXPECTED_EXECUTOR_STAGE_BYTES:
        _fail("Executor witness bytes do not exactly match the TASK-039 contract")
    return {
        "path": EXECUTOR_STAGE_PATH,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
    }


def validate_recomputed_dispatch(
    request: Any,
    result: Any,
    evidence: Any,
    parsed_receipt: dict[str, Any],
) -> None:
    scalars = parsed_receipt["scalars"]
    if request.fingerprint() != scalars["DISPATCH_REQUEST_FINGERPRINT"]:
        _fail("Recomputed dispatch request fingerprint does not match receipt")
    if result.fingerprint() != scalars["DISPATCH_RESULT_FINGERPRINT"]:
        _fail("Recomputed dispatch result fingerprint does not match receipt")
    if (
        result.status is not DispatchStatus.SELECTED
        or result.selected_actor_id != SELECTED_EXECUTOR
        or result.actor_kind is not DispatchActorKind.EXECUTOR
    ):
        _fail("Recomputed dispatch result does not select exact Codex Executor")
    evaluations = {item.actor_id: item for item in result.evaluations}
    if set(evaluations) != {EXHAUSTED_EXECUTOR, SELECTED_EXECUTOR}:
        _fail("Recomputed dispatch evaluations do not contain exact TASK-039 actors")
    recomputed_rows: dict[str, dict[str, Any]] = {}
    for item in evidence:
        evaluation = evaluations.get(item.actor_id)
        if evaluation is None:
            _fail(f"Missing recomputed evaluation for {item.actor_id}")
        recomputed_rows[item.actor_id] = {
            **item.to_dict(),
            "compatible": evaluation.compatible,
            "reasons": [reason.value for reason in evaluation.reasons],
            "runnable": evaluation.runnable,
        }
    if recomputed_rows != parsed_receipt["candidate_evidence"]:
        _fail("Recomputed dispatch evidence does not exactly match recommendation receipt")


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        with temp.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        try:
            directory_fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            pass
    finally:
        if temp.exists():
            temp.unlink()


def _copy_receipt_fail_closed(repo_root: Path, raw: bytes) -> None:
    destination = _safe_exact_path(repo_root, RECEIPT_COPY_PATH, context="Receipt copy")
    if destination.exists():
        st = os.lstat(destination)
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
            _fail("Committed receipt copy must be a non-symlink regular file")
        if destination.read_bytes() != raw:
            _fail("Existing committed receipt copy differs from validated external receipt")
        return
    _atomic_write_bytes(destination, raw)


def _write_and_verify_proof(repo_root: Path, proof: dict[str, Any]) -> None:
    destination = _safe_exact_path(repo_root, OUTPUT_PATH, context="Proof output")
    payload = (
        json.dumps(proof, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    _atomic_write_bytes(destination, payload)
    written = json.loads(destination.read_text(encoding="utf-8"))
    if written != proof:
        _fail("PROOF.json atomic write read-back semantics differ")
    verify_proof_fingerprint_integrity(written)


def _git_head(repo_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, stderr=subprocess.PIPE
        ).decode("ascii").strip()
    except Exception as exc:
        raise ContinuityStateValidationError(f"Failed to resolve git HEAD: {exc}") from exc


def verify_real_dispatch_proof(repo_root: Path | None = None) -> dict[str, Any]:
    root = (repo_root or REPO_DIR).resolve()
    if Path.cwd().resolve() != root:
        _fail(f"Verifier must be executed from repository root: {root}")
    if current_branch() != EXPECTED_BRANCH:
        _fail(f"Current branch must be exactly {EXPECTED_BRANCH}")
    if _git_head(root) != BASELINE_SHA:
        _fail(f"Git HEAD must be exact TASK-039 baseline {BASELINE_SHA}")

    runtime_root = get_runtime_paths(root)["root"]
    receipt = read_exact_external_receipt(runtime_root)
    parsed_receipt = parse_recommendation_receipt(receipt["text"])
    exact_task_blob, _task_content, policy = load_exact_task_control(parsed_receipt)

    now_epoch_seconds = int(time.time())
    capacity_store = get_runtime_capacity_store()
    records: dict[str, RuntimeCapacityRecord] = {}
    capacity_mtimes: dict[str, int] = {}
    for actor_id in (EXHAUSTED_EXECUTOR, SELECTED_EXECUTOR):
        record = validate_capacity_record(
            capacity_store.load(DispatchActorKind.EXECUTOR, actor_id),
            actor_id=actor_id,
            expected_state=_EXPECTED_CAPACITY_STATES[actor_id],
            expected_fingerprint=parsed_receipt["capacity_fingerprints"][actor_id],
            now_epoch_seconds=now_epoch_seconds,
        )
        record_path = capacity_store.record_path(DispatchActorKind.EXECUTOR, actor_id)
        record_stat = os.lstat(record_path)
        if stat.S_ISLNK(record_stat.st_mode) or not stat.S_ISREG(record_stat.st_mode):
            _fail(f"Capacity record must be a non-symlink regular file for {actor_id}")
        records[actor_id] = record
        capacity_mtimes[actor_id] = record_stat.st_mtime_ns

    request, evidence = build_executor_dispatch_request_from_runtime(
        policy, capacity_store, now_epoch_seconds
    )
    result = dispatch_executor(request)
    validate_recomputed_dispatch(request, result, evidence, parsed_receipt)

    auth = get_active_authorization(TASK_NUM, ACTION)
    auth_snapshot = validate_authorization(auth, exact_task_blob)
    auth_path = get_auth_path(TASK_NUM)
    if not auth_path.exists():
        _fail("Exact TASK-039 authorization file is missing")
    auth_stat = os.lstat(auth_path)
    if stat.S_ISLNK(auth_stat.st_mode) or not stat.S_ISREG(auth_stat.st_mode):
        _fail("Authorization path must be a non-symlink regular file")
    validate_causal_ordering(
        capacity_mtimes, receipt["st_mtime_ns"], auth_stat.st_mtime_ns
    )

    lease = validate_active_lease(auth)
    executor_stage = read_executor_stage(root)

    semantic_proof: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "baseline_sha": BASELINE_SHA,
        "target_branch": EXPECTED_BRANCH,
        "control_artifact": {"path": TASK_PATH, "blob_sha": exact_task_blob},
        "recommendation": {
            "receipt_path": RECEIPT_COPY_PATH,
            "receipt_sha256": receipt["sha256"],
            "runtime_receipt_mtime_ns": receipt["st_mtime_ns"],
            "policy_fingerprint": policy.fingerprint(),
            "request_fingerprint": request.fingerprint(),
            "result_fingerprint": result.fingerprint(),
            "status": result.status.value,
            "selected_executor": result.selected_actor_id,
            "human_approval_required": True,
            "authorization_changed": False,
            "lease_changed": False,
        },
        "capacity": {
            actor: {
                "record": records[actor].to_dict(),
                "record_mtime_ns": capacity_mtimes[actor],
            }
            for actor in (EXHAUSTED_EXECUTOR, SELECTED_EXECUTOR)
        },
        "authorization": {
            "snapshot": auth_snapshot,
            "authorization_file_mtime_ns": auth_stat.st_mtime_ns,
        },
        "lease": {
            "snapshot": lease.to_dict(),
            "fingerprint": lease.fingerprint(),
        },
        "executor_stage": executor_stage,
        "causal_ordering": {
            "capacity_before_or_equal_receipt": True,
            "receipt_before_or_equal_authorization": True,
        },
    }
    proof_fingerprint, _ = compute_canonical_semantic_proof_fingerprint(semantic_proof)
    full_proof = {**semantic_proof, "proof_fingerprint": proof_fingerprint}

    _copy_receipt_fail_closed(root, receipt["bytes"])
    _write_and_verify_proof(root, full_proof)
    return {
        "status": "PASS",
        "task_id": TASK_ID,
        "selected_executor": SELECTED_EXECUTOR,
        "proof_fingerprint": proof_fingerprint,
        "output_path": str(root / OUTPUT_PATH),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="TASK-039 M10.3 real operational dispatch proof verifier"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("verify", help="Verify the real dispatch chain and emit proof")
    args = parser.parse_args()
    if args.command == "verify":
        try:
            result = verify_real_dispatch_proof(REPO_DIR)
            print("M10_3_REAL_OPERATIONAL_DISPATCH_PROOF: PASS")
            print(f"TASK_ID: {result['task_id']}")
            print(f"SELECTED_EXECUTOR: {result['selected_executor']}")
            print(f"PROOF_FINGERPRINT: {result['proof_fingerprint']}")
            return 0
        except Exception as exc:
            print(f"[ERROR] M10.3 proof verification failed: {exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
