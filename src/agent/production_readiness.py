from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import logging
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from src.agent.loop import AgentLoop
from src.agent.policy import RunPolicy
from src.agent.replay_engine import ReplayEngine
from src.core.checkpoint_contract import (
    CheckpointCorruptionError,
    CheckpointEvent,
    CheckpointEventType,
    CheckpointStateError,
    RunState,
    validate_event_sequence,
    validate_state_transition,
)
from src.core.idempotency_contract import (
    IdempotencyCorruptionError,
    IdempotencyRecord,
    RecordKey,
    RecordStatus,
)
from src.core.idempotency_store_v2 import JsonlIdempotencyStore
from src.core.recovery_diagnostics import RecoveryAnalyzer, RecoveryPotential
from src.core.retry import RetryPolicy
from src.core.types import ToolCall

logger = logging.getLogger(__name__)


class ReadinessStatus(str, Enum):
    READY = "READY"
    NOT_READY = "NOT_READY"


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    passed: bool
    reason: str


@dataclass(frozen=True)
class ProductionReadinessReport:
    status: ReadinessStatus
    checks: Tuple[ReadinessCheck, ...]

    @property
    def ready(self) -> bool:
        return self.status == ReadinessStatus.READY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "ready": self.ready,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "reason": c.reason,
                }
                for c in self.checks
            ],
        }


