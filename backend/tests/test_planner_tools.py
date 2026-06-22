"""Tests for Planner tool visibility.

The Planner used to describe only 4 tools in its system prompt
(crawler / news_search / rag_retrieve / llm_synthesize), so the registered
financial/stock/news_summary tools could never be planned. These tests pin the
prompt, the validation allowlist, and the executor-facing registry together so
the "9 tools" can actually be selected and run.
"""

import re
from unittest.mock import MagicMock

from app.core.planner import PLANNER_SYSTEM, PlannerAgent
from app.tools.financial_report_tool import FinancialAnalysisTool, FinancialReportTool
from app.tools.news_summary_tool import NewsSummaryTool
from app.tools.registry import ToolRegistry
from app.tools.stock_price_tool import StockHistoryTool, StockPriceTool

# Tools the Planner emits that are backed by a registered tool instance
# (``llm_synthesize`` is handled specially by the executor, not via the registry).
_REGISTERED_PLANNER_TOOLS = {
    "stock_price",
    "stock_history",
    "financial_report",
    "financial_analysis",
    "news_summary",
    "news_search",
    "crawler",
    "rag_retrieve",
}


def _planner() -> PlannerAgent:
    return PlannerAgent(llm_client=MagicMock(), router=None)


def _prompt_tool_names() -> set[str]:
    # Tool entries look like: - "stock_price": ...
    return set(re.findall(r'-\s+"([a-z_]+)":', PLANNER_SYSTEM))


def test_prompt_exposes_all_nine_tools():
    names = _prompt_tool_names()
    expected = _REGISTERED_PLANNER_TOOLS | {"llm_synthesize"}
    assert expected <= names, f"prompt missing tools: {expected - names}"


def test_prompt_tools_are_all_in_validation_allowlist():
    for name in _prompt_tool_names():
        assert name in PlannerAgent._VALID_TOOLS


def test_newly_exposed_tools_are_registry_resolvable():
    """Every non-synthesize tool the Planner can emit must resolve in the
    same registry the executor uses, otherwise the plan would fail at runtime."""
    registry = ToolRegistry()
    for tool in [
        StockPriceTool(api_key=""),
        StockHistoryTool(api_key=""),
        FinancialReportTool(api_key=""),
        FinancialAnalysisTool(api_key=""),
        NewsSummaryTool(api_key=""),
    ]:
        registry.register(tool)

    for name in (
        "stock_price",
        "stock_history",
        "financial_report",
        "financial_analysis",
        "news_summary",
    ):
        assert registry.get(name) is not None


def test_financial_plan_tools_are_preserved_not_coerced():
    planner = _planner()
    subtasks = planner._build_subtasks(
        {
            "subtasks": [
                {
                    "task_id": "t1",
                    "tool_name": "stock_price",
                    "params": {"symbol": "AAPL"},
                },
                {
                    "task_id": "t2",
                    "tool_name": "financial_analysis",
                    "params": {"symbol": "AAPL", "analysis_type": "valuation"},
                },
                {
                    "task_id": "t3",
                    "tool_name": "llm_synthesize",
                    "depends_on": ["t1", "t2"],
                },
            ]
        }
    )
    planner._validate_dag(subtasks)
    assert [s.tool_name for s in subtasks] == [
        "stock_price",
        "financial_analysis",
        "llm_synthesize",
    ]
