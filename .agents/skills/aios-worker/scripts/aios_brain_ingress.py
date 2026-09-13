#!/usr/bin/env python3
"""Pinned, repository-owned carrier for canonical Brain authoring ingress.

This carrier owns only runtime provenance and transport. Envelope structure,
authoring semantics, canonical destinations, idempotency, and Git mutation are
owned by the exact pinned ``aios_renew.operator ingress`` implementation.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
from typing import Sequence

from aios_worker import (
    BootstrapError,
    WorkerSurfaceError,
    ensure_runtime,
    get_repo_root,
    invoke_kernel,
    runtime_layout,
)


def ingress_command(python: Path, *, envelope: Path, repo: Path) -> tuple[str, ...]:
    """Build the sole canonical pinned ingress delegation."""

    return (
        str(python),
        "-m",
        "aios_renew.operator",
        "ingress",
        str(envelope),
        "--repo",
        str(repo),
    )


def _emit_completed(completed: subprocess.CompletedProcess[str]) -> None:
    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
    if completed.stderr:
        print(
            completed.stderr,
            end="" if completed.stderr.endswith("\n") else "\n",
            file=sys.stderr,
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aios_brain_ingress.py")
    parser.add_argument("envelope", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        if sys.version_info < (3, 11):
            raise BootstrapError("BOOTSTRAP_INTERPRETER_UNAVAILABLE")
        args = _parser().parse_args(argv)
        envelope = args.envelope.resolve(strict=True)
        if not envelope.is_file():
            raise WorkerSurfaceError(f"ingress envelope is not a file: {envelope}")

        repo = get_repo_root()
        python = ensure_runtime(runtime_layout(repo))
        completed = invoke_kernel(
            ingress_command(python, envelope=envelope, repo=repo),
            repo=repo,
        )
        _emit_completed(completed)
        return completed.returncode
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    except (WorkerSurfaceError, OSError, UnicodeError) as exc:
        print(f"AIOS BRAIN INGRESS ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
