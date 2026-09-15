#!/usr/bin/env python3
"""Pinned bootstrap for one approved Phase-2 remediation intent.

This script owns selector framing, exact-pin runtime bootstrap, and one operator
delegation only. The pinned ``approved-remediation-intent`` boundary separately
owns A3 approval persistence/reuse and entry into A6 durable correction dispatch.
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
    parse_run_id,
    runtime_layout,
)


SELECTOR_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
APPROVER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-\[\]]{0,99}\Z")
ALLOWED_EXECUTORS = ("antigravity", "codex")


def parse_selector(raw: str, *, name: str) -> str:
    if not SELECTOR_PATTERN.fullmatch(raw):
        raise WorkerSurfaceError(f"invalid {name}")
    return raw


def parse_approver(raw: str) -> str:
    if not APPROVER_PATTERN.fullmatch(raw):
        raise WorkerSurfaceError("invalid trusted approver attribution")
    return raw


def remediation_command(
    python: Path,
    *,
    correction_dispatch_id: str,
    source_run_id: str,
    finding_id: str,
    executor: str,
    approver: str,
    repo: Path,
) -> tuple[str, ...]:
    """Build the sole pinned A3/A6 coalesced-intent delegation."""

    return (
        str(python),
        "-m",
        "aios_renew.operator",
        "approved-remediation-intent",
        correction_dispatch_id,
        source_run_id,
        finding_id,
        "--executor",
        executor,
        "--approver",
        approver,
        "--repo",
        str(repo),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aios_phase2_remediation.py")
    parser.add_argument("correction_dispatch_id")
    parser.add_argument("source_run_id")
    parser.add_argument("finding_id")
    parser.add_argument("--executor", required=True, choices=ALLOWED_EXECUTORS)
    parser.add_argument("--approver", required=True)
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
        correction_dispatch_id = parse_selector(
            args.correction_dispatch_id, name="correction dispatch ID"
        )
        source_run_id = parse_run_id(args.source_run_id)
        finding_id = parse_selector(args.finding_id, name="finding ID")
        approver = parse_approver(args.approver)
        repo = _repository(args.repo)
        python = ensure_runtime(runtime_layout(repo))
        completed = invoke_kernel(
            remediation_command(
                python,
                correction_dispatch_id=correction_dispatch_id,
                source_run_id=source_run_id,
                finding_id=finding_id,
                executor=args.executor,
                approver=approver,
                repo=repo,
            ),
            repo=repo,
        )
        _emit_completed(completed)
        return completed.returncode
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    except (WorkerSurfaceError, OSError, UnicodeError) as exc:
        print(f"AIOS PHASE-2 REMEDIATION ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
