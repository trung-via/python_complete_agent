import os
import logging
import json
import uuid
import google.generativeai as genai
from typing import Optional
from src.core.types import ToolCall
from src.core.errors import AgentException

logger = logging.getLogger(__name__)

class AIController:
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key or api_key == "your_gemini_api_key_here":
            logger.warning("GEMINI_API_KEY is not set or is invalid. AI Controller will not function properly.")
        else:
            genai.configure(api_key=api_key)
            model_name = os.environ.get("GEMINI_MODEL_NAME", "gemini-1.5-pro-latest")
            self.model = genai.GenerativeModel(model_name)
            logger.info(f"AI Controller initialized with Gemini API using model: {model_name}")

    async def plan_action(self, user_prompt: str, tools_schema: list[dict], run_id: str) -> ToolCall:
        """
        Uses Gemini Function Calling to select the appropriate tool and extract arguments.
        Returns a strongly-typed ToolCall object.
        Raises AgentException on failure.
        """
        if not hasattr(self, 'model'):
            raise AgentException("AI model not initialized", code="AI_INIT_ERROR")
            
        if not tools_schema:
            raise AgentException("No tools available to schema", code="AI_SCHEMA_ERROR")

        system_instruction = "You are the AI Controller. Select the most appropriate tool to handle the user's request."
        
        # Convert our schema to Gemini's format
        function_declarations = []
        for tool in tools_schema:
            function_declarations.append({
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool.get("parameters", {"type": "object", "properties": {}})
            })
            
        tools = [{"function_declarations": function_declarations}]
        
        try:
            response = await self.model.generate_content_async(
                system_instruction + "\n\nUser Request: " + user_prompt,
                tools=tools
            )
            
            # Extract function call
            if response.candidates and response.candidates[0].content.parts:
                part = response.candidates[0].content.parts[0]
                if part.function_call:
                    func_name = part.function_call.name
                    args = dict(part.function_call.args)
                    logger.info(f"AI chose tool: {func_name} with args: {args}")
                    
                    # Try to preserve provider-specific call ID if it exists, fallback to UUID
                    provider_call_id = getattr(part.function_call, 'id', None)
                    if not provider_call_id:
                        provider_call_id = str(uuid.uuid4())
                        
                    return ToolCall(
                        name=func_name,
                        arguments=args,
                        call_id=provider_call_id,
                        run_id=run_id
                    )
                    
            logger.warning("AI did not return a function call.")
            raise AgentException("AI did not return a function call", code="AI_NO_FUNCTION_CALL")
            
        except AgentException:
            raise
        except Exception as e:
            logger.error(f"Error during AI function calling: {e}")
            raise AgentException(f"AI planning failed: {str(e)}", code="AI_PLANNING_FAILED", retryable=True)

