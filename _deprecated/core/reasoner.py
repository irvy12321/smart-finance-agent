"""
Reasoner - 多步推理 + 可解释分析 + 图表规格输出
整合了原 ChartAgent 的 LLM 推理能力
"""
import json
import re
from dataclasses import dataclass, field
from infrastructure.llm_client import LLMClient, LiteLLMRouter
from core.agent_status import EventBus, AgentEvent
from utils.logger import get_logger

logger = get_logger("reasoner")


@dataclass
class ChartSpec:
    """图表规格"""
    chart_type: str  # "bar", "line", "pie", "scatter"
    title: str
    x_label: str
    y_label: str
    data: list[dict] = field(default_factory=list)
    description: str = ""


@dataclass
class ReasoningResult:
    reasoning: str
    critique: str
    confidence: float  # 0-1
    key_insights: list[str]
    chart_specs: list[ChartSpec] = field(default_factory=list)


REASONER_SYSTEM = """You are a reasoning engine. Given context and question, produce reasoning AND chart specs.

Output ONLY valid JSON:
{
  "reasoning": "concise step-by-step analysis",
  "key_insights": ["insight 1", "insight 2"],
  "confidence": 0.8,
  "critique": "what might be uncertain",
  "charts": [
    {"chart_type":"bar","title":"Title","x_label":"X","y_label":"Y","data":[{"label":"A","value":100},{"label":"B","value":200},{"label":"C","value":150}]}
  ]
}

Chart types: bar, line, pie, scatter. Each chart needs 3+ data points. Keep reasoning under 300 words."""


class Reasoner:
    def __init__(self, llm_client: LLMClient | None = None, router: LiteLLMRouter | None = None):
        self.router = router
        self.llm = llm_client or LLMClient.get_instance()
        self.event_bus = EventBus.get_instance()

    async def reason(self, context: str, question: str) -> ReasoningResult:
        """多步推理 + 图表规格生成"""
        logger.info(f"Reasoning for: {question[:60]}...")
        await self.event_bus.emit(AgentEvent(
            event_type="reasoning_start",
            agent_name="reasoner",
            data={"question": question[:100]},
        ))

        prompt = (
            f"## Context\n{context}\n\n"
            f"## Question\n{question}\n\n"
            f"Provide reasoning, insights, and chart specifications."
        )

        try:
            if self.router:
                response = await self.router.complete(
                    "reasoner", prompt=prompt, system=REASONER_SYSTEM, max_tokens=1500,
                )
            else:
                response = await self.llm.complete(
                    prompt=prompt, system=REASONER_SYSTEM, temperature=0.4, max_tokens=1500,
                )

            # MiMo reasoning_content fallback
            if not response:
                logger.warning("Empty response from reasoner")
                return ReasoningResult(
                    reasoning="No reasoning generated",
                    critique="LLM returned empty response",
                    confidence=0.0,
                    key_insights=[],
                )

            result = self._parse_response(response)

            await self.event_bus.emit(AgentEvent(
                event_type="reasoning_complete",
                agent_name="reasoner",
                data={
                    "confidence": result.confidence,
                    "insights_count": len(result.key_insights),
                    "charts_count": len(result.chart_specs),
                },
            ))

            logger.info(
                f"Reasoning done: confidence={result.confidence:.1%}, "
                f"insights={len(result.key_insights)}, charts={len(result.chart_specs)}"
            )
            return result

        except Exception as e:
            logger.error(f"Reasoning failed: {e}")
            return ReasoningResult(
                reasoning=f"Reasoning failed: {e}",
                critique="Unable to complete reasoning",
                confidence=0.0,
                key_insights=[],
            )

    def _parse_response(self, response: str) -> ReasoningResult:
        text = response.strip()
        if "```" in text:
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            text = text[start:end]

        text = re.sub(r",\s*([}\]])", r"\1", text)
        text = re.sub(r"[\x00-\x1f\x7f]", "", text)

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return ReasoningResult(
                reasoning=text[:500],
                critique="",
                confidence=0.5,
                key_insights=[],
            )

        # 解析图表规格
        chart_specs = []
        for c in data.get("charts", []):
            if isinstance(c, dict):
                raw_data = c.get("data", [])
                valid_data = [d for d in raw_data if isinstance(d, dict) and "label" in d and "value" in d]
                chart_specs.append(ChartSpec(
                    chart_type=str(c.get("chart_type", "bar")),
                    title=str(c.get("title", "")),
                    x_label=str(c.get("x_label", "")),
                    y_label=str(c.get("y_label", "")),
                    data=valid_data,
                    description=str(c.get("description", "")),
                ))

        return ReasoningResult(
            reasoning=data.get("reasoning", ""),
            critique=data.get("critique", ""),
            confidence=float(data.get("confidence", 0.5)),
            key_insights=data.get("key_insights", []),
            chart_specs=chart_specs,
        )

    async def critique(self, answer: str, question: str) -> str:
        """对已有答案进行批判性分析"""
        prompt = (
            f"Question: {question}\n\nAnswer: {answer}\n\n"
            "Critique this answer. Strengths? Weaknesses? How to improve?"
        )
        if self.router:
            return await self.router.complete("reasoner", prompt=prompt, max_tokens=1024)
        else:
            return await self.llm.complete(prompt=prompt, temperature=0.3, max_tokens=1024)
