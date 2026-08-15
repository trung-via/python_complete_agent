#!/usr/bin/env python3
"""
AI Engineering OS Lite Bridge v0.3.2
====================================

Transport layer between:
  ChatGPT <-> GitHub control branch <-> local repo <-> Antigravity

Safety model:
- New TASK/REVIEW is synchronized, never auto-executed.
- Explicit human approval is required before TASK/FIX execution.
- Implementation may commit/push only to an isolated task branch.
- This tool NEVER merges.
- Runtime/config/checkpoint/inbox/artifacts are stored OUTSIDE the Git worktree.
- Receiving TASK/REVIEW events NEVER dirties the active Git worktree.

Typical:
    python bridge.py setup --base-branch main
    python bridge.py watch

When notified:
    python bridge.py pending
    python bridge.py approve 1

Then in Antigravity:
    /aios-worker
    RUN TASK-001

At the end Antigravity can run:
    python bridge.py publish 1 --test "pytest -q" --summary "Implemented ..."
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

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
        "state": rdir / "state" / "CURRENT_STATE.json",
        "artifacts": rdir / "artifacts",
        "history": rdir / "history",
    }


def get_artifact_path(path: str, repo_root: Path | None = None) -> Path:
    """Returns external runtime storage path for synchronized control artifacts."""
    clean_path = path.lstrip("/\\")
    return get_runtime_paths(repo_root)["artifacts"] / clean_path


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def fail(msg: str, code: int = 1):
    print(f"[ERROR] {msg}", file=sys.stderr)
    raise SystemExit(code)


def run(cmd, check=True, capture=True, shell=False, env=None):
    p = subprocess.run(
        cmd,
        cwd=PROJECT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=capture,
        shell=shell,
        env=env,
    )
    if check and p.returncode != 0:
        stderr = (p.stderr or "").strip()
        stdout = (p.stdout or "").strip()
        fail(f"Command failed ({p.returncode}): {cmd}\n{stderr or stdout}")
    return p


def git(*args, check=True):
    env = os.environ.copy()
    env["LANG"] = "C.UTF-8"
    env["LC_ALL"] = "C.UTF-8"
    return run(["git", *args], check=check, env=env)


def ensure_git():
    p = git("rev-parse", "--show-toplevel", check=False)
    if p.returncode != 0:
        fail("Bridge phải chạy ở trong một Git repository.")
    root = Path(p.stdout.strip()).resolve()
    if root != PROJECT.resolve():
        fail(f"Hãy chạy bridge.py tại repo root: {root}")


def ensure_dirs():
    paths = get_runtime_paths()
    paths["root"].mkdir(parents=True, exist_ok=True)
    paths["inbox"].mkdir(parents=True, exist_ok=True)
    paths["state"].parent.mkdir(parents=True, exist_ok=True)
    paths["artifacts"].mkdir(parents=True, exist_ok=True)
    paths["history"].mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_config():
    cfg_file = get_runtime_paths()["config"]
    if not cfg_file.exists():
        fail("Bridge chưa setup. Chạy: python bridge.py setup --base-branch <branch>")
    return load_json(cfg_file, {})


def remote_ref(cfg) -> str:
    return f"refs/remotes/{cfg['remote']}/{cfg['control_branch']}"


def branch_exists_remote(remote: str, branch: str) -> bool:
    p = git("ls-remote", "--heads", remote, f"refs/heads/{branch}", check=False)
    return bool((p.stdout or "").strip())


def local_branch_exists(branch: str) -> bool:
    p = git("show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False)
    return p.returncode == 0


def current_branch() -> str:
    p = git("branch", "--show-current")
    return p.stdout.strip()


def non_ai_dirty_paths():
    p = git("status", "--porcelain")
    paths = []
    for line in p.stdout.splitlines():
        if not line.strip():
            continue
        raw = line[3:] if len(line) >= 4 else line
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1]
        raw = raw.strip('"')
        if not raw.startswith(".ai/"):
            paths.append(raw)
    return paths


def archive_local(path: Path, task_id: int):
    if not path.exists():
        return
    hdir = get_runtime_paths()["history"] / f"TASK-{task_id:03d}"
    hdir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target = hdir / f"{path.stem}.{ts}{path.suffix}"
    shutil.copy2(path, target)


def notify(title: str, message: str, windows_popup: bool = True):
    print("\n" + "=" * 72)
    print(f"[{title}] {message}")
    print("=" * 72 + "\a", flush=True)

    if os.name == "nt" and windows_popup:
        safe_title = title.replace("'", "''")
        safe_message = message.replace("'", "''")
        ps = (
            "Add-Type -AssemblyName PresentationFramework; "
            f"[System.Windows.MessageBox]::Show('{safe_message}','{safe_title}') | Out-Null"
        )
        try:
            subprocess.Popen(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
                cwd=PROJECT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass


def notify_best_effort(title: str, message: str, windows_popup: bool = True):
    try:
        notify(title, message, windows_popup)
    except Exception as e:
        try:
            print(f"[NOTIFY][WARN] {e}", file=sys.stderr)
        except Exception:
            pass


def write_pending(kind: str, task_id: int, path: str, blob_sha: str):
    inbox = get_runtime_paths()["inbox"]
    name = f"{kind.upper()}-{task_id:03d}.{blob_sha[:10]}.json"
    event = {
        "kind": kind.upper(),
        "task_id": f"TASK-{task_id:03d}",
        "path": path,
        "blob_sha": blob_sha,
        "detected_at": now(),
        "approval": "PENDING",
    }
    target = inbox / name
    save_json(target, event)
    return target


def parse_task_id(path: str):
    m = re.search(r"(?:TASK|REVIEW)-(\d+)\.md$", path)
    return int(m.group(1)) if m else None


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
    if status == "CHANGES_REQUIRED":
        state["last_review"] = f"REVIEW-{task_id:03d}"
    save_json(state_file, state)


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
    print("\nTiếp theo mở một terminal riêng và chạy:")
    print("  python bridge.py watch")


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


def read_remote_file(cfg, path: str):
    ref = remote_ref(cfg)
    p = git("show", f"{ref}:{path}")
    return p.stdout


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
        # Store synchronized inbound control artifacts in external runtime directory
        # so receiving events NEVER dirties the active Git worktree!
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
            write_pending("TASK", task_id, path, blob_sha)
            update_state(
                task_id,
                "NOT_STARTED",
                "Approve TASK before Antigravity execution",
            )
            notification = (
                "AIOS: TASK mới",
                f"TASK-{task_id:03d} đã nhận qua bridge. Chưa chạy. "
                f"Dùng `python bridge.py approve {task_id}` rồi `/aios-worker`.",
                cfg.get("windows_popup", True),
            )
        elif task_id and path.startswith(".ai/reviews/"):
            write_pending("REVIEW", task_id, path, blob_sha)
            update_state(
                task_id,
                "CHANGES_REQUIRED",
                "Approve review fix before execution",
            )
            notification = (
                "AIOS: REVIEW mới",
                f"REVIEW-{task_id:03d} đã nhận qua bridge. Chưa sửa. "
                f"Dùng `python bridge.py approve {task_id} --kind review` rồi `/aios-worker`.",
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
        eid = int(re.search(r"\d+", e.get("task_id", "0")).group())
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
            "Worktree có thay đổi ngoài .ai; không tự switch branch:\n  "
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
    data["approval"] = "APPROVED"
    data["approved_at"] = now()
    save_json(f, data)

    if data.get("kind") == "REVIEW":
        update_state(
            args.task_id,
            "CHANGES_REQUIRED",
            "Antigravity may apply REVIEW after explicit approval",
        )
        action = "FIX"
    else:
        update_state(
            args.task_id,
            "IN_PROGRESS",
            "Antigravity may execute TASK after explicit approval",
        )
        action = "RUN"

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
            eid = int(re.search(r"\d+", d.get("task_id", "0")).group())
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

    data = {
        "task_id": f"TASK-{task_id:03d}",
        "approved_event": event,
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

    if not latest_approved(task_id):
        fail("Không có approval event cho task này. Không publish.")

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

    result_content = (
        f"""# RESULT-{task_id:03d}

STATUS: READY_FOR_REVIEW

## Summary
{summary}

## Branch
{branch}

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


def build_parser():
    p = argparse.ArgumentParser(description="AI Engineering OS Lite Bridge v0.3.2")
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
    s.add_argument("--test")
    s.add_argument("--summary")
    s.add_argument("--notes")
    s.add_argument("--message")
    s.set_defaults(func=cmd_publish)

    return p


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
