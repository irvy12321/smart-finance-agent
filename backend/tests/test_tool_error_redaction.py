import pytest

from app.tools.crawler_tool import CrawlerTool
from app.tools.financial_report_tool import FinancialReportTool
from app.tools.news_summary_tool import NewsSummaryTool
from app.tools.stock_price_tool import StockPriceTool
from app.utils.redaction import redact_sensitive_text


def test_redact_sensitive_text_filters_url_query_and_assignments():
    raw = (
        "GET https://example.com/data?apikey=secret-key-123456&stream_token=abc123456 "
        "Authorization: Bearer abc.def-ghi_12345 "
        'api_key="json-secret-value" password=plain-secret-value'
    )

    cleaned = redact_sensitive_text(raw)

    assert "secret-key-123456" not in cleaned
    assert "abc123456" not in cleaned
    assert "abc.def-ghi_12345" not in cleaned
    assert "json-secret-value" not in cleaned
    assert "plain-secret-value" not in cleaned
    assert "apikey=***" in cleaned
    assert "stream_token=***" in cleaned
    assert "Bearer ***" in cleaned


@pytest.mark.asyncio
async def test_financial_report_error_does_not_return_api_key(monkeypatch):
    secret = "financial-secret-key-123456"
    monkeypatch.setenv("ALLOW_MOCK_DATA", "false")
    tool = FinancialReportTool(api_key=secret)

    async def boom(symbol: str, report_type: str):
        raise RuntimeError(f"GET https://fmp.example/profile?apikey={secret}&x=1")

    monkeypatch.setattr(tool, "_fetch_real_data", boom)

    result = await tool.execute(symbol="AAPL")

    assert result.success is False
    assert secret not in result.error
    assert "apikey=***" in result.error


@pytest.mark.asyncio
async def test_stock_price_error_does_not_return_api_key(monkeypatch):
    secret = "alpha-secret-key-123456"
    monkeypatch.setenv("ALLOW_MOCK_DATA", "false")
    tool = StockPriceTool(api_key=secret)

    async def boom(symbol: str):
        raise RuntimeError(f"https://alpha.example/query?apikey={secret}")

    monkeypatch.setattr(tool, "_fetch_real_price", boom)

    result = await tool.execute(symbol="ZZZSEC")

    assert result.success is False
    assert secret not in result.error
    assert "apikey=***" in result.error


@pytest.mark.asyncio
async def test_news_summary_error_does_not_return_api_key(monkeypatch):
    secret = "news-secret-key-123456"
    monkeypatch.setenv("ALLOW_MOCK_DATA", "false")
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    tool = NewsSummaryTool(api_key=secret)

    async def boom(query: str, max_results: int):
        raise RuntimeError(f"https://news.example/everything?apiKey={secret}")

    monkeypatch.setattr(tool, "_search_real_news", boom)

    result = await tool.execute(query="AAPL")

    assert result.success is False
    assert secret not in result.error
    assert "apiKey=***" in result.error


@pytest.mark.asyncio
async def test_crawler_error_does_not_return_url_token(monkeypatch):
    secret = "crawler-token-123456"
    tool = CrawlerTool()
    monkeypatch.setattr("app.tools.crawler_tool._validate_url", lambda url: None)

    async def boom(url: str):
        raise RuntimeError(f"fetch failed for {url}")

    monkeypatch.setattr(tool, "_fetch", boom)

    result = await tool.execute(url=f"https://example.com/page?token={secret}")

    assert result.success is False
    assert secret not in result.error
    assert "token=***" in result.error
