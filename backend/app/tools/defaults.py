"""Default tool registration shared by the orchestrator and the MCP server."""

import os

from app.tools.crawler_tool import CrawlerTool
from app.tools.financial_report_tool import FinancialAnalysisTool, FinancialReportTool
from app.tools.news_summary_tool import NewsAnalysisTool, NewsSummaryTool
from app.tools.news_tool import NewsTool
from app.tools.rag_tool import RAGTool
from app.tools.registry import ToolRegistry
from app.tools.research_tool import StockResearchTool
from app.tools.stock_price_tool import StockHistoryTool, StockPriceTool


def register_default_tools(registry: ToolRegistry) -> ToolRegistry:
    """Register the full default tool set onto ``registry``.

    API keys are read from the environment so the same construction works for
    the in-process orchestrator and the standalone MCP server entrypoint.
    """
    news_api_key = os.getenv("NEWS_API_KEY", "")
    alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    fmp_api_key = os.getenv("FMP_API_KEY", "")

    tools = [
        CrawlerTool(),
        NewsTool(api_key=news_api_key),
        RAGTool(),
        StockPriceTool(api_key=alpha_vantage_key),
        StockHistoryTool(api_key=alpha_vantage_key),
        FinancialReportTool(api_key=fmp_api_key),
        FinancialAnalysisTool(api_key=fmp_api_key),
        NewsSummaryTool(api_key=news_api_key),
        NewsAnalysisTool(),  # NewsAnalysisTool uses NewsSummaryTool internally
        StockResearchTool(),  # full grounded single-stock pipeline as one DAG node
    ]
    for tool in tools:
        registry.register(tool)
    return registry
