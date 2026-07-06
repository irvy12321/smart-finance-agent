"""Tests for the MCP server wrapping ToolRegistry.

Exercises the server end-to-end over an in-memory MCP client session:
tools/list must mirror the registry (names, descriptions, input schemas) and
tools/call must route to BaseTool.execute and serialize ToolResult to JSON.
"""

import json

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from app.mcp_server import (
    TOOL_INPUT_SCHEMAS,
    build_server,
    tool_result_to_json,
)
from app.tools.base_tool import BaseTool, ToolResult
from app.tools.defaults import register_default_tools
from app.tools.registry import ToolRegistry


class EchoTool(BaseTool):
    name = "echo"
    description = "Echoes back the provided message"

    async def execute(self, **kwargs) -> ToolResult:
        message = kwargs.get("message", "")
        if not message:
            return ToolResult(success=False, error="No message", tool_name=self.name)
        return ToolResult(
            success=True, data={"echo": message}, tool_name=self.name, source="test"
        )


class BoomTool(BaseTool):
    name = "boom"
    description = "Always raises"

    async def execute(self, **kwargs) -> ToolResult:
        raise RuntimeError("boom failed")


@pytest.fixture(autouse=True)
def isolated_registry():
    """ToolRegistry is a singleton; keep these tests from leaking into others."""
    registry = ToolRegistry()
    saved = dict(registry.get_all())
    registry._tools.clear()
    yield
    registry._tools.clear()
    registry._tools.update(saved)


def _fresh_registry(*tools: BaseTool) -> ToolRegistry:
    registry = ToolRegistry()
    registry._tools.clear()
    for tool in tools:
        registry.register(tool)
    return registry


@pytest.mark.asyncio
async def test_list_tools_exposes_full_default_registry():
    registry = _fresh_registry()
    register_default_tools(registry)
    server = build_server(registry)

    async with create_connected_server_and_client_session(server) as client:
        result = await client.list_tools()

    listed = {t.name: t for t in result.tools}
    assert set(listed) == set(registry.get_all())
    assert len(listed) == 10
    for name, tool in registry.get_all().items():
        assert listed[name].description == tool.description
        assert listed[name].inputSchema == TOOL_INPUT_SCHEMAS[name]


def test_every_default_tool_has_an_input_schema():
    registry = _fresh_registry()
    register_default_tools(registry)
    for name in registry.get_all():
        schema = TOOL_INPUT_SCHEMAS[name]
        assert schema["type"] == "object"
        assert schema["required"], f"{name} should declare required params"


@pytest.mark.asyncio
async def test_call_tool_routes_to_execute_and_serializes_toolresult():
    server = build_server(_fresh_registry(EchoTool()))

    async with create_connected_server_and_client_session(server) as client:
        result = await client.call_tool("echo", {"message": "hi"})

    payload = json.loads(result.content[0].text)
    assert payload["success"] is True
    assert payload["data"] == {"echo": "hi"}
    assert payload["tool_name"] == "echo"
    assert payload["source"] == "test"


@pytest.mark.asyncio
async def test_call_tool_failure_result_is_reported():
    server = build_server(_fresh_registry(EchoTool()))

    async with create_connected_server_and_client_session(server) as client:
        result = await client.call_tool("echo", {})

    payload = json.loads(result.content[0].text)
    assert payload["success"] is False
    assert "message" in payload["error"].lower()


@pytest.mark.asyncio
async def test_call_tool_exception_is_caught_not_crashing_server():
    server = build_server(_fresh_registry(BoomTool()))

    async with create_connected_server_and_client_session(server) as client:
        result = await client.call_tool("boom", {})

    payload = json.loads(result.content[0].text)
    assert payload["success"] is False
    assert "boom failed" in payload["error"]


@pytest.mark.asyncio
async def test_call_unknown_tool_returns_error_payload():
    server = build_server(_fresh_registry(EchoTool()))

    async with create_connected_server_and_client_session(server) as client:
        result = await client.call_tool("nope", {})

    payload = json.loads(result.content[0].text)
    assert payload["success"] is False
    assert "Unknown tool" in payload["error"]


def test_tool_result_to_json_handles_non_serializable_data():
    result = ToolResult(success=True, data={"obj": object()}, tool_name="x")
    payload = json.loads(tool_result_to_json(result))
    assert payload["success"] is True
    assert isinstance(payload["data"], (str, dict))
