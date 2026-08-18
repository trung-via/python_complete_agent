"""Adversarial M9.1 tests for exact, non-mutating hot-handoff checkpoints."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib
import os
from pathlib import Path
import subprocess

import pytest

from src.aios_bridge.continuity.hot_handoff import (
    HotHandoffCheckpoint,
    HotHandoffCheckpointError,
    capture_hot_handoff_checkpoint,
    verify_hot_handoff_checkpoint,
)
from src.aios_bridge.continuity import hot_handoff as hot_handoff_module


BRANCH = "ai/task-034"
WORKSPACE_ID = "1" * 64
LEASE_FINGERPRINT = "2" * 64
EXECUTION_FINGERPRINT = "3" * 64


def _git(repo: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    return result.stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    _git(root, "init", "-b", BRANCH)
    _git(root, "config", "user.name", "M9 Test")
    _git(root, "config", "user.email", "m9@example.invalid")
    _git(root, "config", "core.autocrlf", "false")
    (root / "src").mkdir()
    (root / "docs").mkdir()
    (root / "src" / "tracked.txt").write_text("baseline\n", encoding="utf-8")
    (root / "docs" / "outside.txt").write_text("outside baseline\n", encoding="utf-8")
    _git(root, "add", "src/tracked.txt", "docs/outside.txt")
    _git(root, "commit", "-m", "baseline")
    return root


def _capture(repo: Path, storage: Path, *, allowed_paths: tuple[str, ...] = ("src",)) -> HotHandoffCheckpoint:
    return capture_hot_handoff_checkpoint(
        repo,
        storage,
        task_id="TASK-034",
        target_branch=BRANCH,
        workspace_id=WORKSPACE_ID,
        source_executor_id="codex",
        source_lease_fingerprint=LEASE_FINGERPRINT,
        source_execution_fingerprint=EXECUTION_FINGERPRINT,
        allowed_paths=allowed_paths,
    )


def _verify(
    checkpoint: HotHandoffCheckpoint,
    repo: Path,
    *,
    allowed_paths: tuple[str, ...] = ("src",),
    workspace_id: str = WORKSPACE_ID,
    storage: Path | None = None,
) -> None:
    verify_hot_handoff_checkpoint(
        checkpoint,
        repo,
        workspace_id=workspace_id,
        allowed_paths=allowed_paths,
        checkpoint_dir=storage,
    )


def _snapshot(repo: Path) -> tuple[bytes, bytes, bytes, bytes, dict[str, bytes]]:
    files = {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(repo).parts
    }
    return (
        _git(repo, "rev-parse", "HEAD"),
        _git(repo, "symbolic-ref", "--short", "HEAD"),
        _git(repo, "ls-files", "--stage", "-z"),
        _git(repo, "status", "--porcelain=v2", "-z", "--untracked-files=all"),
        files,
    )


def test_identical_state_is_deterministic_immutable_and_content_addressed(repo: Path, tmp_path: Path) -> None:
    storage = tmp_path / "runtime" / "checkpoints"
    (repo / "src" / "tracked.txt").write_text("dirty text\n", encoding="utf-8")
    first = _capture(repo, storage)
    second = _capture(repo, storage)

    assert first == second
    assert first.checkpoint_fingerprint == second.checkpoint_fingerprint
    assert first.checkpoint_fingerprint == first.compute_fingerprint()
    assert len(list(storage.glob("*.json"))) == 1
    assert HotHandoffCheckpoint.from_json(first.to_canonical_json()) == first
    with pytest.raises(FrozenInstanceError):
        first.head_sha = "0" * 40  # type: ignore[misc]


def test_valid_tracked_text_edit_is_captured_and_verified(repo: Path, tmp_path: Path) -> None:
    edited = b"baseline\ncontinued by replacement\n"
    (repo / "src" / "tracked.txt").write_bytes(edited)
    checkpoint = _capture(repo, tmp_path / "runtime")

    assert checkpoint.tracked_file_manifest[0].path == "src/tracked.txt"
    assert checkpoint.tracked_file_manifest[0].size_bytes == len(edited)
    assert checkpoint.tracked_file_manifest[0].sha256 == hashlib.sha256(edited).hexdigest()
    _verify(checkpoint, repo, storage=tmp_path / "runtime")


def test_valid_untracked_text_file_is_captured_and_verified(repo: Path, tmp_path: Path) -> None:
    payload = b"unpublished text\n"
    (repo / "src" / "new.txt").write_bytes(payload)
    checkpoint = _capture(repo, tmp_path / "runtime")

    assert [entry.path for entry in checkpoint.untracked_file_manifest] == ["src/new.txt"]
    assert checkpoint.untracked_file_manifest[0].sha256 == hashlib.sha256(payload).hexdigest()
    _verify(checkpoint, repo)


def test_tracked_file_tamper_fails_verification(repo: Path, tmp_path: Path) -> None:
    path = repo / "src" / "tracked.txt"
    path.write_text("checkpoint state\n", encoding="utf-8")
    checkpoint = _capture(repo, tmp_path / "runtime")
    path.write_text("tampered state\n", encoding="utf-8")

    with pytest.raises(HotHandoffCheckpointError, match="mismatch"):
        _verify(checkpoint, repo)


def test_untracked_file_byte_tamper_fails_verification(repo: Path, tmp_path: Path) -> None:
    path = repo / "src" / "new.txt"
    path.write_text("same length A\n", encoding="utf-8")
    checkpoint = _capture(repo, tmp_path / "runtime")
    path.write_text("same length B\n", encoding="utf-8")

    with pytest.raises(HotHandoffCheckpointError, match="mismatch"):
        _verify(checkpoint, repo)


@pytest.mark.parametrize("operation", ["add", "remove"])
def test_untracked_file_add_or_remove_fails_verification(repo: Path, tmp_path: Path, operation: str) -> None:
    original = repo / "src" / "one.txt"
    original.write_text("one\n", encoding="utf-8")
    checkpoint = _capture(repo, tmp_path / "runtime")
    if operation == "add":
        (repo / "src" / "two.txt").write_text("two\n", encoding="utf-8")
    else:
        original.unlink()

    with pytest.raises(HotHandoffCheckpointError, match="mismatch"):
        _verify(checkpoint, repo)


def test_head_drift_fails_without_history_fallback(repo: Path, tmp_path: Path) -> None:
    (repo / "src" / "tracked.txt").write_text("dirty checkpoint\n", encoding="utf-8")
    checkpoint = _capture(repo, tmp_path / "runtime")
    _git(repo, "commit", "--allow-empty", "-m", "HEAD drift")

    with pytest.raises(HotHandoffCheckpointError, match="mismatch"):
        _verify(checkpoint, repo)


def test_branch_drift_fails_verification(repo: Path, tmp_path: Path) -> None:
    (repo / "src" / "tracked.txt").write_text("dirty checkpoint\n", encoding="utf-8")
    checkpoint = _capture(repo, tmp_path / "runtime")
    _git(repo, "switch", "-c", "other-branch")

    with pytest.raises(HotHandoffCheckpointError, match="branch mismatch"):
        _verify(checkpoint, repo)


def test_detached_head_and_branch_mismatch_fail_capture(repo: Path, tmp_path: Path) -> None:
    with pytest.raises(HotHandoffCheckpointError, match="branch mismatch"):
        capture_hot_handoff_checkpoint(
            repo,
            tmp_path / "runtime-mismatch",
            task_id="TASK-034",
            target_branch="wrong-branch",
            workspace_id=WORKSPACE_ID,
            source_executor_id="codex",
            source_lease_fingerprint=LEASE_FINGERPRINT,
            source_execution_fingerprint=EXECUTION_FINGERPRINT,
            allowed_paths=("src",),
        )
    _git(repo, "checkout", "--detach")
    with pytest.raises(HotHandoffCheckpointError, match="detached HEAD"):
        _capture(repo, tmp_path / "runtime-detached")


def test_staged_changes_fail_capture(repo: Path, tmp_path: Path) -> None:
    (repo / "src" / "tracked.txt").write_text("staged\n", encoding="utf-8")
    _git(repo, "add", "src/tracked.txt")
    with pytest.raises(HotHandoffCheckpointError, match="staged changes"):
        _capture(repo, tmp_path / "runtime")


def test_conflicted_unmerged_state_fails_capture(repo: Path, tmp_path: Path) -> None:
    _git(repo, "switch", "-c", "conflict-side")
    (repo / "src" / "tracked.txt").write_text("side\n", encoding="utf-8")
    _git(repo, "commit", "-am", "side")
    _git(repo, "switch", BRANCH)
    (repo / "src" / "tracked.txt").write_text("main side\n", encoding="utf-8")
    _git(repo, "commit", "-am", "main side")
    merge = subprocess.run(
        ["git", "merge", "conflict-side"], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    assert merge.returncode != 0

    with pytest.raises(HotHandoffCheckpointError, match="Git operation in progress|unmerged"):
        _capture(repo, tmp_path / "runtime")


@pytest.mark.parametrize("marker", ["MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-apply", "rebase-merge"])
def test_git_operation_markers_fail_closed(repo: Path, tmp_path: Path, marker: str) -> None:
    marker_path = Path(_git(repo, "rev-parse", "--git-path", marker).decode().strip())
    if not marker_path.is_absolute():
        marker_path = repo / marker_path
    if marker.startswith("rebase-"):
        marker_path.mkdir(parents=True)
    else:
        marker_path.write_text("0" * 40 + "\n", encoding="ascii")

    with pytest.raises(HotHandoffCheckpointError, match="Git operation in progress"):
        _capture(repo, tmp_path / f"runtime-{marker}")


def test_out_of_scope_modified_and_untracked_paths_fail(repo: Path, tmp_path: Path) -> None:
    (repo / "docs" / "outside.txt").write_text("changed outside\n", encoding="utf-8")
    with pytest.raises(HotHandoffCheckpointError, match="outside allowed scope"):
        _capture(repo, tmp_path / "runtime-modified")

    _git(repo, "restore", "docs/outside.txt")
    (repo / "docs" / "new.txt").write_text("untracked outside\n", encoding="utf-8")
    with pytest.raises(HotHandoffCheckpointError, match="outside allowed scope"):
        _capture(repo, tmp_path / "runtime-untracked")


@pytest.mark.parametrize("bad", ["../src", "src/../docs", "./src", "src//child"])
def test_traversal_and_noncanonical_allowed_paths_fail(repo: Path, tmp_path: Path, bad: str) -> None:
    with pytest.raises(HotHandoffCheckpointError):
        _capture(repo, tmp_path / "runtime", allowed_paths=(bad,))


def test_absolute_allowed_path_fails(repo: Path, tmp_path: Path) -> None:
    with pytest.raises(HotHandoffCheckpointError, match="absolute|POSIX"):
        _capture(repo, tmp_path / "runtime", allowed_paths=(str(repo / "src"),))


def test_symlink_index_mode_fails_even_without_os_symlink_privilege(repo: Path, tmp_path: Path) -> None:
    blob = _git(repo, "hash-object", "-w", "--stdin", input_bytes=b"target.txt").decode().strip()
    _git(repo, "update-index", "--add", "--cacheinfo", f"120000,{blob},src/link")
    _git(repo, "commit", "-m", "tracked symlink mode")
    _git(repo, "config", "core.symlinks", "false")
    _git(repo, "checkout-index", "-f", "--", "src/link")
    (repo / "src" / "link").write_text("changed link target\n", encoding="utf-8")

    with pytest.raises(HotHandoffCheckpointError, match="symlink/submodule/special"):
        _capture(repo, tmp_path / "runtime")


def test_symlink_escape_in_allowed_scope_fails_when_supported(repo: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    link = repo / "src" / "escape"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("OS account cannot create symlinks")

    with pytest.raises(HotHandoffCheckpointError, match="symlink"):
        _capture(repo, tmp_path / "runtime", allowed_paths=("src/escape",))


def test_binary_payload_fails_capture(repo: Path, tmp_path: Path) -> None:
    (repo / "src" / "binary.bin").write_bytes(b"text-prefix\x00binary")
    with pytest.raises(HotHandoffCheckpointError, match="binary payload"):
        _capture(repo, tmp_path / "runtime")


def test_directory_masquerading_as_file_is_rejected(repo: Path) -> None:
    (repo / "src" / "directory-payload").mkdir()
    with pytest.raises(HotHandoffCheckpointError, match="special/non-regular"):
        hot_handoff_module._manifest_entry(repo, "src/directory-payload")


def test_clean_workspace_is_not_a_hot_handoff_checkpoint(repo: Path, tmp_path: Path) -> None:
    with pytest.raises(HotHandoffCheckpointError, match="requires unpublished dirty"):
        _capture(repo, tmp_path / "runtime")


def test_checkpoint_storage_inside_worktree_fails_without_writing(repo: Path) -> None:
    forbidden = repo / "src" / "checkpoint-storage"
    with pytest.raises(HotHandoffCheckpointError, match="outside"):
        _capture(repo, forbidden)
    assert not forbidden.exists()


def test_checkpoint_object_and_persisted_fingerprint_tamper_fail(repo: Path, tmp_path: Path) -> None:
    (repo / "src" / "tracked.txt").write_text("dirty\n", encoding="utf-8")
    storage = tmp_path / "runtime"
    checkpoint = _capture(repo, storage)
    object.__setattr__(checkpoint, "checkpoint_fingerprint", "f" * 64)
    with pytest.raises(HotHandoffCheckpointError, match="fingerprint tamper"):
        _verify(checkpoint, repo)

    clean_checkpoint = _capture(repo, storage)
    persisted = storage / f"{clean_checkpoint.checkpoint_fingerprint}.json"
    persisted.chmod(0o600)
    persisted.write_text("{}\n", encoding="utf-8")
    with pytest.raises(HotHandoffCheckpointError, match="persisted checkpoint evidence mismatch"):
        _verify(clean_checkpoint, repo, storage=storage)


def test_workspace_id_and_allowed_path_mismatch_fail(repo: Path, tmp_path: Path) -> None:
    (repo / "src" / "tracked.txt").write_text("dirty\n", encoding="utf-8")
    checkpoint = _capture(repo, tmp_path / "runtime")

    with pytest.raises(HotHandoffCheckpointError, match="workspace_id mismatch"):
        _verify(checkpoint, repo, workspace_id="9" * 64)
    with pytest.raises(HotHandoffCheckpointError, match="allowed_paths mismatch"):
        _verify(checkpoint, repo, allowed_paths=("src/tracked.txt",))


def test_capture_and_verify_leave_head_index_status_and_worktree_unchanged(repo: Path, tmp_path: Path) -> None:
    (repo / "src" / "tracked.txt").write_text("dirty tracked\n", encoding="utf-8")
    (repo / "src" / "untracked.txt").write_text("dirty untracked\n", encoding="utf-8")
    before_capture = _snapshot(repo)
    checkpoint = _capture(repo, tmp_path / "runtime")
    after_capture = _snapshot(repo)
    assert after_capture == before_capture

    _verify(checkpoint, repo, storage=tmp_path / "runtime")
    after_verify = _snapshot(repo)
    assert after_verify == before_capture


def test_no_history_or_nearest_match_fallback(repo: Path, tmp_path: Path) -> None:
    path = repo / "src" / "tracked.txt"
    path.write_text("historical dirty state\n", encoding="utf-8")
    checkpoint = _capture(repo, tmp_path / "runtime")
    _git(repo, "restore", "src/tracked.txt")

    with pytest.raises(HotHandoffCheckpointError, match="mismatch"):
        _verify(checkpoint, repo)


def test_runtime_secret_and_transcript_scopes_fail_closed(repo: Path, tmp_path: Path) -> None:
    for forbidden in (".ai", ".env", "src/transcripts", "src/sessions"):
        with pytest.raises(HotHandoffCheckpointError, match="forbidden"):
            _capture(repo, tmp_path / forbidden.replace("/", "-"), allowed_paths=(forbidden,))
