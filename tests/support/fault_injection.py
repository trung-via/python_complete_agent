from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
import threading
from typing import Any, Callable, Dict, List, Optional, Set

from src.agent.messages import LLMMessage
from src.core.checkpoint import CheckpointManager
from src.core.checkpoint_contract import CheckpointEvent, CheckpointEventType
from src.core.types import ToolCall, ToolResult, ToolStatus
from src.providers.base import LLMProvider, LLMResponse, ProviderToolCall


class FaultPoint(str, Enum):
    BEFORE_LLM_REQUEST = "BEFORE_LLM_REQUEST"
    AFTER_LLM_REQUEST = "AFTER_LLM_REQUEST"
    AFTER_LLM_RESPONSE = "AFTER_LLM_RESPONSE"
    BEFORE_TOOL_EXECUTION = "BEFORE_TOOL_EXECUTION"
    BEFORE_TOOL_ATTEMPT = "BEFORE_TOOL_ATTEMPT"
    AFTER_TOOL_SIDE_EFFECT_BEFORE_CHECKPOINT = "AFTER_TOOL_SIDE_EFFECT_BEFORE_CHECKPOINT"
    AFTER_FAILED_ATTEMPT_BEFORE_RETRY = "AFTER_FAILED_ATTEMPT_BEFORE_RETRY"
    AFTER_RETRY_SCHEDULED = "AFTER_RETRY_SCHEDULED"
    BEFORE_RESUMED_PENDING_TOOL = "BEFORE_RESUMED_PENDING_TOOL"
    AFTER_RESUMED_PENDING_TOOL = "AFTER_RESUMED_PENDING_TOOL"
    CHECKPOINT_WRITE_FAILURE = "CHECKPOINT_WRITE_FAILURE"


class FaultInjectionException(Exception):
    """Deterministic simulated fault / process interruption exception."""


class FaultInjector:
    """
    Thread-safe and async-safe deterministic fault injection manager.
    Enables triggering exceptions, callbacks, or barriers at explicit failpoints.
    """

    def __init__(self) -> None:
        self._failpoints: Dict[str, Dict[str, Any]] = {}
        self._counts: Dict[str, int] = {}
        self._lock = threading.Lock()

    def register_failpoint(
        self,
        point: FaultPoint | str,
        *,
        trigger_on_count: int = 1,
        exception: Optional[Exception] = None,
        callback: Optional[Callable[[], Any]] = None,
        async_callback: Optional[Callable[[], Any]] = None,
        event_to_set: Optional[asyncio.Event | threading.Event] = None,
        event_to_wait: Optional[asyncio.Event | threading.Event] = None,
    ) -> None:
        key = point.value if isinstance(point, FaultPoint) else str(point)
        with self._lock:
            self._failpoints[key] = {
                "trigger_on_count": trigger_on_count,
                "exception": exception or FaultInjectionException(f"Simulated fault at {key}"),
                "callback": callback,
                "async_callback": async_callback,
                "event_to_set": event_to_set,
                "event_to_wait": event_to_wait,
            }
            self._counts[key] = 0

    async def trigger(self, point: FaultPoint | str) -> None:
        key = point.value if isinstance(point, FaultPoint) else str(point)
        config: Optional[Dict[str, Any]] = None
        should_trigger = False

        with self._lock:
            if key in self._failpoints:
                self._counts[key] = self._counts.get(key, 0) + 1
                cfg = self._failpoints[key]
                if self._counts[key] == cfg["trigger_on_count"]:
                    config = cfg
                    should_trigger = True

        if should_trigger and config is not None:
            if config["event_to_set"] is not None:
                config["event_to_set"].set()

            if config["event_to_wait"] is not None:
                ev = config["event_to_wait"]
                if isinstance(ev, asyncio.Event):
                    await ev.wait()
                elif isinstance(ev, threading.Event):
                    ev.wait()

            if config["callback"] is not None:
                config["callback"]()

            if config["async_callback"] is not None:
                res = config["async_callback"]()
                if asyncio.iscoroutine(res):
                    await res

            if config["exception"] is not None:
                raise config["exception"]


class FaultyCheckpointManager(CheckpointManager):
    """
    CheckpointManager proxy that injects deterministic write failures or corruptions.
    """

    def __init__(
        self,
        db_path: str,
        fail_on_event_types: Optional[Set[CheckpointEventType | str]] = None,
        fail_on_write_count: Optional[int] = None,
        exception_to_raise: Optional[Exception] = None,
    ) -> None:
        super().__init__(db_path=db_path)
        self.fail_on_event_types: Set[str] = {
            e.value if isinstance(e, CheckpointEventType) else str(e)
            for e in (fail_on_event_types or set())
        }
        self.fail_on_write_count = fail_on_write_count
        self.write_count = 0
        self.exception_to_raise = exception_to_raise or OSError("Simulated checkpoint write failure")
        self._lock = threading.Lock()

    def log_event(self, run_id: str, event_type: str, payload: dict) -> None:
        with self._lock:
            self.write_count += 1
            if (
                self.fail_on_write_count is not None
                and self.write_count == self.fail_on_write_count
            ):
                raise self.exception_to_raise

            if event_type in self.fail_on_event_types:
                raise self.exception_to_raise

        super().log_event(run_id, event_type, payload)


class FaultyLLMProvider(LLMProvider):
    """
    LLMProvider with deterministic failpoints and synchronization barriers.
    """

    def __init__(
        self,
        responses: List[LLMResponse],
        injector: Optional[FaultInjector] = None,
    ) -> None:
        self.responses = responses
        self.call_count = 0
        self.injector = injector or FaultInjector()

    async def generate(
        self,
        messages: List[LLMMessage],
        tools: List[dict],
    ) -> LLMResponse:
        await self.injector.trigger(FaultPoint.BEFORE_LLM_REQUEST)

        if self.call_count >= len(self.responses):
            resp = LLMResponse(
                provider="mock",
                provider_response_id="fallback",
                content="Default Final Answer",
                tool_calls=[],
            )
        else:
            resp = self.responses[self.call_count]
            self.call_count += 1

        await self.injector.trigger(FaultPoint.AFTER_LLM_RESPONSE)
        return resp


class FaultyTool:
    """
    Tool implementation with deterministic side-effect execution and optional failpoints/barriers.
    """

    def __init__(
        self,
        name: str = "faulty_tool",
        injector: Optional[FaultInjector] = None,
        crash_after_side_effect: bool = False,
    ) -> None:
        self.name = name
        self.description = "fault injection test tool"
        self.side_effects: List[Dict[str, Any]] = []
        self.injector = injector or FaultInjector()
        self.crash_after_side_effect = crash_after_side_effect

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string"},
                "val": {"type": "integer"},
            },
        }

    async def execute(self, call: ToolCall, context: Dict[str, Any]) -> ToolResult:
        await self.injector.trigger(FaultPoint.BEFORE_TOOL_ATTEMPT)

        # Execute external side effect
        self.side_effects.append({"call_id": call.call_id, "args": call.arguments})

        if self.crash_after_side_effect:
            await self.injector.trigger(FaultPoint.AFTER_TOOL_SIDE_EFFECT_BEFORE_CHECKPOINT)
            raise FaultInjectionException("Process crashed immediately after tool side effect!")

        return ToolResult(
            call_id=call.call_id,
            run_id=call.run_id,
            tool_name=call.name,
            status=ToolStatus.SUCCESS,
            data={"result": "ok", "side_effect_count": len(self.side_effects)},
        )
