"""
财务报告分析工具 - 支持财务数据查询和分析
"""

import os
from datetime import datetime

import aiohttp

from app.tools.base_tool import MOCK_WARNING, BaseTool, ToolResult, mock_enabled
from app.utils.logger import get_logger

logger = get_logger("financial_report_tool")

# Financial Modeling Prep API
FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"

# 模拟财务数据（API 不可用时的降级方案）
MOCK_FINANCIAL_DATA = {
    "AAPL": {
        "name": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "financials": {
            "revenue": {"2024": 391.04e9, "2023": 383.29e9, "2022": 394.33e9},
            "net_income": {"2024": 93.74e9, "2023": 96.99e9, "2022": 99.80e9},
            "eps": {"2024": 6.13, "2023": 6.15, "2022": 6.11},
            "pe_ratio": {"2024": 28.5, "2023": 29.2, "2022": 24.8},
            "dividend_yield": {"2024": 0.55, "2023": 0.50, "2022": 0.60},
            "debt_to_equity": {"2024": 1.76, "2023": 1.95, "2022": 2.10},
            "return_on_equity": {"2024": 1.60, "2023": 1.72, "2022": 1.96},
        },
        "quarterly": {
            "Q4 2024": {"revenue": 119.58e9, "net_income": 33.92e9, "eps": 2.18},
            "Q3 2024": {"revenue": 81.80e9, "net_income": 19.88e9, "eps": 1.26},
            "Q2 2024": {"revenue": 85.78e9, "net_income": 21.45e9, "eps": 1.36},
            "Q1 2024": {"revenue": 119.58e9, "net_income": 33.92e9, "eps": 2.18},
        },
    },
    "TSLA": {
        "name": "Tesla Inc.",
        "sector": "Consumer Cyclical",
        "industry": "Auto Manufacturers",
        "financials": {
            "revenue": {"2024": 97.69e9, "2023": 96.77e9, "2022": 81.46e9},
            "net_income": {"2024": 7.13e9, "2023": 14.99e9, "2022": 12.56e9},
            "eps": {"2024": 4.30, "2023": 4.31, "2022": 3.62},
            "pe_ratio": {"2024": 62.3, "2023": 78.5, "2022": 52.4},
            "dividend_yield": {"2024": 0, "2023": 0, "2022": 0},
            "debt_to_equity": {"2024": 0.15, "2023": 0.17, "2022": 0.20},
            "return_on_equity": {"2024": 0.22, "2023": 0.25, "2022": 0.28},
        },
        "quarterly": {
            "Q4 2024": {"revenue": 25.17e9, "net_income": 4.18e9, "eps": 1.19},
            "Q3 2024": {"revenue": 23.35e9, "net_income": 3.50e9, "eps": 1.00},
            "Q2 2024": {"revenue": 24.90e9, "net_income": 3.75e9, "eps": 1.07},
            "Q1 2024": {"revenue": 23.35e9, "net_income": 3.54e9, "eps": 1.01},
        },
    },
    "GOOGL": {
        "name": "Alphabet Inc.",
        "sector": "Communication Services",
        "industry": "Internet Content & Information",
        "financials": {
            "revenue": {"2024": 350.02e9, "2023": 307.39e9, "2022": 282.84e9},
            "net_income": {"2024": 100.12e9, "2023": 73.80e9, "2022": 59.97e9},
            "eps": {"2024": 8.04, "2023": 5.80, "2022": 4.56},
            "pe_ratio": {"2024": 24.8, "2023": 24.5, "2022": 20.2},
            "dividend_yield": {"2024": 0, "2023": 0, "2022": 0},
            "debt_to_equity": {"2024": 0.05, "2023": 0.06, "2022": 0.06},
            "return_on_equity": {"2024": 0.27, "2023": 0.27, "2022": 0.23},
        },
        "quarterly": {
            "Q4 2024": {"revenue": 86.31e9, "net_income": 20.69e9, "eps": 1.64},
            "Q3 2024": {"revenue": 76.69e9, "net_income": 19.69e9, "eps": 1.55},
            "Q2 2024": {"revenue": 73.73e9, "net_income": 18.37e9, "eps": 1.45},
            "Q1 2024": {"revenue": 80.54e9, "net_income": 23.66e9, "eps": 1.86},
        },
    },
}


