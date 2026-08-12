from __future__ import annotations

from contextlib import contextmanager
import json
import logging
import os
import threading
import time
import uuid
from typing import Any, Dict, Iterator, List, Optional

from src.core.checkpoint_contract import (
    CheckpointCorruptionError,
    CheckpointEvent,
    CheckpointEventType,
)
from src.core.errors import SystemStateError

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Manages state checkpoints for the autonomous agent.

    Uses dedicated cross-process file locking (checkpoints.jsonl.lock) and
    commit-before-memory-update persistence for strict durability.
    """

    _LOCAL_LOCKS: Dict[str, threading.RLock] = {}
    _LOCAL_LOCKS_GUARD = threading.Lock()

    def __init__(self, db_path: str = "checkpoints.jsonl") -> None:
        self.db_path = db_path
        self.lock_path = f"{db_path}.lock"
        self._last_sequences: Dict[str, int] = {}
        self._last_timestamps: Dict[str, float] = {}

        if os.path.exists(self.db_path):
            with self._store_lock():
                self._reload_locked()

    def log_task_start(self, task_context: str) -> str:
        """Logs the start of a task and returns a unique run_id."""
        run_id = str(uuid.uuid4())
        self.log_event(
            run_id,
            CheckpointEventType.TASK_START.value,
            {
                "task_context": task_context,
                "status": "PENDING",
                "retry_count": 0,
            },
        )
        return run_id

    def log_run_started(self, run_id: str, system_prompt: str, user_prompt: str) -> None:
        self.log_event(
            run_id,
            CheckpointEventType.RUN_STARTED.value,
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            },
        )

    def log_llm_requested(self, run_id: str, iteration: int) -> None:
        self.log_event(
            run_id,
            CheckpointEventType.LLM_REQUESTED.value,
            {"iteration": iteration},
        )

    def log_llm_responded(
        self,
        run_id: str,
        iteration: int,
        content: Optional[str],
        num_tool_calls: int,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        payload: Dict[str, Any] = {
            "iteration": iteration,
            "has_content": bool(content),
            "content": content,
            "num_tool_calls": num_tool_calls,
            "tool_calls": tool_calls or [],
        }
        self.log_event(
            run_id,
            CheckpointEventType.LLM_RESPONDED.value,
            payload,
        )

    def log_tool_call_created(
        self, run_id: str, call_id: str, tool_name: str, arguments: dict
    ) -> None:
        self.log_event(
            run_id,
            CheckpointEventType.TOOL_CALL_CREATED.value,
            {
                "call_id": call_id,
                "tool_name": tool_name,
                "arguments": arguments,
            },
        )

    def log_tool_attempt_started(self, run_id: str, call_id: str) -> None:
        self.log_event(
            run_id,
            CheckpointEventType.TOOL_ATTEMPT_STARTED.value,
            {"call_id": call_id},
        )

    def log_tool_attempt_ended(
        self,
        run_id: str,
        call_id: str,
        attempt: int,
        status: str,
        error_msg: Optional[str] = None,
    ) -> None:
        self.log_event(
            run_id,
            CheckpointEventType.TOOL_ATTEMPT_ENDED.value,
            {
                "call_id": call_id,
                "attempt": attempt,
                "status": status,
                "error": error_msg,
            },
        )

    def log_tool_result_received(
        self,
        run_id: str,
        call_id: str,
        status: str,
        tool_name: str = "",
        result: Optional[Dict[str, Any]] = None,
        iteration_complete: bool = True,
    ) -> None:
        self.log_event(
            run_id,
            CheckpointEventType.TOOL_RESULT_RECEIVED.value,
            {
                "call_id": call_id,
                "tool_name": tool_name,
                "status": status,
                "result": result or {},
                "iteration_complete": iteration_complete,
            },
        )

    def log_tool_call_rejected(self, run_id: str, call_id: str, reason: str) -> None:
        self.log_event(
            run_id,
            CheckpointEventType.TOOL_CALL_REJECTED.value,
            {"call_id": call_id, "reason": reason},
        )

    def log_llm_final_response(self, run_id: str, content: Optional[str]) -> None:
        self.log_event(
            run_id,
            CheckpointEventType.LLM_FINAL_RESPONSE.value,
            {"has_content": bool(content), "content": content},
        )

    def log_run_completed(self, run_id: str) -> None:
        self.log_event(
            run_id,
            CheckpointEventType.RUN_COMPLETED.value,
            {},
        )

    def log_run_failed(self, run_id: str, error: str) -> None:
        self.log_event(
            run_id,
            CheckpointEventType.RUN_FAILED.value,
            {"error": error},
        )

    def log_run_halted(self, run_id: str, reason: str) -> None:
        self.log_event(
            run_id,
            CheckpointEventType.RUN_HALTED.value,
            {"reason": reason},
        )

    def log_task_end(
        self, run_id: str, success: bool, retry_count: int, data: Optional[dict] = None
    ) -> None:
        self.log_event(
            run_id,
            CheckpointEventType.TASK_END.value,
            {
                "status": "SUCCESS" if success else "FAILED",
                "retry_count": retry_count,
                "data": data or {},
            },
        )

    def log_event(self, run_id: str, event_name: str, payload: dict) -> None:
        """
        Log any checkpoint event under lock using commit-before-memory-update.

        Per-run sequence_id is automatically auto-incremented (+1).
        """
        try:
            evt_type = CheckpointEventType(event_name)
        except (TypeError, ValueError):
            # Fallback for legacy event names
            evt_type = CheckpointEventType.RUN_STARTED

        with self._store_lock():
            self._reload_locked()

            seq = self._last_sequences.get(run_id, 0) + 1
            now = time.time()
            last_ts = self._last_timestamps.get(run_id, 0.0)
            ts = max(now, last_ts + 0.000001)

            event = CheckpointEvent(
                run_id=run_id,
                sequence_id=seq,
                timestamp=ts,
                event_type=evt_type,
                payload=payload,
            )

            # Durable append before updating memory
            self._append_locked(event)

            # Update memory only after append succeeds
            self._last_sequences[run_id] = seq
            self._last_timestamps[run_id] = ts

    def get_completed_tasks(self) -> List[str]:
        """Reads the ledger to find which tasks successfully completed."""
        with self._store_lock():
            self._reload_locked()

            if not os.path.exists(self.db_path):
                return []

            task_starts: Dict[str, str] = {}
            completed: set[str] = set()

            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    for line in f:
                        stripped = line.strip()
                        if not stripped:
                            continue
                        try:
                            data = json.loads(stripped)
                            run_id = data.get("run_id")
                            evt_type = data.get("event_type") or data.get("event")
                            payload = data.get("payload", {})
                            if not payload and isinstance(data, dict):
                                payload = data

                            if evt_type == CheckpointEventType.TASK_START.value:
                                task_starts[run_id] = payload.get("task_context", "")
                            elif evt_type == CheckpointEventType.TASK_END.value:
                                if payload.get("status") == "SUCCESS":
                                    ctx = task_starts.get(run_id)
                                    if ctx:
                                        completed.add(ctx)
                        except Exception:
                            continue
            except Exception as e:
                logger.error(f"Failed to read checkpoints: {e}")

            return list(completed)

    # ------------------------------------------------------------------
    # Private Locking & Persistence Helpers
    # ------------------------------------------------------------------

    def _reload_locked(self) -> None:
        """Scan db_path to update per-run last_sequences and last_timestamps."""
        self._last_sequences.clear()
        self._last_timestamps.clear()

        if not os.path.exists(self.db_path):
            return

        try:
            with open(self.db_path, "r", encoding="utf-8") as handle:
                for line in handle:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        data = json.loads(stripped)
                        if "run_id" in data and "sequence_id" in data:
                            rid = data["run_id"]
                            seq = data["sequence_id"]
                            ts = data.get("timestamp", 0.0)
                            if isinstance(seq, int):
                                self._last_sequences[rid] = max(
                                    self._last_sequences.get(rid, 0), seq
                                )
                            if isinstance(ts, (int, float)):
                                self._last_timestamps[rid] = max(
                                    self._last_timestamps.get(rid, 0.0), float(ts)
                                )
                    except Exception:
                        continue
        except OSError as exc:
            raise SystemStateError(f"Failed to reload checkpoints: {exc}") from exc

    def _append_locked(self, event: CheckpointEvent) -> None:
        """Append event to file, flush and fsync. Raises SystemStateError on failure."""
        payload = event.to_dict()

        try:
            with open(self.db_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        except Exception as exc:
            logger.critical(
                f"CRITICAL: Failed to write checkpoint event for run {event.run_id}! Error: {exc}"
            )
            raise SystemStateError(
                f"Checkpoint write failed for run {event.run_id}: {exc}"
            ) from exc

    def _ensure_parent_directory(self) -> None:
        parent = os.path.dirname(os.path.abspath(self.db_path))
        if parent and not os.path.exists(parent):
            try:
                os.makedirs(parent, exist_ok=True)
            except OSError:
                pass

    @contextmanager
    def _store_lock(self) -> Iterator[None]:
        """Acquire both in-process RLock and OS-level exclusive file lock."""
        local_lock = self._get_local_lock(self.lock_path)

        with local_lock:
            handle = None
            try:
                handle = open(self.lock_path, "a+b")
                self._acquire_os_lock(handle)
                try:
                    yield
                finally:
                    self._release_os_lock(handle)
            except Exception as exc:
                raise SystemStateError(f"Failed to acquire lock: {exc}") from exc
            finally:
                if handle is not None:
                    try:
                        handle.close()
                    except OSError:
                        pass

    @classmethod
    def _get_local_lock(cls, lock_path: str) -> threading.RLock:
        normalized = os.path.abspath(lock_path)
        with cls._LOCAL_LOCKS_GUARD:
            lock = cls._LOCAL_LOCKS.get(normalized)
            if lock is None:
                lock = threading.RLock()
                cls._LOCAL_LOCKS[normalized] = lock
            return lock

    @staticmethod
    def _acquire_os_lock(handle: Any) -> None:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            return

        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)

    @staticmethod
    def _release_os_lock(handle: Any) -> None:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            return

        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
