"""MCP server exposing the ToolRegistry over the Model Context Protocol.

Wraps the same 10 tools the orchestrator uses and serves them via MCP stdio,
so any MCP client (Claude Desktop, Cursor, an agent runtime, ...) can call
them without going through the FastAPI app.

Run from ``backend/``:

    python -m app.mcp_server
"""

import asyncio
import json
import logging
import sys
from dataclasses import asdict
from typing import Any

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from app.tools.base_tool import ToolResult
from app.tools.defaults import register_default_tools
from app.tools.registry import ToolRegistry
from app.utils.logger import get_logger

logger = get_logger("mcp_server")

SERVER_NAME = "smart-finance-agent"

_STRING = {"type": "string"}

# JSON Schema for each tool's inputs. Tools accept **kwargs internally, so the
# schemas are maintained here as the single MCP-facing contract.
TOOL_INPUT_SCHEMAS: dict[str, dict[str, Any]] = {
    "crawler": {
        "type": "object",
        "properties": {"url": {**_STRING, "description": "Web page URL to fetch"}},
        "required": ["url"],
    },
    "news_search": {
        "type": "object",
        "properties": {"query": {**_STRING, "description": "News search keywords"}},
        "required": ["query"],
    },
    "rag_retrieve": {
        "type": "object",
        "properties": {
            "query": {**_STRING, "description": "Question to retrieve context for"},
            "top_k": {
                "type": "integer",
                "description": "Number of chunks to return",
                "default": 5,
            },
        },
        "required": ["query"],
    },
    "stock_price": {
        "type": "object",
        "properties": {"symbol": {**_STRING, "description": "Stock ticker, e.g. AAPL"}},
        "required": ["symbol"],
    },
    "stock_history": {
        "type": "object",
        "properties": {
            "symbol": {**_STRING, "description": "Stock ticker, e.g. AAPL"},
            "period": {
                **_STRING,
                "description": "History window",
                "enum": ["1d", "1w", "1m", "3m", "6m", "1y"],
                "default": "1m",
            },
        },
        "required": ["symbol"],
    },
    "financial_report": {
        "type": "object",
        "properties": {
            "symbol": {**_STRING, "description": "Stock ticker, e.g. AAPL"},
            "report_type": {
                **_STRING,
                "enum": ["summary", "detailed", "quarterly"],
                "default": "summary",
            },
        },
        "required": ["symbol"],
    },
    "financial_analysis": {
        "type": "object",
        "properties": {
            "symbol": {**_STRING, "description": "Stock ticker, e.g. AAPL"},
            "analysis_type": {
                **_STRING,
                "enum": ["comprehensive", "valuation", "profitability", "growth"],
                "default": "comprehensive",
            },
        },
        "required": ["symbol"],
    },
    "news_summary": {
        "type": "object",
        "properties": {
            "query": {**_STRING, "description": "Topic or company to summarize"},
            "max_results": {
                "type": "integer",
                "description": "Max articles to summarize",
                "default": 5,
            },
        },
        "required": ["query"],
    },
    "news_analysis": {
        "type": "object",
        "properties": {
            "query": {**_STRING, "description": "Topic or company to analyze"},
            "period": {
                **_STRING,
                "description": "Analysis window",
                "enum": ["1d", "7d", "30d"],
                "default": "7d",
            },
        },
        "required": ["query"],
    },
    "stock_research": {
        "type": "object",
        "properties": {
            "symbol": {**_STRING, "description": "Stock ticker, e.g. AAPL"},
            "language": {**_STRING, "enum": ["en", "zh"], "default": "en"},
            "use_llm": {
                "type": "boolean",
                "description": "Whether to generate the LLM interpretation section",
                "default": True,
            },
        },
        "required": ["symbol"],
    },
}

_FALLBACK_SCHEMA: dict[str, Any] = {"type": "object", "properties": {}}


def tool_result_to_json(result: ToolResult) -> str:
    """Serialize a ToolResult to a JSON string, tolerating non-JSON data."""
    payload = asdict(result)
    try:
        return json.dumps(payload, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        payload["data"] = str(payload.get("data"))
        return json.dumps(payload, ensure_ascii=False, default=str)


def build_server(registry: ToolRegistry | None = None) -> Server:
    """Build an MCP Server serving every tool registered in ``registry``."""
    if registry is None:
        registry = register_default_tools(ToolRegistry())

    server: Server = Server(SERVER_NAME)

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name=tool.name,
                description=tool.description,
                inputSchema=TOOL_INPUT_SCHEMAS.get(tool.name, _FALLBACK_SCHEMA),
            )
            for tool in registry.get_all().values()
        ]

    @server.call_tool()
    async def call_tool(
        name: str, arguments: dict[str, Any]
    ) -> list[types.TextContent]:
        tool = registry.get(name)
        if tool is None:
            result = ToolResult(
                success=False, error=f"Unknown tool: {name}", tool_name=name
            )
        else:
            try:
                result = await tool.execute(**(arguments or {}))
            except Exception as e:
                logger.error(f"MCP tool '{name}' raised: {e}")
                result = ToolResult(success=False, error=str(e), tool_name=name)
        return [types.TextContent(type="text", text=tool_result_to_json(result))]

    return server


def _route_logs_to_stderr() -> None:
    """stdout carries the MCP JSON-RPC stream; all logs must go to stderr."""
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.StreamHandler) and handler.stream is sys.stdout:
            handler.setStream(sys.stderr)


async def run_stdio() -> None:
    _route_logs_to_stderr()
    server = build_server()
    async with stdio_server() as (read_stream, write_stream):
        logger.info(f"MCP server '{SERVER_NAME}' started on stdio")
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(run_stdio())
