"""Tests for StockResearchTool — the DAG-executable wrapper around ResearchService.

Confirms the grounded research pipeline can run as a single ``stock_research``
DAG node (data → indicators → trust → summary) and that a plan using it executes
cleanly through the real ExecutorAgent, without disturbing ResearchService itself.
"""

from unittest.mock import AsyncMock

import pytest

from app.core.executor import ExecutorAgent
from app.core.planner import Plan, SubTask
from app.tools.registry import ToolRegistry
from app.tools.research_tool import StockResearchTool


@pytest.mark.asyncio
async def test_stock_research_returns_grounded_report(monkeypatch):
    monkeypatch.setenv("ALLOW_MOCK_DATA", "true")
    # No real LLM: research should fall back to the deterministic summary.
    result = await StockResearchTool().execute(symbol="AAPL", use_llm=False)

    assert result.success
    assert result.tool_name == "stock_research"
    assert result.source == "stock_research"
    # The wrapped pipeline's structure is preserved in the tool payload.
    for key in ("data", "indicators", "trust", "report", "disclaimer"):
        assert key in result.data
    assert result.data["report"]["key_findings"]


@pytest.mark.asyncio
async def test_stock_research_requires_symbol():
    result = await StockResearchTool().execute(symbol="")
    assert not result.success
    assert "symbol" in result.error.lower()


@pytest.mark.asyncio
async def test_stock_research_node_runs_in_dag(monkeypatch):
    monkeypatch.setenv("ALLOW_MOCK_DATA", "true")
    registry = ToolRegistry()
    registry.register(StockResearchTool())

    llm = AsyncMock()
    llm.complete = AsyncMock(return_value="FINAL")
    executor = ExecutorAgent(tool_registry=registry, llm_client=llm, router=None)

    plan = Plan(
        original_query="Analyze AAPL",
        subtasks=[
            SubTask("t1", "stock_research", {"symbol": "AAPL"}, "full research"),
            SubTask(
                "t2",
                "llm_synthesize",
                {"prompt": "Summarize"},
                "synthesize",
                depends_on=["t1"],
            ),
        ],
    )

    result = await executor.execute(plan)
    by_id = {r.task_id: r for r in result.task_results}

    assert by_id["t1"].tool_name == "stock_research"
    assert by_id["t1"].success
    assert "not found in registry" not in (by_id["t1"].error or "")
    assert by_id["t2"].success
    assert result.final_answer == "FINAL"
