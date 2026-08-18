"""Focused unit and adversarial tests for M9.3 Real Hot Local Handoff Proof (TASK-036 / ADR-025).

Addresses Finding R1-1 and Finding R1-2 from REVIEW-036:
- Complete adversarial coverage of authority/provenance fail-closed trust boundaries.
- Path-safety and parent-component symlink / path escape validation.
- Proof preservation invariants and tamper detection.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import pytest
import subprocess
from typing import Any

from scripts.aios_m9_real_hot_handoff_proof import (
    BASELINE_SHA,
    EXPECTED_BRANCH,
    EXPECTED_SOURCE_CONTENT,
    OUTPUT_PATH,
    REPLACEMENT_EXECUTOR,
    REPLACEMENT_PATH,
    SCHEMA_VERSION,
    SOURCE_EXECUTOR,
    SOURCE_PATH,
    TASK_ID,
    compute_canonical_semantic_proof_fingerprint,
    safe_read_workspace_payload,
    validate_safe_repository_path,
    verify_proof_fingerprint_integrity,
    verify_real_hot_handoff_proof,
)
from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.hot_handoff import (
    HotHandoffCheckpoint,
    capture_hot_handoff_checkpoint,
)


def _recompute_checkpoint(ckpt_dict: dict[str, Any]) -> HotHandoffCheckpoint:
    """Helper to recalculate checkpoint fingerprint and return a valid HotHandoffCheckpoint."""
    semantic = {k: v for k, v in ckpt_dict.items() if k != "checkpoint_fingerprint"}
    canon = json.dumps(semantic, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    fp = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    ckpt_dict["checkpoint_fingerprint"] = fp
    return HotHandoffCheckpoint.from_dict(ckpt_dict)


@pytest.fixture
def fake_proof_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Creates a mock valid workspace and monkeypatches Bridge seams for test isolation."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Initialize a dummy git repo so capture_hot_handoff_checkpoint works
    subprocess.run(["git", "init", "-b", EXPECTED_BRANCH], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "AIOS Test"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.email", "test@aios.local"], cwd=repo_root, check=True)

    dummy_tracked = repo_root / "README.md"
    dummy_tracked.write_bytes(b"# Baseline\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-m", "Baseline commit"], cwd=repo_root, check=True, capture_output=True)

    proofs_dir = repo_root / "proofs" / "TASK-036-M9"
    proofs_dir.mkdir(parents=True)

    source_file = repo_root / SOURCE_PATH
    source_file.write_bytes(EXPECTED_SOURCE_CONTENT.encode("utf-8"))

    workspace_id = hashlib.sha256(b"test-workspace-id").hexdigest()
    storage = tmp_path / "checkpoints"
    storage.mkdir()

    raw_checkpoint = capture_hot_handoff_checkpoint(
        repo_root,
        storage,
        task_id=TASK_ID,
        target_branch=EXPECTED_BRANCH,
        workspace_id=workspace_id,
        source_executor_id=SOURCE_EXECUTOR,
        source_lease_fingerprint="a" * 64,
        source_execution_fingerprint="b" * 64,
        allowed_paths=(SOURCE_PATH,),
    )

    # Rebind head_sha to exact BASELINE_SHA
    ckpt_dict = raw_checkpoint.to_dict()
    ckpt_dict["head_sha"] = BASELINE_SHA
    checkpoint = _recompute_checkpoint(ckpt_dict)
    checkpoint_fp = checkpoint.checkpoint_fingerprint

    replacement_content = (
        "TASK_ID: TASK-036\n"
        "STAGE: REPLACEMENT_POST_ACTIVATION\n"
        "EXECUTOR_ID: antigravity\n"
        f"CHECKPOINT_FINGERPRINT: {checkpoint_fp}\n"
        "PAYLOAD_VERSION: 1\n"
    )
    replacement_file = repo_root / REPLACEMENT_PATH
    replacement_file.write_bytes(replacement_content.encode("utf-8"))

    auth = {
        "task_id": TASK_ID,
        "action": "RUN",
        "kind": "TASK",
        "artifact_path": ".ai/tasks/TASK-036.md",
        "artifact_blob_sha": "c" * 40,
        "branch": EXPECTED_BRANCH,
        "status": "ACTIVE",
        "executor_id": REPLACEMENT_EXECUTOR,
        "lease_id": "lease-task-036-repl",
        "lease_fingerprint": "d" * 64,
        "workspace_id": workspace_id,
        "execution_fingerprint": "e" * 64,
        "hot_handoff": {
            "checkpoint_fingerprint": checkpoint_fp,
            "allowed_paths": [SOURCE_PATH],
            "source_executor_id": SOURCE_EXECUTOR,
            "source_lease_id": "lease-task-036-src",
            "source_lease_fingerprint": "a" * 64,
            "source_execution_fingerprint": "b" * 64,
            "replacement_executor_id": REPLACEMENT_EXECUTOR,
            "replacement_lease_id": "lease-task-036-repl",
            "replacement_lease_fingerprint": "d" * 64,
            "replacement_execution_fingerprint": "e" * 64,
        },
    }

    class FakeLeaseStore:
        def require_active(self, lease):
            pass

    monkeypatch.chdir(repo_root)
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.current_branch", lambda *a, **k: EXPECTED_BRANCH)
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.subprocess.check_output", lambda cmd, **kw: BASELINE_SHA.encode() + b"\n")
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.get_active_authorization", lambda tid: copy.deepcopy(auth))
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.reconstruct_expected_executor_lease", lambda a: "mock-lease")
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.get_lease_store", lambda: FakeLeaseStore())
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.validate_active_hot_handoff_provenance", lambda tid, a, l: a.get("hot_handoff"))
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.load_persisted_hot_handoff_checkpoint", lambda tid, fp: checkpoint)
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.get_workspace_id", lambda root: workspace_id)

    return {
        "repo_root": repo_root,
        "checkpoint": checkpoint,
        "checkpoint_fp": checkpoint_fp,
        "auth": auth,
        "workspace_id": workspace_id,
        "source_file": source_file,
        "replacement_file": replacement_file,
    }


# ==============================================================================
# Finding R1-2: Path Safety and Symlink Escape Tests
# ==============================================================================

def test_safe_read_workspace_payload_valid(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_bytes(b"Hello UTF-8\n")
    res = safe_read_workspace_payload(tmp_path, "test.txt")
    assert res["text"] == "Hello UTF-8\n"
    assert res["size_bytes"] == 12
    assert res["sha256"] == hashlib.sha256(b"Hello UTF-8\n").hexdigest()


def test_safe_read_workspace_payload_rejects_absolute_or_traversal_paths(tmp_path: Path):
    with pytest.raises(ContinuityStateValidationError, match="repository-relative"):
        safe_read_workspace_payload(tmp_path, "/abs/path/file.txt")
    with pytest.raises(ContinuityStateValidationError, match="traversal components"):
        safe_read_workspace_payload(tmp_path, "../outside.txt")
    with pytest.raises(ContinuityStateValidationError, match="traversal components"):
        safe_read_workspace_payload(tmp_path, "foo/../../bar.txt")


def test_safe_read_workspace_payload_rejects_symlink_leaf(tmp_path: Path):
    target = tmp_path / "target.txt"
    target.write_bytes(b"real\n")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported on this platform/privilege level")
    with pytest.raises(ContinuityStateValidationError, match="must not be a symlink"):
        safe_read_workspace_payload(tmp_path, "link.txt")


def test_safe_read_workspace_payload_rejects_symlink_parent_directory(tmp_path: Path):
    real_dir = tmp_path / "real_dir"
    real_dir.mkdir()
    target_file = real_dir / "leaf.txt"
    target_file.write_bytes(b"content\n")

    link_dir = tmp_path / "link_dir"
    try:
        link_dir.symlink_to(real_dir, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported on this platform/privilege level")

    with pytest.raises(ContinuityStateValidationError, match="Path component must not be a symlink"):
        safe_read_workspace_payload(tmp_path, "link_dir/leaf.txt")


def test_validate_safe_repository_path_rejects_mocked_parent_symlink(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Deterministic, platform-independent unit test for parent-component symlink rejection."""
    nested_file = tmp_path / "a" / "b" / "c.txt"
    nested_file.parent.mkdir(parents=True)
    nested_file.write_bytes(b"test\n")

    original_lstat = os.lstat

    def fake_lstat(path, *args, **kwargs):
        p_str = str(path).replace("\\", "/")
        if p_str.endswith("/a/b"):
            # Mock directory 'b' as a symlink
            return os.stat_result((stat.S_IFLNK | 0o777, 0, 0, 0, 0, 0, 0, 0, 0, 0))
        return original_lstat(path, *args, **kwargs)

    monkeypatch.setattr(os, "lstat", fake_lstat)
    with pytest.raises(ContinuityStateValidationError, match="Path component must not be a symlink: 'b'"):
        validate_safe_repository_path(tmp_path, "a/b/c.txt")


