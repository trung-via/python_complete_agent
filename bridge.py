#!/usr/bin/env python3
"""
AI Engineering OS Lite Bridge v0.4.0
====================================

Transport layer between:
  ChatGPT <-> GitHub control branch <-> local repo <-> Antigravity

Zero-Touch Workflow Model:
- User issues `/aios-worker RUN TASK-N` in Antigravity.
- Bridge `handoff` directly fetches `ai-control`, reconciles local main,
  prepares `ai/task-N`, caches artifact externally, and records exact authorization.
- On review feedback, user issues `/aios-worker FIX TASK-N`.
- Bridge `handoff --action fix` validates CHANGES_REQUIRED review and authorizes fix.
- Bridge `publish` verifies current authorization and control artifact consistency,
  runs tests, generates RESULT-N, commits and pushes to remote task branch.
- No force-push, no auto-merge, no dirty worktree mutations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from src.aios_bridge.continuity.executor import ExecutionOperation
from src.aios_bridge.continuity.lease import (
    MAX_ACTIVE_EXECUTORS_PER_TASK,
    ExecutorLease,
    validate_executor_lease_binding,
)
from src.aios_bridge.runtime_lease import AtomicExecutorLeaseStore

PROJECT = Path.cwd()
AI = PROJECT / ".ai"

INBOUND_PREFIXES = (
    ".ai/tasks/",
    ".ai/reviews/",
    ".ai/decisions/",
    ".ai/context/",
)


def configure_utf8_console():
    """Use UTF-8 end-to-end without assuming a particular terminal host."""
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass

    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except Exception:
            pass


configure_utf8_console()


def get_repo_root() -> Path:
    p = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=PROJECT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if p.returncode == 0 and p.stdout.strip():
        return Path(p.stdout.strip()).resolve()
    return PROJECT.resolve()


def get_runtime_dir(repo_root: Path | None = None) -> Path:
    """
    Returns the user-local, persistent runtime directory for the repository.
    Deterministic per-repository, located outside the Git worktree.
    Can be overridden by environment variable AIOS_RUNTIME_DIR.
    """
    override = os.environ.get("AIOS_RUNTIME_DIR")
    if override:
        return Path(override).resolve()

    root = (repo_root or get_repo_root()).resolve()
    norm_path = str(root).replace("\\", "/").lower()
    repo_hash = hashlib.sha256(norm_path.encode("utf-8")).hexdigest()[:12]
    repo_name = re.sub(r"[^\w\-\.]", "_", root.name) or "repo"

    base_dir = os.environ.get("AIOS_HOME")
    if base_dir:
        runtime_base = Path(base_dir).resolve()
    elif os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            runtime_base = Path(local_app_data) / "aios-bridge"
        else:
            runtime_base = Path.home() / ".aios-bridge"
    else:
        xdg_data = os.environ.get("XDG_DATA_HOME")
        if xdg_data:
            runtime_base = Path(xdg_data) / "aios-bridge"
        else:
            runtime_base = Path.home() / ".aios-bridge"

    return runtime_base / f"{repo_name}-{repo_hash}"


def get_runtime_paths(repo_root: Path | None = None):
    rdir = get_runtime_dir(repo_root)
    return {
        "root": rdir,
        "config": rdir / "config.json",
        "seen": rdir / "seen.json",
        "inbox": rdir / "inbox",
        "auth": rdir / "auth",
        "state": rdir / "state" / "CURRENT_STATE.json",
        "artifacts": rdir / "artifacts",
        "history": rdir / "history",
        "leases": rdir / "leases",
    }


def get_artifact_path(path: str, repo_root: Path | None = None) -> Path:
    """Returns external runtime storage path for synchronized control artifacts."""
    clean_path = path.lstrip("/\\")
    return get_runtime_paths(repo_root)["artifacts"] / clean_path


def get_workspace_id(repo_root: Path | None = None) -> str:
    """Returns exact deterministic 64-hex SHA-256 fingerprint for the current workspace root (C5)."""
    root = (repo_root or get_repo_root()).resolve()
    norm_path = str(root).replace("\\", "/").lower()
    return hashlib.sha256(norm_path.encode("utf-8")).hexdigest()


def build_execution_fingerprint(
    *,
    task_id: str,
    workspace_id: str,
    executor_id: str,
    operation: str,
    target_branch: str,
    authorized_artifact_path: str,
    authorized_artifact_blob_sha: str,
) -> str:
    """Deterministic activation fingerprint binding task, workspace, actor, operation, and artifacts (C6 / AIP-6)."""
    payload = {
        "authorized_artifact_blob_sha": authorized_artifact_blob_sha,
        "authorized_artifact_path": authorized_artifact_path,
        "executor_id": executor_id,
        "operation": operation.upper(),
        "target_branch": target_branch,
        "task_id": task_id,
        "workspace_id": workspace_id,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_executor_lease_candidate(
    *,
    task_id: str,
    workspace_id: str,
    operation: ExecutionOperation,
    target_branch: str,
    authorized_artifact_path: str,
    authorized_artifact_blob_sha: str,
    executor_id: str = "antigravity",
    lease_id: str | None = None,
) -> ExecutorLease:
    """Builds a canonical ExecutorLease candidate for task activation (AIP-6)."""
    if not lease_id:
        random_suffix = secrets.token_hex(6)
        lease_id = f"lease-{task_id.lower()}-{random_suffix}"
    exec_fp = build_execution_fingerprint(
        task_id=task_id,
        workspace_id=workspace_id,
        executor_id=executor_id,
        operation=operation.value,
        target_branch=target_branch,
        authorized_artifact_path=authorized_artifact_path,
        authorized_artifact_blob_sha=authorized_artifact_blob_sha,
    )
    return ExecutorLease(
        schema_version="1",
        lease_id=lease_id,
        task_id=task_id,
        workspace_id=workspace_id,
        executor_id=executor_id,
        operation=operation,
        execution_fingerprint=exec_fp,
    )


def get_lease_store(repo_root: Path | None = None) -> AtomicExecutorLeaseStore:
    """Returns atomic lease store initialized for current repository runtime and workspace ID (AIP-3)."""
    paths = get_runtime_paths(repo_root)
    ws_id = get_workspace_id(repo_root)
    return AtomicExecutorLeaseStore(lease_root=paths["leases"], workspace_id=ws_id)


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def fail(msg: str, code: int = 1):
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(code)


def run(cmd, cwd=None, check=True, capture=True, **kwargs):
    kwargs.setdefault("encoding", "utf-8")
    kwargs.setdefault("errors", "replace")
    return subprocess.run(
        cmd,
        cwd=cwd or PROJECT,
        check=check,
        capture_output=capture,
        text=True,
        **kwargs,
    )


def git(*args, check=True):
    env = dict(os.environ)
    env["LANG"] = "C.UTF-8"
    env["LC_ALL"] = "C.UTF-8"
    p = subprocess.run(
        ["git", *args],
        cwd=PROJECT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    if check and p.returncode != 0:
        cmd_str = " ".join(args)
        stderr_msg = p.stderr.strip() or p.stdout.strip()
        fail(f"git {cmd_str} thất bại: {stderr_msg}")
    return p


def ensure_git():
    p = git("rev-parse", "--is-inside-work-tree", check=False)
    if p.returncode != 0:
        fail(f"Thư mục '{PROJECT}' không phải là một git repository.")


def ensure_dirs():
    paths = get_runtime_paths()
    for key in ("inbox", "auth", "artifacts", "history", "leases"):
        paths[key].mkdir(parents=True, exist_ok=True)
    paths["state"].parent.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default=None):
    if not path.exists():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    tmp.replace(path)


def load_config():
    cfg_file = get_runtime_paths()["config"]
    if not cfg_file.exists():
        fail(
            f"Chưa cấu hình bridge. File '{cfg_file}' không tồn tại. "
            "Chạy `python bridge.py setup --base-branch <branch>` trước."
        )
    return load_json(cfg_file)


def branch_exists_remote(remote: str, branch: str) -> bool:
    p = git(
        "ls-remote",
        "--heads",
        remote,
        f"refs/heads/{branch}",
        check=False,
    )
    return bool(p.stdout.strip())


def local_branch_exists(branch: str) -> bool:
    p = git("show-ref", "--verify", f"refs/heads/{branch}", check=False)
    return p.returncode == 0


def current_branch() -> str:
    p = git("branch", "--show-current")
    return p.stdout.strip()


def non_ai_dirty_paths() -> list[str]:
    p = git("status", "--porcelain")
    dirty = []
    for line in p.stdout.splitlines():
        if len(line) < 4:
            continue
        rel = line[3:].strip()
        if " -> " in rel:
            rel = rel.split(" -> ")[1].strip()
        # All control artifacts now live outside the repo worktree.
        # Any dirty worktree path is considered blocking.
        dirty.append(rel)
    return dirty


def is_worktree_clean() -> bool:
    return len(non_ai_dirty_paths()) == 0


def notify(title: str, message: str):
    print(f"\n{'='*72}\n[{title}] {message}\n{'='*72}")
    if os.name == "nt":
        script = (
            "[reflection.assembly]::loadwithpartialname('System.Windows.Forms') | Out-Null; "
            f"[System.Windows.Forms.MessageBox]::Show('{message}', '{title}', "
            "[System.Windows.Forms.MessageBoxButtons]::OK, "
            "[System.Windows.Forms.MessageBoxIcon]::Information)"
        )
        subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def notify_best_effort(title: str, message: str, windows_popup: bool = True):
    print(f"\n{'='*72}\n[{title}] {message}\n{'='*72} ")
    if not windows_popup or os.name != "nt":
        return
    try:
        clean_msg = message.replace("'", "''").replace('"', '`"')
        clean_title = title.replace("'", "''").replace('"', '`"')
        script = (
            "[reflection.assembly]::loadwithpartialname('System.Windows.Forms') | Out-Null; "
            f"[System.Windows.Forms.MessageBox]::Show('{clean_msg}', '{clean_title}', "
            "[System.Windows.Forms.MessageBoxButtons]::OK, "
            "[System.Windows.Forms.MessageBoxIcon]::Information)"
        )
        subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        print(f"[NOTIFY][WARN] Windows popup notification failed: {e}", file=sys.stderr)


def remote_ref(cfg):
    return f"refs/remotes/{cfg['remote']}/{cfg['control_branch']}"


def write_pending(kind: str, task_id: int, path: str, blob_sha: str):
    inbox = get_runtime_paths()["inbox"]
    inbox.mkdir(parents=True, exist_ok=True)
    filename = f"{kind}-TASK-{task_id:03d}.{blob_sha[:10]}.json"
    target = inbox / filename
    data = {
        "kind": kind,
        "task_id": f"TASK-{task_id:03d}",
        "path": path,
        "blob_sha": blob_sha,
        "detected_at": now(),
        "approval": "PENDING",
    }
    save_json(target, data)
    return target


def clear_pending_events(kind: str, task_id: int):
    """Removes any prior pending events for a specific kind and task_id."""
    inbox = get_runtime_paths()["inbox"]
    if not inbox.exists():
        return
    for f in inbox.glob("*.json"):
        data = load_json(f, {})
        raw_tid = str(data.get("task_id", ""))
        eid = parse_task_id(raw_tid)
        if eid == task_id and data.get("kind") == kind.upper():
            try:
                f.unlink()
            except OSError:
                pass


def clear_pending_reviews(task_id: int):
    clear_pending_events("REVIEW", task_id)


def parse_task_id(path: str) -> int | None:
    m = re.search(r"(?:TASK|REVIEW)-(\d+)", path)
    return int(m.group(1)) if m else None


def parse_review_status(content: str) -> str | None:
    """
    Parses review status from review markdown content.
    Supports formats:
      ## Status
      CHANGES_REQUIRED
      or
      ## Status: APPROVED
      or
      STATUS: APPROVED
    """
    m = re.search(
        r"^#{1,3}\s*Status\s*$\s*\n\s*([A-Za-z0-9_]+)",
        content,
        re.MULTILINE | re.IGNORECASE,
    )
    if m:
        return m.group(1).upper()

    m = re.search(
        r"^#{1,3}\s*Status\s*:\s*([A-Za-z0-9_]+)",
        content,
        re.MULTILINE | re.IGNORECASE,
    )
    if m:
        return m.group(1).upper()

    m = re.search(
        r"^\s*STATUS\s*:\s*([A-Za-z0-9_]+)",
        content,
        re.MULTILINE | re.IGNORECASE,
    )
    if m:
        return m.group(1).upper()

    return None


def update_state(task_id: int, status: str, next_step: str | None = None):
    state_file = get_runtime_paths()["state"]
    state = load_json(
        state_file,
        {
            "phase": "unset",
            "active_task": None,
            "status": "NOT_STARTED",
            "last_review": None,
            "next_step": None,
        },
    )
    state["active_task"] = f"TASK-{task_id:03d}"
    state["status"] = status
    if next_step is not None:
        state["next_step"] = next_step
    if status in ("CHANGES_REQUIRED", "APPROVED", "REVIEW_RECEIVED"):
        state["last_review"] = f"REVIEW-{task_id:03d}"
    save_json(state_file, state)


# ---------------------------------------------------------------------------
# Authorization Storage & Verification (v0.4.0)
# ---------------------------------------------------------------------------


def get_auth_path(task_id: int) -> Path:
    return get_runtime_paths()["auth"] / f"AUTH-TASK-{task_id:03d}.json"


def load_authorization(task_id: int) -> dict | None:
    f = get_auth_path(task_id)
    if not f.exists():
        return None
    return load_json(f, None)


def save_authorization(task_id: int, data: dict):
    f = get_auth_path(task_id)
    save_json(f, data)


def get_active_authorization(task_id: int, action: str | None = None) -> dict | None:
    auth = load_authorization(task_id)
    if not auth:
        return None
    if auth.get("status") != "ACTIVE":
        return None
    if action and auth.get("action", "").upper() != action.upper():
        return None
    return auth


# ---------------------------------------------------------------------------
# Core Git & Control Branch Operations
# ---------------------------------------------------------------------------


def fetch_control(cfg):
    git("fetch", cfg["remote"], cfg["control_branch"], "--quiet")
    git(
        "fetch",
        cfg["remote"],
        f"+refs/heads/{cfg['control_branch']}:refs/remotes/{cfg['remote']}/{cfg['control_branch']}",
        "--quiet",
    )


def list_remote_inbound(cfg):
    ref = remote_ref(cfg)
    p = git("ls-tree", "-r", ref, "--", ".ai")
    items = []
    for line in p.stdout.splitlines():
        if "\t" not in line:
            continue
        meta, path = line.split("\t", 1)
        parts = meta.split()
        if len(parts) < 3:
            continue
        blob_sha = parts[2]
        if any(path.startswith(prefix) for prefix in INBOUND_PREFIXES):
            items.append((path, blob_sha))
    return items


def get_remote_blob_sha(cfg, path: str) -> str | None:
    ref = remote_ref(cfg)
    clean_path = path.lstrip("/\\")
    p = git("ls-tree", ref, "--", clean_path, check=False)
    if p.returncode != 0 or not p.stdout.strip():
        return None
    for line in p.stdout.splitlines():
        if "\t" in line:
            meta, pth = line.split("\t", 1)
            parts = meta.split()
            if len(parts) >= 3 and pth == clean_path:
                return parts[2]
    return None


def read_remote_file(cfg, path: str) -> str:
    ref = remote_ref(cfg)
    p = git("show", f"{ref}:{path}")
    return p.stdout


def archive_local(dest: Path, task_id: int):
    if not dest.exists():
        return
    history_dir = get_runtime_paths()["history"] / f"TASK-{task_id:03d}"
    history_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = history_dir / f"{dest.stem}_{ts}{dest.suffix}"
    shutil.copy2(dest, target)


# ---------------------------------------------------------------------------
# Safe Local-Main Reconciliation & Task-Branch Preparation (v0.4.0)
# ---------------------------------------------------------------------------


def reconcile_local_main(cfg) -> str:
    """
    Safely reconciles local base_branch with remote base_branch before starting a new RUN.
    - Fails closed on dirty worktree.
    - Fast-forwards local main if strictly behind remote.
    - Fails closed on diverged / ahead local main.
    - Never uses reset --hard or destructive checkout.
    - Returns canonical base_main_sha.
    """
    dirty = non_ai_dirty_paths()
    if dirty:
        fail(
            "Worktree có thay đổi chưa commit; không thể tự động reconcile main:\n  "
            + "\n  ".join(dirty)
        )

    remote = cfg["remote"]
    base = cfg["base_branch"]
    git("fetch", remote, "--prune", check=False)

    remote_base_ref = f"refs/remotes/{remote}/{base}"
    p_remote = git("rev-parse", remote_base_ref, check=False)
    if p_remote.returncode != 0 or not p_remote.stdout.strip():
        # If remote tracking ref not found, check if local base exists
        p_local = git("rev-parse", f"refs/heads/{base}", check=False)
        if p_local.returncode == 0:
            return p_local.stdout.strip()
        fail(f"Không tìm thấy remote branch '{remote}/{base}'.")
    remote_sha = p_remote.stdout.strip()

    local_base_ref = f"refs/heads/{base}"
    p_local = git("rev-parse", local_base_ref, check=False)
    if p_local.returncode != 0 or not p_local.stdout.strip():
        # Local base branch doesn't exist yet; create it tracking remote
        git("branch", base, remote_base_ref)
        return remote_sha

    local_sha = p_local.stdout.strip()
    if local_sha == remote_sha:
        return remote_sha

    # Check if local is an ancestor of remote (strictly behind)
    p_ancestor = git("merge-base", "--is-ancestor", local_base_ref, remote_base_ref, check=False)
    if p_ancestor.returncode == 0:
        # Local main is strictly behind remote main; fast-forward safely
        if current_branch() == base:
            git("merge", "--ff-only", remote_base_ref)
        else:
            # Fast forward the local branch ref without switching
            git("fetch", ".", f"{remote_base_ref}:{local_base_ref}")
        print(f"[RECONCILE] Fast-forwarded local '{base}' to '{remote}/{base}' ({remote_sha[:10]})")
        return remote_sha

    # Check if remote is ancestor of local (local is ahead)
    p_ahead = git("merge-base", "--is-ancestor", remote_base_ref, local_base_ref, check=False)
    if p_ahead.returncode == 0:
        fail(
            f"Local branch '{base}' đang ahead so với '{remote}/{base}'. "
            "Cần push hoặc đối soát thủ công; bridge không tự ghi đè."
        )

    # Branches have diverged
    fail(
        f"Local branch '{base}' đã bị DIVERGED so với '{remote}/{base}'. "
        "Cần xử lý merge/rebase thủ công; bridge không tự động sửa."
    )


def sync_existing_task_branch(remote: str, branch: str):
    """
    Classifies relation between local task branch and remote task branch:
    - local == remote: OK, continue
    - local strictly behind remote: fast-forward merge and verify
    - local ahead of remote: fail closed
    - local/remote diverged: fail closed
    """
    remote_branch_ref = f"refs/remotes/{remote}/{branch}"
    local_branch_ref = f"refs/heads/{branch}"

    p_remote = git("rev-parse", remote_branch_ref, check=False)
    if p_remote.returncode != 0 or not p_remote.stdout.strip():
        # Remote task branch does not exist yet; local only is valid
        return

    remote_sha = p_remote.stdout.strip()
    p_local = git("rev-parse", local_branch_ref, check=False)
    if p_local.returncode != 0 or not p_local.stdout.strip():
        return

    local_sha = p_local.stdout.strip()
    if local_sha == remote_sha:
        return

    # Check if local is an ancestor of remote (strictly behind)
    p_ancestor = git("merge-base", "--is-ancestor", local_branch_ref, remote_branch_ref, check=False)
    if p_ancestor.returncode == 0:
        if current_branch() == branch:
            git("merge", "--ff-only", remote_branch_ref)
        else:
            git("fetch", ".", f"{remote_branch_ref}:{local_branch_ref}")
        print(f"[BRANCH] Fast-forwarded task branch '{branch}' to '{remote}/{branch}' ({remote_sha[:10]})")
        return

    # Check if remote is ancestor of local (local is ahead)
    p_ahead = git("merge-base", "--is-ancestor", remote_branch_ref, local_branch_ref, check=False)
    if p_ahead.returncode == 0:
        fail(
            f"Task branch '{branch}' ở local đang AHEAD so với '{remote}/{branch}'. "
            "Không thể tự động resume an toàn; cần push hoặc đối soát commit thủ công."
        )

    # Branches have diverged
    fail(
        f"Task branch '{branch}' ở local đã bị DIVERGED so với '{remote}/{branch}'. "
        "Không thể tự động resume an toàn; cần đối soát hoặc rebase/merge thủ công."
    )


def prepare_task_branch(cfg, task_id: int, action: str) -> str:
    """
    Safely prepares and switches to the task branch.
    For RUN: Creates from synchronized canonical main or safely resumes.
    For FIX: Requires existing branch, fetches remote, and resumes without rebase.
    Fails closed on local-ahead or diverged state when remote branch exists.
    """
    dirty = non_ai_dirty_paths()
    if dirty:
        fail(
            "Worktree có thay đổi chưa commit; không thể switch task branch:\n  "
            + "\n  ".join(dirty)
        )

    remote = cfg["remote"]
    branch = f"{cfg['task_branch_prefix']}{task_id:03d}"
    base = cfg["base_branch"]
    git("fetch", remote, "--prune", check=False)

    if action.upper() == "RUN":
        if current_branch() == branch:
            sync_existing_task_branch(remote, branch)
            return branch

        if local_branch_exists(branch):
            sync_existing_task_branch(remote, branch)
            git("checkout", branch)
            return branch

        if branch_exists_remote(remote, branch):
            git("checkout", "-b", branch, "--track", f"{remote}/{branch}")
            return branch

        # Create new branch from synchronized canonical base
        git("checkout", "-b", branch, f"refs/heads/{base}")
        print(f"[BRANCH] Tạo task branch '{branch}' từ '{base}'")
        return branch

    elif action.upper() == "FIX":
        if current_branch() == branch:
            sync_existing_task_branch(remote, branch)
            return branch

        if local_branch_exists(branch):
            sync_existing_task_branch(remote, branch)
            git("checkout", branch)
            return branch

        if branch_exists_remote(remote, branch):
            git("checkout", "-b", branch, "--track", f"{remote}/{branch}")
            return branch

        fail(
            f"Không thể FIX: Không tìm thấy task branch '{branch}' ở local hoặc '{remote}'."
        )

    else:
        fail(f"Hành động không hợp lệ: {action}")


# ---------------------------------------------------------------------------
# Zero-Touch Handoff Command (v0.4.0)
# ---------------------------------------------------------------------------


def cmd_handoff(args):
    ensure_git()
    ensure_dirs()
    cfg = load_config()
    task_id = args.task_id
    action = args.action.upper()

    fetch_control(cfg)
    paths = get_runtime_paths()

    if action == "RUN":
        artifact_rel = f".ai/tasks/TASK-{task_id:03d}.md"
        blob_sha = get_remote_blob_sha(cfg, artifact_rel)
        if not blob_sha:
            fail(
                f"Không tìm thấy task artifact '{artifact_rel}' trên control branch '{cfg['control_branch']}'."
            )

        content = read_remote_file(cfg, artifact_rel)
        if not content.strip():
            fail(f"Task artifact '{artifact_rel}' bị rỗng.")

        task_ident = f"TASK-{task_id:03d}"
        if not re.search(rf"\b{re.escape(task_ident)}\b", content, re.IGNORECASE):
            fail(
                f"Task artifact '{artifact_rel}' bị malformed (không tìm thấy định danh {task_ident})."
            )

        dest = get_artifact_path(artifact_rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")

        seen = load_json(paths["seen"], {})
        seen[artifact_rel] = blob_sha
        save_json(paths["seen"], seen)

        clear_pending_events("TASK", task_id)

        base_main_sha = reconcile_local_main(cfg)
        branch = prepare_task_branch(cfg, task_id, "RUN")

        task_id_str = f"TASK-{task_id:03d}"
        ws_id = get_workspace_id()
        lease_candidate = build_executor_lease_candidate(
            task_id=task_id_str,
            workspace_id=ws_id,
            operation=ExecutionOperation.RUN,
            target_branch=branch,
            authorized_artifact_path=artifact_rel,
            authorized_artifact_blob_sha=blob_sha,
            executor_id="antigravity",
        )
        store = get_lease_store()
        try:
            acquired_lease = store.acquire(lease_candidate)
        except Exception as e:
            fail(f"Chiếm executor lease thất bại cho {task_id_str}: {e}")

        auth_record = {
            "task_id": task_id_str,
            "action": "RUN",
            "kind": "TASK",
            "artifact_path": artifact_rel,
            "artifact_blob_sha": blob_sha,
            "approved_at": now(),
            "branch": branch,
            "status": "ACTIVE",
            "base_main_sha": base_main_sha,
            "executor_id": acquired_lease.executor_id,
            "lease_id": acquired_lease.lease_id,
            "lease_fingerprint": acquired_lease.fingerprint(),
            "workspace_id": acquired_lease.workspace_id,
            "execution_fingerprint": acquired_lease.execution_fingerprint,
        }
        try:
            save_authorization(task_id, auth_record)
        except Exception as e:
            try:
                store.release(acquired_lease)
            except Exception:
                pass
            fail(f"Lưu authorization thất bại sau khi acquire lease: {e}")

        update_state(
            task_id,
            "IN_PROGRESS",
            f"TASK-{task_id:03d} authorized for execution by Antigravity",
        )

    elif action == "FIX":
        artifact_rel = f".ai/reviews/REVIEW-{task_id:03d}.md"
        blob_sha = get_remote_blob_sha(cfg, artifact_rel)
        if not blob_sha:
            fail(
                f"Không tìm thấy review artifact '{artifact_rel}' trên control branch '{cfg['control_branch']}'."
            )

        content = read_remote_file(cfg, artifact_rel)
        status = parse_review_status(content)
        if status != "CHANGES_REQUIRED":
            if status == "APPROVED":
                fail(
                    f"REVIEW-{task_id:03d} đã APPROVED. Không cần sửa mã nguồn."
                )
            fail(
                f"REVIEW-{task_id:03d} có trạng thái '{status or 'UNSPECIFIED'}', không phải CHANGES_REQUIRED. Không thể FIX."
            )

        dest = get_artifact_path(artifact_rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")

        seen = load_json(paths["seen"], {})
        seen[artifact_rel] = blob_sha
        save_json(paths["seen"], seen)

        clear_pending_events("REVIEW", task_id)

        branch = prepare_task_branch(cfg, task_id, "FIX")

        task_id_str = f"TASK-{task_id:03d}"
        ws_id = get_workspace_id()
        lease_candidate = build_executor_lease_candidate(
            task_id=task_id_str,
            workspace_id=ws_id,
            operation=ExecutionOperation.FIX,
            target_branch=branch,
            authorized_artifact_path=artifact_rel,
            authorized_artifact_blob_sha=blob_sha,
            executor_id="antigravity",
        )
        store = get_lease_store()
        try:
            acquired_lease = store.acquire(lease_candidate)
        except Exception as e:
            fail(f"Chiếm executor lease thất bại cho {task_id_str}: {e}")

        auth_record = {
            "task_id": task_id_str,
            "action": "FIX",
            "kind": "REVIEW",
            "artifact_path": artifact_rel,
            "artifact_blob_sha": blob_sha,
            "approved_at": now(),
            "branch": branch,
            "status": "ACTIVE",
            "executor_id": acquired_lease.executor_id,
            "lease_id": acquired_lease.lease_id,
            "lease_fingerprint": acquired_lease.fingerprint(),
            "workspace_id": acquired_lease.workspace_id,
            "execution_fingerprint": acquired_lease.execution_fingerprint,
        }
        try:
            save_authorization(task_id, auth_record)
        except Exception as e:
            try:
                store.release(acquired_lease)
            except Exception:
                pass
            fail(f"Lưu authorization thất bại sau khi acquire lease: {e}")

        update_state(
            task_id,
            "CHANGES_REQUIRED",
            f"FIX TASK-{task_id:03d} authorized for execution by Antigravity",
        )

    else:
        fail(f"Hành động không hợp lệ: {action}")

    # Output context JSON for Antigravity worker
    cmd_context(args)


# ---------------------------------------------------------------------------
# Watcher & Sync (v0.4.0)
# ---------------------------------------------------------------------------


def sync_once(verbose=True):
    ensure_git()
    ensure_dirs()
    cfg = load_config()
    fetch_control(cfg)

    paths = get_runtime_paths()
    seen = load_json(paths["seen"], {})
    changed = []
    for path, blob_sha in list_remote_inbound(cfg):
        if seen.get(path) == blob_sha:
            continue

        content = read_remote_file(cfg, path)
        dest = get_artifact_path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        task_id = parse_task_id(path)
        if (
            dest.exists()
            and dest.read_text(encoding="utf-8", errors="replace") != content
        ):
            if task_id and ("/results/" in path or "/reviews/" in path):
                archive_local(dest, task_id)
            elif task_id and "/reviews/" in path:
                archive_local(dest, task_id)

        dest.write_text(content, encoding="utf-8")
        notification = None

        if task_id and path.startswith(".ai/tasks/"):
            clear_pending_events("TASK", task_id)
            write_pending("TASK", task_id, path, blob_sha)
            update_state(
                task_id,
                "NOT_STARTED",
                "Approve TASK before Antigravity execution",
            )
            notification = (
                "AIOS: TASK mới",
                f"TASK-{task_id:03d} đã nhận qua bridge. "
                f"Dùng `/aios-worker RUN TASK-{task_id:03d}` để thực hiện.",
                cfg.get("windows_popup", True),
            )
        elif task_id and path.startswith(".ai/reviews/"):
            review_status = parse_review_status(content)
            if review_status == "CHANGES_REQUIRED":
                clear_pending_events("REVIEW", task_id)
                write_pending("REVIEW", task_id, path, blob_sha)
                update_state(
                    task_id,
                    "CHANGES_REQUIRED",
                    "Approve review fix before execution",
                )
                notification = (
                    "AIOS: REVIEW mới",
                    f"REVIEW-{task_id:03d} yêu cầu sửa đổi (CHANGES_REQUIRED). "
                    f"Dùng `/aios-worker FIX TASK-{task_id:03d}` để sửa.",
                    cfg.get("windows_popup", True),
                )
            elif review_status == "APPROVED":
                clear_pending_events("REVIEW", task_id)
                update_state(
                    task_id,
                    "APPROVED",
                    f"REVIEW-{task_id:03d} approved; ready for next task or merge",
                )
                notification = (
                    "AIOS: REVIEW đã duyệt",
                    f"REVIEW-{task_id:03d} đã APPROVED. Không cần sửa.",
                    cfg.get("windows_popup", True),
                )
            else:
                clear_pending_events("REVIEW", task_id)
                update_state(
                    task_id,
                    "REVIEW_RECEIVED",
                    f"REVIEW-{task_id:03d} received (status: {review_status or 'UNSPECIFIED'})",
                )
                notification = (
                    "AIOS: REVIEW cập nhật",
                    f"REVIEW-{task_id:03d} đã cập nhật (status: {review_status or 'UNSPECIFIED'}).",
                    cfg.get("windows_popup", True),
                )

        seen[path] = blob_sha
        save_json(paths["seen"], seen)
        changed.append(path)

        if notification is not None:
            notify_best_effort(*notification)

    save_json(paths["seen"], seen)
    if verbose:
        if changed:
            print("[SYNC] Updated:")
            for p in changed:
                print("  -", p)
        else:
            print("[SYNC] No new inbound artifacts.")
    return changed


def cmd_sync(args):
    sync_once(verbose=True)


def cmd_watch(args):
    cfg = load_config()
    seconds = args.poll_seconds or int(cfg.get("poll_seconds", 20))
    print(
        f"[WATCH] control={cfg['control_branch']} remote={cfg['remote']} every {seconds}s"
    )
    print("[WATCH] Ctrl+C để dừng. Bridge chỉ đồng bộ/báo, không tự code.")
    try:
        while True:
            try:
                sync_once(verbose=False)
            except SystemExit as e:
                print(
                    f"[WATCH][WARN] sync failed (exit={e.code}); retrying in {seconds}s",
                    file=sys.stderr,
                )
            except Exception as e:
                print(f"[WATCH][WARN] {e}; retrying in {seconds}s", file=sys.stderr)
            time.sleep(seconds)
    except KeyboardInterrupt:
        print("\n[WATCH] Stopped.")


def pending_events():
    inbox = get_runtime_paths()["inbox"]
    events = []
    if not inbox.exists():
        return events
    for f in sorted(inbox.glob("*.json")):
        data = load_json(f, {})
        if data.get("approval") == "PENDING":
            data["_file"] = str(f)
            events.append(data)
    return events


def cmd_pending(args):
    events = pending_events()
    if not events:
        print("(không có TASK/REVIEW đang chờ approval)")
        return
    for e in events:
        print(
            f"{e.get('kind'):7} {e.get('task_id'):10} {e.get('detected_at')}  {e.get('path')}"
        )


def find_latest_event(task_id: int, kind: str | None):
    candidates = []
    for e in pending_events():
        eid = parse_task_id(e.get("task_id", "0"))
        if eid != task_id:
            continue
        if kind and e.get("kind", "").lower() != kind.lower():
            continue
        candidates.append(e)
    if not candidates:
        return None
    candidates.sort(key=lambda x: x.get("detected_at", ""))
    return candidates[-1]


def checkout_task_branch(cfg, task_id: int):
    dirty = non_ai_dirty_paths()
    if dirty:
        fail(
            "Worktree có thay đổi chưa commit; không tự switch branch:\n  "
            + "\n  ".join(dirty)
        )

    remote = cfg["remote"]
    branch = f"{cfg['task_branch_prefix']}{task_id:03d}"
    base = cfg["base_branch"]
    git("fetch", remote, "--prune")

    if current_branch() == branch:
        return branch

    if local_branch_exists(branch):
        git("checkout", branch)
    elif branch_exists_remote(remote, branch):
        git("checkout", "-b", branch, "--track", f"{remote}/{branch}")
    else:
        base_ref = f"{remote}/{base}" if branch_exists_remote(remote, base) else base
        git("checkout", "-b", branch, base_ref)
    return branch


def cmd_approve(args):
    cfg = load_config()
    kind = args.kind.lower() if args.kind else None
    event = find_latest_event(args.task_id, kind)
    if not event:
        fail(f"Không có pending event phù hợp cho TASK-{args.task_id:03d}.")

    branch = checkout_task_branch(cfg, args.task_id)
    f = Path(event["_file"])
    data = load_json(f, {})
    orig_approval = data.get("approval", "PENDING")

    action = "FIX" if data.get("kind") == "REVIEW" else "RUN"
    task_id_str = f"TASK-{args.task_id:03d}"
    ws_id = get_workspace_id()
    op = ExecutionOperation.FIX if action == "FIX" else ExecutionOperation.RUN
    art_path = data.get("path", f".ai/tasks/TASK-{args.task_id:03d}.md")
    art_blob = data.get("blob_sha", "")

    lease_candidate = build_executor_lease_candidate(
        task_id=task_id_str,
        workspace_id=ws_id,
        operation=op,
        target_branch=branch,
        authorized_artifact_path=art_path,
        authorized_artifact_blob_sha=art_blob,
        executor_id="antigravity",
    )
    store = get_lease_store()
    try:
        acquired_lease = store.acquire(lease_candidate)
    except Exception as e:
        # Note: Event file remains PENDING and operational state is untouched so it remains retryable (R1-4)
        fail(f"Chiếm executor lease thất bại khi approve {task_id_str}: {e}")

    # Comprehensive post-acquire atomic activation unit (R2-1)
    try:
        data["approval"] = "APPROVED"
        data["approved_at"] = now()
        save_json(f, data)

        if data.get("kind") == "REVIEW":
            update_state(
                args.task_id,
                "CHANGES_REQUIRED",
                "Antigravity may apply REVIEW after explicit approval",
            )
        else:
            update_state(
                args.task_id,
                "IN_PROGRESS",
                "Antigravity may execute TASK after explicit approval",
            )

        auth = {
            "task_id": task_id_str,
            "action": action,
            "kind": data.get("kind", "TASK"),
            "artifact_path": art_path,
            "artifact_blob_sha": art_blob,
            "approved_at": now(),
            "branch": branch,
            "status": "ACTIVE",
            "executor_id": acquired_lease.executor_id,
            "lease_id": acquired_lease.lease_id,
            "lease_fingerprint": acquired_lease.fingerprint(),
            "workspace_id": acquired_lease.workspace_id,
            "execution_fingerprint": acquired_lease.execution_fingerprint,
        }
        save_authorization(args.task_id, auth)
    except Exception as e:
        # Full post-acquire rollback: release lease, restore inbox event to PENDING, restore state (R2-1)
        rollback_diagnostics: list[str] = []
        try:
            store.release(acquired_lease)
            rollback_diagnostics.append("lease_released: OK")
        except Exception as re:
            rollback_diagnostics.append(f"lease_release_failed: {re}")

        inbox_restored = False
        try:
            data["approval"] = orig_approval
            if "approved_at" in data:
                del data["approved_at"]
            save_json(f, data)
            inbox_restored = True
            rollback_diagnostics.append("inbox_restored: PENDING")
        except Exception as ie:
            rollback_diagnostics.append(f"inbox_restore_failed: {ie}")

        try:
            state_label = "PENDING_APPROVAL" if inbox_restored else "RECOVERY_REQUIRED"
            update_state(
                args.task_id,
                state_label,
                f"Approval failed during activation ({e}); recovery: {'; '.join(rollback_diagnostics)}",
            )
            rollback_diagnostics.append(f"state_updated: {state_label}")
        except Exception as se:
            rollback_diagnostics.append(f"state_restore_failed: {se}")

        diag_str = f" [Rollback diagnostics: {'; '.join(rollback_diagnostics)}]"
        fail(f"Kích hoạt approval thất bại sau khi chiếm lease: {e}{diag_str}")

    print(f"[APPROVED] {data.get('kind')} for TASK-{args.task_id:03d}")
    print(f"[BRANCH] {branch}")
    print("\nTrong Antigravity chạy:")
    print("  /aios-worker")
    print(f"và yêu cầu action: {action} TASK-{args.task_id:03d}")


def latest_approved(task_id: int):
    inbox = get_runtime_paths()["inbox"]
    approved = []
    if not inbox.exists():
        return None
    for f in inbox.glob("*.json"):
        d = load_json(f, {})
        try:
            eid = parse_task_id(d.get("task_id", "0"))
        except Exception:
            continue
        if eid == task_id and d.get("approval") == "APPROVED":
            d["_file"] = str(f)
            approved.append(d)
    approved.sort(key=lambda x: x.get("approved_at", ""))
    return approved[-1] if approved else None


def changed_files():
    p = git("status", "--porcelain")
    out = []
    for line in p.stdout.splitlines():
        if len(line) >= 4:
            out.append(line[3:].strip())
    return out


def cmd_context(args):
    cfg = load_config()
    task_id = args.task_id
    event = latest_approved(task_id)
    auth = load_authorization(task_id)
    paths = get_runtime_paths()

    task_artifact = get_artifact_path(f".ai/tasks/TASK-{task_id:03d}.md")
    review_artifact = get_artifact_path(f".ai/reviews/REVIEW-{task_id:03d}.md")
    project_context_artifact = get_artifact_path(".ai/context/PROJECT_CONTEXT.md")
    roadmap_artifact = get_artifact_path(".ai/context/ROADMAP.md")

    task_file = (
        task_artifact
        if task_artifact.exists()
        else (AI / "tasks" / f"TASK-{task_id:03d}.md")
    )
    review_file = (
        review_artifact
        if review_artifact.exists()
        else (AI / "reviews" / f"REVIEW-{task_id:03d}.md")
    )
    project_context = (
        project_context_artifact
        if project_context_artifact.exists()
        else (AI / "context" / "PROJECT_CONTEXT.md")
    )
    roadmap = (
        roadmap_artifact
        if roadmap_artifact.exists()
        else (AI / "context" / "ROADMAP.md")
    )

    active_lease_info = None
    try:
        store = get_lease_store()
        loaded = store.load_active(f"TASK-{task_id:03d}")
        if loaded:
            active_lease_info = {
                "lease_id": loaded.lease_id,
                "lease_fingerprint": loaded.fingerprint(),
                "executor_id": loaded.executor_id,
                "operation": loaded.operation.value,
                "workspace_id": loaded.workspace_id,
                "execution_fingerprint": loaded.execution_fingerprint,
            }
    except Exception:
        pass

    data = {
        "task_id": f"TASK-{task_id:03d}",
        "approved_event": event,
        "authorization": auth,
        "lease": active_lease_info,
        "current_branch": current_branch(),
        "expected_branch": f"{cfg['task_branch_prefix']}{task_id:03d}",
        "task_file": str(task_file),
        "review_file": str(review_file),
        "project_context": str(project_context),
        "roadmap": str(roadmap),
        "runtime_dir": str(paths["root"]),
        "state_file": str(paths["state"]),
    }
    print(json.dumps(data, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# Strengthened Publish Command (v0.4.0 / M5)
# ---------------------------------------------------------------------------


def cmd_publish(args):
    ensure_git()
    cfg = load_config()
    task_id = args.task_id
    expected = f"{cfg['task_branch_prefix']}{task_id:03d}"
    branch = current_branch()
    if branch != expected:
        fail(
            f"Publish chỉ được phép trên task branch '{expected}', hiện tại là '{branch}'."
        )

    auth = get_active_authorization(task_id)
    if not auth:
        fail(
            f"Không có ACTIVE authorization cho TASK-{task_id:03d}. "
            f"Cần chạy `/aios-worker RUN TASK-{task_id:03d}` hoặc `/aios-worker FIX TASK-{task_id:03d}` trước khi publish."
        )

    # Validate M5 lease binding fields in authorization (C20 / AIP-7)
    for required_lease_field in ["lease_id", "lease_fingerprint", "workspace_id", "execution_fingerprint"]:
        if not auth.get(required_lease_field):
            fail(f"ACTIVE authorization thiếu thông tin lease bắt buộc: '{required_lease_field}'.")

    # Reconstruct expected lease from ACTIVE authorization (AIP-7 / C20)
    try:
        expected_lease = ExecutorLease(
            schema_version="1",
            lease_id=auth["lease_id"],
            task_id=auth["task_id"],
            workspace_id=auth["workspace_id"],
            executor_id=auth.get("executor_id", "antigravity"),
            operation=ExecutionOperation(auth["action"]),
            execution_fingerprint=auth["execution_fingerprint"],
        )
    except Exception as e:
        fail(f"Tái cấu trúc expected lease từ authorization thất bại: {e}")

    if expected_lease.fingerprint() != auth["lease_fingerprint"]:
        fail("Lease fingerprint trong authorization không khớp với canonical lease.")

    # Require exact active lease before test execution or workspace mutation (AIP-9 / C20)
    store = get_lease_store()
    try:
        store.require_active(expected_lease)
    except Exception as e:
        fail(f"Xác thực active executor lease thất bại trước khi publish: {e}")

    if getattr(args, "action", None):
        req_action = args.action.upper()
        if auth["action"] != req_action:
            fail(
                f"Yêu cầu publish action '{req_action}' không khớp với ACTIVE authorization action '{auth['action']}'."
            )

    # Re-validate against current control branch
    fetch_control(cfg)
    current_blob = get_remote_blob_sha(cfg, auth["artifact_path"])
    if not current_blob or current_blob != auth["artifact_blob_sha"]:
        fail(
            f"Artifact '{auth['artifact_path']}' đã thay đổi trên control branch kể từ lúc handoff. "
            f"Cần chạy lại `/aios-worker {auth['action']} TASK-{task_id:03d}`."
        )

    if auth["action"] == "RUN":
        review_rel = f".ai/reviews/REVIEW-{task_id:03d}.md"
        review_blob = get_remote_blob_sha(cfg, review_rel)
        if review_blob:
            review_content = read_remote_file(cfg, review_rel)
            status = parse_review_status(review_content)
            if status == "CHANGES_REQUIRED":
                fail(
                    f"Đã có REVIEW-{task_id:03d} yêu cầu sửa đổi (CHANGES_REQUIRED) trên control branch. "
                    f"Không thể dùng RUN authorization để publish. Cần chạy `/aios-worker FIX TASK-{task_id:03d}`."
                )

    elif auth["action"] == "FIX":
        content = read_remote_file(cfg, auth["artifact_path"])
        status = parse_review_status(content)
        if status != "CHANGES_REQUIRED":
            fail(
                f"Review '{auth['artifact_path']}' hiện không ở trạng thái CHANGES_REQUIRED (status={status}). Không publish."
            )

    test_output = "(no test command supplied)"
    test_rc = 0
    if args.test:
        print(f"[TEST] {args.test}")
        p = run(args.test, check=False, capture=True, shell=True)
        test_rc = p.returncode
        test_output = (
            (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")
        ).strip()
        if len(test_output) > 30000:
            test_output = test_output[-30000:]
        if test_rc != 0:
            update_state(task_id, "CHANGES_REQUIRED", "Tests failed; do not publish")
            print(test_output)
            fail(
                f"Tests failed (exit={test_rc}). Không commit/push.",
                code=test_rc or 1,
            )

    result = AI / "results" / f"RESULT-{task_id:03d}.md"
    result.parent.mkdir(parents=True, exist_ok=True)
    archive_local(result, task_id)

    files = changed_files()
    diffstat = git("diff", "--stat", "HEAD").stdout.strip()
    summary = (
        args.summary
        or "Implementation completed by Antigravity; pending ChatGPT review."
    )

    action_label = auth.get("action", "RUN") if auth else "RUN"
    artifact_label = (
        f"{auth.get('artifact_path')} ({auth.get('artifact_blob_sha')[:10]})"
        if auth
        else "(legacy approval)"
    )
    base_main_label = auth.get("base_main_sha", "(n/a)") if auth else "(n/a)"

    result_content = (
        f"""# RESULT-{task_id:03d}

