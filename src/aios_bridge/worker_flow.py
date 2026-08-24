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
from typing import Callable, Sequence


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
      - Exact valid marker -> returns corresponding FixExecutionMode.
      - Unknown marker -> raises ValueError (fails closed).
      - Multiple / conflicting markers -> raises ValueError (fails closed).
    """
    if not review_text or not isinstance(review_text, str):
        return FixExecutionMode.IMPLEMENTATION

    matches = _FIX_MODE_PATTERN.findall(review_text)
    if not matches:
        return FixExecutionMode.IMPLEMENTATION

    # Normalize values
    cleaned = [m.strip().upper() for m in matches if m.strip()]
    if not cleaned:
        return FixExecutionMode.IMPLEMENTATION

    unique_values = set(cleaned)
    if len(unique_values) > 1:
        raise ValueError(
            f"Conflicting FIX_EXECUTION_MODE markers found in review: {sorted(unique_values)}"
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
    """Coordinates single-command worker transactions with automatic sync and mode routing."""

    def __init__(
        self,
        repo_root: Path,
        run_bridge_cmd_fn: Callable[[list[str]], int] | None = None,
        review_resolver_fn: Callable[[int], str | None] | None = None,
    ) -> None:
        self.repo_root = repo_root
        self._run_bridge_cmd = run_bridge_cmd_fn or self._default_run_bridge_cmd
        self._review_resolver = review_resolver_fn or self._default_resolve_review

    def _default_run_bridge_cmd(self, args: list[str]) -> int:
        bridge_py = self.repo_root / "bridge.py"
        cmd = [sys.executable, str(bridge_py)] + args
        proc = subprocess.run(cmd, cwd=self.repo_root, shell=False)
        return proc.returncode

    def _default_resolve_review(self, task_num: int) -> str | None:
        local_path = self.repo_root / f".ai/reviews/REVIEW-{task_num:03d}.md"
        if local_path.is_file():
            try:
                return local_path.read_text(encoding="utf-8")
            except Exception:
                pass

        # Resolve from origin/ai-control or local artifact cache
        try:
            cmd = ["git", "show", f"origin/ai-control:.ai/reviews/REVIEW-{task_num:03d}.md"]
            proc = subprocess.run(
                cmd,
                cwd=self.repo_root,
                capture_output=True,
                shell=False,
            )
            if proc.returncode == 0:
                return proc.stdout.decode("utf-8")
        except Exception:
            pass
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

        # 2. RUN transaction: sync then handoff [then execute if codex]
        if action == WorkerAction.RUN:
            sync_code = self.sync()
            if sync_code != 0:
                return WorkerFlowResult(
                    action=action.value,
                    task_id=task_id,
                    adapter=adapter.value,
                    status="SYNC_FAILED",
                    returncode=sync_code,
                    message="Pre-authority sync failed for RUN",
                )

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

        # 3. FIX transaction: sync, resolve review mode, handoff, then appropriate continuation
        if action == WorkerAction.FIX:
            sync_code = self.sync()
            if sync_code != 0:
                return WorkerFlowResult(
                    action=action.value,
                    task_id=task_id,
                    adapter=adapter.value,
                    status="SYNC_FAILED",
                    returncode=sync_code,
                    message="Pre-authority sync failed for FIX",
                )

            review_content = self._review_resolver(task_num)
            try:
                fix_mode = extract_fix_execution_mode(review_content)
            except ValueError as e:
                return WorkerFlowResult(
                    action=action.value,
                    task_id=task_id,
                    adapter=adapter.value,
                    status="INVALID_FIX_MODE",
                    returncode=1,
                    message=str(e),
                )

            handoff_args = ["handoff", str(task_num), "--action", "fix", "--executor", adapter.value]
            handoff_code = self._run_bridge_cmd(handoff_args)
            if handoff_code != 0:
                return WorkerFlowResult(
                    action=action.value,
                    task_id=task_id,
                    adapter=adapter.value,
                    status="HANDOFF_FAILED",
                    fix_execution_mode=fix_mode.value,
                    returncode=handoff_code,
                    message="Handoff failed for FIX",
                )

            # Route by fix mode
            if fix_mode == FixExecutionMode.EVIDENCE_REFRESH:
                # Evidence Refresh: skip bounded executor, certify and publish directly
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
