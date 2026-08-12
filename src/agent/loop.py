import asyncio
import json
import logging
import time
from typing import List, Optional

from src.agent.messages import AssistantToolCall, LLMMessage, MessageRole
from src.agent.policy import RunPolicy
from src.core.checkpoint import CheckpointManager
from src.core.errors import AgentException, SystemStateError
from src.core.tool_executor import ToolExecutor
from src.core.tool_registry import ToolRegistry
from src.core.types import ToolCall, ToolResult, ToolStatus
from src.providers.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class AgentLoop:
    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_executor: ToolExecutor,
        tool_registry: ToolRegistry,
        checkpoints: CheckpointManager,
        policy: RunPolicy = RunPolicy(),
    ):
        self.llm = llm_provider
        self.tool_executor = tool_executor
        self.tool_registry = tool_registry
        self.checkpoints = checkpoints
        self.policy = policy

    async def run(self, run_id: str, system_prompt: str, user_prompt: str) -> Optional[str]:
        """
        Executes the closed-loop autonomous agent reasoning cycle with a hard timeout.
        Returns the final answer text, or None if halted/failed.
        """
        try:
            return await asyncio.wait_for(
                self._run_internal(run_id, system_prompt, user_prompt),
                timeout=self.policy.timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Run {run_id} halted: Hard timeout ({self.policy.timeout_seconds}s) reached.")
            self.checkpoints.log_run_halted(run_id, "TIMEOUT_REACHED")
            return None

    async def resume(self, run_id: str) -> Optional[str]:
        """
        Resume an interrupted run_id using ReplayEngine.

        Restores messages, pending tool calls, and LLM state, then executes
        remaining tools and continues LLM loop without duplicate executions.
        """
        try:
            return await asyncio.wait_for(
                self._resume_internal(run_id),
                timeout=self.policy.timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Resumed run {run_id} halted: Hard timeout ({self.policy.timeout_seconds}s) reached.")
            self.checkpoints.log_run_halted(run_id, "TIMEOUT_REACHED")
            return None

    async def _run_internal(self, run_id: str, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Internal run loop without timeout wrapping."""
        iterations = 0
        total_tool_calls = 0

        messages: List[LLMMessage] = [
            LLMMessage(role=MessageRole.SYSTEM, content=system_prompt),
            LLMMessage(role=MessageRole.USER, content=user_prompt),
        ]

        self.checkpoints.log_run_started(run_id, system_prompt, user_prompt)
        tools_schema = self.tool_registry.get_tools_schema()

        while True:
            # 1. Check Safety Limits
            if iterations >= self.policy.max_iterations:
                logger.warning(f"Run {run_id} halted: Max iterations ({self.policy.max_iterations}) reached.")
                self.checkpoints.log_run_halted(run_id, "MAX_ITERATIONS_REACHED")
                return None

            iterations += 1
            self.checkpoints.log_llm_requested(run_id, iterations)

            # 2. Invoke LLM
            try:
                response: LLMResponse = await self.llm.generate(messages, tools_schema)
                tool_calls_payload = [
                    {
                        "call_id": tc.provider_call_id,
                        "name": tc.name,
                        "arguments": tc.arguments,
                    }
                    for tc in response.tool_calls
                ]
                self.checkpoints.log_llm_responded(
                    run_id,
                    iterations,
                    response.content,
                    len(response.tool_calls),
                    tool_calls=tool_calls_payload,
                )
            except SystemStateError as e:
                logger.critical(f"FATAL: System state error in LLM Provider: {e}")
                self.checkpoints.log_run_halted(run_id, f"SYSTEM_STATE_ERROR: {e}")
                raise
            except AgentException as e:
                logger.error(f"LLM Provider recoverable failure: {e}")
                self.checkpoints.log_run_failed(run_id, str(e))
                return None
            except Exception as e:
                logger.error(f"Unexpected LLM Provider failure: {e}", exc_info=True)
                self.checkpoints.log_run_failed(run_id, str(e))
                return None

            # Append ASSISTANT message
            msg_tool_calls = [
                AssistantToolCall(call_id=tc.provider_call_id, name=tc.name, arguments=tc.arguments)
                for tc in response.tool_calls
            ]
            messages.append(
                LLMMessage(
                    role=MessageRole.ASSISTANT,
                    content=response.content,
                    tool_calls=msg_tool_calls,
                )
            )

            # 3. Check for Final Answer
            if not response.tool_calls:
                self.checkpoints.log_llm_final_response(run_id, response.content)
                self.checkpoints.log_run_completed(run_id)
                return response.content

            # 4. Execute Tools
            for idx, p_call in enumerate(response.tool_calls):
                total_tool_calls += 1
                if total_tool_calls > self.policy.max_tool_calls:
                    logger.warning(f"Run {run_id} halted: Max tool calls ({self.policy.max_tool_calls}) reached.")
                    self.checkpoints.log_run_halted(run_id, "MAX_TOOL_CALLS_REACHED")
                    return None

                call = ToolCall(
                    name=p_call.name,
                    arguments=p_call.arguments,
                    call_id=p_call.provider_call_id,
                    run_id=run_id,
                )

                try:
                    result: ToolResult = await self.tool_executor.execute(call)
                    is_last_in_batch = idx == len(response.tool_calls) - 1
                    self.checkpoints.log_tool_result_received(
                        run_id,
                        call.call_id,
                        result.status.value,
                        tool_name=call.name,
                        result=result.to_dict(),
                        iteration_complete=is_last_in_batch,
                    )

                    tool_response_content = {
                        "status": result.status.value,
                        "data": result.data,
                    }
                    if result.error:
                        tool_response_content["error"] = {
                            "code": result.error.code,
                            "message": result.error.message,
                        }

                    messages.append(
                        LLMMessage(
                            role=MessageRole.TOOL,
                            content=json.dumps(tool_response_content),
                            tool_call_id=call.call_id,
                            tool_name=call.name,
                        )
                    )

                except SystemStateError as e:
                    logger.critical(f"SystemStateError during tool execution: {e}")
                    self.checkpoints.log_run_halted(run_id, f"SYSTEM_STATE_ERROR: {e}")
                    return None

    async def _resume_internal(self, run_id: str) -> Optional[str]:
        """Internal resume implementation via ReplayEngine."""
        from src.agent.replay_engine import ReplayEngine
        from src.core.checkpoint_contract import RunState

        session = ReplayEngine.reconstruct_session(
            self.checkpoints.db_path, run_id
        )

        if session.last_state == RunState.COMPLETED:
            for msg in reversed(session.messages):
                if msg.role == MessageRole.ASSISTANT and msg.content:
                    return msg.content
            return None

        if session.last_state in (RunState.FAILED, RunState.HALTED):
            return None

        messages = list(session.messages)
        tools_schema = self.tool_registry.get_tools_schema()
        total_tool_calls = len(session.completed_tool_calls) + len(session.pending_tool_calls)

        # 1. Process pending tool calls if any
        if session.pending_tool_calls:
            pending_items = list(session.pending_tool_calls.items())
            for idx, (cid, p_call) in enumerate(pending_items):
                is_last_in_batch = idx == len(pending_items) - 1
                try:
                    result: ToolResult = await self.tool_executor.execute(p_call)
                    self.checkpoints.log_tool_result_received(
                        run_id=run_id,
                        call_id=cid,
                        status=result.status.value,
                        tool_name=p_call.name,
                        result=result.to_dict(),
                        iteration_complete=is_last_in_batch,
                    )

                    tool_response_content = {
                        "status": result.status.value,
                        "data": result.data,
                    }
                    if result.error:
                        tool_response_content["error"] = {
                            "code": result.error.code,
                            "message": result.error.message,
                        }

                    messages.append(
                        LLMMessage(
                            role=MessageRole.TOOL,
                            content=json.dumps(tool_response_content),
                            tool_call_id=cid,
                            tool_name=p_call.name,
                        )
                    )
                except SystemStateError as e:
                    logger.critical(f"SystemStateError during resumed tool execution: {e}")
                    self.checkpoints.log_run_halted(run_id, f"SYSTEM_STATE_ERROR: {e}")
                    return None

        # 2. Continue main LLM loop from current iteration
        events = ReplayEngine.load_events_for_run(self.checkpoints.db_path, run_id)
        iterations = max(
            [e.payload.get("iteration", 0) for e in events if isinstance(e.payload, dict)]
            or [0]
        )

        while True:
            if iterations >= self.policy.max_iterations:
                logger.warning(f"Run {run_id} halted: Max iterations ({self.policy.max_iterations}) reached.")
                self.checkpoints.log_run_halted(run_id, "MAX_ITERATIONS_REACHED")
                return None

            iterations += 1
            self.checkpoints.log_llm_requested(run_id, iterations)

            try:
                response: LLMResponse = await self.llm.generate(messages, tools_schema)
                tool_calls_payload = [
                    {
                        "call_id": tc.provider_call_id,
                        "name": tc.name,
                        "arguments": tc.arguments,
                    }
                    for tc in response.tool_calls
                ]
                self.checkpoints.log_llm_responded(
                    run_id,
                    iterations,
                    response.content,
                    len(response.tool_calls),
                    tool_calls=tool_calls_payload,
                )
            except SystemStateError as e:
                logger.critical(f"FATAL: System state error in LLM Provider: {e}")
                self.checkpoints.log_run_halted(run_id, f"SYSTEM_STATE_ERROR: {e}")
                raise
            except AgentException as e:
                logger.error(f"LLM Provider recoverable failure: {e}")
                self.checkpoints.log_run_failed(run_id, str(e))
                return None
            except Exception as e:
                logger.error(f"Unexpected LLM Provider failure: {e}", exc_info=True)
                self.checkpoints.log_run_failed(run_id, str(e))
                return None

            msg_tool_calls = [
                AssistantToolCall(call_id=tc.provider_call_id, name=tc.name, arguments=tc.arguments)
                for tc in response.tool_calls
            ]
            messages.append(
                LLMMessage(
                    role=MessageRole.ASSISTANT,
                    content=response.content,
                    tool_calls=msg_tool_calls,
                )
            )

            if not response.tool_calls:
                self.checkpoints.log_llm_final_response(run_id, response.content)
                self.checkpoints.log_run_completed(run_id)
                return response.content

            for idx, p_call in enumerate(response.tool_calls):
                total_tool_calls += 1
                if total_tool_calls > self.policy.max_tool_calls:
                    logger.warning(f"Run {run_id} halted: Max tool calls ({self.policy.max_tool_calls}) reached.")
                    self.checkpoints.log_run_halted(run_id, "MAX_TOOL_CALLS_REACHED")
                    return None

                call = ToolCall(
                    name=p_call.name,
                    arguments=p_call.arguments,
                    call_id=p_call.provider_call_id,
                    run_id=run_id,
                )

                try:
                    result: ToolResult = await self.tool_executor.execute(call)
                    is_last_in_batch = idx == len(response.tool_calls) - 1
                    self.checkpoints.log_tool_result_received(
                        run_id,
                        call.call_id,
                        result.status.value,
                        tool_name=call.name,
                        result=result.to_dict(),
                        iteration_complete=is_last_in_batch,
                    )

                    tool_response_content = {
                        "status": result.status.value,
                        "data": result.data,
                    }
                    if result.error:
                        tool_response_content["error"] = {
                            "code": result.error.code,
                            "message": result.error.message,
                        }

                    messages.append(
                        LLMMessage(
                            role=MessageRole.TOOL,
                            content=json.dumps(tool_response_content),
                            tool_call_id=call.call_id,
                            tool_name=call.name,
                        )
                    )

                except SystemStateError as e:
                    logger.critical(f"SystemStateError during tool execution: {e}")
                    self.checkpoints.log_run_halted(run_id, f"SYSTEM_STATE_ERROR: {e}")
                    return None
