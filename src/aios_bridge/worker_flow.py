"""AIOS Transactional Worker Flow and FIX Recovery Module (ADR-061 / ADR-062).

Defines the transactional operator flow contracts, closed FIX execution modes
(IMPLEMENTATION vs EVIDENCE_REFRESH), review re-resolution, and evidence refresh
continuations.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re
import subprocess
import sys
from typing import Callable


class FixExecutionMode(str, Enum):
    """Closed execution mode for CHANGES_REQUIRED reviews."""
    IMPLEMENTATION = "IMPLEMENTATION"
    EVIDENCE_REFRESH = "EVIDENCE_REFRESH"


class WorkerAction(str, Enum):
    """Supported operator action verbs."""
    RUN = "RUN"
    FIX = "FIX"
    STATUS = "STATUS"


class WorkerAdapter(str, Enum):
    """Supported UI adapter environments."""
    CODEX = "codex"
    ANTIGRAVITY = "antigravity"


_FIX_MODE_PATTERN = re.compile(r"^FIX_EXECUTION_MODE:\s*(.+)$", re.MULTILINE | re.IGNORECASE)


def extract_fix_execution_mode(review_text: str | None) -> FixExecutionMode:
    """Extract and validate the closed FIX_EXECUTION_MODE from review content.

    Rules:
      - Missing marker -> defaults to FixExecutionMode.IMPLEMENTATION.
      - Exact single valid marker -> returns corresponding FixExecutionMode.
      - Multiple markers (even if identical) -> raises ValueError (fails closed).
      - Unknown marker -> raises ValueError (fails closed).
    """
    if not review_text or not isinstance(review_text, str):
        return FixExecutionMode.IMPLEMENTATION

    matches = _FIX_MODE_PATTERN.findall(review_text)
    if not matches:
        return FixExecutionMode.IMPLEMENTATION

    cleaned = [m.strip().upper() for m in matches if m.strip()]
    if not cleaned:
        return FixExecutionMode.IMPLEMENTATION

    if len(cleaned) > 1:
        raise ValueError(
            f"Multiple FIX_EXECUTION_MODE markers found in review (count={len(cleaned)}): {cleaned}"
        )

    val = cleaned[0]
    if val == FixExecutionMode.IMPLEMENTATION.value:
        return FixExecutionMode.IMPLEMENTATION
    elif val == FixExecutionMode.EVIDENCE_REFRESH.value:
        return FixExecutionMode.EVIDENCE_REFRESH
    else:
        raise ValueError(f"Unknown or unsupported FIX_EXECUTION_MODE '{val}' in review")


@dataclass(frozen=True)
class WorkerIntent:
    """Represents a validated single-command operator transaction."""
    action: WorkerAction
    task_id: str
    task_num: int
    adapter: WorkerAdapter


@dataclass(frozen=True)
class WorkerFlowResult:
    """Result of a transactional worker flow operation."""
    action: str
    task_id: str
    adapter: str
    status: str
    fix_execution_mode: str | None = None
    executor_invocations: int = 0
    returncode: int = 0
    message: str = ""


class WorkerFlowCoordinator:
    """Coordinates single-command worker transactions with mode routing."""

    def __init__(
        self,
        repo_root: Path,
        run_bridge_cmd_fn: Callable[[list[str]], int] | None = None,
        load_auth_fn: Callable[[int], dict | None] | None = None,
    ) -> None:
        self.repo_root = repo_root
        self._run_bridge_cmd = run_bridge_cmd_fn or self._default_run_bridge_cmd
        self._load_auth = load_auth_fn or self._default_load_auth

    def _default_run_bridge_cmd(self, args: list[str]) -> int:
        bridge_py = self.repo_root / "bridge.py"
        cmd = [sys.executable, str(bridge_py)] + args
        proc = subprocess.run(cmd, cwd=self.repo_root, shell=False)
        return proc.returncode

    def _default_load_auth(self, task_num: int) -> dict | None:
        try:
            from bridge import get_active_authorization
            return get_active_authorization(task_num, "FIX")
        except Exception:
            return None

    def sync(self) -> int:
        """Executes read-only control branch synchronization."""
        return self._run_bridge_cmd(["sync"])

    def execute_transaction(self, intent: WorkerIntent) -> WorkerFlowResult:
        """Executes the full single-command worker transaction."""
        action = intent.action
        task_id = intent.task_id
        task_num = intent.task_num
        adapter = intent.adapter

        # 1. STATUS transaction: sync then pending (non-authorizing)
        if action == WorkerAction.STATUS:
            sync_code = self.sync()
            if sync_code != 0:
                return WorkerFlowResult(
                    action=action.value,
                    task_id=task_id,
                    adapter=adapter.value,
                    status="SYNC_FAILED",
                    returncode=sync_code,
                    message="Bridge sync failed during STATUS",
                )
            pending_code = self._run_bridge_cmd(["pending"])
            if pending_code != 0:
                return WorkerFlowResult(
                    action=action.value,
                    task_id=task_id,
                    adapter=adapter.value,
                    status="PENDING_FAILED",
                    returncode=pending_code,
                    message="Bridge pending check failed",
                )
            return WorkerFlowResult(
                action=action.value,
                task_id=task_id,
                adapter=adapter.value,
                status="SYNCED",
                returncode=0,
                message=f"Synced status for {task_id}",
            )

        # 2. RUN transaction: handoff [then execute if codex]
        if action == WorkerAction.RUN:
            handoff_args = ["handoff", str(task_num), "--action", "run", "--executor", adapter.value]
            handoff_code = self._run_bridge_cmd(handoff_args)
            if handoff_code != 0:
                return WorkerFlowResult(
                    action=action.value,
                    task_id=task_id,
                    adapter=adapter.value,
                    status="HANDOFF_FAILED",
                    returncode=handoff_code,
                    message="Handoff failed for RUN",
                )

            if adapter == WorkerAdapter.CODEX:
                exec_code = self._run_bridge_cmd(["execute", str(task_num)])
                if exec_code != 0:
                    return WorkerFlowResult(
                        action=action.value,
                        task_id=task_id,
                        adapter=adapter.value,
                        status="EXECUTION_FAILED",
                        executor_invocations=1,
                        returncode=exec_code,
                        message="Codex execution failed for RUN",
                    )
                return WorkerFlowResult(
                    action=action.value,
                    task_id=task_id,
                    adapter=adapter.value,
                    status="PUBLISHED",
                    executor_invocations=1,
                    returncode=0,
                    message=f"RUN {task_id} completed and published",
                )
            else:
                return WorkerFlowResult(
                    action=action.value,
                    task_id=task_id,
                    adapter=adapter.value,
                    status="AUTHORIZED",
                    executor_invocations=0,
                    returncode=0,
                    message=f"RUN {task_id} authorized for {adapter.value}",
                )

        # 3. FIX transaction: handoff, inspect authorized fix mode, then appropriate continuation
        if action == WorkerAction.FIX:
            handoff_args = ["handoff", str(task_num), "--action", "fix", "--executor", adapter.value]
            handoff_code = self._run_bridge_cmd(handoff_args)
            if handoff_code != 0:
                return WorkerFlowResult(
                    action=action.value,
                    task_id=task_id,
                    adapter=adapter.value,
                    status="HANDOFF_FAILED",
                    returncode=handoff_code,
                    message="Handoff failed for FIX",
                )

            # Load the exact authorized fix execution mode frozen by Bridge handoff
            auth = self._load_auth(task_num)
            if not auth or auth.get("status") != "ACTIVE" or auth.get("action", "").upper() != "FIX":
                return WorkerFlowResult(
                    action=action.value,
                    task_id=task_id,
                    adapter=adapter.value,
                    status="AUTH_INVALID",
                    returncode=1,
                    message="Active authorization missing or invalid post-handoff",
                )

            mode_raw = auth.get("fix_execution_mode")
            if not mode_raw:
                return WorkerFlowResult(
                    action=action.value,
                    task_id=task_id,
                    adapter=adapter.value,
                    status="AUTH_INVALID",
                    returncode=1,
                    message="Active FIX authorization missing explicit 'fix_execution_mode'",
                )

            try:
                fix_mode = FixExecutionMode(mode_raw)
            except ValueError as exc:
                return WorkerFlowResult(
                    action=action.value,
                    task_id=task_id,
                    adapter=adapter.value,
                    status="INVALID_FIX_MODE",
                    returncode=1,
                    message=f"Invalid authorized FIX_EXECUTION_MODE '{mode_raw}': {exc}",
                )

            # Route continuation strictly based on exact authorized fix_mode
            if fix_mode == FixExecutionMode.EVIDENCE_REFRESH:
                # Evidence Refresh: skip bounded executor, certify canonical suite, publish directly
                publish_args = [
                    "publish",
                    str(task_num),
                    "--action",
                    "fix",
                    "--test",
                    r"venv\Scripts\python.exe -m pytest tests/ -q",
                    "--summary",
                    f"EVIDENCE_REFRESH for {task_id}: certified unchanged clean worktree against canonical full test suite.",
                    "--notes",
                    f"EVIDENCE_REFRESH continuation for {task_id}. Executor invocation skipped (count = 0). Full canonical suite certified.",
                    "--message",
                    f"{task_id}: Evidence refresh certification and republication",
                ]
                publish_code = self._run_bridge_cmd(publish_args)
                if publish_code != 0:
                    return WorkerFlowResult(
                        action=action.value,
                        task_id=task_id,
                        adapter=adapter.value,
                        status="EVIDENCE_REFRESH_PUBLISH_FAILED",
                        fix_execution_mode=fix_mode.value,
                        executor_invocations=0,
                        returncode=publish_code,
                        message="Evidence refresh publish failed",
                    )
                return WorkerFlowResult(
                    action=action.value,
                    task_id=task_id,
                    adapter=adapter.value,
                    status="PUBLISHED",
                    fix_execution_mode=fix_mode.value,
                    executor_invocations=0,
                    returncode=0,
                    message=f"EVIDENCE_REFRESH {task_id} certified and published",
                )
            else:
                # IMPLEMENTATION mode
                if adapter == WorkerAdapter.CODEX:
                    exec_code = self._run_bridge_cmd(["execute", str(task_num)])
                    if exec_code != 0:
                        return WorkerFlowResult(
                            action=action.value,
                            task_id=task_id,
                            adapter=adapter.value,
                            status="EXECUTION_FAILED",
                            fix_execution_mode=fix_mode.value,
                            executor_invocations=1,
                            returncode=exec_code,
                            message="Codex execution failed for FIX",
                        )
                    return WorkerFlowResult(
                        action=action.value,
                        task_id=task_id,
                        adapter=adapter.value,
                        status="PUBLISHED",
                        fix_execution_mode=fix_mode.value,
                        executor_invocations=1,
                        returncode=0,
                        message=f"FIX {task_id} completed and published",
                    )
                else:
                    return WorkerFlowResult(
                        action=action.value,
                        task_id=task_id,
                        adapter=adapter.value,
                        status="AUTHORIZED",
                        fix_execution_mode=fix_mode.value,
                        executor_invocations=0,
                        returncode=0,
                        message=f"FIX {task_id} authorized for {adapter.value}",
                    )

        return WorkerFlowResult(
            action=str(action),
            task_id=task_id,
            adapter=str(adapter),
            status="UNKNOWN_ACTION",
            returncode=1,
            message=f"Unknown worker action '{action}'",
        )


__all__ = [
    "FixExecutionMode",
    "WorkerAction",
    "WorkerAdapter",
    "WorkerIntent",
    "WorkerFlowResult",
    "WorkerFlowCoordinator",
    "extract_fix_execution_mode",
]
