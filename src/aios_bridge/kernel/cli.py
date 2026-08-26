"""AIOS Bridge Kernel v1 CLI Entry Point (ADR-068 / TASK-098)."""

import argparse
import json
import sys
from pathlib import Path

from src.aios_bridge.kernel.model import load_task_record, save_task_record, KernelStatus
from src.aios_bridge.kernel.authority import authorize_kernel_task
from src.aios_bridge.kernel.context import get_compact_context
from src.aios_bridge.kernel.publish import complete_kernel_task


def main():
    parser = argparse.ArgumentParser(prog="aios-kernel", description="AIOS Bridge Kernel v1 Control Surface")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = subparsers.add_parser("status", help="Get kernel status of TASK-N")
    p_status.add_argument("task_id", help="Task ID (e.g. TASK-098 or 98)")

    # authorize
    p_auth = subparsers.add_parser("authorize", help="Authorize TASK-N execution")
    p_auth.add_argument("task_id", help="Task ID (e.g. TASK-098 or 98)")
    p_auth.add_argument("--action", choices=["run", "fix", "RUN", "FIX"], required=True, help="Action type")
    p_auth.add_argument("--executor", choices=["codex", "antigravity"], required=True, help="Human-selected executor")

    # context
    p_ctx = subparsers.add_parser("context", help="Emit compact context for TASK-N")
    p_ctx.add_argument("task_id", help="Task ID (e.g. TASK-098 or 98)")

    # complete
    p_comp = subparsers.add_parser("complete", help="VERIFY and PUBLISH candidate for TASK-N")
    p_comp.add_argument("task_id", help="Task ID (e.g. TASK-098 or 98)")

    # cancel
    p_canc = subparsers.add_parser("cancel", help="Cancel authorization for TASK-N")
    p_canc.add_argument("task_id", help="Task ID (e.g. TASK-098 or 98)")

    args = parser.parse_args()

    norm_task_id = args.task_id.upper()
    if not norm_task_id.startswith("TASK-"):
        if norm_task_id.isdigit():
            norm_task_id = f"TASK-{int(norm_task_id):03d}"

    if args.command == "status":
        rec = load_task_record(norm_task_id)
        if not rec:
            print(json.dumps({"task_id": norm_task_id, "status": "NOT_FOUND"}, indent=2))
            sys.exit(1)
        print(json.dumps(rec.to_dict(), indent=2))

    elif args.command == "authorize":
        try:
            rec = authorize_kernel_task(norm_task_id, args.action, args.executor)
            ctx = get_compact_context(norm_task_id)
            print(json.dumps({"status": "AUTHORIZED", "record": rec.to_dict(), "context": ctx}, indent=2))
        except Exception as exc:
            print(f"[ERROR] Kernel authorize failed: {exc}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "context":
        try:
            ctx = get_compact_context(norm_task_id)
            print(json.dumps(ctx, indent=2))
        except Exception as exc:
            print(f"[ERROR] Kernel context failed: {exc}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "complete":
        try:
            res = complete_kernel_task(norm_task_id)
            if res.success:
                print(json.dumps({"status": "PUBLISHED", "published_head_sha": res.published_head_sha}, indent=2))
            else:
                print(json.dumps({"status": "BLOCKED", "error": res.error}, indent=2))
                sys.exit(1)
        except Exception as exc:
            print(f"[ERROR] Kernel complete failed: {exc}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "cancel":
        rec = load_task_record(norm_task_id)
        if not rec:
            print(f"[ERROR] Task '{norm_task_id}' not found", file=sys.stderr)
            sys.exit(1)
        rec.status = KernelStatus.CANCELLED.value
        save_task_record(rec)
        print(json.dumps({"status": "CANCELLED", "task_id": norm_task_id}, indent=2))


if __name__ == "__main__":
    main()
