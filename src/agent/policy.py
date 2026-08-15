from dataclasses import dataclass
from typing import Union

@dataclass
class RunPolicy:
    """Safety limits to prevent infinite LLM reasoning loops or runaway costs."""
    max_iterations: int = 20
    max_tool_calls: int = 30
    timeout_seconds: Union[int, float] = 300 # 5 minutes

    def __post_init__(self):
        if self.max_iterations < 0:
            raise ValueError(f"max_iterations must be non-negative, got {self.max_iterations}")
        if self.max_tool_calls < 0:
            raise ValueError(f"max_tool_calls must be non-negative, got {self.max_tool_calls}")
        if self.timeout_seconds <= 0:
            raise ValueError(f"timeout_seconds must be positive, got {self.timeout_seconds}")

