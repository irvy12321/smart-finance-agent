"""
工具模块
"""
from app.tools.base_tool import BaseTool, ToolResult
from app.tools.registry import ToolRegistry
from app.tools.crawler_tool import CrawlerTool
from app.tools.news_tool import NewsTool
from app.tools.rag_tool import RAGTool
from app.tools.stock_price_tool import StockPriceTool, StockHistoryTool
from app.tools.financial_report_tool import FinancialReportTool, FinancialAnalysisTool
from app.tools.news_summary_tool import NewsSummaryTool, NewsAnalysisTool

__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolRegistry",
    "CrawlerTool",
    "NewsTool",
    "RAGTool",
    "StockPriceTool",
    "StockHistoryTool",
    "FinancialReportTool",
    "FinancialAnalysisTool",
    "NewsSummaryTool",
    "NewsAnalysisTool",
]