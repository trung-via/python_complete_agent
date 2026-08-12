import os
import logging
import uuid
import json
import google.generativeai as genai
from typing import List, Optional

from src.providers.base import LLMProvider, LLMResponse, ProviderToolCall
from src.agent.messages import LLMMessage, MessageRole
from src.core.errors import AgentException

logger = logging.getLogger(__name__)

class GeminiProvider(LLMProvider):
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key or api_key == "your_gemini_api_key_here":
            logger.warning("GEMINI_API_KEY is not set. GeminiProvider will fail on generation.")
        else:
            genai.configure(api_key=api_key)
            
        self.model_name = os.environ.get("GEMINI_MODEL_NAME", "gemini-1.5-pro-latest")
        
    async def generate(self, messages: List[LLMMessage], tools: List[dict]) -> LLMResponse:
        system_instruction = None
        contents = []
        
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_instruction = msg.content
                continue
                
            if msg.role == MessageRole.USER:
                contents.append({"role": "user", "parts": [msg.content]})
            elif msg.role == MessageRole.ASSISTANT:
                parts = []
                if msg.content:
                    parts.append(msg.content)
                for tc in msg.tool_calls:
                    parts.append({
                        "function_call": {
                            "name": tc.name,
                            "args": tc.arguments
                        }
                    })
                contents.append({"role": "model", "parts": parts})
            elif msg.role == MessageRole.TOOL:
                # Gemini expects function responses
                # We format it to match Gemini's strict requirements
                result = msg.content
                # Attempt to parse as JSON if it's a string, since Gemini expects a struct
                try:
                    if isinstance(result, str):
                        result = json.loads(result)
                except:
                    result = {"result": result}
                    
                contents.append({
                    "role": "function",
                    "parts": [{
                        "functionResponse": {
                            "name": msg.tool_name,
                            "response": result
                        }
                    }]
                })

        # Format tools for Gemini
        function_declarations = []
        for tool in tools:
            function_declarations.append({
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool.get("parameters", {"type": "object", "properties": {}})
            })
            
        gemini_tools = [{"function_declarations": function_declarations}] if function_declarations else None
        
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_instruction
        )
        
        try:
            response = await model.generate_content_async(
                contents=contents,
                tools=gemini_tools
            )
        except Exception as e:
            logger.error(f"Error during Gemini generation: {e}")
            raise AgentException(f"LLM Provider failure: {str(e)}", code="LLM_PROVIDER_ERROR", retryable=True)

        provider_tool_calls = []
        text_content = None
        
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.text:
                    if text_content is None:
                        text_content = part.text
                    else:
                        text_content += "\n" + part.text
                        
                if part.function_call:
                    func_name = part.function_call.name
                    args = dict(part.function_call.args)
                    
                    provider_call_id = getattr(part.function_call, 'id', None)
                    if not provider_call_id:
                        provider_call_id = str(uuid.uuid4())
                        
                    provider_tool_calls.append(ProviderToolCall(
                        provider_call_id=provider_call_id,
                        name=func_name,
                        arguments=args
                    ))

        return LLMResponse(
            provider="gemini",
            provider_response_id=None,  # Gemini Python SDK doesn't consistently expose a response ID
            content=text_content,
            tool_calls=provider_tool_calls,
            finish_reason=str(response.candidates[0].finish_reason) if response.candidates else None,
            usage={} # Usage stats omitted for simplicity, but could be added
        )
