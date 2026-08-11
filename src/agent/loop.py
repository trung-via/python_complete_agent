import logging
import asyncio
import time
from typing import List, Optional

from src.agent.messages import LLMMessage, MessageRole
from src.agent.policy import RunPolicy
from src.providers.base import LLMProvider, LLMResponse
from src.core.tool_executor import ToolExecutor
from src.core.tool_registry import ToolRegistry
from src.core.checkpoint import CheckpointManager
from src.core.types import ToolCall, ToolResult, ToolStatus
from src.core.errors import SystemStateError

logger = logging.getLogger(__name__)

class AgentLoop:
    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_executor: ToolExecutor,
        tool_registry: ToolRegistry,
        checkpoints: CheckpointManager,
        policy: RunPolicy = RunPolicy()
    ):
        self.llm = llm_provider
        self.tool_executor = tool_executor
        self.tool_registry = tool_registry
        self.checkpoints = checkpoints
        self.policy = policy
        
    async def run(self, run_id: str, system_prompt: str, user_prompt: str) -> Optional[str]:
        """
        Executes the closed-loop autonomous agent reasoning cycle.
        Returns the final answer text, or None if halted/failed.
        """
        start_time = time.time()
        iterations = 0
        total_tool_calls = 0
        
        messages: List[LLMMessage] = [
            LLMMessage(role=MessageRole.SYSTEM, content=system_prompt),
            LLMMessage(role=MessageRole.USER, content=user_prompt)
        ]
        
        self.checkpoints.log_run_started(run_id, system_prompt, user_prompt)
        tools_schema = self.tool_registry.get_tools_schema()
        
        while True:
            # 1. Check Safety Limits
            if iterations >= self.policy.max_iterations:
                logger.warning(f"Run {run_id} halted: Max iterations ({self.policy.max_iterations}) reached.")
                self.checkpoints.log_run_halted(run_id, "MAX_ITERATIONS_REACHED")
                return None
                
            if time.time() - start_time > self.policy.timeout_seconds:
                logger.warning(f"Run {run_id} halted: Timeout ({self.policy.timeout_seconds}s) reached.")
                self.checkpoints.log_run_halted(run_id, "TIMEOUT_REACHED")
                return None
                
            iterations += 1
            self.checkpoints.log_llm_requested(run_id, iterations)
            
            # 2. Invoke LLM
            try:
                response: LLMResponse = await self.llm.generate(messages, tools_schema)
                self.checkpoints.log_llm_responded(run_id, iterations, response.content, len(response.tool_calls))
            except Exception as e:
                logger.error(f"LLM Provider failed: {e}")
                self.checkpoints.log_run_failed(run_id, str(e))
                return None
                
            # Append ASSISTANT message
            msg_tool_calls = [{"name": tc.name, "arguments": tc.arguments} for tc in response.tool_calls]
            messages.append(LLMMessage(
                role=MessageRole.ASSISTANT,
                content=response.content,
                tool_calls=msg_tool_calls
            ))
            
            # 3. Check for Final Answer
            if not response.tool_calls:
                # If there are no tool calls, this is the final answer
                self.checkpoints.log_llm_final_response(run_id, response.content)
                self.checkpoints.log_run_completed(run_id)
                return response.content
                
            # 4. Execute Tools
            for p_call in response.tool_calls:
                total_tool_calls += 1
                if total_tool_calls > self.policy.max_tool_calls:
                    logger.warning(f"Run {run_id} halted: Max tool calls ({self.policy.max_tool_calls}) reached.")
                    self.checkpoints.log_run_halted(run_id, "MAX_TOOL_CALLS_REACHED")
                    return None
                    
                # Convert to canonical ToolCall
                call = ToolCall(
                    name=p_call.name,
                    arguments=p_call.arguments,
                    call_id=p_call.provider_call_id,
                    run_id=run_id
                )
                
                try:
                    result: ToolResult = await self.tool_executor.execute(call)
                    self.checkpoints.log_tool_result_received(run_id, call.call_id, result.status.value)
                    
                    # Feed result back to LLM
                    tool_response_content = {
                        "status": result.status.value,
                        "data": result.data,
                    }
                    if result.error:
                        tool_response_content["error"] = {
                            "code": result.error.code,
                            "message": result.error.message
                        }
                        
                    import json
                    messages.append(LLMMessage(
                        role=MessageRole.TOOL,
                        content=json.dumps(tool_response_content),
                        tool_call_id=call.call_id,
                        tool_name=call.name
                    ))
                    
                except SystemStateError as e:
                    # Critical infrastructure failure, must halt immediately
                    logger.critical(f"SystemStateError during tool execution: {e}")
                    self.checkpoints.log_run_halted(run_id, f"SYSTEM_STATE_ERROR: {e}")
                    return None
