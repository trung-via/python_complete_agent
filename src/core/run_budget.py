from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import logging
from typing import List, Optional, Set

from src.agent.policy import RunPolicy
from src.core.checkpoint_contract import CheckpointEvent, CheckpointEventType

logger = logging.getLogger(__name__)


class BudgetDimension(str, Enum):
    ITERATIONS = "ITERATIONS"
    TOOL_CALLS = "TOOL_CALLS"
    TIME = "TIME"


@dataclass(frozen=True)
class BudgetUsage:
    iterations_used: int
    tool_calls_used: int
    seen_tool_call_ids: frozenset[str] = frozenset()
    elapsed_seconds: float = 0.0


@dataclass(frozen=True)
class BudgetDecision:
    allowed: bool
    exhausted_dimension: Optional[BudgetDimension] = None
    reason: Optional[str] = None


class RunBudgetEngine:
    """
    Deterministic, side-effect-free decision engine for production execution budgets.
    
    Evaluates whether requested work (iterations, logical tool calls) fits within
    the configured RunPolicy constraints without side-effects or mutations.
    """

    @staticmethod
    def decide(
        policy: RunPolicy,
        usage: BudgetUsage,
        requested_iterations: int = 0,
        requested_tool_calls: int = 0,
    ) -> BudgetDecision:
        """
        Evaluates whether requested work exceeds configured limits.

        - max_iterations=N permits exactly N LLM iterations, never N+1.
        - max_tool_calls=N permits exactly N logical tool calls, never N+1.
        """
        # 1. Check Iterations
        projected_iterations = usage.iterations_used + requested_iterations
        if projected_iterations > policy.max_iterations:
            return BudgetDecision(
                allowed=False,
                exhausted_dimension=BudgetDimension.ITERATIONS,
                reason="MAX_ITERATIONS_REACHED",
            )

        # 2. Check Logical Tool Calls
        projected_tool_calls = usage.tool_calls_used + requested_tool_calls
        if projected_tool_calls > policy.max_tool_calls:
            return BudgetDecision(
                allowed=False,
                exhausted_dimension=BudgetDimension.TOOL_CALLS,
                reason="MAX_TOOL_CALLS_REACHED",
            )

        return BudgetDecision(allowed=True, exhausted_dimension=None, reason=None)

    @staticmethod
    def reconstruct_usage(events: List[CheckpointEvent]) -> BudgetUsage:
        """
        Reconstructs budget usage for a run from durable checkpoint events.

        - LLM iterations: highest iteration index (or count of distinct requested/responded iterations).
        - Logical tool calls: count of distinct logical tool `call_id`s.
        - Retry attempts (e.g. multiple TOOL_ATTEMPT_STARTED with the same call_id) do NOT
          inflate logical tool-call count.
        """
        iterations: Set[int] = set()
        logical_tool_call_ids: Set[str] = set()

        for ev in events:
            payload = ev.payload if isinstance(ev.payload, dict) else {}

            # Track iterations
            if ev.event_type in (
                CheckpointEventType.LLM_REQUESTED,
                CheckpointEventType.LLM_RESPONDED,
            ):
                iter_num = payload.get("iteration")
                if isinstance(iter_num, int) and iter_num > 0:
                    iterations.add(iter_num)

            # Track logical tool calls from LLM_RESPONDED
            if ev.event_type == CheckpointEventType.LLM_RESPONDED:
                tool_calls = payload.get("tool_calls")
                if isinstance(tool_calls, list):
                    for tc in tool_calls:
                        if isinstance(tc, dict) and tc.get("call_id"):
                            logical_tool_call_ids.add(tc["call_id"])

            # Track logical tool calls from execution / retry / result events
            if ev.event_type in (
                CheckpointEventType.TOOL_ATTEMPT_STARTED,
                CheckpointEventType.TOOL_RESULT_RECEIVED,
                CheckpointEventType.TOOL_ATTEMPT_ENDED,
            ):
                cid = payload.get("call_id")
                if cid:
                    logical_tool_call_ids.add(cid)

        iter_count = max(iterations) if iterations else 0

        return BudgetUsage(
            iterations_used=iter_count,
            tool_calls_used=len(logical_tool_call_ids),
            seen_tool_call_ids=frozenset(logical_tool_call_ids),
            elapsed_seconds=0.0,
        )

    @classmethod
    def reconstruct_from_db(cls, db_path: str, run_id: str) -> BudgetUsage:
        """Reconstruct budget usage by reading validated events from checkpoint file."""
        from src.agent.replay_engine import ReplayEngine
        events = ReplayEngine.load_events_for_run(db_path, run_id)
        return cls.reconstruct_usage(events)

