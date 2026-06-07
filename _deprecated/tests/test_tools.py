"""
Component Tests - Tools
Verifies: ToolRegistry, tool execution, BaseTool interface
All tests run offline
"""
import pytest
from tools.base_tool import BaseTool, ToolResult
from tools.registry import ToolRegistry


@pytest.fixture
def fresh_registry():
    """Fresh ToolRegistry for each test"""
    ToolRegistry._instance = None
    registry = ToolRegistry()
    yield registry
    ToolRegistry._instance = None


def test_tool_registry_register(fresh_registry):
    """Tools can be registered and retrieved"""

    class DummyTool(BaseTool):
        name = "dummy"
        description = "Test tool"

        async def execute(self, **kwargs) -> ToolResult:
            return ToolResult(success=True, data="ok", tool_name=self.name)

    tool = DummyTool()
    fresh_registry.register(tool)

    assert "dummy" in fresh_registry
    assert fresh_registry.get("dummy") is tool


def test_tool_registry_get_missing(fresh_registry):
    """Getting non-existent tool returns None"""
    assert fresh_registry.get("nonexistent") is None


def test_tool_registry_list_tools(fresh_registry):
    """list_tools returns schema for all registered tools"""

    class ToolA(BaseTool):
        name = "tool_a"
        description = "Tool A"

        async def execute(self, **kwargs) -> ToolResult:
            return ToolResult(success=True, tool_name=self.name)

    class ToolB(BaseTool):
        name = "tool_b"
        description = "Tool B"

        async def execute(self, **kwargs) -> ToolResult:
            return ToolResult(success=True, tool_name=self.name)

    fresh_registry.register(ToolA())
    fresh_registry.register(ToolB())

    tools = fresh_registry.list_tools()
    names = [t["name"] for t in tools]

    assert "tool_a" in names
    assert "tool_b" in names
    assert len(tools) == 2


def test_tool_registry_get_all(fresh_registry):
    """get_all returns dict of all tools"""

    class DummyTool(BaseTool):
        name = "dummy"
        description = "Test"

        async def execute(self, **kwargs) -> ToolResult:
            return ToolResult(success=True, tool_name=self.name)

    fresh_registry.register(DummyTool())

    all_tools = fresh_registry.get_all()
    assert "dummy" in all_tools
    assert isinstance(all_tools["dummy"], DummyTool)


@pytest.mark.asyncio
async def test_tool_execute_returns_toolresult(fresh_registry):
    """Tool execute must return ToolResult"""

    class EchoTool(BaseTool):
        name = "echo"
        description = "Echo tool"

        async def execute(self, **kwargs) -> ToolResult:
            return ToolResult(success=True, data=kwargs, tool_name=self.name)

    fresh_registry.register(EchoTool())
    tool = fresh_registry.get("echo")

    result = await tool.execute(query="test", top_k=3)

    assert isinstance(result, ToolResult)
    assert result.success is True
    assert result.tool_name == "echo"
    assert result.data == {"query": "test", "top_k": 3}


@pytest.mark.asyncio
async def test_tool_error_handling(fresh_registry):
    """Tool that raises exception should be catchable"""

    class FailTool(BaseTool):
        name = "fail"
        description = "Always fails"

        async def execute(self, **kwargs) -> ToolResult:
            raise RuntimeError("Tool failure")

    fresh_registry.register(FailTool())
    tool = fresh_registry.get("fail")

    with pytest.raises(RuntimeError, match="Tool failure"):
        await tool.execute()


def test_tool_result_str():
    """ToolResult __str__ should work for both success and failure"""
    ok = ToolResult(success=True, data="some data", tool_name="test")
    assert "OK" in str(ok)

    fail = ToolResult(success=False, error="something broke", tool_name="test")
    assert "ERROR" in str(fail)


def test_tool_schema():
    """to_schema returns name and description"""

    class SchemaTool(BaseTool):
        name = "schema_test"
        description = "A tool for schema testing"

        async def execute(self, **kwargs) -> ToolResult:
            return ToolResult(success=True, tool_name=self.name)

    tool = SchemaTool()
    schema = tool.to_schema()

    assert schema["name"] == "schema_test"
    assert schema["description"] == "A tool for schema testing"