def test_safe_read_workspace_payload_rejects_binary_or_nul(tmp_path: Path):
    p = tmp_path / "nul.txt"
    p.write_bytes(b"bad\x00data")
    with pytest.raises(ContinuityStateValidationError, match="forbidden NUL bytes"):
        safe_read_workspace_payload(tmp_path, "nul.txt")


def test_safe_read_workspace_payload_rejects_non_utf8(tmp_path: Path):
    p = tmp_path / "latin.txt"
    p.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(ContinuityStateValidationError, match="forbidden NUL bytes|not valid UTF-8"):
        safe_read_workspace_payload(tmp_path, "latin.txt")


# ==============================================================================
# Finding R1-1: End-to-End Success & Proof Determinism
# ==============================================================================

def test_canonical_semantic_proof_fingerprint_determinism():
    data1 = {"schema_version": "1", "task_id": "TASK-036", "source": {"executor_id": "codex"}}
    data2 = {"task_id": "TASK-036", "source": {"executor_id": "codex"}, "schema_version": "1"}
    fp1, json1 = compute_canonical_semantic_proof_fingerprint(data1)
    fp2, json2 = compute_canonical_semantic_proof_fingerprint(data2)
    assert fp1 == fp2
    assert json1 == json2


def test_verify_proof_fingerprint_integrity_success_and_tamper():
    semantic = {
        "schema_version": "1",
        "task_id": "TASK-036",
        "source": {"executor_id": "codex"},
    }
    fp, _ = compute_canonical_semantic_proof_fingerprint(semantic)
    valid_proof = {**semantic, "proof_fingerprint": fp}

    assert verify_proof_fingerprint_integrity(valid_proof) == fp

    # Tamper with semantic field
    tampered_semantic = copy.deepcopy(valid_proof)
    tampered_semantic["task_id"] = "TASK-099"
    with pytest.raises(ContinuityStateValidationError, match="Proof fingerprint mismatch"):
        verify_proof_fingerprint_integrity(tampered_semantic)

    # Tamper with fingerprint string
    tampered_fp = copy.deepcopy(valid_proof)
    tampered_fp["proof_fingerprint"] = "0" * 64
    with pytest.raises(ContinuityStateValidationError, match="Proof fingerprint mismatch"):
        verify_proof_fingerprint_integrity(tampered_fp)

    # Missing fingerprint
    with pytest.raises(ContinuityStateValidationError, match="Missing or invalid"):
        verify_proof_fingerprint_integrity(semantic)


