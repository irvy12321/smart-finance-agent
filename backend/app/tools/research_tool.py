"""DAG-executable wrapper around the ResearchService mainline.

The grounded single-stock research pipeline (data → indicators → trust → LLM
interpretation) used to be reachable only via ``POST /api/research/{symbol}``,
entirely disconnected from the Planner/Executor DAG. This tool exposes that same
pipeline as a single ``stock_research`` node so the Planner can place the whole
"fetch + compute indicators + confidence + anti-hallucination summary" flow
inside a DAG. ``ResearchService`` and the existing endpoint are unchanged.
"""

from __future__ import annotations

from typing import Any

from app.core.research import ResearchService
from app.tools.base_tool import BaseTool, ToolResult
from app.utils.logger import get_logger

logger = get_logger("research_tool")


class StockResearchTool(BaseTool):
    name = "stock_research"
    description = (
        "Full grounded research pipeline for ONE stock: fetches price / history / "
        "financials / news, computes indicators (SMA/RSI/EMA/PE) in pure Python, "
        "aggregates data confidence, and writes an anti-hallucination summary. "
        'Params: {"symbol": "<TICKER>"}.'
    )

    def __init__(self, service: ResearchService | None = None):
        self.service = service or ResearchService()

    async def execute(self, **kwargs) -> ToolResult:
        symbol = str(kwargs.get("symbol", "")).strip().upper()
        if not symbol:
            return ToolResult(
                success=False,
                error="No stock symbol provided",
                tool_name=self.name,
            )

        language = kwargs.get("language", "en")
        use_llm = kwargs.get("use_llm", True)

        try:
            result = await self.service.research(
                symbol, language=language, use_llm=use_llm
            )
        except Exception as e:
            logger.error(f"stock_research failed for {symbol}: {e}")
            return ToolResult(success=False, error=str(e), tool_name=self.name)

        data: dict[str, Any] = result.to_dict()
        # The whole report is mock-tainted if any underlying section is simulated;
        # surfacing this lets the trust layer lower confidence accordingly.
        is_mock = any(
            isinstance(section, dict) and section.get("is_mock")
            for section in result.data.values()
        )
        return ToolResult(
            success=True,
            data=data,
            tool_name=self.name,
            source="stock_research",
            is_mock=is_mock,
        )
