"""
股票价格查询工具 - 支持实时股价查询和历史数据
"""
from datetime import datetime, timedelta

import aiohttp

from app.tools.base_tool import BaseTool, ToolResult
from app.utils.logger import get_logger

logger = get_logger("stock_price_tool")

# 模拟股票数据（生产环境应接入真实API）
MOCK_STOCK_DATA = {
    "AAPL": {
        "name": "Apple Inc.",
        "price": 182.52,
        "change": 1.25,
        "change_percent": 0.69,
        "volume": 52345678,
        "market_cap": 2.85e12,
        "pe_ratio": 28.5,
        "52w_high": 199.62,
        "52w_low": 124.17,
    },
    "TSLA": {
        "name": "Tesla Inc.",
        "price": 248.42,
        "change": -3.18,
        "change_percent": -1.26,
        "volume": 87654321,
        "market_cap": 7.89e11,
        "pe_ratio": 62.3,
        "52w_high": 299.29,
        "52w_low": 152.37,
    },
    "GOOGL": {
        "name": "Alphabet Inc.",
        "price": 141.80,
        "change": 0.95,
        "change_percent": 0.67,
        "volume": 23456789,
        "market_cap": 1.78e12,
        "pe_ratio": 24.8,
        "52w_high": 153.78,
        "52w_low": 101.88,
    },
    "MSFT": {
        "name": "Microsoft Corp.",
        "price": 378.91,
        "change": 2.34,
        "change_percent": 0.62,
        "volume": 34567890,
        "market_cap": 2.81e12,
        "pe_ratio": 35.2,
        "52w_high": 384.30,
        "52w_low": 245.61,
    },
    "AMZN": {
        "name": "Amazon.com Inc.",
        "price": 178.25,
        "change": 1.56,
        "change_percent": 0.88,
        "volume": 45678901,
        "market_cap": 1.85e12,
        "pe_ratio": 58.7,
        "52w_high": 189.77,
        "52w_low": 118.35,
    },
    "NVDA": {
        "name": "NVIDIA Corp.",
        "price": 875.28,
        "change": 12.45,
        "change_percent": 1.44,
        "volume": 67890123,
        "market_cap": 2.15e12,
        "pe_ratio": 72.4,
        "52w_high": 974.00,
        "52w_low": 394.36,
    },
    "META": {
        "name": "Meta Platforms Inc.",
        "price": 505.75,
        "change": 3.21,
        "change_percent": 0.64,
        "volume": 28901234,
        "market_cap": 1.29e12,
        "pe_ratio": 28.9,
        "52w_high": 542.81,
        "52w_low": 274.38,
    },
}


class StockPriceTool(BaseTool):
    name = "stock_price"
    description = "Queries real-time stock price and market data for a given stock symbol"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    async def execute(self, **kwargs) -> ToolResult:
        symbol = kwargs.get("symbol", "").upper()
        if not symbol:
            return ToolResult(success=False, error="No stock symbol provided", tool_name=self.name)

        try:
            # 尝试使用真实API（如果配置了API key）
            if self.api_key:
                return await self._fetch_real_price(symbol)
            else:
                return await self._get_mock_price(symbol)
        except Exception as e:
            logger.error(f"Stock price query failed for {symbol}: {e}")
            return await self._get_mock_price(symbol)

    async def _fetch_real_price(self, symbol: str) -> ToolResult:
        """从真实API获取股价（使用Alpha Vantage）"""
        import os
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": self.api_key,
        }

        proxy = os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")
        
        timeout = aiohttp.ClientTimeout(total=20)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params, proxy=proxy) as resp:
                    data = await resp.json()
                    quote = data.get("Global Quote", {})

                    if not quote:
                        logger.warning(f"Alpha Vantage returned empty quote for {symbol}")
                        return await self._get_mock_price(symbol)

                    result = {
                        "symbol": symbol,
                        "price": float(quote.get("05. price", 0)),
                        "change": float(quote.get("09. change", 0)),
                        "change_percent": quote.get("10. change percent", "0%"),
                        "volume": int(quote.get("06. volume", 0)),
                        "latest_trading_day": quote.get("07. latest trading day", ""),
                        "previous_close": float(quote.get("08. previous close", 0)),
                        "open": float(quote.get("02. open", 0)),
                        "high": float(quote.get("03. high", 0)),
                        "low": float(quote.get("04. low", 0)),
                        "source": "alpha_vantage",
                    }

                    return ToolResult(success=True, data=result, tool_name=self.name)
        except Exception as e:
            logger.error(f"Alpha Vantage API error for {symbol}: {e}")
            return await self._get_mock_price(symbol)

    async def _get_mock_price(self, symbol: str) -> ToolResult:
        """获取模拟股价数据"""
        if symbol in MOCK_STOCK_DATA:
            data = MOCK_STOCK_DATA[symbol].copy()
            data["symbol"] = symbol
            data["timestamp"] = datetime.now().isoformat()
            data["source"] = "mock_data"
            return ToolResult(success=True, data=data, tool_name=self.name)
        else:
            # 返回通用模拟数据
            return ToolResult(
                success=True,
                data={
                    "symbol": symbol,
                    "name": f"{symbol} Corp.",
                    "price": 150.00,
                    "change": 1.50,
                    "change_percent": 1.01,
                    "volume": 10000000,
                    "market_cap": 5.0e11,
                    "pe_ratio": 25.0,
                    "52w_high": 175.00,
                    "52w_low": 120.00,
                    "timestamp": datetime.now().isoformat(),
                    "source": "mock_data",
                    "note": f"Simulated data for {symbol}. Configure ALPHA_VANTAGE_API_KEY for real data.",
                },
                tool_name=self.name,
            )

    async def fallback_execute(self, **kwargs) -> ToolResult:
        """降级执行：返回模拟数据"""
        symbol = kwargs.get("symbol", "UNKNOWN").upper()
        logger.warning(f"Stock price fallback for: {symbol}")
        return await self._get_mock_price(symbol)


