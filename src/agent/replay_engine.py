from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from src.agent.messages import AssistantToolCall, LLMMessage, MessageRole
from src.core.checkpoint_contract import (
    CheckpointCorruptionError,
    CheckpointEvent,
    CheckpointEventType,
    ReconstructedSession,
    RunState,
    validate_event_sequence,
    validate_state_transition,
)
from src.core.types import ToolCall, ToolResult, ToolStatus


class ReplayEngine:
    """
    Read-only engine that reconstructs an agent session from a checkpoints JSONL file.

    ReplayEngine is strictly read-only: it NEVER appends, repairs, or mutates
    the checkpoint file.
    """

    @classmethod
    def load_events_for_run(
        cls,
        db_path: str,
        run_id: str,
    ) -> List[CheckpointEvent]:
        """Read and validate all CheckpointEvent entries for a target run_id."""
        if not os.path.exists(db_path):
            return []

        all_events: List[CheckpointEvent] = []
        target_events: List[CheckpointEvent] = []

        try:
            with open(db_path, "r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    stripped = line.strip()
                    if not stripped:
                        continue

                    try:
                        data = json.loads(stripped)
                    except json.JSONDecodeError as exc:
                        raise CheckpointCorruptionError(
                            run_id,
                            f"<line:{line_number}> Invalid JSON: {exc.msg}",
                        ) from exc

                    event = CheckpointEvent.from_dict(data, line_number=line_number)
                    all_events.append(event)
                    if event.run_id == run_id:
                        target_events.append(event)

        except OSError as exc:
            raise CheckpointCorruptionError(
                run_id,
                f"Failed to read checkpoint store: {exc}",
            ) from exc

        # Validate sequence & timestamp monotonicity across all events
        validate_event_sequence(all_events)

        return target_events

    @classmethod
    def reconstruct_session(
        cls,
        db_path: str,
        run_id: str,
    ) -> ReconstructedSession:
        """
        Reconstruct a ReconstructedSession for run_id from db_path.

        Read-only.
        """
        events = cls.load_events_for_run(db_path, run_id)
        if not events:
            return ReconstructedSession(run_id=run_id)

        system_prompt = ""
        user_prompt = ""
        messages: List[LLMMessage] = []
        completed_tool_calls: Dict[str, ToolResult] = {}
        pending_tool_calls: Dict[str, ToolCall] = {}
        current_state = RunState.PENDING

        for event in events:
            current_state = validate_state_transition(current_state, event)
            evt_type = event.event_type
            payload = event.payload

            if evt_type in (
                CheckpointEventType.TASK_START,
                CheckpointEventType.RUN_STARTED,
            ):
                system_prompt = payload.get("system_prompt", payload.get("task_context", ""))
                user_prompt = payload.get("user_prompt", "")
                messages = [
                    LLMMessage(role=MessageRole.SYSTEM, content=system_prompt),
                    LLMMessage(role=MessageRole.USER, content=user_prompt),
                ]

            elif evt_type == CheckpointEventType.LLM_RESPONDED:
                content = payload.get("content")
                tool_calls_raw = payload.get("tool_calls", [])

                assistant_tool_calls: List[AssistantToolCall] = []
                for tc in tool_calls_raw:
                    cid = tc["call_id"]
                    name = tc["name"]
                    args = tc.get("arguments", {})
                    assistant_tool_calls.append(
                        AssistantToolCall(call_id=cid, name=name, arguments=args)
                    )

                    t_call = ToolCall(
                        name=name,
                        arguments=args,
                        call_id=cid,
                        run_id=run_id,
                    )

                    if "idempotency_key" in tc:
                        t_call.idempotency_key = tc["idempotency_key"]

                    pending_tool_calls[cid] = t_call

                messages.append(
                    LLMMessage(
                        role=MessageRole.ASSISTANT,
                        content=content,
                        tool_calls=assistant_tool_calls,
                    )
                )

            elif evt_type == CheckpointEventType.TOOL_RESULT_RECEIVED:
                call_id = payload.get("call_id", "")
                result_data = payload.get("result", {})
                status_str = payload.get("status", ToolStatus.SUCCESS.value)

                # Remove from pending if present
                pending_tool_calls.pop(call_id, None)

                # Construct ToolResult
                if isinstance(result_data, dict) and "call_id" in result_data:
                    tool_result = ToolResult.from_dict(result_data)
                else:
                    tool_result = ToolResult(
                        call_id=call_id,
                        run_id=run_id,
                        tool_name=payload.get("tool_name", ""),
                        status=ToolStatus(status_str),
                        data=result_data.get("data") if isinstance(result_data, dict) else result_data,
                    )

                completed_tool_calls[call_id] = tool_result

                tool_response_content: Dict[str, Any] = {
                    "status": tool_result.status.value,
                    "data": tool_result.data,
                }
                if tool_result.error:
                    tool_response_content["error"] = {
                        "code": tool_result.error.code,
                        "message": tool_result.error.message,
                    }

                messages.append(
                    LLMMessage(
                        role=MessageRole.TOOL,
                        content=json.dumps(tool_response_content),
                        tool_call_id=call_id,
                        tool_name=tool_result.tool_name,
                    )
                )

        next_sequence_id = max(e.sequence_id for e in events) + 1 if events else 1

        return ReconstructedSession(
            run_id=run_id,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            messages=messages,
            last_state=current_state,
            completed_tool_calls=completed_tool_calls,
            pending_tool_calls=pending_tool_calls,
            next_sequence_id=next_sequence_id,
            last_event=events[-1] if events else None,
        )
