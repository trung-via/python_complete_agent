#!/usr/bin/env python3
"""Unified AIOS Worker Control Surface Adapter (TASK-048 / ADR-037).

A thin operator adapter script that exposes the single AIOS worker semantic
protocol (RUN TASK-N, FIX TASK-N, STATUS TASK-N) to Codex and Antigravity UIs,
delegating all authorization, state, and execution to AIOS Bridge.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Sequence


def get_repo_root() -> Path:
    """Deterministically resolves the repository root from script layout."""
    # Expected: <repo>/.agents/skills/aios-worker/scripts/aios_worker.py
    script_path = Path(__file__).resolve()
    repo_root = script_path.parent.parent.parent.parent.parent
    bridge_py = repo_root / "bridge.py"
    if not bridge_py.is_file():
        raise FileNotFoundError(f"AIOS Bridge entrypoint not found at: {bridge_py}")
    return repo_root


# Ensure repository root is on sys.path for internal bridge imports
_repo_root = get_repo_root()
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from src.aios_bridge.worker_flow import (
    FixExecutionMode,
    WorkerAction,
    WorkerAdapter,
    WorkerFlowCoordinator,
    WorkerFlowResult,
    WorkerIntent,
    extract_fix_execution_mode,
)

TASK_PATTERN = re.compile(r"^TASK-(\d+)\Z")
ALLOWED_ACTIONS = {"RUN", "FIX", "STATUS"}
ALLOWED_ADAPTERS = {"codex", "antigravity"}


def parse_task_id(raw_task: str) -> tuple[str, int]:
    """Validates and parses the canonical TASK-N string into (task_id, task_num).

    Rejects non-canonical forms, missing digits, zero/negative task numbers,
    lowercase, prefixes, suffixes, or padding irregularities.
    """
    if not isinstance(raw_task, str):
        raise ValueError(f"Task ID must be a string, got: {type(raw_task)}")

    match = TASK_PATTERN.match(raw_task)
    if not match:
        raise ValueError(
            f"Invalid task ID format '{raw_task}'. Must be canonical 'TASK-<digits>' (e.g. TASK-048, TASK-48)."
        )

    digits_str = match.group(1)
    task_num = int(digits_str)
    if task_num <= 0:
        raise ValueError(f"Task number must be greater than zero, got: {task_num} in '{raw_task}'")

    return raw_task, task_num


def run_bridge_command(repo_root: Path, bridge_args: list[str]) -> int:
    """Executes a bridge command using sys.executable without shell composition."""
    bridge_py = repo_root / "bridge.py"
    cmd = [sys.executable, str(bridge_py)] + bridge_args
    proc = subprocess.run(
        cmd,
        cwd=repo_root,
        shell=False,
    )
    return proc.returncode


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="aios_worker.py",
        description="Unified AIOS Worker Control Surface Adapter (ADR-037 / ADR-061)",
        add_help=True,
    )
    parser.add_argument(
        "action",
        help="Action verb: RUN, FIX, or STATUS",
    )
    parser.add_argument(
        "task_id",
        help="Task ID in canonical form: TASK-<digits>",
    )
    parser.add_argument(
        "--adapter",
        required=True,
        choices=sorted(ALLOWED_ADAPTERS),
        help="UI Adapter: codex or antigravity",
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1

    # Validate action
    action = args.action.upper()
    if action not in ALLOWED_ACTIONS:
        print(
            f"[ERROR] Invalid action '{action}'. Allowed actions: {', '.join(sorted(ALLOWED_ACTIONS))}",
            file=sys.stderr,
        )
        return 1

    # Validate task_id
    try:
        task_id, task_num = parse_task_id(args.task_id)
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    # Resolve repo root
    try:
        repo_root = get_repo_root()
    except Exception as e:
        print(f"[ERROR] Failed to resolve repository root: {e}", file=sys.stderr)
        return 1

    # Dispatch via WorkerFlowCoordinator for single-command transactional flow
    intent = WorkerIntent(
        action=WorkerAction(action),
        task_id=task_id,
        task_num=task_num,
        adapter=WorkerAdapter(args.adapter),
    )
    coordinator = WorkerFlowCoordinator(repo_root=repo_root)
    result = coordinator.execute_transaction(intent)

    if result.returncode != 0:
        if result.failure_class:
            print(
                f"\nAIOS_WORKER_STATUS: {result.status}\n"
                f"TASK_ID: {task_id}\n"
                f"ACTION: {action}\n"
                f"EXECUTOR: {args.adapter}\n"
                f"FAILURE_CLASS: {result.failure_class}\n"
                f"NEXT_ACTION: {result.next_action}\n"
                f"GUIDANCE: {result.human_guidance}",
                file=sys.stderr,
            )
        elif result.message:
            print(f"[ERROR] {result.message}", file=sys.stderr)
        return result.returncode

    if result.status == "SYNCED":
        print(
            f"\nAIOS_WORKER_STATUS: SYNCED\n"
            f"TASK_ID: {task_id}\n"
            f"ADAPTER: {args.adapter}"
        )
    elif result.status == "AUTHORIZED":
        print(
            f"\nAIOS_WORKER_STATUS: AUTHORIZED\n"
            f"TASK_ID: {task_id}\n"
            f"ACTION: {action}\n"
            f"EXECUTOR: {args.adapter}\n"
            f"NEXT: continue in the authorized Antigravity worker session"
        )
    elif result.status == "PUBLISHED":
        print(
            f"\nAIOS_WORKER_STATUS: PUBLISHED\n"
            f"TASK_ID: {task_id}\n"
            f"ACTION: {action}\n"
            f"EXECUTOR: {args.adapter}\n"
            f"NEXT: Review {task_id} in ChatGPT"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
