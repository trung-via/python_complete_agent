"""Execution runner and helper utilities for External Brain PLAN operations."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import math
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence
import uuid

from .context import ContextBudget, ContextBuilder, ContextBuildResult, ContextItem, ContextKind
from .contracts import (
    BrainOperation,
    BrainOutputType,
    BrainRole,
    ModelRequest,
    ModelResponse,
    ModelResponseStatus,
)
from .errors import (
    ContextBuildError,
    ContractValidationError,
    ExternalBrainError,
    MandatoryContextBudgetError,
    SensitiveContextError,
)
from .gateway import GatewayResult, ModelGateway
from .providers.minimax import MiniMaxOpenAIProvider
from .transport import ModelTransport
from .usage import JsonlUsageLedger, UsageLedger


def parse_context_spec(spec: str) -> tuple[ContextKind, str]:
    """
    Parses a context specification of the format 'KIND:PATH'.
    Validates that KIND is a recognized ContextKind enum member.
    """
    if not isinstance(spec, str) or not spec.strip():
        raise ContractValidationError("Context spec must be a non-empty string in format 'KIND:PATH'")

    parts = spec.split(":", 1)
    if len(parts) != 2:
        raise ContractValidationError(
            f"Invalid context spec format: {spec!r} (expected 'KIND:PATH')"
        )

    kind_str, path_str = parts[0].strip().upper(), parts[1].strip()
    if not kind_str or not path_str:
        raise ContractValidationError(
            f"Invalid context spec format: {spec!r} (both KIND and PATH must be non-empty)"
        )

    try:
        kind = ContextKind(kind_str)
    except ValueError as e:
        valid_kinds = ", ".join(k.value for k in ContextKind)
        raise ContractValidationError(
            f"Unrecognized ContextKind {kind_str!r} in spec {spec!r}. Valid kinds: {valid_kinds}"
        ) from e

    return kind, path_str


def load_explicit_context(
    task_file: str | Path,
    context_specs: Sequence[str] = (),
    *,
    base_dir: str | Path | None = None,
) -> list[ContextItem]:
    """
    Loads explicit task content and specified context files.
    Strictly reads ONLY explicitly specified files without repo crawling or discovery.
    """
    base_path = Path(base_dir).resolve() if base_dir is not None else Path.cwd().resolve()

    # 1. Load TASK file
    task_path = Path(task_file)
    if not task_path.is_absolute():
        task_path = base_path / task_path

    if not task_path.exists() or not task_path.is_file():
        raise ContractValidationError(f"Task file not found: {str(task_file)!r}")

    try:
        task_content = task_path.read_text(encoding="utf-8")
    except Exception as e:
        raise ContractValidationError(f"Failed to read task file {str(task_file)!r}: {type(e).__name__}") from e

    items: list[ContextItem] = [
        ContextItem(
            kind=ContextKind.TASK,
            content=task_content,
            path=str(task_file),
        )
    ]

    # 2. Load explicitly specified context files
    for spec in context_specs:
        kind, path_str = parse_context_spec(spec)
        target_path = Path(path_str)
        if not target_path.is_absolute():
            target_path = base_path / target_path

        if not target_path.exists() or not target_path.is_file():
            raise ContractValidationError(f"Context file not found for spec {spec!r}: {path_str!r}")

        try:
            content = target_path.read_text(encoding="utf-8")
        except Exception as e:
            raise ContractValidationError(f"Failed to read context file {path_str!r}: {type(e).__name__}") from e

        items.append(
            ContextItem(
                kind=kind,
                content=content,
                path=path_str,
            )
        )

    return items


def build_plan_request(
    task_id: str,
    context_build: ContextBuildResult,
    *,
    model: str = "MiniMax-M3",
    provider: str = "minimax",
    request_id: str | None = None,
    max_output_tokens: int = 8192,
) -> ModelRequest:
    """
    Constructs a contract-compliant ModelRequest for ARCHITECT PLAN operation.
    """
    req_id = request_id.strip() if request_id and request_id.strip() else f"req-plan-{uuid.uuid4().hex[:12]}"
    return ModelRequest(
        schema_version="1",
        request_id=req_id,
        task_id=task_id.strip(),
        role=BrainRole.ARCHITECT,
        operation=BrainOperation.PLAN,
        instruction="Generate a comprehensive, contract-compliant execution plan for the specified task.",
        output_format=BrainOutputType.PLAN,
        context=context_build.selected,
        provider=provider.strip() if provider else "minimax",
        model=model.strip() if model else "MiniMax-M3",
        max_output_tokens=max_output_tokens,
    )


def format_safe_plan_output(
    result: GatewayResult,
    context_build: ContextBuildResult | None = None,
) -> str:
    """
    Formats execution telemetry and final validated PLAN content safely.
    Strictly excludes API keys, authorization headers, raw HTTP bodies, and reasoning markers.
    """
    resp = result.response
    lines: list[str] = []

    lines.append("=" * 72)
    lines.append("AIOS EXTERNAL BRAIN — PLAN EXECUTION RESULT")
    lines.append("=" * 72)
    lines.append(f"Status:               {resp.status.value}")
    lines.append(f"Provider:             {resp.provider}")
    lines.append(f"Model:                {resp.model}")
    lines.append(f"Request ID:           {resp.request_id}")
    lines.append(f"Task ID:              {resp.task_id}")

    if resp.provider_request_id:
        lines.append(f"Provider Request ID:  {resp.provider_request_id}")

    if resp.latency_ms is not None:
        lines.append(f"Latency:              {resp.latency_ms} ms")

    if resp.input_tokens is not None or resp.output_tokens is not None:
        lines.append(
            f"Tokens (Provider):    Input={resp.input_tokens or 0}, "
            f"Output={resp.output_tokens or 0}, "
            f"Total={(resp.input_tokens or 0) + (resp.output_tokens or 0)}"
        )

    if context_build is not None:
        lines.append(f"Context Fingerprint:  {context_build.context_fingerprint}")
        lines.append(
            f"Context Tokens (M2):  {context_build.counted_tokens} "
            f"(exact={context_build.token_count_is_exact}, counter={context_build.counter_id})"
        )
        lines.append(f"Selected Items:       {len(context_build.selected)} (excluded={len(context_build.excluded)})")

    if result.ledger_persisted is not None:
        lines.append(f"Ledger Persisted:     {result.ledger_persisted}")
        if result.ledger_error_code:
            lines.append(f"Ledger Error Code:    {result.ledger_error_code}")

    if resp.status != ModelResponseStatus.SUCCESS:
        lines.append("-" * 72)
        lines.append(f"Error Code:           {resp.error_code or 'UNKNOWN'}")
        if resp.error_message:
            lines.append(f"Error Message:        {resp.error_message}")
        lines.append("=" * 72)
        return "\n".join(lines)

    lines.append("=" * 72)
    lines.append("VALIDATED PLAN CONTENT")
    lines.append("-" * 72)
    lines.append(resp.content or "(empty plan content)")
    lines.append("=" * 72)

    return "\n".join(lines)


async def execute_plan_runner(
    task_file: str | Path,
    *,
    context_specs: Sequence[str] = (),
    api_key: str | None = None,
    model: str = "MiniMax-M3",
    provider_id: str = "minimax",
    max_context_tokens: int = 32000,
    max_output_tokens: int = 8192,
    timeout_seconds: float = 180.0,
    ledger_path: str | Path | None = None,
    request_id: str | None = None,
    custom_transport: ModelTransport | None = None,
    custom_gateway: ModelGateway | None = None,
) -> tuple[int, str]:
    """
    End-to-end asynchronous executor for the manual External Brain PLAN runner.
    Returns (exit_code, formatted_output_string).
    """
    # 1. API key resolution & validation
    resolved_key = api_key or os.environ.get("AIOS_MINIMAX_API_KEY", "")
    if not resolved_key or not resolved_key.strip():
        err_msg = "Preflight check failed: Missing MiniMax API key. Set AIOS_MINIMAX_API_KEY environment variable."
        return 1, f"[ERROR] {err_msg}"

    # 2. Explicit context loading
    try:
        candidates = load_explicit_context(task_file, context_specs)
    except (ContractValidationError, ExternalBrainError) as e:
        return 1, f"[ERROR] Context loading failed: {str(e)}"

    # 3. Context budget & building through M2
    budget = ContextBudget(max_context_tokens=max_context_tokens)
    builder = ContextBuilder()
    try:
        context_build = builder.build(candidates, budget)
    except (MandatoryContextBudgetError, SensitiveContextError, ContextBuildError, ContractValidationError, ExternalBrainError) as e:
        return 1, f"[ERROR] Context build failed: {str(e)}"

    # Derive task_id from task_file basename
    task_basename = Path(task_file).stem
    task_id = task_basename if task_basename.startswith("TASK-") else "TASK-017"

    # 4. Build ModelRequest
    try:
        request = build_plan_request(
            task_id=task_id,
            context_build=context_build,
            model=model,
            provider=provider_id,
            request_id=request_id,
            max_output_tokens=max_output_tokens,
        )
    except ContractValidationError as e:
        return 1, f"[ERROR] Request construction failed: {str(e)}"

    # 5. ModelGateway & Provider setup
    ledger: UsageLedger | None = None
    if ledger_path:
        ledger = JsonlUsageLedger(ledger_path)

    if custom_gateway is not None:
        gateway = custom_gateway
    else:
        try:
            provider = MiniMaxOpenAIProvider(
                api_key=resolved_key,
                model_name=model,
                timeout_seconds=timeout_seconds,
                transport=custom_transport,
            )
            gateway = ModelGateway(provider=provider, ledger=ledger)
        except ContractValidationError as e:
            return 1, f"[ERROR] Gateway initialization failed: {str(e)}"

    # 6. Execute Gateway invocation (single call, no retry)
    try:
        result = await gateway.invoke(request, context_build=context_build)
    except Exception as e:
        return 1, f"[ERROR] Gateway execution failed: {type(e).__name__}"

    formatted_output = format_safe_plan_output(result, context_build)
    exit_code = 0 if result.response.status == ModelResponseStatus.SUCCESS else 1
    return exit_code, formatted_output
