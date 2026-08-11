import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from src.core.errors import AgentException

@dataclass
class ToolCall:
    """Represents a request to execute a specific tool with arguments."""
    name: str
    arguments: Dict[str, Any]
    call_id: str
    run_id: str
    operation_key: str = field(init=False)
    idempotency_key: str = field(init=False)
    
    def __post_init__(self):
        # Generate an operation key based on tool name and its arguments
        hasher = hashlib.md5()
        hasher.update(self.name.encode('utf-8'))
        args_str = json.dumps(self.arguments, sort_keys=True)
        hasher.update(args_str.encode('utf-8'))
        self.operation_key = hasher.hexdigest()
        
        # Idempotency key is scoped to the specific run to prevent duplicate side effects within one run
        self.idempotency_key = f"{self.run_id}_{self.operation_key}"
        
from enum import Enum

class ToolStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"

@dataclass
class ToolResult:
    """Represents the standardized output of a tool execution."""
    call_id: str
    run_id: str
    tool_name: str
    status: ToolStatus
    data: Optional[Any] = None
    error: Optional[AgentException] = None
    duration_ms: int = 0
    logs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "call_id": self.call_id,
            "run_id": self.run_id,
            "tool_name": self.tool_name,
            "status": self.status.value,
            "data": self.data,
            "error": {
                "message": self.error.message,
                "code": self.error.code,
                "retryable": self.error.retryable,
                "details": self.error.details
            } if self.error else None,
            "duration_ms": self.duration_ms,
            "logs": self.logs
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ToolResult':
        error = None
        if data.get("error"):
            e_data = data["error"]
            error = AgentException(
                message=e_data.get("message", ""),
                code=e_data.get("code", "UNKNOWN_ERROR"),
                retryable=e_data.get("retryable", False),
                details=e_data.get("details", {})
            )
        return cls(
            call_id=data["call_id"],
            run_id=data["run_id"],
            tool_name=data["tool_name"],
            status=ToolStatus(data["status"]),
            data=data.get("data"),
            error=error,
            duration_ms=data.get("duration_ms", 0),
            logs=data.get("logs", [])
        )
