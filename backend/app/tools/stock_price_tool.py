"""
股票价格查询工具 - 支持实时股价查询和历史数据
"""

import hashlib
import os
import random
from datetime import datetime, timedelta

import aiohttp

from app.tools.base_tool import MOCK_WARNING, BaseTool, ToolResult, mock_enabled
from app.tools.cache import get_cache
from app.utils.logger import get_logger
from app.utils.redaction import redact_sensitive_text

logger = get_logger("stock_price_tool")

# 缓存 TTL 配置
STOCK_PRICE_CACHE_TTL = 60  # 股票价格缓存 60 秒
STOCK_HISTORY_CACHE_TTL = 300  # 历史数据缓存 300 秒


class RateLimitError(RuntimeError):
    """Raised when the upstream data provider reports a rate/quota limit."""


def _parse_percent(value: object) -> float:
    """Parse Alpha Vantage percent strings like '-0.4116%' into a float."""
    if value is None:
        return 0.0
    try:
        return float(str(value).strip().rstrip("%") or 0)
    except (TypeError, ValueError):
        return 0.0


def _raise_if_rate_limited(data: dict) -> None:
    """Alpha Vantage signals throttling via 'Note'/'Information' instead of data."""
    message = data.get("Note") or data.get("Information")
    if message:
        raise RateLimitError(message)


def _symbol_rng(symbol: str) -> "random.Random":
    """Deterministic RNG seeded by symbol so each symbol gets stable, distinct values."""
    seed = int(hashlib.sha256(symbol.encode("utf-8")).hexdigest(), 16)
    return random.Random(seed)


def _generate_mock_price(symbol: str) -> dict:
    """Plausible, per-symbol-varied simulated quote for unknown symbols.

    Deterministic (same symbol -> same numbers) so the demo is stable, but
    different symbols no longer collapse to one identical placeholder price.
    """
    rng = _symbol_rng(symbol)
    price = round(rng.uniform(25.0, 650.0), 2)
    change_percent = round(rng.uniform(-3.5, 3.5), 2)
    change = round(price * change_percent / 100, 2)
    return {
        "symbol": symbol,
        "name": f"{symbol} Corp.",
        "price": price,
        "change": change,
        "change_percent": change_percent,
        "volume": rng.randint(1_000_000, 90_000_000),
        "market_cap": round(price * rng.randint(50_000_000, 5_000_000_000)),
        "pe_ratio": round(rng.uniform(8.0, 60.0), 1),
        "52w_high": round(price * rng.uniform(1.05, 1.45), 2),
        "52w_low": round(price * rng.uniform(0.55, 0.95), 2),
    }


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
    # Common market-index proxies (ETFs) shown on the dashboard overview.
    "SPY": {
        "name": "SPDR S&P 500 ETF",
        "price": 542.34,
        "change": 1.87,
        "change_percent": 0.35,
        "volume": 41234567,
        "market_cap": 4.9e11,
        "pe_ratio": 24.6,
        "52w_high": 565.16,
        "52w_low": 418.92,
    },
    "QQQ": {
        "name": "Invesco QQQ (NASDAQ-100)",
        "price": 478.21,
        "change": -2.43,
        "change_percent": -0.51,
        "volume": 33456789,
        "market_cap": 2.7e11,
        "pe_ratio": 31.2,
        "52w_high": 503.52,
        "52w_low": 342.21,
    },
    "DIA": {
        "name": "SPDR Dow Jones ETF",
        "price": 393.07,
        "change": 0.62,
        "change_percent": 0.16,
        "volume": 3456789,
        "market_cap": 3.4e10,
        "pe_ratio": 22.1,
        "52w_high": 411.10,
        "52w_low": 327.45,
    },
    "VIX": {
        "name": "CBOE Volatility Index",
        "price": 14.27,
        "change": -0.53,
        "change_percent": -3.58,
        "volume": 0,
        "market_cap": 0,
        "pe_ratio": 0,
        "52w_high": 65.73,
        "52w_low": 11.52,
    },
}