STATUS: READY_FOR_REVIEW

## Summary
{summary}

## Task Metadata
- Task: `TASK-{task_id:03d}`
- Action: `{action_label}`
- Authorized Artifact: `{artifact_label}`
- Base Main SHA: `{base_main_label}`
- Branch: `{branch}`

## Files Changed
"""
        + (
            "\n".join(f"- {x}" for x in files)
            if files
            else "- (none before result generation)"
        )
        + f"""

## Diff Stat
```text
{diffstat}
```

## Tests
Command: `{args.test or '(not supplied)'}`  
Exit code: {test_rc}

```text
{test_output}
```

## Risks / Notes
{args.notes or '(none supplied)'}

## Generated
{now()}
"""
    )
    result.write_text(result_content, encoding="utf-8")

    git("add", "-A")
    git(
        "reset",
        "--",
        ".ai/bridge",
        ".ai/inbox",
        ".ai/auth",
        ".ai/state/CURRENT_STATE.json",
        check=False,
    )

    staged = git("diff", "--cached", "--name-only").stdout.strip()
    if not staged:
        fail("Không có staged changes để commit.")

    msg = args.message or f"TASK-{task_id:03d}: implementation ready for review"
    git("commit", "-m", msg)
    sha = git("rev-parse", "HEAD").stdout.strip()
    git("push", "-u", cfg["remote"], branch)

    # Release exact lease after push success (C22 / AIP-10)
    try:
        store.release(expected_lease)
    except Exception as e:
        fail(f"Release lease thất bại sau khi push: {e}")

    if auth:
        auth["status"] = "CONSUMED"
        auth["published_sha"] = sha
        auth["published_at"] = now()
        save_authorization(task_id, auth)

    update_state(
        task_id,
        "IN_REVIEW",
        f"Published {sha}; ask ChatGPT to review TASK-{task_id:03d}",
    )

    print("\n[PUBLISHED]")
    print(f"Task:   TASK-{task_id:03d}")
    print(f"Branch: {branch}")
    print(f"SHA:    {sha}")
    print("\nTiếp theo trong ChatGPT chỉ cần nói:")
    print(f'  "Review TASK-{task_id:03d}"')


# ---------------------------------------------------------------------------
# Human Recovery & Lease Diagnostic Commands (C23)
# ---------------------------------------------------------------------------


def cmd_lease_status(args):
    """Read-only diagnostic command for active executor leases (C23)."""
    paths = get_runtime_paths()
    leases_dir = paths["leases"]
    store = get_lease_store()

    if getattr(args, "task_id", None) is not None:
        task_id_str = f"TASK-{args.task_id:03d}"
        active = None
        try:
            active = store.load_active(task_id_str)
        except Exception as e:
            print(f"[LEASE-STATUS] {task_id_str}: CORRUPT / ERROR ({e})")
            return

        if active is None:
            print(f"[LEASE-STATUS] {task_id_str}: (no active lease)")
        else:
            print(f"[LEASE-STATUS] {task_id_str}:")
            print(f"  lease_id:              {active.lease_id}")
            print(f"  executor_id:           {active.executor_id}")
            print(f"  operation:             {active.operation.value}")
            print(f"  workspace_id:          {active.workspace_id}")
            print(f"  lease_fingerprint:     {active.fingerprint()}")
            print(f"  execution_fingerprint: {active.execution_fingerprint}")
    else:
        if not leases_dir.exists():
            print("[LEASE-STATUS] (no lease records found)")
            return

        found = 0
        for task_dir in sorted(leases_dir.glob("TASK-*")):
            if not task_dir.is_dir():
                continue
            task_id_str = task_dir.name
            try:
                active = store.load_active(task_id_str)
                if active:
                    found += 1
                    print(
                        f"- {task_id_str}: lease_id={active.lease_id} executor={active.executor_id} op={active.operation.value}"
                    )
            except Exception as e:
                found += 1
                print(f"- {task_id_str}: CORRUPT / ERROR ({e})")

        if found == 0:
            print("[LEASE-STATUS] (no active leases)")


def cmd_lease_release(args):
    """Explicit confirmation-gated human recovery lease release (C23 / AIP-11)."""
    if not getattr(args, "confirm_stopped", False):
        fail(
            "lease-release yêu cầu cờ '--confirm-stopped' để xác nhận Executor đã dừng hoàn toàn."
        )

    task_id_str = f"TASK-{args.task_id:03d}"
    store = get_lease_store()

    try:
        active = store.load_active(task_id_str)
    except Exception as e:
        fail(f"Không thể đọc active lease cho {task_id_str}: {e}")

    if active is None:
        fail(f"Không tìm thấy active lease cho {task_id_str}.")

    if active.lease_id != args.lease_id:
        fail(
            f"lease_id '{args.lease_id}' không khớp với active lease_id '{active.lease_id}' của {task_id_str}."
        )

    # 1. Deactivate associated ACTIVE authorization before release (AIP-11)
    auth = load_authorization(args.task_id)
    if auth and auth.get("status") == "ACTIVE":
        auth["status"] = "CANCELLED"
        auth["cancelled_at"] = now()
        auth["cancellation_reason"] = f"Human recovery release with lease_id {args.lease_id}"
        save_authorization(args.task_id, auth)

    # 2. Compare-and-release exact lease
    try:
        store.release(active)
    except Exception as e:
        fail(f"Release lease thất bại cho {task_id_str}: {e}")

    print(f"[RELEASED] Đã giải phóng lease '{active.lease_id}' cho {task_id_str}.")


def cmd_setup(args):
    ensure_git()
    ensure_dirs()
    remote = args.remote
    base = args.base_branch
    control = args.control_branch

    if git("remote", "get-url", remote, check=False).returncode != 0:
        fail(f"Không tìm thấy git remote '{remote}'.")

    git("fetch", remote, "--prune")

    base_remote_exists = branch_exists_remote(remote, base)
    if not base_remote_exists and not local_branch_exists(base):
        fail(f"Không tìm thấy base branch '{base}' ở local hoặc {remote}.")

    if not branch_exists_remote(remote, control):
        source = (
            f"refs/remotes/{remote}/{base}"
            if base_remote_exists
            else f"refs/heads/{base}"
        )
        print(f"[SETUP] Tạo control branch '{control}' từ '{base}'...")
        git("push", remote, f"{source}:refs/heads/{control}")

    cfg = {
        "remote": remote,
        "base_branch": base,
        "control_branch": control,
        "task_branch_prefix": args.task_branch_prefix,
        "poll_seconds": args.poll_seconds,
        "windows_popup": not args.no_popup,
    }
    paths = get_runtime_paths()
    save_json(paths["config"], cfg)
    if not paths["seen"].exists():
        save_json(paths["seen"], {})

    print("[OK] Bridge configured in external runtime directory:")
    print(f"  {paths['root']}")
    print(json.dumps(cfg, ensure_ascii=False, indent=2))


def build_parser():
    p = argparse.ArgumentParser(
        description="AI Engineering OS Lite Bridge v0.4.0"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("setup", help="Configure GitHub control branch")
    s.add_argument("--base-branch", required=True)
    s.add_argument("--remote", default="origin")
    s.add_argument("--control-branch", default="ai-control")
    s.add_argument("--task-branch-prefix", default="ai/task-")
    s.add_argument("--poll-seconds", type=int, default=20)
    s.add_argument("--no-popup", action="store_true")
    s.set_defaults(func=cmd_setup)

    s = sub.add_parser(
        "handoff",
        help="Zero-touch handoff: fetch artifact, reconcile main, prepare task branch, and record authorization",
    )
    s.add_argument("task_id", type=int)
    s.add_argument(
        "--action", choices=["run", "fix", "RUN", "FIX"], default="run"
    )
    s.set_defaults(func=cmd_handoff)

    s = sub.add_parser(
        "sync", help="Fetch TASK/REVIEW/ADR/context from control branch"
    )
    s.set_defaults(func=cmd_sync)

    s = sub.add_parser(
        "watch", help="Continuously poll control branch; never executes code"
    )
    s.add_argument("--poll-seconds", type=int)
    s.set_defaults(func=cmd_watch)

    s = sub.add_parser("pending", help="List events waiting for human approval")
    s.set_defaults(func=cmd_pending)

    s = sub.add_parser(
        "approve", help="Approve a TASK or REVIEW and prepare task branch"
    )
    s.add_argument("task_id", type=int)
    s.add_argument("--kind", choices=["task", "review"])
    s.set_defaults(func=cmd_approve)

    s = sub.add_parser("context", help="Print execution context for Antigravity")
    s.add_argument("task_id", type=int)
    s.set_defaults(func=cmd_context)

    s = sub.add_parser(
        "publish", help="Run tests, create RESULT, commit and push task branch"
    )
    s.add_argument("task_id", type=int)
    s.add_argument("--action", choices=["run", "fix", "RUN", "FIX"])
    s.add_argument("--test")
    s.add_argument("--summary")
    s.add_argument("--notes")
    s.add_argument("--message")
    s.set_defaults(func=cmd_publish)

    s = sub.add_parser(
        "lease-status", help="Read-only diagnostic command for active executor leases"
    )
    s.add_argument("task_id", type=int, nargs="?", default=None)
    s.set_defaults(func=cmd_lease_status)

    s = sub.add_parser(
        "lease-release", help="Explicit human recovery lease release"
    )
    s.add_argument("task_id", type=int)
    s.add_argument("--lease-id", required=True)
    s.add_argument("--confirm-stopped", action="store_true")
    s.set_defaults(func=cmd_lease_release)

    return p


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
