#!/usr/bin/env python3
"""Pinned, repository-owned bootstrap for self-hosted Phase-1 PRIMARY wakeup.

This script owns environment bootstrap and operator delegation only.
Durable dispatch identity, at-most-once semantics, RUN allocation,
synchronization, verification, Executor invocation, and reconciliation are
owned by the exact pinned ``aios_renew.operator wakeup`` implementation.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
from typing import Sequence

from aios_worker import (
    BootstrapError,
    WorkerSurfaceError,
    _emit_completed,
    ensure_runtime,
    get_repo_root,
    invoke_kernel,
    parse_task_id,
    runtime_layout,
)

DISPATCH_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
ALLOWED_EXECUTORS = ("antigravity", "codex")


def parse_dispatch_id(raw_dispatch_id: str) -> str:
    if not DISPATCH_ID_PATTERN.fullmatch(raw_dispatch_id):
        raise WorkerSurfaceError(
            f"invalid dispatch ID {raw_dispatch_id!r}; expected format '^[A-Za-z0-9][A-Za-z0-9_-]{{0,127}}$'"
        )
    return raw_dispatch_id


def wakeup_command(
    python: Path,
    *,
    dispatch_id: str,
    task_id: str,
    executor: str,
    repo: Path,
) -> tuple[str, ...]:
    """Build the sole canonical pinned PRIMARY wakeup delegation."""

    return (
        str(python),
        "-m",
        "aios_renew.operator",
        "wakeup",
        dispatch_id,
        task_id,
        "--executor",
        executor,
        "--repo",
        str(repo),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aios_phase1_wakeup.py")
    parser.add_argument("dispatch_id")
    parser.add_argument("task_id")
    parser.add_argument("--executor", required=True, choices=ALLOWED_EXECUTORS)
    parser.add_argument("--repo", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        if sys.version_info < (3, 11):
            raise BootstrapError("BOOTSTRAP_INTERPRETER_UNAVAILABLE")
        args = _parser().parse_args(argv)
        dispatch_id = parse_dispatch_id(args.dispatch_id)
        task_id, _ = parse_task_id(args.task_id)

        if args.repo is not None:
            repo = args.repo.resolve(strict=True)
            if not (repo / ".ai" / "tasks").is_dir():
                raise WorkerSurfaceError(f"repository task store not found at {repo}")
        else:
            repo = get_repo_root()

        layout = runtime_layout(repo)
        python = ensure_runtime(layout)
        completed = invoke_kernel(
            wakeup_command(
                python,
                dispatch_id=dispatch_id,
                task_id=task_id,
                executor=args.executor,
                repo=repo,
            ),
            repo=repo,
        )
        _emit_completed(completed)
        return completed.returncode
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    except (WorkerSurfaceError, OSError, UnicodeError) as exc:
        print(f"AIOS PHASE-1 WAKEUP ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
