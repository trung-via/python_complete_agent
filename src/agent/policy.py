from dataclasses import dataclass

@dataclass
class RunPolicy:
    """Safety limits to prevent infinite LLM reasoning loops or runaway costs."""
    max_iterations: int = 20
    max_tool_calls: int = 30
    timeout_seconds: int = 300 # 5 minutes
