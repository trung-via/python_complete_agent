#!/usr/bin/env python3
"""
Operator CLI utility for validating and fingerprinting Continuity State files.
Conforms strictly to ADR-010 and ADR-011 (M1).

Commands:
  validate <path>     Validates a ContinuityState JSON file and displays metadata.
  fingerprint <path>  Computes and displays the canonical SHA-256 state fingerprint.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

# Ensure repository root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.aios_bridge.continuity import (
    ContinuityError,
    ContinuityState,
    ContinuityStateValidationError,
)


def cmd_validate(path: Path) -> int:
    """Validates an explicit ContinuityState file and prints safe metadata."""
    if not path.exists() or not path.is_file():
        print(f"[ERROR] State file not found: {str(path)!r}", file=sys.stderr)
        return 1

    try:
        content = path.read_bytes()
        state = ContinuityState.from_json(content)
    except ContinuityStateValidationError as e:
        print(f"[INVALID] Validation failed: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[ERROR] Failed to read/parse state file: {type(e).__name__}", file=sys.stderr)
        return 1

    canonical_json = state.to_canonical_json()
    fp = state.fingerprint()

    print("=" * 60)
    print("AIOS CONTINUITY STATE — VALIDATION SUCCESS")
    print("=" * 60)
    print(f"Task ID:          {state.task_id}")
    print(f"Phase:            {state.phase.value}")
    print(f"Next Operation:   {state.next_operation.value}")
    print(f"Main Branch:      {state.main.branch} ({state.main.sha[:10]}...)")
    print(f"Task Branch:      {state.task_branch.branch} (sha={state.task_branch.sha[:10] if state.task_branch.sha else 'null'})")
    print(f"Contracts Count:  {len(state.artifacts.contracts)}")
    print(f"Brain:            {state.brain.last_id or 'none'} (op={state.brain.last_operation.value if state.brain.last_operation else 'none'})")
    print(f"Executor:         {state.executor.last_id or 'none'}")
    print(f"Fingerprint:      {fp}")
    print(f"Serialized Size:  {len(canonical_json.encode('utf-8'))} bytes")
    print("=" * 60)
    return 0


def cmd_fingerprint(path: Path) -> int:
    """Computes and prints the deterministic SHA-256 fingerprint."""
    if not path.exists() or not path.is_file():
        print(f"[ERROR] State file not found: {str(path)!r}", file=sys.stderr)
        return 1

    try:
        content = path.read_bytes()
        state = ContinuityState.from_json(content)
    except ContinuityError as e:
        print(f"[ERROR] Validation failed: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[ERROR] Failed to process state file: {type(e).__name__}", file=sys.stderr)
        return 1

    print(state.fingerprint())
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Continuity State CLI Validator & Fingerprinter (M1)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate a Continuity State JSON file")
    validate_parser.add_argument("path", type=Path, help="Path to JSON state file")

    fp_parser = subparsers.add_parser("fingerprint", help="Compute canonical SHA-256 fingerprint")
    fp_parser.add_argument("path", type=Path, help="Path to JSON state file")

    args = parser.parse_args(argv)

    if args.command == "validate":
        return cmd_validate(args.path)
    elif args.command == "fingerprint":
        return cmd_fingerprint(args.path)
    else:
        parser.print_help(sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