def parse_idempotency_store_read_only(
    idempotency_path: Optional[str],
) -> Tuple[Optional[str], Dict[str, IdempotencyRecord]]:
    """
    Strictly read-only parser and lifecycle validator for JSONL idempotency stores.
    
    Invariants:
    - Never creates directories, data files, lock files, or temp files.
    - Reuses production JsonlIdempotencyStore._record_from_dict to enforce identical schema/type rules:
      * created_at and updated_at numeric
      * updated_at >= created_at
      * non-empty owner_id
      * integer attempt >= 1 (bool rejected)
      * data is dict or None
    - Validates per-key persisted lifecycle invariants:
      * timestamp monotonicity (updated_at >= prev.updated_at)
      * created_at immutability (created_at == prev.created_at)
      * attempt monotonicity (attempt >= prev.attempt)
      * no terminal reopening (transitions from COMPLETED/FAILED to any other status rejected)
      * no invalid intermediate transitions (e.g. RECOVERABLE to RECOVERABLE/COMPLETED without IN_PROGRESS)
    """
    if not idempotency_path or not os.path.exists(idempotency_path):
        return None, {}

    records: Dict[str, IdempotencyRecord] = {}

    try:
        with open(idempotency_path, "r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue

                try:
                    payload = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    return f"Malformed JSON at line {line_number}: {exc.msg}", {}

                try:
                    record = JsonlIdempotencyStore._record_from_dict(payload, line_number)
                except IdempotencyCorruptionError as exc:
                    return f"Line {line_number}: {exc.message}", {}

                if record.updated_at < record.created_at:
                    return (
                        f"Line {line_number}: updated_at ({record.updated_at}) is earlier than "
                        f"created_at ({record.created_at}) for key {record.key.canonical}",
                        {},
                    )

                canonical = record.key.canonical
                if canonical in records:
                    prev = records[canonical]

                    if record.updated_at < prev.updated_at:
                        return (
                            f"Line {line_number}: timestamp rollback for key {canonical} "
                            f"(previous: {prev.updated_at}, current: {record.updated_at})",
                            {},
                        )

                    if record.created_at != prev.created_at:
                        return (
                            f"Line {line_number}: created_at changed for key {canonical} "
                            f"(previous: {prev.created_at}, current: {record.created_at})",
                            {},
                        )

                    if record.attempt < prev.attempt:
                        return (
                            f"Line {line_number}: attempt rollback for key {canonical} "
                            f"(previous: {prev.attempt}, current: {record.attempt})",
                            {},
                        )

                    # Terminal states cannot reopen or change
                    if prev.status in (RecordStatus.COMPLETED, RecordStatus.FAILED):
                        return (
                            f"Line {line_number}: illegal transition from terminal status "
                            f"{prev.status.value} to {record.status.value} for key {canonical}",
                            {},
                        )

                    if prev.status == RecordStatus.IN_PROGRESS:
                        if record.status not in (
                            RecordStatus.IN_PROGRESS,
                            RecordStatus.COMPLETED,
                            RecordStatus.FAILED,
                            RecordStatus.RECOVERABLE,
                        ):
                            return (
                                f"Line {line_number}: illegal transition from IN_PROGRESS to "
                                f"{record.status.value} for key {canonical}",
                                {},
                            )

                    if prev.status == RecordStatus.RECOVERABLE:
                        if record.status != RecordStatus.IN_PROGRESS:
                            return (
                                f"Line {line_number}: illegal transition from RECOVERABLE to "
                                f"{record.status.value} for key {canonical} (must reclaim to IN_PROGRESS first)",
                                {},
                            )
                        if record.attempt != prev.attempt + 1:
                            return (
                                f"Line {line_number}: reclaiming RECOVERABLE record for key {canonical} "
                                f"must increment attempt by 1 (previous: {prev.attempt}, current: {record.attempt})",
                                {},
                            )

                records[canonical] = record

    except OSError as exc:
        return f"I/O error reading idempotency store: {exc}", {}

    return None, records


class ProductionReadinessChecker:
    """
    Deterministic, strictly read-only preflight gate verifying Phase 5.6 reliability controls.
    
    Evaluates:
    - RunPolicy configuration validity
    - RetryPolicy configuration sanity
    - Checkpoint store structural health (zero corruption, valid sequences & state transitions)
    - Idempotency store structural health (zero corruption, valid schema, valid lifecycle history)
    - Cross-store consistency for recoverable/active runs (exact RecordKey matching)
    - Terminal run immutability (no unsafe terminal continuation)
    
    Invariants:
    - Strictly read-only: zero provider calls, zero tool executions, zero store mutations, zero lock file touches.
    - Deterministic: same inputs/files produce identical reports.
    - Fail-closed: any failed safety check marks overall status NOT_READY.
    - No secret, prompt, or payload leakage in reports.
    """

    @classmethod
    def evaluate_agent(cls, loop: AgentLoop) -> ProductionReadinessReport:
        """Evaluate readiness directly from an AgentLoop instance."""
        checkpoint_path = getattr(loop.checkpoints, "db_path", None)
        idempotency_path = getattr(
            getattr(loop.tool_executor, "idempotency_store", None),
            "db_path",
            None,
        )
        retry_policy = getattr(
            getattr(loop.tool_executor, "retry_manager", None),
            "policy",
            None,
        )
        return cls.evaluate(
            policy=loop.policy,
            retry_policy=retry_policy,
            checkpoint_path=checkpoint_path,
            idempotency_path=idempotency_path,
        )

    @classmethod
    def evaluate(
        cls,
        policy: Optional[RunPolicy] = None,
        retry_policy: Optional[RetryPolicy] = None,
        checkpoint_path: Optional[str] = None,
        idempotency_path: Optional[str] = None,
        run_ids: Optional[Sequence[str]] = None,
    ) -> ProductionReadinessReport:
        """
        Evaluate production readiness across all configured components.
        """
        checks: List[ReadinessCheck] = []

        # 1. RunPolicy validity
        checks.append(cls._check_run_policy(policy))

        # 2. RetryPolicy sanity
        checks.append(cls._check_retry_policy(retry_policy))

        # 3. Checkpoint store structural health
        chk_event_runs: List[str] = []
        cp_check, discovered_runs = cls._check_checkpoint_store(checkpoint_path)
        checks.append(cp_check)
        if discovered_runs:
            chk_event_runs.extend(discovered_runs)
        if run_ids:
            chk_event_runs.extend(run_ids)
        unique_runs = list(dict.fromkeys(chk_event_runs))

        # 4. Idempotency store structural health (strictly read-only)
        idem_check, idem_records = cls._check_idempotency_store(idempotency_path)
        checks.append(idem_check)

        # 5. Cross-store consistency
        checks.append(
            cls._check_cross_store_consistency(
                checkpoint_path=checkpoint_path,
                idempotency_path=idempotency_path,
                idempotency_records=idem_records,
                run_ids=unique_runs,
                cp_healthy=cp_check.passed,
                idem_healthy=idem_check.passed,
            )
        )

        # 6. Terminal run immutability
        checks.append(
            cls._check_terminal_run_immutability(
                checkpoint_path=checkpoint_path,
                run_ids=unique_runs,
                cp_healthy=cp_check.passed,
            )
        )

        all_passed = all(c.passed for c in checks)
        status = ReadinessStatus.READY if all_passed else ReadinessStatus.NOT_READY

        return ProductionReadinessReport(
            status=status,
            checks=tuple(checks),
        )

    @staticmethod
    def _check_run_policy(policy: Optional[RunPolicy]) -> ReadinessCheck:
        name = "run_policy_validity"
        if policy is None:
            return ReadinessCheck(name=name, passed=False, reason="RunPolicy is missing (None)")

        if not isinstance(policy, RunPolicy):
            return ReadinessCheck(
                name=name,
                passed=False,
                reason=f"Expected RunPolicy instance, got {type(policy).__name__}",
            )

        if policy.max_iterations < 0:
            return ReadinessCheck(
                name=name,
                passed=False,
                reason=f"max_iterations must be non-negative, got {policy.max_iterations}",
            )

        if policy.max_tool_calls < 0:
            return ReadinessCheck(
                name=name,
                passed=False,
                reason=f"max_tool_calls must be non-negative, got {policy.max_tool_calls}",
            )

        if policy.timeout_seconds <= 0:
            return ReadinessCheck(
                name=name,
                passed=False,
                reason=f"timeout_seconds must be positive, got {policy.timeout_seconds}",
            )

        return ReadinessCheck(
            name=name,
            passed=True,
            reason=(
                f"RunPolicy valid (max_iterations={policy.max_iterations}, "
                f"max_tool_calls={policy.max_tool_calls}, "
                f"timeout_seconds={policy.timeout_seconds})"
            ),
        )

    @staticmethod
    def _check_retry_policy(retry_policy: Optional[RetryPolicy]) -> ReadinessCheck:
        name = "retry_policy_sanity"
        if retry_policy is None:
            return ReadinessCheck(
                name=name,
                passed=False,
                reason="RetryPolicy is missing (None)",
            )

        if not isinstance(retry_policy, RetryPolicy):
            return ReadinessCheck(
                name=name,
                passed=False,
                reason=f"Expected RetryPolicy instance, got {type(retry_policy).__name__}",
            )

        if retry_policy.max_attempts < 1:
            return ReadinessCheck(
                name=name,
                passed=False,
                reason=f"max_attempts must be at least 1, got {retry_policy.max_attempts}",
            )

        if retry_policy.base_delay < 0:
            return ReadinessCheck(
                name=name,
                passed=False,
                reason=f"base_delay must be non-negative, got {retry_policy.base_delay}",
            )

        if retry_policy.max_delay < retry_policy.base_delay:
            return ReadinessCheck(
                name=name,
                passed=False,
                reason=(
                    f"max_delay ({retry_policy.max_delay}) must be greater than or equal "
                    f"to base_delay ({retry_policy.base_delay})"
                ),
            )

        return ReadinessCheck(
            name=name,
            passed=True,
            reason=(
                f"RetryPolicy valid (max_attempts={retry_policy.max_attempts}, "
                f"base_delay={retry_policy.base_delay}, "
                f"max_delay={retry_policy.max_delay}, "
                f"jitter={retry_policy.jitter})"
            ),
        )

    @staticmethod
    def _check_checkpoint_store(
        checkpoint_path: Optional[str],
    ) -> Tuple[ReadinessCheck, List[str]]:
        name = "checkpoint_store_health"
        if not checkpoint_path:
            return (
                ReadinessCheck(
                    name=name,
                    passed=True,
                    reason="Checkpoint store path not configured (in-memory/fresh runtime)",
                ),
                [],
            )

        if not os.path.exists(checkpoint_path):
            return (
                ReadinessCheck(
                    name=name,
                    passed=True,
                    reason=f"Checkpoint store file does not exist ({checkpoint_path}) — fresh runtime ready",
                ),
                [],
            )

        events_by_run: Dict[str, List[CheckpointEvent]] = {}
        total_events = 0

        try:
            with open(checkpoint_path, "r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    stripped = line.strip()
                    if not stripped:
                        continue

                    try:
                        data = json.loads(stripped)
                    except json.JSONDecodeError as exc:
                        return (
                            ReadinessCheck(
                                name=name,
                                passed=False,
                                reason=f"Malformed JSON at line {line_number}: {exc.msg}",
                            ),
                            [],
                        )

                    try:
                        evt = CheckpointEvent.from_dict(data, line_number=line_number)
                        events_by_run.setdefault(evt.run_id, []).append(evt)
                        total_events += 1
                    except CheckpointCorruptionError as exc:
                        return (
                            ReadinessCheck(
                                name=name,
                                passed=False,
                                reason=f"Checkpoint corruption at line {line_number}: {exc.message}",
                            ),
                            [],
                        )

            # Validate sequence and state transitions per run
            for rid, evts in events_by_run.items():
                try:
                    validate_event_sequence(evts)
                except (CheckpointStateError, CheckpointCorruptionError) as exc:
                    return (
                        ReadinessCheck(
                            name=name,
                            passed=False,
                            reason=f"Invalid event sequence in run '{rid}': {exc}",
                        ),
                        [],
                    )

                state = RunState.PENDING
                for evt in evts:
                    try:
                        state = validate_state_transition(state, evt)
                    except CheckpointStateError as exc:
                        return (
                            ReadinessCheck(
                                name=name,
                                passed=False,
                                reason=f"Invalid state transition in run '{rid}': {exc}",
                            ),
                            [],
                        )

        except OSError as exc:
            return (
                ReadinessCheck(
                    name=name,
                    passed=False,
                    reason=f"I/O error reading checkpoint store: {exc}",
                ),
                [],
            )

        runs = list(events_by_run.keys())
        return (
            ReadinessCheck(
                name=name,
                passed=True,
                reason=f"Checkpoint store structurally sound ({len(runs)} runs, {total_events} events verified)",
            ),
            runs,
        )

    @staticmethod
    def _check_idempotency_store(
        idempotency_path: Optional[str],
    ) -> Tuple[ReadinessCheck, Dict[str, IdempotencyRecord]]:
        name = "idempotency_store_health"
        if not idempotency_path:
            return (
                ReadinessCheck(
                    name=name,
                    passed=True,
                    reason="Idempotency store path not configured (in-memory/fresh runtime)",
                ),
                {},
            )

        if not os.path.exists(idempotency_path):
            return (
                ReadinessCheck(
                    name=name,
                    passed=True,
                    reason=f"Idempotency store file does not exist ({idempotency_path}) — fresh runtime ready",
                ),
                {},
            )

        err, records = parse_idempotency_store_read_only(idempotency_path)
        if err is not None:
            return (
                ReadinessCheck(
                    name=name,
                    passed=False,
                    reason=f"Idempotency store corruption: {err}",
                ),
                {},
            )

        return (
            ReadinessCheck(
                name=name,
                passed=True,
                reason=f"Idempotency store structurally sound ({len(records)} records verified)",
            ),
            records,
        )

    @staticmethod
    def _check_cross_store_consistency(
        checkpoint_path: Optional[str],
        idempotency_path: Optional[str],
        idempotency_records: Dict[str, IdempotencyRecord],
        run_ids: List[str],
        cp_healthy: bool,
        idem_healthy: bool,
    ) -> ReadinessCheck:
        name = "cross_store_consistency"
        if not cp_healthy or not idem_healthy:
            return ReadinessCheck(
                name=name,
                passed=False,
                reason="Skipped cross-store check due to corrupted checkpoint or idempotency store",
            )

        if not checkpoint_path or not os.path.exists(checkpoint_path) or not run_ids:
            return ReadinessCheck(
                name=name,
                passed=True,
                reason="No active runs to verify cross-store consistency (fresh runtime)",
            )

        # For each run in checkpoints, verify exact tool call RecordKey in idempotency store
        for rid in run_ids:
            try:
                events = ReplayEngine.load_events_for_run(checkpoint_path, rid)
                session = ReplayEngine.reconstruct_session(checkpoint_path, rid)

                # Track tool calls where durable execution/attempt/retry began
                started_call_ids = set()
                for evt in events:
                    if evt.event_type in (
                        CheckpointEventType.TOOL_ATTEMPT_STARTED,
                        CheckpointEventType.RETRY_SCHEDULED,
                        CheckpointEventType.TOOL_RESULT_RECEIVED,
                        CheckpointEventType.TOOL_CALL_REJECTED,
                    ):
                        cid = evt.payload.get("call_id")
                        if cid:
                            started_call_ids.add(cid)

                # 1. Verify completed tool calls
                for cid, result in session.completed_tool_calls.items():
                    t_call = None
                    for msg in session.messages:
                        if msg.tool_calls:
                            for tc in msg.tool_calls:
                                if tc.call_id == cid:
                                    t_call = ToolCall(
                                        name=tc.name,
                                        arguments=tc.arguments,
                                        call_id=cid,
                                        run_id=rid,
                                    )
                                    break
                        if t_call:
                            break

                    if not t_call:
                        t_call = ToolCall(
                            name=result.tool_name,
                            arguments={},
                            call_id=cid,
                            run_id=rid,
                        )

                    canonical_key = json.dumps(
                        [f"tool:{t_call.name}", t_call.idempotency_key],
                        separators=(",", ":"),
                    )

                    if canonical_key not in idempotency_records:
                        return ReadinessCheck(
                            name=name,
                            passed=False,
                            reason=(
                                f"Cross-store mismatch in run '{rid}': completed tool call '{cid}' "
                                f"missing exact idempotency record for key {canonical_key}"
                            ),
                        )

                    rec = idempotency_records[canonical_key]
                    if rec.status != RecordStatus.COMPLETED:
                        return ReadinessCheck(
                            name=name,
                            passed=False,
                            reason=(
                                f"Cross-store mismatch in run '{rid}': completed tool call '{cid}' "
                                f"has non-completed idempotency record status {rec.status.value}"
                            ),
                        )

                # 2. Verify pending/recoverable tool calls for non-terminal runs
                if session.last_state not in (RunState.COMPLETED, RunState.HALTED, RunState.FAILED):
                    for cid, t_call in session.pending_tool_calls.items():
                        # Only require idempotency record if durable history shows execution/attempt started
                        if cid in started_call_ids:
                            canonical_key = json.dumps(
                                [f"tool:{t_call.name}", t_call.idempotency_key],
                                separators=(",", ":"),
                            )
                            if canonical_key not in idempotency_records:
                                return ReadinessCheck(
                                    name=name,
                                    passed=False,
                                    reason=(
                                        f"Cross-store mismatch in run '{rid}': started/recoverable tool call "
                                        f"'{cid}' missing required idempotency record for key {canonical_key}"
                                    ),
                                )

            except Exception as exc:
                return ReadinessCheck(
                    name=name,
                    passed=False,
                    reason=f"Failed to verify integrity for run '{rid}': {exc}",
                )

        return ReadinessCheck(
            name=name,
            passed=True,
            reason=f"Cross-store integrity verified across {len(run_ids)} runs",
        )

    @staticmethod
    def _check_terminal_run_immutability(
        checkpoint_path: Optional[str],
        run_ids: List[str],
        cp_healthy: bool,
    ) -> ReadinessCheck:
        name = "terminal_run_immutability"
        if not cp_healthy:
            return ReadinessCheck(
                name=name,
                passed=False,
                reason="Skipped terminal run immutability check due to corrupted checkpoint store",
            )

        if not checkpoint_path or not os.path.exists(checkpoint_path) or not run_ids:
            return ReadinessCheck(
                name=name,
                passed=True,
                reason="No runs present (fresh runtime)",
            )

        for rid in run_ids:
            try:
                diag = RecoveryAnalyzer.analyze(rid, checkpoint_path)
                if diag.current_state in (RunState.COMPLETED, RunState.HALTED, RunState.FAILED):
                    if diag.recovery_potential == RecoveryPotential.RECOVERABLE:
                        return ReadinessCheck(
                            name=name,
                            passed=False,
                            reason=f"Terminal run '{rid}' in state {diag.current_state.value} unexpectedly marked RECOVERABLE",
                        )
            except Exception as exc:
                return ReadinessCheck(
                    name=name,
                    passed=False,
                    reason=f"Error inspecting recovery diagnostics for run '{rid}': {exc}",
                )

        return ReadinessCheck(
            name=name,
            passed=True,
            reason="All persisted terminal runs are safely non-recoverable or completed",
        )
