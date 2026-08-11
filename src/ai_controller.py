import os
import logging
import json
import google.generativeai as genai

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

    def plan_action(self, user_prompt: str, tools_schema: list[dict] = None) -> dict:
        """
        Uses Gemini Function Calling to select the appropriate tool and extract arguments.
        """
        if not hasattr(self, 'model'):
            return {"error": "AI model not initialized"}
            
        if not tools_schema:
            logger.warning("No tools schema provided to AI.")
            return {"error": "No tools available"}

        system_instruction = "You are the AI Controller. Select the most appropriate tool to handle the user's request."
        
        # Convert our schema to Gemini's format
        function_declarations = []
        for tool in tools_schema:
            function_declarations.append({
                "name": tool["name"],
                "description": tool["description"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string", 
                            "description": "The URL extracted from the prompt"
                        }
                    },
                    "required": ["url"]
                }
            })
            
        tools = [{"function_declarations": function_declarations}]
        
        try:
            # We don't use response_mime_type="application/json" anymore
            response = self.model.generate_content(
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
                    return {
                        "action": func_name,
                        "url": args.get("url")
                    }
                    
            logger.warning("AI did not return a function call.")
            return {"action": "unknown", "url": None}
            
        except Exception as e:
            logger.error(f"Error during AI function calling: {e}")
            return {"error": str(e)}