class StockHistoryTool(BaseTool):
    name = "stock_history"
    description = "Retrieves historical stock price data for a given symbol and time period"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    async def execute(self, **kwargs) -> ToolResult:
        symbol = kwargs.get("symbol", "").upper()
        period = kwargs.get("period", "1m")  # 1d, 1w, 1m, 3m, 6m, 1y

        if not symbol:
            return ToolResult(success=False, error="No stock symbol provided", tool_name=self.name)

        try:
            if self.api_key:
                return await self._fetch_real_history(symbol, period)
            else:
                return await self._get_mock_history(symbol, period)
        except Exception as e:
            logger.error(f"Stock history query failed for {symbol}: {e}")
            return await self._get_mock_history(symbol, period)

    async def _fetch_real_history(self, symbol: str, period: str) -> ToolResult:
        """从真实API获取历史数据"""
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": "compact",
            "apikey": self.api_key,
        }

        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params) as resp:
                data = await resp.json()
                time_series = data.get("Time Series (Daily)", {})

                if not time_series:
                    return await self._get_mock_history(symbol, period)

                # 转换数据格式
                history = []
                for date, values in list(time_series.items())[:30]:  # 最近30天
                    history.append({
                        "date": date,
                        "open": float(values.get("1. open", 0)),
                        "high": float(values.get("2. high", 0)),
                        "low": float(values.get("3. low", 0)),
                        "close": float(values.get("4. close", 0)),
                        "volume": int(values.get("5. volume", 0)),
                    })

                return ToolResult(
                    success=True,
                    data={"symbol": symbol, "period": period, "history": history},
                    tool_name=self.name,
                )

    async def _get_mock_history(self, symbol: str, period: str) -> ToolResult:
        """生成模拟历史数据"""
        import random

        base_price = MOCK_STOCK_DATA.get(symbol, {}).get("price", 150.00)
        days = {"1d": 1, "1w": 7, "1m": 30, "3m": 90, "6m": 180, "1y": 365}.get(period, 30)

        history = []
        current_date = datetime.now()
        price = base_price * 0.9  # 从较低价格开始

        for i in range(min(days, 30)):  # 最多返回30个数据点
            date = current_date - timedelta(days=days - i)
            change = random.uniform(-0.03, 0.03) * price
            price = max(price + change, base_price * 0.5)

            history.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": round(price * random.uniform(0.99, 1.01), 2),
                "high": round(price * random.uniform(1.00, 1.03), 2),
                "low": round(price * random.uniform(0.97, 1.00), 2),
                "close": round(price, 2),
                "volume": random.randint(5000000, 100000000),
            })

        return ToolResult(
            success=True,
            data={
                "symbol": symbol,
                "period": period,
                "history": history,
                "source": "mock_data",
                "note": "Simulated data. Configure ALPHA_VANTAGE_API_KEY for real data.",
            },
            tool_name=self.name,
        )

    async def fallback_execute(self, **kwargs) -> ToolResult:
        """降级执行"""
        symbol = kwargs.get("symbol", "UNKNOWN").upper()
        period = kwargs.get("period", "1m")
        logger.warning(f"Stock history fallback for: {symbol}")
        return await self._get_mock_history(symbol, period)
