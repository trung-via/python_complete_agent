#!/usr/bin/env python3
"""Pinned bootstrap for one immutable Phase-2 REPAIR wakeup.

This script owns selector framing, exact-pin runtime bootstrap, and one operator
delegation only. The pinned ``repair-wakeup`` boundary owns repair authority,
action-specific Executor requirements, at-most-once state, and execution.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
from typing import Sequence

from aios_worker import (
    BootstrapError,
    SHA_PATTERN,
    WorkerSurfaceError,
    _emit_completed,
    ensure_runtime,
    get_repo_root,
    invoke_kernel,
    parse_run_id,
    runtime_layout,
)


DISPATCH_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
ALLOWED_EXECUTORS = ("antigravity", "codex")


def parse_dispatch_id(raw: str) -> str:
    if not DISPATCH_ID_PATTERN.fullmatch(raw):
        raise WorkerSurfaceError("invalid REPAIR dispatch ID")
    return raw


def parse_repair_sha(raw: str) -> str:
    if not SHA_PATTERN.fullmatch(raw):
        raise WorkerSurfaceError("invalid REPAIR authorization SHA")
    return raw


def repair_command(
    python: Path,
    *,
    repair_dispatch_id: str,
    failed_run_id: str,
    repair_sha: str,
    executor: str | None,
    repo: Path,
) -> tuple[str, ...]:
    """Build the sole dedicated pinned REPAIR-wakeup delegation."""

    command = [
        str(python),
        "-m",
        "aios_renew.operator",
        "repair-wakeup",
        repair_dispatch_id,
        failed_run_id,
        repair_sha,
    ]
    if executor is not None:
        command.extend(("--executor", executor))
    command.extend(("--repo", str(repo)))
    return tuple(command)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aios_phase2_repair.py")
    parser.add_argument("repair_dispatch_id")
    parser.add_argument("failed_run_id")
    parser.add_argument("repair_sha")
    parser.add_argument("--executor", choices=ALLOWED_EXECUTORS)
    parser.add_argument("--repo", type=Path, default=None)
    return parser


def _repository(value: Path | None) -> Path:
    if value is None:
        return get_repo_root()
    repo = value.resolve(strict=True)
    if not (repo / ".ai" / "tasks").is_dir():
        raise WorkerSurfaceError(f"repository task store not found at {repo}")
    return repo


def main(argv: Sequence[str] | None = None) -> int:
    try:
        if sys.version_info < (3, 11):
            raise BootstrapError("BOOTSTRAP_INTERPRETER_UNAVAILABLE")
        args = _parser().parse_args(argv)
        repair_dispatch_id = parse_dispatch_id(args.repair_dispatch_id)
        failed_run_id = parse_run_id(args.failed_run_id)
        repair_sha = parse_repair_sha(args.repair_sha)
        repo = _repository(args.repo)
        python = ensure_runtime(runtime_layout(repo))
        completed = invoke_kernel(
            repair_command(
                python,
                repair_dispatch_id=repair_dispatch_id,
                failed_run_id=failed_run_id,
                repair_sha=repair_sha,
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
        print(f"AIOS PHASE-2 REPAIR ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