def test_verify_real_hot_handoff_proof_e2e_success(fake_proof_workspace):
    ws = fake_proof_workspace
    res = verify_real_hot_handoff_proof(ws["repo_root"])
    assert res["status"] == "PASS"
    assert res["task_id"] == "TASK-036"
    assert res["source_executor"] == "codex"
    assert res["replacement_executor"] == "antigravity"
    assert res["checkpoint_fingerprint"] == ws["checkpoint_fp"]

    out_file = ws["repo_root"] / OUTPUT_PATH
    assert out_file.exists()
    proof = json.loads(out_file.read_text(encoding="utf-8"))
    assert proof["proof_fingerprint"] == res["proof_fingerprint"]
    assert proof["checkpoint"]["source_executor_id"] == "codex"
    assert proof["replacement"]["absent_from_source_checkpoint"] is True


# ==============================================================================
# Finding R1-1: 11 Adversarial Proof Boundary Tests
# ==============================================================================

# Case 1: authorization exists but status != ACTIVE
def test_verify_fails_on_non_active_auth_status(fake_proof_workspace, monkeypatch):
    ws = fake_proof_workspace
    bad_auth = copy.deepcopy(ws["auth"])
    bad_auth["status"] = "PENDING"
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.get_active_authorization", lambda tid: bad_auth)

    out_file = ws["repo_root"] / OUTPUT_PATH
    with pytest.raises(ContinuityStateValidationError, match="ACTIVE authorization"):
        verify_real_hot_handoff_proof(ws["repo_root"])
    assert not out_file.exists()