class StockPriceTool(BaseTool):
    name = "stock_price"
    description = (
        "Queries real-time stock price and market data for a given stock symbol"
    )

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY", "")
        self._cache = get_cache()

    async def execute(self, **kwargs) -> ToolResult:
        symbol = kwargs.get("symbol", "").upper()
        if not symbol:
            return ToolResult(
                success=False, error="No stock symbol provided", tool_name=self.name
            )

        # 检查缓存
        cache_key = f"stock_price:{symbol}"
        hit, cached_result = self._cache.get(cache_key)
        if hit:
            logger.debug(f"Stock price cache hit: {symbol}")
            return cached_result

        if not self.api_key:
            return self._unavailable(symbol, "ALPHA_VANTAGE_API_KEY not configured")

        try:
            result = await self._fetch_real_price(symbol)
            if result.success:
                self._cache.set(cache_key, result, ttl=STOCK_PRICE_CACHE_TTL)
            return result
        except Exception as e:
            safe_error = redact_sensitive_text(e)
            logger.error(f"Stock price query failed for {symbol}: {safe_error}")
            return self._unavailable(symbol, f"real data unavailable: {safe_error}")

    def _unavailable(self, symbol: str, reason: str) -> ToolResult:
        """Return an explicit failure, or a clearly-labelled mock if ALLOW_MOCK_DATA is set."""
        if not mock_enabled():
            return ToolResult(
                success=False,
                error=f"Real stock price unavailable for {symbol} ({reason}). "
                f"Set ALLOW_MOCK_DATA=true to allow simulated data.",
                tool_name=self.name,
                source="alpha_vantage",
            )
        return self._mock_price_sync(symbol)

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
            async with (
                aiohttp.ClientSession(timeout=timeout) as session,
                session.get(url, params=params, proxy=proxy) as resp,
            ):
                data = await resp.json()

                _raise_if_rate_limited(data)

                quote = data.get("Global Quote", {})

                if not quote:
                    raise ValueError("Alpha Vantage returned an empty quote")

                result = {
                    "symbol": symbol,
                    "price": float(quote.get("05. price", 0)),
                    "change": float(quote.get("09. change", 0)),
                    "change_percent": _parse_percent(quote.get("10. change percent")),
                    "volume": int(quote.get("06. volume", 0)),
                    "latest_trading_day": quote.get("07. latest trading day", ""),
                    "previous_close": float(quote.get("08. previous close", 0)),
                    "open": float(quote.get("02. open", 0)),
                    "high": float(quote.get("03. high", 0)),
                    "low": float(quote.get("04. low", 0)),
                    "source": "alpha_vantage",
                }

                return ToolResult(
                    success=True,
                    data=result,
                    tool_name=self.name,
                    source="alpha_vantage",
                    is_mock=False,
                )
        except Exception as e:
            safe_error = redact_sensitive_text(e)
            logger.error(f"Alpha Vantage API error for {symbol}: {safe_error}")
            raise

    def _mock_price_sync(self, symbol: str) -> ToolResult:
        """Clearly-labelled simulated price data (only when ALLOW_MOCK_DATA=true)."""
        if symbol in MOCK_STOCK_DATA:
            data = MOCK_STOCK_DATA[symbol].copy()
            data["symbol"] = symbol
        else:
            data = _generate_mock_price(symbol)
        data["timestamp"] = datetime.now().isoformat()
        data["source"] = "mock"
        data["is_mock"] = True
        data["warning"] = MOCK_WARNING
        return ToolResult(
            success=True,
            data=data,
            tool_name=self.name,
            source="mock",
            is_mock=True,
            warning=MOCK_WARNING,
        )

    async def fallback_execute(self, **kwargs) -> ToolResult:
        symbol = kwargs.get("symbol", "UNKNOWN").upper()
        logger.warning(f"Stock price fallback for: {symbol}")
        return self._unavailable(symbol, "primary execution failed")


class StockHistoryTool(BaseTool):
    name = "stock_history"
    description = (
        "Retrieves historical stock price data for a given symbol and time period"
    )

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY", "")

    async def execute(self, **kwargs) -> ToolResult:
        symbol = kwargs.get("symbol", "").upper()
        period = kwargs.get("period", "1m")  # 1d, 1w, 1m, 3m, 6m, 1y

        if not symbol:
            return ToolResult(
                success=False, error="No stock symbol provided", tool_name=self.name
            )

        if not self.api_key:
            return self._unavailable(
                symbol, period, "ALPHA_VANTAGE_API_KEY not configured"
            )

        try:
            return await self._fetch_real_history(symbol, period)
        except Exception as e:
            safe_error = redact_sensitive_text(e)
            logger.error(f"Stock history query failed for {symbol}: {safe_error}")
            return self._unavailable(
                symbol, period, f"real data unavailable: {safe_error}"
            )

    def _unavailable(self, symbol: str, period: str, reason: str) -> ToolResult:
        if not mock_enabled():
            return ToolResult(
                success=False,
                error=f"Real stock history unavailable for {symbol} ({reason}). "
                f"Set ALLOW_MOCK_DATA=true to allow simulated data.",
                tool_name=self.name,
                source="alpha_vantage",
            )
        return self._mock_history_sync(symbol, period)

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
        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.get(url, params=params) as resp,
        ):
            data = await resp.json()

            _raise_if_rate_limited(data)

            time_series = data.get("Time Series (Daily)", {})

            if not time_series:
                raise ValueError("Alpha Vantage returned an empty time series")

            # 转换数据格式
            history = []
            for date, values in list(time_series.items())[:30]:  # 最近30天
                history.append(
                    {
                        "date": date,
                        "open": float(values.get("1. open", 0)),
                        "high": float(values.get("2. high", 0)),
                        "low": float(values.get("3. low", 0)),
                        "close": float(values.get("4. close", 0)),
                        "volume": int(values.get("5. volume", 0)),
                    }
                )

            return ToolResult(
                success=True,
                data={"symbol": symbol, "period": period, "history": history},
                tool_name=self.name,
                source="alpha_vantage",
                is_mock=False,
            )

    def _mock_history_sync(self, symbol: str, period: str) -> ToolResult:
        """Clearly-labelled simulated history (only when ALLOW_MOCK_DATA=true)."""
        rng = _symbol_rng(symbol)
        base_price = MOCK_STOCK_DATA.get(symbol, {}).get(
            "price", _generate_mock_price(symbol)["price"]
        )
        days = {"1d": 1, "1w": 7, "1m": 30, "3m": 90, "6m": 180, "1y": 365}.get(
            period, 30
        )

        history = []
        current_date = datetime.now()
        price = base_price * 0.9  # 从较低价格开始

        for i in range(min(days, 30)):  # 最多返回30个数据点
            date = current_date - timedelta(days=days - i)
            change = rng.uniform(-0.03, 0.03) * price
            price = max(price + change, base_price * 0.5)

            history.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "open": round(price * rng.uniform(0.99, 1.01), 2),
                    "high": round(price * rng.uniform(1.00, 1.03), 2),
                    "low": round(price * rng.uniform(0.97, 1.00), 2),
                    "close": round(price, 2),
                    "volume": rng.randint(5000000, 100000000),
                }
            )

        return ToolResult(
            success=True,
            data={
                "symbol": symbol,
                "period": period,
                "history": history,
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
        period = kwargs.get("period", "1m")
        logger.warning(f"Stock history fallback for: {symbol}")
        return self._unavailable(symbol, period, "primary execution failed")
