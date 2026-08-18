"""Deterministic M9.3 Real Two-Executor Hot Local Handoff Proof Verifier (TASK-036 / ADR-025).

Proves unpublished dirty-workspace continuity across executor boundaries (codex -> antigravity)
at an exact quiescent checkpoint without data loss, transcript transfer, or manual claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import Any

REPO_DIR = Path(__file__).resolve().parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from bridge import (
    current_branch,
    get_active_authorization,
    get_lease_store,
    get_workspace_id,
    load_persisted_hot_handoff_checkpoint,
    reconstruct_expected_executor_lease,
    validate_active_hot_handoff_provenance,
)
from src.aios_bridge.continuity.errors import ContinuityStateValidationError

TASK_NUM = 36
TASK_ID = "TASK-036"
EXPECTED_BRANCH = "ai/task-036"
BASELINE_SHA = "6b698eca9be428d3043a2e13064a19f1f4dd2faf"
SOURCE_EXECUTOR = "codex"
REPLACEMENT_EXECUTOR = "antigravity"
SOURCE_PATH = "proofs/TASK-036-M9/source-stage.txt"
REPLACEMENT_PATH = "proofs/TASK-036-M9/replacement-stage.txt"
OUTPUT_PATH = "proofs/TASK-036-M9/PROOF.json"
SCHEMA_VERSION = "1"

EXPECTED_SOURCE_CONTENT = (
    "TASK_ID: TASK-036\n"
    "STAGE: SOURCE_PRE_HANDOFF\n"
    "EXECUTOR_ID: codex\n"
    "PAYLOAD_VERSION: 1\n"
)


def validate_safe_repository_path(repo_root: Path, relative_path: str) -> Path:
    """
    Validates that a repository-relative path does not use absolute paths, traversal,
    or symlinks at any component (intermediate directories or leaf), and is physically
    confined within repo_root.
    """
    if (
        os.path.isabs(relative_path)
        or Path(relative_path).is_absolute()
        or relative_path.startswith(("/", "\\"))
        or ":" in relative_path
    ):
        raise ContinuityStateValidationError(f"Path must be repository-relative: {relative_path!r}")

    norm_path = relative_path.replace("\\", "/")
    parts = norm_path.split("/")
    if not parts or any(p in ("..", ".", "") for p in parts):
        raise ContinuityStateValidationError(f"Path must be canonical without traversal components: {relative_path!r}")

    current = repo_root.resolve()
    for part in parts:
        current = current / part
        # Check if current path exists or is a broken symlink
        if current.exists() or current.is_symlink():
            st = os.lstat(current)
            if stat.S_ISLNK(st.st_mode):
                raise ContinuityStateValidationError(f"Path component must not be a symlink: '{part}' in '{relative_path}'")

    # Verify physical confinement within repo_root
    try:
        current.resolve().relative_to(repo_root.resolve())
    except ValueError as e:
        raise ContinuityStateValidationError(f"Path escapes repository root: {relative_path}") from e

    return current


def safe_read_workspace_payload(repo_root: Path, relative_path: str) -> dict[str, Any]:
    """
    Safely reads a repository-relative payload file without following symlinks.
    Rejects parent/leaf symlinks, non-regular files, binary/NUL content, or non-UTF-8 data.
    """
    full_path = validate_safe_repository_path(repo_root, relative_path)
    if not full_path.exists():
        raise ContinuityStateValidationError(f"Required payload file does not exist: {relative_path}")

    st = os.lstat(full_path)
    if stat.S_ISLNK(st.st_mode):
        raise ContinuityStateValidationError(f"Payload file must not be a symlink: {relative_path}")
    if not stat.S_ISREG(st.st_mode):
        raise ContinuityStateValidationError(f"Payload file must be a regular file: {relative_path}")

    data = full_path.read_bytes()
    if b"\x00" in data:
        raise ContinuityStateValidationError(f"Payload file contains forbidden NUL bytes: {relative_path}")

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ContinuityStateValidationError(f"Payload file is not valid UTF-8: {relative_path}") from e

    sha256 = hashlib.sha256(data).hexdigest()
    size_bytes = len(data)

    return {
        "bytes": data,
        "text": text,
        "sha256": sha256,
        "size_bytes": size_bytes,
    }


def compute_canonical_semantic_proof_fingerprint(semantic_proof: dict[str, Any]) -> tuple[str, str]:
    """
    Computes deterministic SHA-256 fingerprint over sorted, unindented canonical JSON.
    Returns (proof_fingerprint, canonical_json_str).
    """
    canonical_json_str = json.dumps(
        semantic_proof,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    proof_fingerprint = hashlib.sha256(canonical_json_str.encode("utf-8")).hexdigest()
    return proof_fingerprint, canonical_json_str


def verify_proof_fingerprint_integrity(proof_data: dict[str, Any]) -> str:
    """
    Verifies that proof_data has a valid top-level proof_fingerprint matching
    the canonical semantic proof fields. Returns the verified proof_fingerprint.
    """
    if not isinstance(proof_data, dict):
        raise ContinuityStateValidationError("Proof data must be a dictionary")
    declared_fp = proof_data.get("proof_fingerprint")
    if not declared_fp or not isinstance(declared_fp, str):
        raise ContinuityStateValidationError("Missing or invalid top-level 'proof_fingerprint'")

    semantic_copy = {k: v for k, v in proof_data.items() if k != "proof_fingerprint"}
    recomputed_fp, _ = compute_canonical_semantic_proof_fingerprint(semantic_copy)
    if declared_fp != recomputed_fp:
        raise ContinuityStateValidationError(
            f"Proof fingerprint mismatch: declared '{declared_fp}', recomputed '{recomputed_fp}'"
        )
    return declared_fp


def verify_real_hot_handoff_proof(repo_root: Path | None = None) -> dict[str, Any]:
    """
    Executes fail-closed mechanical verification of the real M9.3 hot handoff proof.
    Verifies runtime authorization, active lease, persisted checkpoint, exact source witness,
    exact replacement witness, and writes PROOF.json atomically.
    """
    root = (repo_root or REPO_DIR).resolve()
    if Path.cwd().resolve() != root:
        raise ContinuityStateValidationError(f"Verifier must be executed from repository root: {root}")

    # 1. Require current branch exactly ai/task-036
    curr_branch = current_branch()
    if curr_branch != EXPECTED_BRANCH:
        raise ContinuityStateValidationError(f"Branch mismatch: expected '{EXPECTED_BRANCH}', got '{curr_branch}'")

    # 2. Load exact ACTIVE authorization for task 36
    auth = get_active_authorization(TASK_NUM)
    if not auth or not isinstance(auth, dict) or auth.get("status") != "ACTIVE":
        raise ContinuityStateValidationError("Task 36 does not have an ACTIVE authorization")

    for req_field in ("task_id", "action", "branch", "executor_id", "lease_id", "lease_fingerprint", "execution_fingerprint"):
        if not auth.get(req_field):
            raise ContinuityStateValidationError(f"Authorization missing or empty required field: '{req_field}'")

    if auth.get("task_id") != TASK_ID:
        raise ContinuityStateValidationError(f"Authorization task_id mismatch: expected '{TASK_ID}', got '{auth.get('task_id')}'")
    if auth.get("action") != "RUN":
        raise ContinuityStateValidationError(f"Authorization action mismatch: expected 'RUN', got '{auth.get('action')}'")
    if auth.get("branch") != EXPECTED_BRANCH:
        raise ContinuityStateValidationError(f"Authorization branch mismatch: expected '{EXPECTED_BRANCH}', got '{auth.get('branch')}'")
    if auth.get("executor_id") != REPLACEMENT_EXECUTOR:
        raise ContinuityStateValidationError(
            f"Authorization executor_id mismatch: expected '{REPLACEMENT_EXECUTOR}', got '{auth.get('executor_id')}'"
        )

    # 3. Require current git rev-parse HEAD exactly BASELINE_SHA
    try:
        head_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, stderr=subprocess.PIPE
        ).decode().strip()
    except Exception as e:
        raise ContinuityStateValidationError(f"Failed to resolve git HEAD: {e}") from e

    if head_sha != BASELINE_SHA:
        raise ContinuityStateValidationError(
            f"Git HEAD mismatch: expected baseline commit '{BASELINE_SHA}', got '{head_sha}'"
        )

    # 4. Reconstruct and verify replacement lease is active
    replacement_lease = reconstruct_expected_executor_lease(auth)
    get_lease_store().require_active(replacement_lease)

    # 5. Validate hot handoff active provenance metadata
    metadata = validate_active_hot_handoff_provenance(TASK_NUM, auth, replacement_lease)
    if not metadata:
        raise ContinuityStateValidationError("Active authorization does not contain valid hot_handoff metadata")

    source_actor = metadata.get("source_executor_id")
    repl_actor = metadata.get("replacement_executor_id")
    if source_actor != SOURCE_EXECUTOR:
        raise ContinuityStateValidationError(
            f"Hot handoff source_executor_id mismatch: expected '{SOURCE_EXECUTOR}', got '{source_actor}'"
        )
    if repl_actor != REPLACEMENT_EXECUTOR:
        raise ContinuityStateValidationError(
            f"Hot handoff replacement_executor_id mismatch: expected '{REPLACEMENT_EXECUTOR}', got '{repl_actor}'"
        )
    if source_actor == repl_actor:
        raise ContinuityStateValidationError(f"Source and replacement executors must differ: '{source_actor}'")

    checkpoint_fp = metadata.get("checkpoint_fingerprint")
    if not checkpoint_fp:
        raise ContinuityStateValidationError("Missing checkpoint_fingerprint in hot handoff metadata")

    # 6. Load persisted checkpoint
    checkpoint = load_persisted_hot_handoff_checkpoint(TASK_NUM, checkpoint_fp)
    if checkpoint.task_id != TASK_ID:
        raise ContinuityStateValidationError(f"Checkpoint task_id mismatch: expected '{TASK_ID}', got '{checkpoint.task_id}'")
    if checkpoint.target_branch != EXPECTED_BRANCH:
        raise ContinuityStateValidationError(
            f"Checkpoint target_branch mismatch: expected '{EXPECTED_BRANCH}', got '{checkpoint.target_branch}'"
        )
    if checkpoint.head_sha != BASELINE_SHA:
        raise ContinuityStateValidationError(f"Checkpoint head_sha mismatch: expected '{BASELINE_SHA}', got '{checkpoint.head_sha}'")

    curr_workspace_id = get_workspace_id(root)
    if checkpoint.workspace_id != curr_workspace_id:
        raise ContinuityStateValidationError(
            f"Checkpoint workspace_id mismatch: expected '{curr_workspace_id}', got '{checkpoint.workspace_id}'"
        )
    if checkpoint.source_executor_id != SOURCE_EXECUTOR:
        raise ContinuityStateValidationError(
            f"Checkpoint source_executor_id mismatch: expected '{SOURCE_EXECUTOR}', got '{checkpoint.source_executor_id}'"
        )
    if checkpoint.source_lease_fingerprint != metadata.get("source_lease_fingerprint"):
        raise ContinuityStateValidationError("Checkpoint source_lease_fingerprint mismatch with active metadata")
    if checkpoint.source_execution_fingerprint != metadata.get("source_execution_fingerprint"):
        raise ContinuityStateValidationError("Checkpoint source_execution_fingerprint mismatch with active metadata")
    if checkpoint.allowed_paths != (SOURCE_PATH,):
        raise ContinuityStateValidationError(
            f"Checkpoint allowed_paths mismatch: expected '{(SOURCE_PATH,)}', got '{checkpoint.allowed_paths}'"
        )

    # 7. Require checkpoint manifests contain exactly one dirty payload total and it is SOURCE_PATH (untracked)
    if len(checkpoint.tracked_file_manifest) != 0:
        raise ContinuityStateValidationError(
            f"Checkpoint tracked manifest must be empty at baseline, found: {len(checkpoint.tracked_file_manifest)} entries"
        )
    if len(checkpoint.untracked_file_manifest) != 1:
        raise ContinuityStateValidationError(
            f"Checkpoint untracked manifest must contain exactly 1 entry, found: {len(checkpoint.untracked_file_manifest)}"
        )
    if checkpoint.untracked_file_manifest[0].path != SOURCE_PATH:
        raise ContinuityStateValidationError(
            f"Checkpoint untracked manifest path mismatch: expected '{SOURCE_PATH}', got '{checkpoint.untracked_file_manifest[0].path}'"
        )

    # 8. Read current SOURCE_PATH and verify exact match with checkpoint entry & canonical content
    source_info = safe_read_workspace_payload(root, SOURCE_PATH)
    if source_info["sha256"] != checkpoint.untracked_file_manifest[0].sha256:
        raise ContinuityStateValidationError(
            f"Current {SOURCE_PATH} sha256 mismatch with checkpoint: expected '{checkpoint.untracked_file_manifest[0].sha256}', got '{source_info['sha256']}'"
        )
    if source_info["size_bytes"] != checkpoint.untracked_file_manifest[0].size_bytes:
        raise ContinuityStateValidationError(
            f"Current {SOURCE_PATH} size mismatch with checkpoint: expected {checkpoint.untracked_file_manifest[0].size_bytes}, got {source_info['size_bytes']}"
        )
    if source_info["text"] != EXPECTED_SOURCE_CONTENT:
        raise ContinuityStateValidationError(f"Current {SOURCE_PATH} content does not match canonical source content")

    # 9. Require REPLACEMENT_PATH absent from both checkpoint manifests
    manifest_paths = {entry.path for entry in checkpoint.tracked_file_manifest} | {
        entry.path for entry in checkpoint.untracked_file_manifest
    }
    if REPLACEMENT_PATH in manifest_paths:
        raise ContinuityStateValidationError(
            f"Replacement payload '{REPLACEMENT_PATH}' was forbiddenly present in source checkpoint"
        )

    # 10. Read current REPLACEMENT_PATH and verify exact format and fingerprint binding
    replacement_info = safe_read_workspace_payload(root, REPLACEMENT_PATH)
    expected_replacement_content = (
        "TASK_ID: TASK-036\n"
        "STAGE: REPLACEMENT_POST_ACTIVATION\n"
        "EXECUTOR_ID: antigravity\n"
        f"CHECKPOINT_FINGERPRINT: {checkpoint_fp}\n"
        "PAYLOAD_VERSION: 1\n"
    )
    if replacement_info["text"] != expected_replacement_content:
        raise ContinuityStateValidationError(
            f"Current {REPLACEMENT_PATH} content does not match expected marker format or active checkpoint fingerprint"
        )

    # 11. Build deterministic semantic proof object
    artifact_path = auth.get("artifact_path") or ".ai/tasks/TASK-036.md"
    artifact_blob_sha = auth.get("artifact_blob_sha")

    semantic_proof: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "baseline_sha": BASELINE_SHA,
        "current_branch": EXPECTED_BRANCH,
        "workspace_id": curr_workspace_id,
        "authorized_artifact": {
            "path": artifact_path,
            "blob_sha": artifact_blob_sha,
        },
        "checkpoint_fingerprint": checkpoint_fp,
        "checkpoint": checkpoint.to_dict(),
        "source": {
            "executor_id": SOURCE_EXECUTOR,
            "lease_id": metadata.get("source_lease_id"),
            "lease_fingerprint": metadata.get("source_lease_fingerprint"),
            "execution_fingerprint": metadata.get("source_execution_fingerprint"),
            "path": SOURCE_PATH,
            "sha256": source_info["sha256"],
            "size_bytes": source_info["size_bytes"],
        },
        "replacement": {
            "executor_id": REPLACEMENT_EXECUTOR,
            "lease_id": auth["lease_id"],
            "lease_fingerprint": auth["lease_fingerprint"],
            "execution_fingerprint": auth["execution_fingerprint"],
            "path": REPLACEMENT_PATH,
            "sha256": replacement_info["sha256"],
            "size_bytes": replacement_info["size_bytes"],
            "absent_from_source_checkpoint": True,
        },
    }

    proof_fingerprint, _ = compute_canonical_semantic_proof_fingerprint(semantic_proof)
    full_proof = {**semantic_proof, "proof_fingerprint": proof_fingerprint}

    # 12. Write PROOF.json atomically
    out_file = root / OUTPUT_PATH
    out_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file = out_file.with_name(f"{out_file.name}.tmp.{os.getpid()}")
    formatted_json = json.dumps(full_proof, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    temp_file.write_text(formatted_json, encoding="utf-8")
    os.replace(temp_file, out_file)

    # 13. Read back and verify exact written output
    written_data = json.loads(out_file.read_text(encoding="utf-8"))
    verify_proof_fingerprint_integrity(written_data)

    return {
        "status": "PASS",
        "task_id": TASK_ID,
        "source_executor": SOURCE_EXECUTOR,
        "replacement_executor": REPLACEMENT_EXECUTOR,
        "checkpoint_fingerprint": checkpoint_fp,
        "proof_fingerprint": proof_fingerprint,
        "output_path": str(out_file),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="M9.3 Real Hot Local Handoff Proof Verifier (TASK-036)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("verify", help="Verifies the real hot handoff proof and generates PROOF.json")

    args = parser.parse_args()

    if args.command == "verify":
        try:
            res = verify_real_hot_handoff_proof(REPO_DIR)
            print("M9_3_REAL_HOT_HANDOFF_PROOF: PASS")
            print(f"TASK_ID: {res['task_id']}")
            print(f"SOURCE_EXECUTOR: {res['source_executor']}")
            print(f"REPLACEMENT_EXECUTOR: {res['replacement_executor']}")
            print(f"CHECKPOINT_FINGERPRINT: {res['checkpoint_fingerprint']}")
            print(f"PROOF_FINGERPRINT: {res['proof_fingerprint']}")
            return 0
        except Exception as e:
            print(f"[ERROR] M9.3 Proof verification failed: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
