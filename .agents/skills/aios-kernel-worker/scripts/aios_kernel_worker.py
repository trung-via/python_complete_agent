#!/usr/bin/env python3
"""AIOS Kernel Worker Control Adapter Script (ADR-068 / TASK-098)."""

import argparse
import json
import sys
from pathlib import Path

# Ensure src is importable
repo_root = Path(__file__).resolve().parents[3]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.aios_bridge.kernel.authority import authorize_kernel_task
from src.aios_bridge.kernel.context import get_compact_context
from src.aios_bridge.kernel.model import load_task_record, save_task_record, KernelStatus
from src.aios_bridge.kernel.publish import complete_kernel_task


def main():
    parser = argparse.ArgumentParser(prog="aios-kernel-worker", description="AIOS Kernel Worker Surface Adapter")
    parser.add_argument("action", choices=["RUN", "FIX", "STATUS", "COMPLETE", "CANCEL", "run", "fix", "status", "complete", "cancel"])
    parser.add_argument("task_id", help="Task ID (e.g. TASK-098 or 98)")
    parser.add_argument("--adapter", choices=["codex", "antigravity"], default="antigravity", help="Worker adapter surface")

    args = parser.parse_args()

    norm_task_id = args.task_id.upper()
    if not norm_task_id.startswith("TASK-"):
        if norm_task_id.isdigit():
            norm_task_id = f"TASK-{int(norm_task_id):03d}"

    action_upper = args.action.upper()

    if action_upper in ("RUN", "FIX"):
        try:
            rec = authorize_kernel_task(norm_task_id, action_upper, args.adapter, repo_root=repo_root)
            ctx = get_compact_context(norm_task_id, repo_root=repo_root)
            print(json.dumps({
                "status": "AUTHORIZED",
                "task_id": norm_task_id,
                "action": action_upper,
                "executor_id": args.adapter,
                "context": ctx,
            }, indent=2))
            print("\nAIOS_WORKER_STATUS: AUTHORIZED")
            print(f"TASK_ID: {norm_task_id}")
            print(f"ACTION: {action_upper}")
            print(f"EXECUTOR: {args.adapter}")
            print(f"NEXT: continue in the authorized {args.adapter} worker session")
        except Exception as exc:
            print(f"[ERROR] Kernel worker authorize failed: {exc}", file=sys.stderr)
            sys.exit(1)

    elif action_upper == "STATUS":
        rec = load_task_record(norm_task_id, repo_root=repo_root)
        if not rec:
            print(json.dumps({"task_id": norm_task_id, "status": "NOT_FOUND"}, indent=2))
            sys.exit(1)
        print(json.dumps(rec.to_dict(), indent=2))

    elif action_upper == "COMPLETE":
        try:
            res = complete_kernel_task(norm_task_id, repo_root=repo_root)
            if res.success:
                print(json.dumps({"status": "PUBLISHED", "published_head_sha": res.published_head_sha}, indent=2))
            else:
                print(json.dumps({"status": "BLOCKED", "error": res.error}, indent=2))
                sys.exit(1)
        except Exception as exc:
            print(f"[ERROR] Kernel worker complete failed: {exc}", file=sys.stderr)
            sys.exit(1)

    elif action_upper == "CANCEL":
        rec = load_task_record(norm_task_id, repo_root=repo_root)
        if rec:
            rec.status = KernelStatus.CANCELLED.value
            save_task_record(rec, repo_root=repo_root)
        print(json.dumps({"status": "CANCELLED", "task_id": norm_task_id}, indent=2))


if __name__ == "__main__":
    main()
