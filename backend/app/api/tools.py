"""
Tools API routes - 提供工具查询和执行接口
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import UserResponse
from app.auth.roles import Role
from app.tools.financial_report_tool import FinancialAnalysisTool, FinancialReportTool
from app.tools.news_summary_tool import NewsAnalysisTool, NewsSummaryTool
from app.tools.registry import ToolRegistry
from app.tools.stock_price_tool import StockHistoryTool, StockPriceTool
from app.utils.logger import get_logger

logger = get_logger("api.tools")

router = APIRouter(prefix="/tools", tags=["tools"])


# ============================================================
# Pydantic Models
# ============================================================

class ToolInfo(BaseModel):
    """Tool information"""
    name: str
    description: str


class ToolListResponse(BaseModel):
    """Response model for tool list"""
    tools: list[ToolInfo]
    total: int


class StockPriceRequest(BaseModel):
    """Request model for stock price query"""
    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol (e.g., AAPL, TSLA)")


class StockPriceResponse(BaseModel):
    """Response model for stock price"""
    symbol: str
    name: str = ""
    price: float
    change: float
    change_percent: float
    volume: int = 0
    market_cap: float = 0
    pe_ratio: float = 0
    high_52w: float = 0
    low_52w: float = 0
    timestamp: str
    source: str


class StockHistoryRequest(BaseModel):
    """Request model for stock history"""
    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol")
    period: str = Field(default="1m", description="Time period (1d, 1w, 1m, 3m, 6m, 1y)")


class StockHistoryResponse(BaseModel):
    """Response model for stock history"""
    symbol: str
    period: str
    history: list[dict[str, Any]]
    source: str = ""


class FinancialReportRequest(BaseModel):
    """Request model for financial report"""
    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol")
    report_type: str = Field(default="summary", description="Report type (summary, detailed, quarterly)")


class FinancialReportResponse(BaseModel):
    """Response model for financial report"""
    symbol: str
    name: str = ""
    sector: str = ""
    industry: str = ""
    financials: dict[str, Any] = {}
    quarterly: dict[str, Any] = {}
    timestamp: str
    source: str


class FinancialAnalysisRequest(BaseModel):
    """Request model for financial analysis"""
    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol")
    analysis_type: str = Field(default="comprehensive", description="Analysis type (comprehensive, valuation, profitability, growth)")


class FinancialAnalysisResponse(BaseModel):
    """Response model for financial analysis"""
    symbol: str
    analysis_type: str
    analysis: dict[str, Any]
    timestamp: str


class NewsRequest(BaseModel):
    """Request model for news query"""
    query: str = Field(..., min_length=1, max_length=200, description="Search query")
    max_results: int = Field(default=5, ge=1, le=20, description="Maximum results")


class NewsResponse(BaseModel):
    """Response model for news"""
    query: str
    results: list[dict[str, Any]]
    summary: str
    total_results: int
    timestamp: str
    source: str = ""


class NewsAnalysisRequest(BaseModel):
    """Request model for news analysis"""
    query: str = Field(..., min_length=1, max_length=200, description="Search query")
    period: str = Field(default="7d", description="Analysis period (1d, 7d, 30d)")


class NewsAnalysisResponse(BaseModel):
    """Response model for news analysis"""
    query: str
    period: str
    analysis: dict[str, Any]
    timestamp: str


# ============================================================
# API Routes
# ============================================================

@router.get("/list", response_model=ToolListResponse)
async def list_tools(current_user: UserResponse = Depends(get_current_user)):
    """List all available tools"""
    try:
        registry = ToolRegistry()
        tools = registry.list_tools()
        return ToolListResponse(
            tools=[ToolInfo(name=t["name"], description=t["description"]) for t in tools],
            total=len(tools),
        )
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/stock/price", response_model=StockPriceResponse)
async def get_stock_price(request: StockPriceRequest, current_user: UserResponse = Depends(require_role(Role.ADMIN, Role.ANALYST))):
    """Get real-time stock price"""
    try:
        tool = StockPriceTool()
        result = await tool.execute(symbol=request.symbol)

        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)

        data = result.data
        return StockPriceResponse(
            symbol=data.get("symbol", request.symbol),
            name=data.get("name", ""),
            price=data.get("price", 0),
            change=data.get("change", 0),
            change_percent=data.get("change_percent", 0),
            volume=data.get("volume", 0),
            market_cap=data.get("market_cap", 0),
            pe_ratio=data.get("pe_ratio", 0),
            high_52w=data.get("52w_high", 0),
            low_52w=data.get("52w_low", 0),
            timestamp=data.get("timestamp", ""),
            source=data.get("source", ""),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stock price: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/stock/history", response_model=StockHistoryResponse)
async def get_stock_history(request: StockHistoryRequest, current_user: UserResponse = Depends(require_role(Role.ADMIN, Role.ANALYST))):
    """Get historical stock data"""
    try:
        tool = StockHistoryTool()
        result = await tool.execute(symbol=request.symbol, period=request.period)

        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)

        data = result.data
        return StockHistoryResponse(
            symbol=data.get("symbol", request.symbol),
            period=data.get("period", request.period),
            history=data.get("history", []),
            source=data.get("source", ""),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stock history: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/financial/report", response_model=FinancialReportResponse)
async def get_financial_report(request: FinancialReportRequest, current_user: UserResponse = Depends(require_role(Role.ADMIN, Role.ANALYST))):
    """Get financial report for a company"""
    try:
        tool = FinancialReportTool()
        result = await tool.execute(symbol=request.symbol, report_type=request.report_type)

        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)

        data = result.data
        return FinancialReportResponse(
            symbol=data.get("symbol", request.symbol),
            name=data.get("name", ""),
            sector=data.get("sector", ""),
            industry=data.get("industry", ""),
            financials=data.get("financials", {}),
            quarterly=data.get("quarterly", {}),
            timestamp=data.get("timestamp", ""),
            source=data.get("source", ""),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting financial report: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/financial/analysis", response_model=FinancialAnalysisResponse)
async def get_financial_analysis(request: FinancialAnalysisRequest, current_user: UserResponse = Depends(require_role(Role.ADMIN, Role.ANALYST))):
    """Get financial analysis for a company"""
    try:
        tool = FinancialAnalysisTool()
        result = await tool.execute(symbol=request.symbol, analysis_type=request.analysis_type)

        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)

        data = result.data
        return FinancialAnalysisResponse(
            symbol=data.get("symbol", request.symbol),
            analysis_type=data.get("analysis_type", request.analysis_type),
            analysis=data.get("analysis", {}),
            timestamp=data.get("timestamp", ""),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting financial analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/news/search", response_model=NewsResponse)
async def search_news(request: NewsRequest, current_user: UserResponse = Depends(require_role(Role.ADMIN, Role.ANALYST))):
    """Search for news articles"""
    try:
        tool = NewsSummaryTool()
        result = await tool.execute(query=request.query, max_results=request.max_results)

        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)

        data = result.data
        return NewsResponse(
            query=data.get("query", request.query),
            results=data.get("results", []),
            summary=data.get("summary", ""),
            total_results=data.get("total_results", 0),
            timestamp=data.get("timestamp", ""),
            source=data.get("source", ""),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching news: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/news/analysis", response_model=NewsAnalysisResponse)
async def get_news_analysis(request: NewsAnalysisRequest, current_user: UserResponse = Depends(require_role(Role.ADMIN, Role.ANALYST))):
    """Get news sentiment analysis"""
    try:
        tool = NewsAnalysisTool()
        result = await tool.execute(query=request.query, period=request.period)

        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)

        data = result.data
        return NewsAnalysisResponse(
            query=data.get("query", request.query),
            period=data.get("period", request.period),
            analysis=data.get("analysis", {}),
            timestamp=data.get("timestamp", ""),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting news analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
