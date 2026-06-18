"""Tests for the Research Copilot mainline (data -> compute -> trust -> LLM)."""

import pytest
from httpx import AsyncClient

from app.core.research import ResearchService


@pytest.fixture
def _mock_env(monkeypatch):
    """Allow simulated data, and ensure no real API keys leak into the test."""
    monkeypatch.setenv("ALLOW_MOCK_DATA", "true")
    for key in (
        "ALPHA_VANTAGE_API_KEY",
        "NEWS_API_KEY",
        "FINNHUB_API_KEY",
        "FMP_API_KEY",
        "MIMO_API_KEY",
        "DEEPSEEK_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def _no_data_env(monkeypatch):
    """Forbid mock data and provide no keys: every source must be unavailable."""
    monkeypatch.setenv("ALLOW_MOCK_DATA", "false")
    for key in (
        "ALPHA_VANTAGE_API_KEY",
        "NEWS_API_KEY",
        "FINNHUB_API_KEY",
        "FMP_API_KEY",
        "MIMO_API_KEY",
        "DEEPSEEK_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)


@pytest.mark.asyncio
async def test_research_mock_is_labelled_and_computed(_mock_env):
    result = await ResearchService().research("AAPL", use_llm=False)
    d = result.to_dict()

    # Every section is present and explicitly labelled as simulated.
    for name in ("price", "history", "financial", "news"):
        assert d["data"][name]["is_mock"] is True
        assert d["data"][name]["warning"]

    # Trust layer reflects that everything is mock.
    assert d["trust"]["mock_ratio"] == 1.0
    assert d["trust"]["data_confidence"] == 0.0
    assert d["trust"]["source_reliability"] == "low"

    # Numbers are produced by the computation layer, not invented.
    assert d["indicators"]["latest_price"] is not None
    assert d["indicators"]["sma_5"] is not None
    assert d["indicators"]["pe_ratio"] is not None

    # Deterministic (rule-based) summary when no LLM is configured.
    assert d["report"]["summary_source"] == "rule_based"
    assert d["report"]["key_findings"]
    assert "investment advice" in d["disclaimer"].lower()
    assert any("simulated" in w.lower() for w in d["warnings"])


@pytest.mark.asyncio
async def test_research_no_silent_fallback(_no_data_env):
    result = await ResearchService().research("AAPL", use_llm=False)
    d = result.to_dict()

    for name in ("price", "history", "financial", "news"):
        assert d["data"][name]["available"] is False
        assert d["data"][name]["is_mock"] is False
        assert d["data"][name]["error"]

    # No data -> no fabricated numbers and zero confidence.
    assert d["indicators"]["latest_price"] is None
    assert d["trust"]["data_confidence"] == 0.0
    assert any("unavailable" in w.lower() for w in d["warnings"])


@pytest.mark.asyncio
async def test_research_endpoint(client: AsyncClient, _mock_env):
    response = await client.post("/api/research/AAPL")
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "AAPL"
    assert {"data", "indicators", "trust", "report", "disclaimer"} <= set(body)
    assert body["report"]["key_findings"]


@pytest.mark.asyncio
async def test_research_endpoint_invalid_symbol(client: AsyncClient, _mock_env):
    response = await client.post("/api/research/not-a-symbol!!")
    assert response.status_code == 400