class FinancialReportTool(BaseTool):
    name = "financial_report"
    description = "Retrieves financial report data and key metrics for a given company"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.getenv("FMP_API_KEY", "")

    async def execute(self, **kwargs) -> ToolResult:
        symbol = kwargs.get("symbol", "").upper()
        report_type = kwargs.get(
            "report_type", "summary"
        )  # summary, detailed, quarterly

        if not symbol:
            return ToolResult(
                success=False, error="No stock symbol provided", tool_name=self.name
            )

        if not self.api_key:
            return await self._unavailable(
                symbol, report_type, "FMP_API_KEY not configured"
            )

        try:
            return await self._fetch_real_data(symbol, report_type)
        except Exception as e:
            logger.error(f"Financial report query failed for {symbol}: {e}")
            return await self._unavailable(
                symbol, report_type, f"real data unavailable: {e}"
            )

    async def _unavailable(
        self, symbol: str, report_type: str, reason: str
    ) -> ToolResult:
        if not mock_enabled():
            return ToolResult(
                success=False,
                error=f"Real financial data unavailable for {symbol} ({reason}). "
                f"Set ALLOW_MOCK_DATA=true to allow simulated data.",
                tool_name=self.name,
                source="fmp",
            )
        return await self._get_mock_data(symbol, report_type)

    async def _fetch_real_data(self, symbol: str, report_type: str) -> ToolResult:
        """从 Financial Modeling Prep API 获取真实财务数据"""
        timeout = aiohttp.ClientTimeout(total=15)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            # 获取公司概况
            profile_url = f"{FMP_BASE_URL}/profile/{symbol}?apikey={self.api_key}"
            async with session.get(profile_url) as resp:
                profile_data = await resp.json()

            if (
                not profile_data
                or not isinstance(profile_data, list)
                or len(profile_data) == 0
            ):
                raise ValueError("FMP returned an empty profile")

            profile = profile_data[0]

            # 获取财务报表
            income_url = f"{FMP_BASE_URL}/income-statement/{symbol}?limit=3&apikey={self.api_key}"
            async with session.get(income_url) as resp:
                income_data = await resp.json()

            # 获取资产负债表
            balance_url = f"{FMP_BASE_URL}/balance-sheet-statement/{symbol}?limit=3&apikey={self.api_key}"
            async with session.get(balance_url) as resp:
                balance_data = await resp.json()

            # 获取关键指标
            metrics_url = (
                f"{FMP_BASE_URL}/key-metrics/{symbol}?limit=3&apikey={self.api_key}"
            )
            async with session.get(metrics_url) as resp:
                metrics_data = await resp.json()

            # 构建财务数据
            financials = self._parse_financials(income_data, balance_data, metrics_data)

            result = {
                "symbol": symbol,
                "name": profile.get("companyName", f"{symbol} Corp."),
                "sector": profile.get("sector", "Unknown"),
                "industry": profile.get("industry", "Unknown"),
                "current_price": profile.get("price", 0),
                "market_cap": profile.get("mktCap", 0),
                "beta": profile.get("beta", 0),
                "description": profile.get("description", ""),
                "financials": financials,
                "timestamp": datetime.now().isoformat(),
                "source": "financialmodelingprep.com",
            }

            if report_type == "quarterly":
                # 获取季度数据
                quarterly_url = f"{FMP_BASE_URL}/income-statement/{symbol}?limit=4&period=quarter&apikey={self.api_key}"
                async with session.get(quarterly_url) as resp:
                    quarterly_data = await resp.json()
                result["quarterly"] = self._parse_quarterly(quarterly_data)

            return ToolResult(
                success=True,
                data=result,
                tool_name=self.name,
                source="fmp",
                is_mock=False,
            )

    def _parse_financials(
        self, income_data: list, balance_data: list, metrics_data: list
    ) -> dict:
        """解析财务报表数据"""
        financials = {
            "revenue": {},
            "net_income": {},
            "eps": {},
            "pe_ratio": {},
            "dividend_yield": {},
            "debt_to_equity": {},
            "return_on_equity": {},
        }

        for item in income_data:
            year = item.get("calendarYear", "")
            if year:
                financials["revenue"][year] = item.get("revenue", 0)
                financials["net_income"][year] = item.get("netIncome", 0)
                financials["eps"][year] = item.get("eps", 0)

        for item in metrics_data:
            year = item.get("calendarYear", "")
            if year:
                financials["pe_ratio"][year] = item.get("peRatio", 0)
                financials["dividend_yield"][year] = item.get("dividendYield", 0)

        for item in balance_data:
            year = item.get("calendarYear", "")
            if year:
                total_equity = item.get("totalStockholdersEquity", 1)
                total_debt = item.get("totalDebt", 0)
                financials["debt_to_equity"][year] = (
                    total_debt / total_equity if total_equity else 0
                )

        # 计算 ROE
        for year in financials["net_income"]:
            for balance in balance_data:
                if balance.get("calendarYear") == year:
                    equity = balance.get("totalStockholdersEquity", 1)
                    net_income = financials["net_income"].get(year, 0)
                    financials["return_on_equity"][year] = (
                        net_income / equity if equity else 0
                    )

        return financials

    def _parse_quarterly(self, quarterly_data: list) -> dict:
        """解析季度数据"""
        quarterly = {}
        for item in quarterly_data:
            period = f"{item.get('period', '')} {item.get('calendarYear', '')}"
            quarterly[period] = {
                "revenue": item.get("revenue", 0),
                "net_income": item.get("netIncome", 0),
                "eps": item.get("eps", 0),
            }
        return quarterly

    async def _get_mock_data(self, symbol: str, report_type: str) -> ToolResult:
        """Clearly-labelled simulated data (only when ALLOW_MOCK_DATA=true)."""
        if symbol in MOCK_FINANCIAL_DATA:
            data = MOCK_FINANCIAL_DATA[symbol].copy()
            data["symbol"] = symbol
            data["report_type"] = report_type
            data["timestamp"] = datetime.now().isoformat()
            data["source"] = "mock"
            data["is_mock"] = True
            data["warning"] = MOCK_WARNING

            if report_type == "summary":
                # 返回摘要信息
                result = {
                    "symbol": symbol,
                    "name": data["name"],
                    "sector": data["sector"],
                    "industry": data["industry"],
                    "current_price": data.get("current_price", 0),
                    "financials": data["financials"],
                    "timestamp": data["timestamp"],
                    "source": data["source"],
                }
            elif report_type == "quarterly":
                # 返回季度数据
                result = {
                    "symbol": symbol,
                    "name": data["name"],
                    "quarterly": data["quarterly"],
                    "timestamp": data["timestamp"],
                    "source": data["source"],
                }
            else:
                # 返回详细数据
                result = data

            return ToolResult(
                success=True,
                data=result,
                tool_name=self.name,
                source="mock",
                is_mock=True,
                warning=MOCK_WARNING,
            )
        else:
            # 返回通用模拟数据
            return ToolResult(
                success=True,
                data={
                    "symbol": symbol,
                    "name": f"{symbol} Corp.",
                    "sector": "Unknown",
                    "industry": "Unknown",
                    "financials": {
                        "revenue": {"2024": 100e9, "2023": 90e9, "2022": 80e9},
                        "net_income": {"2024": 15e9, "2023": 12e9, "2022": 10e9},
                        "eps": {"2024": 3.50, "2023": 2.80, "2022": 2.30},
                        "pe_ratio": {"2024": 25.0, "2023": 28.0, "2022": 22.0},
                    },
                    "timestamp": datetime.now().isoformat(),
                    "source": "mock",
                    "is_mock": True,
                    "warning": MOCK_WARNING,
                },
                tool_name=self.name,
                source="mock",
                is_mock=True,
                warning=MOCK_WARNING,
            )

    async def fallback_execute(self, **kwargs) -> ToolResult:
        """降级执行"""
        symbol = kwargs.get("symbol", "UNKNOWN").upper()
        logger.warning(f"Financial report fallback for: {symbol}")
        return await self._unavailable(symbol, "summary", "primary execution failed")


