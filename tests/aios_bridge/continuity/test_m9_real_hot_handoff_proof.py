"""Focused unit and adversarial tests for M9.3 Real Hot Local Handoff Proof (TASK-036 / ADR-025)."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import pytest
import subprocess

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


def test_canonical_semantic_proof_fingerprint_determinism():
    data1 = {"schema_version": "1", "task_id": "TASK-036", "source": {"executor_id": "codex"}}
    data2 = {"task_id": "TASK-036", "source": {"executor_id": "codex"}, "schema_version": "1"}
    fp1, json1 = compute_canonical_semantic_proof_fingerprint(data1)
    fp2, json2 = compute_canonical_semantic_proof_fingerprint(data2)
    assert fp1 == fp2
    assert json1 == json2


def test_safe_read_workspace_payload_valid(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_bytes(b"Hello UTF-8\n")
    res = safe_read_workspace_payload(tmp_path, "test.txt")
    assert res["text"] == "Hello UTF-8\n"
    assert res["size_bytes"] == 12
    assert res["sha256"] == hashlib.sha256(b"Hello UTF-8\n").hexdigest()


def test_safe_read_workspace_payload_rejects_symlink(tmp_path: Path):
    target = tmp_path / "target.txt"
    target.write_bytes(b"real\n")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported on this platform/privilege level")
    with pytest.raises(ContinuityStateValidationError, match="must not be a symlink"):
        safe_read_workspace_payload(tmp_path, "link.txt")


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


def test_verify_fails_on_missing_or_non_active_auth(fake_proof_workspace, monkeypatch):
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.get_active_authorization", lambda tid: None)
    with pytest.raises(ContinuityStateValidationError, match="ACTIVE authorization"):
        verify_real_hot_handoff_proof(fake_proof_workspace["repo_root"])


def test_verify_fails_on_wrong_task_or_action_or_branch(fake_proof_workspace, monkeypatch):
    ws = fake_proof_workspace
    bad_auth = copy.deepcopy(ws["auth"])
    bad_auth["action"] = "FIX"
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.get_active_authorization", lambda tid: bad_auth)
    with pytest.raises(ContinuityStateValidationError, match="Authorization action mismatch"):
        verify_real_hot_handoff_proof(ws["repo_root"])


def test_verify_fails_on_wrong_source_actor(fake_proof_workspace, monkeypatch):
    ws = fake_proof_workspace
    bad_auth = copy.deepcopy(ws["auth"])
    bad_auth["hot_handoff"]["source_executor_id"] = "claude-code"
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.get_active_authorization", lambda tid: bad_auth)
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.validate_active_hot_handoff_provenance", lambda tid, a, l: bad_auth["hot_handoff"])
    with pytest.raises(ContinuityStateValidationError, match="Hot handoff source_executor_id mismatch"):
        verify_real_hot_handoff_proof(ws["repo_root"])


def test_verify_fails_on_wrong_replacement_actor(fake_proof_workspace, monkeypatch):
    ws = fake_proof_workspace
    bad_auth = copy.deepcopy(ws["auth"])
    bad_auth["executor_id"] = "claude-code"
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.get_active_authorization", lambda tid: bad_auth)
    with pytest.raises(ContinuityStateValidationError, match="Authorization executor_id mismatch"):
        verify_real_hot_handoff_proof(ws["repo_root"])


def test_verify_fails_on_same_source_and_replacement_actor(fake_proof_workspace, monkeypatch):
    ws = fake_proof_workspace
    bad_auth = copy.deepcopy(ws["auth"])
    bad_auth["hot_handoff"]["source_executor_id"] = "antigravity"
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.get_active_authorization", lambda tid: bad_auth)
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.validate_active_hot_handoff_provenance", lambda tid, a, l: bad_auth["hot_handoff"])
    with pytest.raises(ContinuityStateValidationError, match="Hot handoff source_executor_id mismatch|must differ"):
        verify_real_hot_handoff_proof(ws["repo_root"])


def test_verify_fails_on_checkpoint_head_mismatch(fake_proof_workspace, monkeypatch):
    ws = fake_proof_workspace
    ckpt_dict = ws["checkpoint"].to_dict()
    ckpt_dict["head_sha"] = "0" * 40
    bad_checkpoint = _recompute_checkpoint(ckpt_dict)
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.load_persisted_hot_handoff_checkpoint", lambda tid, fp: bad_checkpoint)
    with pytest.raises(ContinuityStateValidationError, match="Checkpoint head_sha mismatch"):
        verify_real_hot_handoff_proof(ws["repo_root"])


def test_verify_fails_on_checkpoint_manifest_extra_payload(fake_proof_workspace, monkeypatch):
    ws = fake_proof_workspace
    ckpt_dict = ws["checkpoint"].to_dict()
    ckpt_dict["untracked_file_manifest"].append({"path": "proofs/other.txt", "size_bytes": 5, "sha256": "1" * 64})
    bad_checkpoint = _recompute_checkpoint(ckpt_dict)
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.load_persisted_hot_handoff_checkpoint", lambda tid, fp: bad_checkpoint)
    with pytest.raises(ContinuityStateValidationError, match="Checkpoint untracked manifest must contain exactly 1 entry"):
        verify_real_hot_handoff_proof(ws["repo_root"])


def test_verify_fails_on_source_stage_drift(fake_proof_workspace):
    ws = fake_proof_workspace
    ws["source_file"].write_bytes(b"TAMPERED CONTENT\n")
    with pytest.raises(ContinuityStateValidationError, match="Current proofs/TASK-036-M9/source-stage.txt sha256 mismatch"):
        verify_real_hot_handoff_proof(ws["repo_root"])


def test_verify_fails_on_replacement_stage_present_in_source_checkpoint(fake_proof_workspace, monkeypatch):
    ws = fake_proof_workspace
    ckpt_dict = ws["checkpoint"].to_dict()
    ckpt_dict["tracked_file_manifest"].append({"path": REPLACEMENT_PATH, "size_bytes": 10, "sha256": "0" * 64})
    bad_checkpoint = _recompute_checkpoint(ckpt_dict)
    monkeypatch.setattr("scripts.aios_m9_real_hot_handoff_proof.load_persisted_hot_handoff_checkpoint", lambda tid, fp: bad_checkpoint)
    with pytest.raises(ContinuityStateValidationError, match="Checkpoint tracked manifest must be empty"):
        verify_real_hot_handoff_proof(ws["repo_root"])


def test_verify_fails_on_replacement_stage_missing(fake_proof_workspace):
    ws = fake_proof_workspace
    ws["replacement_file"].unlink()
    with pytest.raises(ContinuityStateValidationError, match="Required payload file does not exist"):
        verify_real_hot_handoff_proof(ws["repo_root"])


def test_verify_fails_on_replacement_stage_fingerprint_mismatch(fake_proof_workspace):
    ws = fake_proof_workspace
    bad_content = (
        "TASK_ID: TASK-036\n"
        "STAGE: REPLACEMENT_POST_ACTIVATION\n"
        "EXECUTOR_ID: antigravity\n"
        f"CHECKPOINT_FINGERPRINT: {'f' * 64}\n"
        "PAYLOAD_VERSION: 1\n"
    )
    ws["replacement_file"].write_bytes(bad_content.encode("utf-8"))
    with pytest.raises(ContinuityStateValidationError, match="content does not match expected marker format"):
        verify_real_hot_handoff_proof(ws["repo_root"])
