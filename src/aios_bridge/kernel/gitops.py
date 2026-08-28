"""AIOS Bridge Kernel v1 Pure Git Operations (ADR-068 / TASK-098)."""

import os
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any


class KernelGitError(RuntimeError):
    pass


def git_cmd(args: List[str], cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    if cwd is None:
        cwd = Path(os.getcwd())
    res = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if check and res.returncode != 0:
        raise KernelGitError(f"Git command failed (exit={res.returncode}): git {' '.join(args)}\nStderr: {res.stderr.strip()}")
    return res


def get_current_branch(cwd: Optional[Path] = None) -> str:
    res = git_cmd(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    return res.stdout.strip()


def get_head_sha(cwd: Optional[Path] = None) -> str:
    res = git_cmd(["rev-parse", "HEAD"], cwd=cwd)
    return res.stdout.strip()


def get_remote_ref_sha(remote: str, ref: str, cwd: Optional[Path] = None) -> Optional[str]:
    res = git_cmd(["rev-parse", f"refs/remotes/{remote}/{ref}"], cwd=cwd, check=False)
    if res.returncode != 0:
        return None
    return res.stdout.strip()


def collect_dirty_paths(cwd: Optional[Path] = None) -> List[str]:
    res = git_cmd(["status", "--porcelain"], cwd=cwd)
    paths = []
    for line in res.stdout.splitlines():
        if not line.strip():
            continue
        path_part = line[3:].strip()
        if " -> " in path_part:
            path_part = path_part.split(" -> ")[-1]
        norm = path_part.replace("\\", "/")
        if not norm.startswith(".aios_runtime/"):
            paths.append(norm)
    return sorted(list(set(paths)))


def collect_worktree_changed_paths(pre_execution_head: str, cwd: Optional[Path] = None) -> List[str]:
    """Collects dirty paths in worktree plus all modified paths between pre_execution_head and HEAD."""
    dirty = collect_dirty_paths(cwd=cwd)

    # Check git diff between pre_execution_head and HEAD
    res = git_cmd(["diff", "--name-only", pre_execution_head, "HEAD"], cwd=cwd, check=False)
    diff_paths = []
    if res.returncode == 0:
        for line in res.stdout.splitlines():
            line = line.strip().replace("\\", "/")
            if line and not line.startswith(".aios_runtime/"):
                diff_paths.append(line)

    all_changed = sorted(list(set(dirty + diff_paths)))
    return all_changed


def capture_publication_trust(remote: str = "origin", cwd: Optional[Path] = None) -> Dict[str, Any]:
    """Captures exact Git-admin publication trust snapshot."""
    url_res = git_cmd(["remote", "get-url", "--all", remote], cwd=cwd, check=False)
    if url_res.returncode != 0:
        raise KernelGitError(f"E4 Git observation failed: remote get-url --all {remote} (exit={url_res.returncode})")

    url = url_res.stdout.strip()
    if not url:
        raise KernelGitError(f"E4 Git observation failed: remote {remote} URL is empty")

    hooks_res = git_cmd(["config", "--get", "core.hooksPath"], cwd=cwd, check=False)
    hooks_path = hooks_res.stdout.strip() if hooks_res.returncode == 0 else ""

    return {
        "remote": remote,
        "remote_url": url,
        "hooks_path": hooks_path,
    }


def verify_publication_trust(snapshot: Dict[str, Any], cwd: Optional[Path] = None) -> None:
    """Verifies pre-test publication trust snapshot against current Git config."""
    remote = snapshot.get("remote", "origin")
    current = capture_publication_trust(remote, cwd=cwd)
    if current != snapshot:
        raise KernelGitError(f"Publication trust verification failed: Git admin config drifted (expected {snapshot}, got {current})")
