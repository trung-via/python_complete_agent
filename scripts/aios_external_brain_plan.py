#!/usr/bin/env python3
"""
Manual External Brain PLAN Runner CLI for AIOS Bridge v0.5.
Operator utility for executing advisory ARCHITECT PLAN operations with MiniMax-M3.

Adheres strictly to ADR-008 and ADR-009 governance:
- Explicit task file and context files only (no automatic discovery or crawl).
- Reuses M1/M2/M3 contracts and primitives (ContextBuilder, ModelGateway, MiniMaxOpenAIProvider).
- Proposal-only: ZERO filesystem write authority, zero Git/shell/patch execution.
- Single provider call: ZERO retries, zero fallbacks.
- Credential safety: API key from environment, never printed or persisted.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Ensure repo root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.aios_bridge.external_brain.runner import execute_plan_runner


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manual External Brain PLAN Runner for AIOS Bridge (MiniMax-M3)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--task-file",
        required=True,
        help="Path to the primary task markdown file (loaded as ContextKind.TASK).",
    )
    parser.add_argument(
        "--context",
        action="append",
        default=[],
        dest="contexts",
        help="Explicit context file spec in format 'KIND:PATH' (e.g. 'CONTRACT:docs/ADR.md', 'SOURCE:src/app.py'). Can be repeated.",
    )
    parser.add_argument(
        "--model",
        default="MiniMax-M3",
        help="Model name for provider inference.",
    )
    parser.add_argument(
        "--provider",
        default="minimax",
        help="Provider adapter ID.",
    )
    parser.add_argument(
        "--max-context-tokens",
        type=int,
        default=32000,
        help="Maximum total context token budget for M2 ContextBuilder.",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=8192,
        help="Maximum output tokens for model generation.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=180.0,
        help="Transport execution timeout in seconds.",
    )
    parser.add_argument(
        "--ledger-file",
        default=None,
        help="Optional explicit path to append JSONL usage telemetry records.",
    )
    parser.add_argument(
        "--request-id",
        default=None,
        help="Optional explicit correlation request ID.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Optional MiniMax API key (defaults to AIOS_MINIMAX_API_KEY environment variable).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    exit_code, output = asyncio.run(
        execute_plan_runner(
            task_file=args.task_file,
            context_specs=args.contexts,
            api_key=args.api_key,
            model=args.model,
            provider_id=args.provider,
            max_context_tokens=args.max_context_tokens,
            max_output_tokens=args.max_output_tokens,
            timeout_seconds=args.timeout_seconds,
            ledger_path=args.ledger_file,
            request_id=args.request_id,
        )
    )

    if exit_code == 0:
        print(output)
    else:
        print(output, file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