# Case 2: malformed/partial authorization required fields
@pytest.mark.parametrize("missing_field", ["task_id", "action", "branch", "executor_id", "lease_id", "lease_fingerprint"])
def test_verify_fails_on_malformed_or_missing_auth_fields(fake_proof_workspace, monkeypatch, missing_field):
    ws = fake_proof_workspace
    bad_auth = copy.deepcopy(ws["auth"])
    del bad_auth[missing_field]
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.get_active_authorization", lambda tid: bad_auth)

    out_file = ws["repo_root"] / OUTPUT_PATH
    with pytest.raises(ContinuityStateValidationError):
        verify_real_hot_handoff_proof(ws["repo_root"])
    assert not out_file.exists()


# Case 3: ACTIVE authorization with no hot_handoff metadata
def test_verify_fails_on_missing_hot_handoff_metadata(fake_proof_workspace, monkeypatch):
    ws = fake_proof_workspace
    bad_auth = copy.deepcopy(ws["auth"])
    del bad_auth["hot_handoff"]
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.get_active_authorization", lambda tid: bad_auth)
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.validate_active_hot_handoff_provenance", lambda tid, a, l: None)

    out_file = ws["repo_root"] / OUTPUT_PATH
    with pytest.raises(ContinuityStateValidationError, match="valid hot_handoff metadata"):
        verify_real_hot_handoff_proof(ws["repo_root"])
    assert not out_file.exists()


# Case 4: active replacement lease mismatch / require_active() failure
def test_verify_fails_on_replacement_lease_mismatch_or_inactive(fake_proof_workspace, monkeypatch):
    ws = fake_proof_workspace

    class InactiveLeaseStore:
        def require_active(self, lease):
            raise ContinuityStateValidationError("Lease is not active in store")

    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.get_lease_store", lambda: InactiveLeaseStore())

    out_file = ws["repo_root"] / OUTPUT_PATH
    with pytest.raises(ContinuityStateValidationError, match="Lease is not active"):
        verify_real_hot_handoff_proof(ws["repo_root"])
    assert not out_file.exists()


# Case 5: exact checkpoint file missing/unreadable
def test_verify_fails_on_missing_checkpoint_file(fake_proof_workspace, monkeypatch):
    ws = fake_proof_workspace

    def fake_missing_loader(tid, fp):
        raise ContinuityStateValidationError(f"Persisted checkpoint not found: {fp}")

    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.load_persisted_hot_handoff_checkpoint", fake_missing_loader)

    out_file = ws["repo_root"] / OUTPUT_PATH
    with pytest.raises(ContinuityStateValidationError, match="Persisted checkpoint not found"):
        verify_real_hot_handoff_proof(ws["repo_root"])
    assert not out_file.exists()


# Case 6: exact checkpoint object / fingerprint tamper
def test_verify_fails_on_checkpoint_fingerprint_tamper(fake_proof_workspace, monkeypatch):
    ws = fake_proof_workspace

    def fake_tampered_loader(tid, fp):
        raise ContinuityStateValidationError("Checkpoint fingerprint mismatch: data altered")

    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.load_persisted_hot_handoff_checkpoint", fake_tampered_loader)

    out_file = ws["repo_root"] / OUTPUT_PATH
    with pytest.raises(ContinuityStateValidationError, match="Checkpoint fingerprint mismatch"):
        verify_real_hot_handoff_proof(ws["repo_root"])
    assert not out_file.exists()


