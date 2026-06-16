import pytest

from app.tools.base_tool import MOCK_WARNING
from app.tools.financial_report_tool import FinancialReportTool
from app.tools.news_summary_tool import NewsSummaryTool
from app.tools.stock_price_tool import (
    RateLimitError,
    StockHistoryTool,
    StockPriceTool,
    _parse_percent,
    _raise_if_rate_limited,
)


def test_parse_percent_handles_alpha_vantage_string():
    # Alpha Vantage returns change percent as e.g. "-0.4116%" (a string).
    assert _parse_percent("-0.4116%") == pytest.approx(-0.4116)
    assert _parse_percent("1.25%") == pytest.approx(1.25)
    assert _parse_percent(0.69) == pytest.approx(0.69)
    assert _parse_percent(None) == 0.0
    assert _parse_percent("n/a") == 0.0


@pytest.mark.asyncio
async def test_mock_prices_differ_per_symbol(monkeypatch):
    # Unknown symbols (e.g. index proxies) must not all collapse to one price.
    monkeypatch.setenv("ALLOW_MOCK_DATA", "true")
    prices = {}
    for sym in ["SPY", "QQQ", "DIA", "VIX", "FOO", "BAR"]:
        res = await StockPriceTool(api_key="").execute(symbol=sym)
        assert res.success is True and res.is_mock is True
        prices[sym] = res.data["price"]
    # All distinct -> the "everything is 150" bug stays fixed.
    assert len(set(prices.values())) == len(prices)
    # Deterministic: same symbol yields the same simulated price.
    again = (await StockPriceTool(api_key="").execute(symbol="FOO")).data["price"]
    assert again == prices["FOO"]


def test_raise_if_rate_limited_detects_note():
    with pytest.raises(RateLimitError):
        _raise_if_rate_limited({"Note": "Thank you... 25 requests per day"})
    with pytest.raises(RateLimitError):
        _raise_if_rate_limited({"Information": "rate limit reached"})
    # A normal payload must not raise.
    _raise_if_rate_limited({"Global Quote": {"05. price": "1"}})


@pytest.mark.asyncio
async def test_stock_price_no_key_no_mock_fails(monkeypatch):
    monkeypatch.setenv("ALLOW_MOCK_DATA", "false")
    res = await StockPriceTool(api_key="").execute(symbol="AAPL")
    assert res.success is False
    assert res.is_mock is False
    assert "ALLOW_MOCK_DATA" in res.error


@pytest.mark.asyncio
async def test_stock_price_no_key_with_mock_is_labelled(monkeypatch):
    monkeypatch.setenv("ALLOW_MOCK_DATA", "true")
    res = await StockPriceTool(api_key="").execute(symbol="AAPL")
    assert res.success is True
    assert res.is_mock is True
    assert res.source == "mock"
    assert res.warning == MOCK_WARNING
    assert res.data["is_mock"] is True


@pytest.mark.asyncio
async def test_stock_history_no_key_no_mock_fails(monkeypatch):
    monkeypatch.setenv("ALLOW_MOCK_DATA", "false")
    res = await StockHistoryTool(api_key="").execute(symbol="AAPL", period="1m")
    assert res.success is False
    assert res.is_mock is False


@pytest.mark.asyncio
async def test_financial_no_key_no_mock_fails(monkeypatch):
    monkeypatch.setenv("ALLOW_MOCK_DATA", "false")
    res = await FinancialReportTool(api_key="").execute(symbol="AAPL")
    assert res.success is False
    assert "ALLOW_MOCK_DATA" in res.error


@pytest.mark.asyncio
async def test_financial_mock_revenue_not_duplicated(monkeypatch):
    monkeypatch.setenv("ALLOW_MOCK_DATA", "true")
    res = await FinancialReportTool(api_key="").execute(
        symbol="AAPL", report_type="detailed"
    )
    assert res.success is True
    assert res.is_mock is True
    revenue = res.data["financials"]["revenue"]
    # The 2024 vs 2023 copy-paste bug used to make these identical.
    assert revenue["2024"] != revenue["2023"]


@pytest.mark.asyncio
async def test_news_no_key_no_mock_fails(monkeypatch):
    monkeypatch.setenv("ALLOW_MOCK_DATA", "false")
    res = await NewsSummaryTool(api_key="").execute(query="Apple")
    assert res.success is False
    assert "ALLOW_MOCK_DATA" in res.error


@pytest.mark.asyncio
async def test_news_mock_is_labelled(monkeypatch):
    monkeypatch.setenv("ALLOW_MOCK_DATA", "true")
    res = await NewsSummaryTool(api_key="").execute(query="Apple")
    assert res.success is True
    assert res.is_mock is True
    assert res.source == "mock"
    assert res.warning == MOCK_WARNING
