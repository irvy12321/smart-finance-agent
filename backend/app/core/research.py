"""Research Copilot mainline.

A single, explicit pipeline that ties the three layers together for one stock:

    Data layer        -> fetch price / history / financials / news via tools,
                         each result carrying ``source`` / ``is_mock``.
    Computation layer -> derive every number with pure Python (indicators.py).
    Trust layer       -> aggregate per-report ``data_confidence`` / ``mock_ratio``.
    LLM layer (opt.)  -> turn the *already-computed* numbers into prose. The LLM
                         never invents numbers; if it is unavailable we fall back
                         to a deterministic, fully-grounded summary.

This is intentionally a flat, readable function rather than another agent layer.
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from app.core import indicators
from app.core.trust import DataEnvelope, aggregate_confidence
from app.infrastructure.llm_client import LLMClient
from app.tools.financial_report_tool import FinancialReportTool
from app.tools.news_summary_tool import NewsSummaryTool
from app.tools.stock_price_tool import StockHistoryTool, StockPriceTool
from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.tools.base_tool import ToolResult

logger = get_logger("research")

DISCLAIMER = (
    "This report is for research and educational purposes only and is NOT "
    "investment advice. Data may be incomplete or simulated; verify "
    "independently before making any financial decision."
)
DISCLAIMER_ZH = (
    "本报告仅用于研究与学习目的，不构成投资建议。数据可能不完整或为模拟数据，"
    "请在做出任何金融决策前独立核实。"
)


@dataclass
class ResearchResult:
    symbol: str
    generated_at: str
    data: dict[str, Any]
    indicators: dict[str, Any]
    trust: dict[str, Any]
    report: dict[str, Any]
    disclaimer: str
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _section(result: ToolResult) -> dict[str, Any]:
    """Render a tool result as a trust-annotated section."""
    return {
        "available": result.success,
        "source": result.source or ("mock" if result.is_mock else "unknown"),
        "is_mock": result.is_mock,
        "warning": result.warning or "",
        "error": result.error or "",
        "value": result.data if result.success else None,
    }


def _sorted_closes(history: dict[str, Any] | None) -> list[float]:
    """Extract closing prices in chronological (oldest -> newest) order."""
    if not history:
        return []
    rows = history.get("history") or []
    with contextlib.suppress(Exception):
        rows = sorted(rows, key=lambda r: r.get("date", ""))
    closes: list[float] = []
    for row in rows:
        close = row.get("close")
        if isinstance(close, (int, float)):
            closes.append(float(close))
    return closes


def _latest_eps(financial: dict[str, Any] | None) -> float | None:
    """Best-effort extraction of the most recent EPS from financial data."""
    if not financial:
        return None
    fin = financial.get("financials") or {}
    eps = fin.get("eps")
    if isinstance(eps, dict) and eps:
        try:
            latest_year = max(eps.keys())
            value = eps[latest_year]
            return float(value) if isinstance(value, (int, float)) else None
        except (ValueError, TypeError):
            return None
    if isinstance(eps, (int, float)):
        return float(eps)
    return None


def _compute_indicators(
    price: dict[str, Any] | None,
    history: dict[str, Any] | None,
    financial: dict[str, Any] | None,
) -> dict[str, Any]:
    closes = _sorted_closes(history)
    latest_price = None
    if isinstance(price, dict) and isinstance(price.get("price"), (int, float)):
        latest_price = float(price["price"])
    elif closes:
        latest_price = closes[-1]

    eps = _latest_eps(financial)

    day_change_pct = None
    if len(closes) >= 2:
        day_change_pct = indicators.pct_change(closes[-1], closes[-2])

    return {
        "latest_price": latest_price,
        "day_change_pct": day_change_pct,
        "sma_5": indicators.sma(closes, 5),
        "sma_10": indicators.sma(closes, 10),
        "ema_12": indicators.ema(closes, 12),
        "rsi_14": indicators.rsi(closes, 14),
        "pe_ratio": indicators.pe_ratio(latest_price, eps)
        if (latest_price and eps)
        else None,
        "history_points": len(closes),
    }


def _rsi_label(rsi: float | None) -> str | None:
    if rsi is None:
        return None
    if rsi >= 70:
        return "overbought"
    if rsi <= 30:
        return "oversold"
    return "neutral"


def _deterministic_findings(symbol: str, ind: dict[str, Any]) -> list[str]:
    """Fully-grounded findings derived only from computed numbers."""
    findings: list[str] = []
    if ind["latest_price"] is not None:
        findings.append(f"Latest price for {symbol}: {ind['latest_price']}.")
    if ind["day_change_pct"] is not None:
        direction = "up" if ind["day_change_pct"] >= 0 else "down"
        findings.append(f"Day-over-day change: {ind['day_change_pct']}% ({direction}).")
    if ind["sma_5"] is not None and ind["sma_10"] is not None:
        trend = "above" if ind["sma_5"] >= ind["sma_10"] else "below"
        findings.append(f"SMA(5)={ind['sma_5']} is {trend} SMA(10)={ind['sma_10']}.")
    rsi_label = _rsi_label(ind["rsi_14"])
    if rsi_label is not None:
        findings.append(f"RSI(14)={ind['rsi_14']} ({rsi_label}).")
    if ind["pe_ratio"] is not None:
        findings.append(f"P/E ratio (price / latest EPS): {ind['pe_ratio']}.")
    if not findings:
        findings.append(
            f"Insufficient data to compute indicators for {symbol}; no numbers fabricated."
        )
    return findings


async def _maybe_llm_summary(
    symbol: str, ind: dict[str, Any], findings: list[str], language: str
) -> str | None:
    """Optional natural-language summary. Returns None when no LLM is configured."""
    client = LLMClient.get_instance()
    if not getattr(client.config, "api_key", ""):
        return None

    facts = "\n".join(f"- {f}" for f in findings)
    if language == "zh":
        system = (
            "你是金融研究助手。只能基于下面提供的、已由代码计算好的事实撰写摘要。"
            "禁止生成、估算或编造任何数字；禁止补全缺失数据。用2-3句中文概括。"
        )
        prompt = f"股票代码：{symbol}\n已计算事实：\n{facts}\n\n请用2-3句话客观概括。"
    else:
        system = (
            "You are a financial research assistant. Write a summary using ONLY "
            "the pre-computed facts below. You MUST NOT generate, estimate or "
            "invent any number, and MUST NOT fill in missing data. 2-3 sentences."
        )
        prompt = f"Symbol: {symbol}\nPre-computed facts:\n{facts}\n\nSummarize objectively in 2-3 sentences."

    try:
        text = await asyncio.wait_for(
            client.complete(
                prompt=prompt, system=system, temperature=0.3, max_tokens=300
            ),
            timeout=30,
        )
        return text.strip() or None
    except Exception as e:
        logger.warning(f"LLM summary unavailable, using deterministic summary: {e}")
        return None


class ResearchService:
    """Coordinates the data/computation/trust/LLM layers for one symbol."""

    def __init__(
        self,
        price_tool: StockPriceTool | None = None,
        history_tool: StockHistoryTool | None = None,
        financial_tool: FinancialReportTool | None = None,
        news_tool: NewsSummaryTool | None = None,
    ):
        self.price_tool = price_tool or StockPriceTool()
        self.history_tool = history_tool or StockHistoryTool()
        self.financial_tool = financial_tool or FinancialReportTool()
        self.news_tool = news_tool or NewsSummaryTool()

    async def research(
        self, symbol: str, language: str = "en", use_llm: bool = True
    ) -> ResearchResult:
        symbol = symbol.strip().upper()
        logger.info(f"Research mainline start: {symbol} (language={language})")

        # ── Data layer ────────────────────────────────────────────────
        price_res, history_res, financial_res, news_res = await asyncio.gather(
            self.price_tool.execute(symbol=symbol),
            self.history_tool.execute(symbol=symbol, period="1m"),
            self.financial_tool.execute(symbol=symbol),
            self.news_tool.execute(query=symbol, max_results=5),
        )

        data = {
            "price": _section(price_res),
            "history": _section(history_res),
            "financial": _section(financial_res),
            "news": _section(news_res),
        }

        # ── Trust layer ───────────────────────────────────────────────
        envelopes = [
            DataEnvelope(
                value=None, source=res.source or "unknown", is_mock=res.is_mock
            )
            for res in (price_res, history_res, financial_res, news_res)
            if res.success
        ]
        trust = aggregate_confidence(envelopes)

        # ── Computation layer ─────────────────────────────────────────
        ind = _compute_indicators(
            price_res.data if price_res.success else None,
            history_res.data if history_res.success else None,
            financial_res.data if financial_res.success else None,
        )

        # ── LLM layer (interpretation only) ───────────────────────────
        findings = _deterministic_findings(symbol, ind)
        summary = None
        if use_llm:
            summary = await _maybe_llm_summary(symbol, ind, findings, language)
        summary_source = "llm" if summary else "rule_based"
        if summary is None:
            summary = " ".join(findings)

        warnings: list[str] = []
        for name, section in data.items():
            if section["is_mock"]:
                warnings.append(f"{name}: simulated data ({section['warning']}).")
            elif not section["available"]:
                warnings.append(f"{name}: unavailable ({section['error']}).")

        report = {
            "summary": summary,
            "summary_source": summary_source,
            "key_findings": findings,
        }

        return ResearchResult(
            symbol=symbol,
            generated_at=datetime.now(timezone.utc).isoformat(),
            data=data,
            indicators=ind,
            trust=trust,
            report=report,
            disclaimer=DISCLAIMER_ZH if language == "zh" else DISCLAIMER,
            warnings=warnings,
        )