# Case 7: checkpoint task/branch/workspace/source provenance mismatch cases
@pytest.mark.parametrize("field, bad_val, err_pattern", [
    ("task_id", "TASK-999", "task_id mismatch"),
    ("target_branch", "main", "target_branch mismatch"),
    ("workspace_id", "0" * 64, "workspace_id mismatch"),
    ("source_executor_id", "claude-code", "source_executor_id mismatch"),
    ("source_lease_fingerprint", "0" * 64, "source_lease_fingerprint mismatch"),
    ("source_execution_fingerprint", "0" * 64, "source_execution_fingerprint mismatch"),
    ("allowed_paths", ["proofs/other.txt"], "allowed_paths mismatch"),
])
def test_verify_fails_on_checkpoint_provenance_mismatches(fake_proof_workspace, monkeypatch, field, bad_val, err_pattern):
    ws = fake_proof_workspace
    ckpt_dict = ws["checkpoint"].to_dict()
    ckpt_dict[field] = bad_val
    bad_checkpoint = _recompute_checkpoint(ckpt_dict)
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.load_persisted_hot_handoff_checkpoint", lambda tid, fp: bad_checkpoint)

    out_file = ws["repo_root"] / OUTPUT_PATH
    with pytest.raises(ContinuityStateValidationError, match=err_pattern):
        verify_real_hot_handoff_proof(ws["repo_root"])
    assert not out_file.exists()


# Case 8: source-stage absent from checkpoint
def test_verify_fails_when_source_stage_absent_from_checkpoint(fake_proof_workspace, monkeypatch):
    ws = fake_proof_workspace
    ckpt_dict = ws["checkpoint"].to_dict()
    ckpt_dict["untracked_file_manifest"] = []
    bad_checkpoint = _recompute_checkpoint(ckpt_dict)
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.load_persisted_hot_handoff_checkpoint", lambda tid, fp: bad_checkpoint)

    out_file = ws["repo_root"] / OUTPUT_PATH
    with pytest.raises(ContinuityStateValidationError, match="untracked manifest must contain exactly 1 entry"):
        verify_real_hot_handoff_proof(ws["repo_root"])
    assert not out_file.exists()


# Case 9: source-stage present in tracked rather than the required untracked manifest
def test_verify_fails_when_source_stage_in_tracked_manifest(fake_proof_workspace, monkeypatch):
    ws = fake_proof_workspace
    ckpt_dict = ws["checkpoint"].to_dict()
    ckpt_dict["tracked_file_manifest"] = ckpt_dict["untracked_file_manifest"]
    ckpt_dict["untracked_file_manifest"] = []
    bad_checkpoint = _recompute_checkpoint(ckpt_dict)
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.load_persisted_hot_handoff_checkpoint", lambda tid, fp: bad_checkpoint)

    out_file = ws["repo_root"] / OUTPUT_PATH
    with pytest.raises(ContinuityStateValidationError, match="tracked manifest must be empty"):
        verify_real_hot_handoff_proof(ws["repo_root"])
    assert not out_file.exists()


# Case 10: generated PROOF semantic content altered while retaining old proof_fingerprint
def test_generated_proof_semantic_alteration_fails_fingerprint_integrity(fake_proof_workspace):
    ws = fake_proof_workspace
    verify_real_hot_handoff_proof(ws["repo_root"])
    out_file = ws["repo_root"] / OUTPUT_PATH
    assert out_file.exists()

    proof_data = json.loads(out_file.read_text(encoding="utf-8"))
    # Alter source executor without updating top-level proof_fingerprint
    proof_data["source"]["executor_id"] = "antigravity"

    with pytest.raises(ContinuityStateValidationError, match="Proof fingerprint mismatch"):
        verify_proof_fingerprint_integrity(proof_data)


# Case 11: prove exact checkpoint lookup receives only the authorization-bound fingerprint (no history/latest/fuzzy fallback)
def test_verify_exact_checkpoint_lookup_no_fallback(fake_proof_workspace, monkeypatch):
    ws = fake_proof_workspace
    recorded_lookups = []

    def tracking_checkpoint_loader(tid, fp):
        recorded_lookups.append((tid, fp))
        return ws["checkpoint"]

    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.load_persisted_hot_handoff_checkpoint", tracking_checkpoint_loader)

    verify_real_hot_handoff_proof(ws["repo_root"])
    assert len(recorded_lookups) == 1
    assert recorded_lookups[0] == (TASK_ID, ws["checkpoint_fp"]) or recorded_lookups[0] == (36, ws["checkpoint_fp"])