class FinancialAnalysisTool(BaseTool):
    name = "financial_analysis"
    description = "Performs financial analysis and generates insights for a company"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.getenv("FMP_API_KEY", "")

    async def execute(self, **kwargs) -> ToolResult:
        symbol = kwargs.get("symbol", "").upper()
        analysis_type = kwargs.get(
            "analysis_type", "comprehensive"
        )  # comprehensive, valuation, profitability, growth

        if not symbol:
            return ToolResult(
                success=False, error="No stock symbol provided", tool_name=self.name
            )

        try:
            # 获取财务数据
            report_tool = FinancialReportTool(api_key=self.api_key)
            report_result = await report_tool.execute(
                symbol=symbol, report_type="detailed"
            )

            if not report_result.success:
                return ToolResult(
                    success=False,
                    error="Failed to fetch financial data",
                    tool_name=self.name,
                )

            data = report_result.data
            analysis = self._analyze_financials(data, analysis_type)

            return ToolResult(
                success=True,
                data={
                    "symbol": symbol,
                    "analysis_type": analysis_type,
                    "analysis": analysis,
                    "timestamp": datetime.now().isoformat(),
                },
                tool_name=self.name,
                source=report_result.source,
                is_mock=report_result.is_mock,
                warning=report_result.warning,
            )
        except Exception as e:
            logger.error(f"Financial analysis failed for {symbol}: {e}")
            return ToolResult(success=False, error=str(e), tool_name=self.name)

    def _analyze_financials(self, data: dict, analysis_type: str) -> dict:
        """分析财务数据"""
        financials = data.get("financials", {})
        analysis = {
            "summary": "",
            "strengths": [],
            "weaknesses": [],
            "opportunities": [],
            "threats": [],
            "metrics": {},
            "recommendation": "",
        }

        # 计算关键指标
        revenue_growth = self._calculate_growth(financials.get("revenue", {}))
        net_income_growth = self._calculate_growth(financials.get("net_income", {}))
        current_pe = financials.get("pe_ratio", {}).get("2024", 0)
        current_roe = financials.get("return_on_equity", {}).get("2024", 0)
        current_de = financials.get("debt_to_equity", {}).get("2024", 0)

        analysis["metrics"] = {
            "revenue_growth": revenue_growth,
            "net_income_growth": net_income_growth,
            "pe_ratio": current_pe,
            "return_on_equity": current_roe,
            "debt_to_equity": current_de,
        }

        # SWOT 分析
        if revenue_growth > 0.05:
            analysis["strengths"].append("Strong revenue growth")
        elif revenue_growth < -0.05:
            analysis["weaknesses"].append("Declining revenue")

        if current_roe > 0.15:
            analysis["strengths"].append("High return on equity")
        elif current_roe < 0.08:
            analysis["weaknesses"].append("Low return on equity")

        if current_de < 0.5:
            analysis["strengths"].append("Low debt-to-equity ratio")
        elif current_de > 1.5:
            analysis["weaknesses"].append("High debt-to-equity ratio")

        if current_pe < 20:
            analysis["opportunities"].append("Potentially undervalued")
        elif current_pe > 40:
            analysis["threats"].append("Potentially overvalued")

        # 生成摘要
        company_name = data.get("name", "Unknown Company")
        if len(analysis["strengths"]) > len(analysis["weaknesses"]):
            analysis["summary"] = (
                f"{company_name} shows strong financial health with {len(analysis['strengths'])} strengths identified."
            )
            analysis["recommendation"] = "Consider buying or holding"
        elif len(analysis["weaknesses"]) > len(analysis["strengths"]):
            analysis["summary"] = (
                f"{company_name} faces some financial challenges with {len(analysis['weaknesses'])} weaknesses identified."
            )
            analysis["recommendation"] = "Exercise caution"
        else:
            analysis["summary"] = f"{company_name} shows mixed financial signals."
            analysis["recommendation"] = "Hold and monitor"

        return analysis

    def _calculate_growth(self, data: dict) -> float:
        """计算增长率"""
        values = list(data.values())
        if len(values) < 2:
            return 0.0
        current = values[0]
        previous = values[1]
        if previous == 0:
            return 0.0
        return (current - previous) / previous

    async def fallback_execute(self, **kwargs) -> ToolResult:
        """降级执行"""
        symbol = kwargs.get("symbol", "UNKNOWN").upper()
        logger.warning(f"Financial analysis fallback for: {symbol}")
        return ToolResult(
            success=True,
            data={
                "symbol": symbol,
                "analysis_type": "fallback",
                "analysis": {
                    "summary": f"Unable to perform detailed analysis for {symbol}. Using basic assessment.",
                    "strengths": [],
                    "weaknesses": [],
                    "opportunities": [],
                    "threats": [],
                    "metrics": {},
                    "recommendation": "Insufficient data for recommendation",
                },
                "timestamp": datetime.now().isoformat(),
            },
            tool_name=self.name,
        )
