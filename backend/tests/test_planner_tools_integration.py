"""End-to-end execution regression for the newly-exposed planner tools.

PR #41 only changed the planner prompt, but the point of that change is that
the executor now actually *receives* plans referencing stock_price /
stock_history / financial_report / financial_analysis / news_summary. This test
feeds such a plan through the real ExecutorAgent + real ToolRegistry (mock data
mode, no network / no real LLM) to prove the whole execution chain — parallel
batching, dependency injection, circuit breaker, fallback, synthesis — still
runs cleanly when those tools are selected.
"""

from unittest.mock import AsyncMock

import pytest

from app.core.executor import ExecutorAgent
from app.core.planner import Plan, SubTask
from app.tools.crawler_tool import CrawlerTool
from app.tools.financial_report_tool import FinancialAnalysisTool, FinancialReportTool
from app.tools.news_summary_tool import NewsSummaryTool
from app.tools.news_tool import NewsTool
from app.tools.rag_tool import RAGTool
from app.tools.registry import ToolRegistry
from app.tools.stock_price_tool import StockHistoryTool, StockPriceTool


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    for tool in [
        CrawlerTool(),
        NewsTool(api_key=""),
        RAGTool(),
        StockPriceTool(api_key=""),
        StockHistoryTool(api_key=""),
        FinancialReportTool(api_key=""),
        FinancialAnalysisTool(api_key=""),
        NewsSummaryTool(api_key=""),
    ]:
        registry.register(tool)
    return registry


def _financial_plan() -> Plan:
    return Plan(
        original_query="Is AAPL a good buy right now?",
        subtasks=[
            SubTask("t1", "stock_price", {"symbol": "AAPL"}, "quote"),
            SubTask(
                "t2", "stock_history", {"symbol": "AAPL", "period": "1m"}, "history"
            ),
            SubTask(
                "t3",
                "financial_report",
                {"symbol": "AAPL", "report_type": "summary"},
                "fundamentals",
            ),
            SubTask(
                "t4",
                "financial_analysis",
                {"symbol": "AAPL", "analysis_type": "valuation"},
                "valuation",
            ),
            SubTask("t5", "news_summary", {"query": "Apple AAPL"}, "news"),
            SubTask(
                "t6",
                "llm_synthesize",
                {"prompt": "Summarize"},
                "synthesize",
                depends_on=["t1", "t2", "t3", "t4", "t5"],
            ),
        ],
    )


@pytest.mark.asyncio
async def test_financial_plan_runs_through_executor(monkeypatch):
    monkeypatch.setenv("ALLOW_MOCK_DATA", "true")

    llm = AsyncMock()
    llm.complete = AsyncMock(return_value="SYNTHESIZED ANSWER")
    executor = ExecutorAgent(tool_registry=_registry(), llm_client=llm, router=None)

    result = await executor.execute(_financial_plan())

    # Every subtask produced a TaskResult (nothing silently dropped / crashed).
    assert len(result.task_results) == 6
    by_id = {r.task_id: r for r in result.task_results}

    # The 5 newly-exposed data tools all executed and resolved to their real
    # tool (not coerced, not "not found in registry").
    for tid, tool_name in [
        ("t1", "stock_price"),
        ("t2", "stock_history"),
        ("t3", "financial_report"),
        ("t4", "financial_analysis"),
        ("t5", "news_summary"),
    ]:
        assert by_id[tid].tool_name == tool_name
        assert "not found in registry" not in (by_id[tid].error or "")
        assert by_id[tid].success, f"{tool_name} failed: {by_id[tid].error}"

    # Synthesis ran on top of the gathered data and produced the final answer.
    assert by_id["t6"].success
    assert result.final_answer == "SYNTHESIZED ANSWER"
    assert llm.complete.await_count >= 1
