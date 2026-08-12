import pytest
from src.core.tool_registry import ToolRegistry
from src.core.base_tool import BaseTool
from src.core.types import ToolCall

class DummyTool(BaseTool):
    name = "dummy"
    description = "A dummy tool"
    parameters = {
        "type": "object",
        "properties": {
            "val": {"type": "integer"}
        },
        "required": ["val"]
    }
    
    def get_schema(self):
        return self.parameters
        
    async def execute(self, *args, **kwargs):
        pass

def test_registry_add_and_get():
    registry = ToolRegistry()
    tool = DummyTool()
    registry.register_tool(tool)
    
    assert registry.get_tool("dummy") == tool
    assert registry.get_tool("nonexistent") is None

def test_registry_schema_generation():
    registry = ToolRegistry()
    registry.register_tool(DummyTool())
    
    schemas = registry.get_tools_schema()
    assert len(schemas) == 1
    assert schemas[0]["name"] == "dummy"
    assert "val" in schemas[0]["parameters"]["properties"]

def test_registry_validation():
    registry = ToolRegistry()
    registry.register_tool(DummyTool())
    
    # Valid call
    call = ToolCall(name="dummy", arguments={"val": 5}, call_id="1", run_id="2")
    registry.validate_call(call)  # Should not raise
    
    # Invalid arguments (missing required)
    invalid_call = ToolCall(name="dummy", arguments={}, call_id="1", run_id="2")
    with pytest.raises(ValueError, match="'val' is a required property"):
        registry.validate_call(invalid_call)
        
    # Unregistered tool
    unregistered_call = ToolCall(name="unknown", arguments={"val": 5}, call_id="1", run_id="2")
    with pytest.raises(ValueError, match="not found in registry"):
        registry.validate_call(unregistered_call)
