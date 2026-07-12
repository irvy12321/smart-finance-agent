"""
Reasoner - 多步推理 + 可解释分析 + 图表规格输出
整合了原 ChartAgent 的 LLM 推理能力
"""

import json
import re
from dataclasses import dataclass, field

from app.core.agent_status import AgentEvent, EventBus
from app.core.prompt_manager import get_prompt
from app.infrastructure.llm_client import LiteLLMRouter, LLMClient
from app.infrastructure.otel import traced
from app.utils.logger import get_logger

logger = get_logger("reasoner")

_PROMPT_EXAMPLE_RE = re.compile(
    r"(concise step-by-step analysis|简洁的逐步分析|insight\s*\d+|洞察\s*\d+|"
    r"what might be uncertain|可能不确定的内容|refined step-by-step analysis|"
    r"修正后的逐步分析|specific issue description|missing analysis angle|"
    r"具体问题描述|遗漏的重要分析角度|^Title$|^标题$)",
    re.IGNORECASE,
)


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

CRITICAL RULES:
- NEVER invent, estimate, or generate numeric values. Only use numbers that appear verbatim in the provided context.
- The charts array is OPTIONAL. Only include a chart when the context already contains concrete numbers for every data point.
- If the context lacks sufficient numbers, return an empty charts array ([]). Do NOT fabricate data to satisfy a chart.
- Chart types: bar, line, pie, scatter
- Keep reasoning under 300 words
- Reply in the same language as the question"""

REASONER_SYSTEM_ZH = """你是一个推理引擎。根据上下文和问题，生成推理和图表规格。

只输出有效的JSON：
{
  "reasoning": "简洁的逐步分析",
  "key_insights": ["洞察1", "洞察2"],
  "confidence": 0.8,
  "critique": "可能不确定的内容",
  "charts": [
    {"chart_type":"bar","title":"标题","x_label":"X","y_label":"Y","data":[{"label":"A","value":100},{"label":"B","value":200},{"label":"C","value":150}]}
  ]
}

关键规则：
- 禁止编造、估算或生成任何数值。只能使用上下文中原样出现的数字。
- charts 字段为可选。只有当上下文已包含每个数据点的具体数字时才输出图表。
- 如果上下文数字不足，返回空的 charts 数组（[]）。不得为了凑出图表而编造数据。
- 图表类型：bar（柱状图）、line（折线图）、pie（饼图）、scatter（散点图）
- 必须使用中文回复"""

REASONER_SYSTEM_EN = """You are a reasoning engine. Given context and question, produce reasoning AND chart specs.

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

CRITICAL RULES:
- NEVER invent, estimate, or generate numeric values. Only use numbers that appear verbatim in the provided context.
- The charts array is OPTIONAL. Only include a chart when the context already contains concrete numbers for every data point.
- If the context lacks sufficient numbers, return an empty charts array ([]). Do NOT fabricate data to satisfy a chart.
- Chart types: bar, line, pie, scatter
- You MUST reply in English"""


# ── Self-Critique prompts ──────────────────────────────────────────────────

CRITIQUE_SYSTEM_ZH = """你是一个批判性审查引擎。你将看到一段金融推理结果、原始上下文和问题。
你的任务是找出推理中的缺陷。

只输出有效的JSON：
{
  "issues": ["具体问题描述1", "具体问题描述2"],
  "missing_angles": ["遗漏的重要分析角度1", "遗漏的重要分析角度2"],
  "severity": "high"
}

severity 取值规则：
- "high": 存在无数据支撑的结论，或编造了上下文中没有的数字
- "medium": 推理有遗漏但无事实错误
- "low": 推理质量良好，无需修正

关键规则：
- 只根据上下文判断，不要引入外部知识
- 如果推理中出现了上下文没有的数字，severity 必须为 "high"
- 如果没有发现问题，返回空数组和 "low"
- 必须使用中文回复"""

CRITIQUE_SYSTEM_EN = """You are a critical review engine. You will see a financial reasoning result, the original context, and the question.
Your task is to find flaws in the reasoning.

Output ONLY valid JSON:
{
  "issues": ["specific issue description 1", "specific issue description 2"],
  "missing_angles": ["missing analysis angle 1", "missing analysis angle 2"],
  "severity": "high"
}

severity rules:
- "high": there are conclusions without data support, or numbers fabricated that don't appear in context
- "medium": reasoning has omissions but no factual errors
- "low": reasoning quality is good, no correction needed

CRITICAL RULES:
- Judge only based on the context, do not introduce external knowledge
- If the reasoning contains numbers not in the context, severity MUST be "high"
- If no issues found, return empty arrays and "low"
- You MUST reply in English"""


# ── Refine prompts ──────────────────────────────────────────────────────────

REFINE_SYSTEM_ZH = """你是一个推理修正引擎。你将看到原始推理、批评意见、上下文和问题。
请根据批评意见修正推理，输出修正后的完整推理结果。

只输出有效的JSON：
{
  "reasoning": "修正后的逐步分析",
  "key_insights": ["修正后的洞察1", "修正后的洞察2"],
  "confidence": 0.8,
  "critique": "已修正的问题说明",
  "charts": [
    {"chart_type":"bar","title":"标题","x_label":"X","y_label":"Y","data":[{"label":"A","value":100}]}
  ]
}

关键规则：
- 禁止编造、估算或生成任何数值。只能使用上下文中原样出现的数字。
- 必须解决批评中指出的每一个 issue
- 如果批评指出某个数字无来源，必须删除该数字
- charts 字段为可选，无足够数据时返回空数组
- 必须使用中文回复"""

REFINE_SYSTEM_EN = """You are a reasoning refinement engine. You will see the original reasoning, critique, context, and question.
Please refine the reasoning based on the critique and output the corrected full reasoning result.

Output ONLY valid JSON:
{
  "reasoning": "refined step-by-step analysis",
  "key_insights": ["refined insight 1", "refined insight 2"],
  "confidence": 0.8,
  "critique": "description of corrections made",
  "charts": [
    {"chart_type":"bar","title":"Title","x_label":"X","y_label":"Y","data":[{"label":"A","value":100}]}
  ]
}

CRITICAL RULES:
- NEVER invent, estimate, or generate numeric values. Only use numbers that appear verbatim in the provided context.
- You MUST address every issue raised in the critique
- If the critique flags a number as unsupported, you MUST remove that number
- charts array is OPTIONAL, return empty array if insufficient data
- You MUST reply in English"""


class Reasoner:
    def __init__(
        self, llm_client: LLMClient | None = None, router: LiteLLMRouter | None = None
    ):
        self.router = router
        self.llm = llm_client or LLMClient.get_instance()
        self.event_bus = EventBus.get_instance()

    @traced("reasoner.reason")
    async def reason(
        self, context: str, question: str, language: str = "en"
    ) -> ReasoningResult:
        """多步推理 + 图表规格生成"""
        logger.info(f"Reasoning for: {question[:60]}... (language={language})")
        await self.event_bus.emit(
            AgentEvent(
                event_type="reasoning_start",
                agent_name="reasoner",
                data={"question": question[:100]},
            )
        )

        prompt = (
            f"## Context\n{context}\n\n"
            f"## Question\n{question}\n\n"
            f"Provide reasoning, insights, and chart specifications."
        )

        # Select system prompt based on language
        system_prompt = get_prompt(
            "reasoner",
            f"system_{language}" if language in ("zh", "en") else "system_en",
            default=REASONER_SYSTEM_ZH if language == "zh" else REASONER_SYSTEM_EN,
        )

        try:
            if self.router:
                response = await self.router.complete(
                    "reasoner",
                    prompt=prompt,
                    system=system_prompt,
                    max_tokens=1500,
                )
            else:
                response = await self.llm.complete(
                    prompt=prompt,
                    system=system_prompt,
                    temperature=0.4,
                    max_tokens=1500,
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

            await self.event_bus.emit(
                AgentEvent(
                    event_type="reasoning_complete",
                    agent_name="reasoner",
                    data={
                        "confidence": result.confidence,
                        "insights_count": len(result.key_insights),
                        "charts_count": len(result.chart_specs),
                    },
                )
            )

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
            lines = [line for line in lines if not line.strip().startswith("```")]
            text = "\n".join(lines).strip()

        data = self._load_first_json_object(text)
        if data is None:
            logger.warning("No valid JSON object found in reasoner response")
            return ReasoningResult(
                reasoning=text[:500],
                critique="",
                confidence=0.0,
                key_insights=[],
            )

        # 解析图表规格
        chart_specs = []
        charts_data = data.get("charts", [])
        logger.info(f"Found {len(charts_data)} charts in response")

        for c in charts_data:
            if isinstance(c, dict):
                raw_data = c.get("data", [])
                valid_data = [
                    d
                    for d in raw_data
                    if isinstance(d, dict) and "label" in d and "value" in d
                ]
                if valid_data:  # Only add chart if it has valid data
                    chart_specs.append(
                        ChartSpec(
                            chart_type=str(c.get("chart_type", "bar")),
                            title=str(c.get("title", "")),
                            x_label=str(c.get("x_label", "")),
                            y_label=str(c.get("y_label", "")),
                            data=valid_data,
                            description=str(c.get("description", "")),
                        )
                    )
                    logger.info(
                        f"Added chart: {c.get('title', 'untitled')} with {len(valid_data)} data points"
                    )
                else:
                    logger.warning(
                        f"Skipping chart with no valid data: {c.get('title', 'untitled')}"
                    )

        return ReasoningResult(
            reasoning=data.get("reasoning", ""),
            critique=data.get("critique", ""),
            confidence=self._parse_confidence(data.get("confidence")),
            key_insights=data.get("key_insights", []),
            chart_specs=chart_specs,
        )

    @classmethod
    def _load_first_json_object(cls, text: str) -> dict | None:
        text = re.sub(r"[\x00-\x1f\x7f]", "", text or "")
        position = 0
        while True:
            start = text.find("{", position)
            if start == -1:
                return None
            end = cls._find_matching_object_end(text, start)
            if end is None:
                position = start + 1
                continue
            json_str = re.sub(r",\s*([}\]])", r"\1", text[start:end])
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                position = end
                continue
            if isinstance(data, dict) and not cls._is_prompt_example_object(data):
                return data
            position = end

    @classmethod
    def _is_prompt_example_object(cls, data: dict) -> bool:
        return any(
            _PROMPT_EXAMPLE_RE.search(value) for value in cls._collect_strings(data)
        )

    @classmethod
    def _collect_strings(cls, value) -> list[str]:
        if isinstance(value, str):
            text = value.strip()
            return [text] if text else []
        if isinstance(value, list):
            strings: list[str] = []
            for item in value:
                strings.extend(cls._collect_strings(item))
            return strings
        if isinstance(value, dict):
            strings: list[str] = []
            for item in value.values():
                strings.extend(cls._collect_strings(item))
            return strings
        return []

    @staticmethod
    def _find_matching_object_end(text: str, start: int) -> int | None:
        depth = 0
        in_string = False
        escaped = False
        for i in range(start, len(text)):
            char = text[i]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return i + 1
        return None

    @staticmethod
    def _parse_confidence(value) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, confidence))

    # ── Self-Critique Loop ───────────────────────────────────────────────

    _CRITIQUE_CONFIDENCE_THRESHOLD = 0.6

    @traced("reasoner.reason_with_critique")
    async def reason_with_critique(
        self,
        context: str,
        question: str,
        language: str = "en",
        critique_rounds: int = 1,
    ) -> ReasoningResult:
        """reason() + self-critique loop.

        1. Generate initial reasoning via ``reason()``.
        2. If confidence < threshold, run ``_self_critique()``.
        3. If critique severity is high/medium, run ``_refine()``.
        4. Return refined result (or original if no issues found).
        """
        result = await self.reason(context, question, language)

        if critique_rounds <= 0:
            return result

        # Only critique if confidence is below threshold
        if result.confidence >= self._CRITIQUE_CONFIDENCE_THRESHOLD:
            logger.info(
                f"Skipping self-critique: confidence={result.confidence:.1%} "
                f">= threshold {self._CRITIQUE_CONFIDENCE_THRESHOLD}"
            )
            return result

        await self.event_bus.emit(
            AgentEvent(
                event_type="reasoning_critique_start",
                agent_name="reasoner",
                data={"confidence": result.confidence},
            )
        )

        try:
            critique_result = await self._self_critique(
                result, context, question, language
            )
        except Exception as e:
            logger.warning(f"Self-critique failed, returning original: {e}")
            return result

        severity = critique_result.get("severity", "low")
        issues = critique_result.get("issues", [])

        if severity == "low" or not issues:
            logger.info(
                f"Self-critique: no issues (severity={severity}), keeping original"
            )
            await self.event_bus.emit(
                AgentEvent(
                    event_type="reasoning_critique_complete",
                    agent_name="reasoner",
                    data={"severity": severity, "refined": False},
                )
            )
            return result

        logger.info(
            f"Self-critique found {len(issues)} issues (severity={severity}), refining..."
        )

        try:
            refined = await self._refine(
                result, critique_result, context, question, language
            )
            await self.event_bus.emit(
                AgentEvent(
                    event_type="reasoning_critique_complete",
                    agent_name="reasoner",
                    data={
                        "severity": severity,
                        "refined": True,
                        "issues_count": len(issues),
                        "original_confidence": result.confidence,
                        "refined_confidence": refined.confidence,
                    },
                )
            )
            return refined
        except Exception as e:
            logger.warning(f"Refine failed, returning original: {e}")
            return result

    async def _self_critique(
        self,
        result: ReasoningResult,
        context: str,
        question: str,
        language: str = "en",
    ) -> dict:
        """Run LLM critique on the reasoning result. Returns structured critique dict."""
        system_prompt = get_prompt(
            "reasoner",
            f"critique_{language}" if language in ("zh", "en") else "critique_en",
            default=CRITIQUE_SYSTEM_ZH if language == "zh" else CRITIQUE_SYSTEM_EN,
        )

        prompt = (
            f"## Context\n{context}\n\n"
            f"## Question\n{question}\n\n"
            f"## Reasoning Result\n"
            f"Reasoning: {result.reasoning}\n"
            f"Key Insights: {json.dumps(result.key_insights, ensure_ascii=False)}\n"
            f"Confidence: {result.confidence}\n"
            f"Critique: {result.critique}\n\n"
            f"Review this reasoning for flaws."
        )

        if self.router:
            response = await self.router.complete(
                "reasoner",
                prompt=prompt,
                system=system_prompt,
                max_tokens=800,
            )
        else:
            response = await self.llm.complete(
                prompt=prompt,
                system=system_prompt,
                temperature=0.3,
                max_tokens=800,
            )

        if not response:
            return {"issues": [], "missing_angles": [], "severity": "low"}

        return self._parse_critique_response(response)

    def _parse_critique_response(self, response: str) -> dict:
        """Parse the critique LLM response into a structured dict."""
        text = response.strip()
        if "```" in text:
            lines = text.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            text = "\n".join(lines).strip()

        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            text = text[start:end]

        text = re.sub(r",\s*([}\]])", r"\1", text)

        try:
            data = json.loads(text)
            return {
                "issues": data.get("issues", []),
                "missing_angles": data.get("missing_angles", []),
                "severity": data.get("severity", "low"),
            }
        except json.JSONDecodeError as e:
            logger.warning(f"Critique JSON parse failed: {e}")
            return {"issues": [], "missing_angles": [], "severity": "low"}

    async def _refine(
        self,
        original: ReasoningResult,
        critique: dict,
        context: str,
        question: str,
        language: str = "en",
    ) -> ReasoningResult:
        """Refine the reasoning based on critique. Returns a new ReasoningResult."""
        system_prompt = get_prompt(
            "reasoner",
            f"refine_{language}" if language in ("zh", "en") else "refine_en",
            default=REFINE_SYSTEM_ZH if language == "zh" else REFINE_SYSTEM_EN,
        )

        critique_text = json.dumps(critique, ensure_ascii=False, indent=2)

        prompt = (
            f"## Context\n{context}\n\n"
            f"## Question\n{question}\n\n"
            f"## Original Reasoning\n"
            f"Reasoning: {original.reasoning}\n"
            f"Key Insights: {json.dumps(original.key_insights, ensure_ascii=False)}\n"
            f"Confidence: {original.confidence}\n\n"
            f"## Critique\n{critique_text}\n\n"
            f"Refine the reasoning addressing all issues. Output the complete refined result."
        )

        if self.router:
            response = await self.router.complete(
                "reasoner",
                prompt=prompt,
                system=system_prompt,
                max_tokens=1500,
            )
        else:
            response = await self.llm.complete(
                prompt=prompt,
                system=system_prompt,
                temperature=0.4,
                max_tokens=1500,
            )

        if not response:
            logger.warning("Empty response from refine, returning original")
            return original

        refined = self._parse_response(response)
        logger.info(
            f"Refined: confidence {original.confidence:.1%} -> {refined.confidence:.1%}"
        )
        return refined

    # ── Legacy critique method (kept for backward compatibility) ──────────

    async def critique(self, answer: str, question: str) -> str:
        """对已有答案进行批判性分析（legacy, returns plain string）"""
        prompt = (
            f"Question: {question}\n\nAnswer: {answer}\n\n"
            "Critique this answer. Strengths? Weaknesses? How to improve?"
        )
        if self.router:
            return await self.router.complete(
                "reasoner", prompt=prompt, max_tokens=1024
            )
        else:
            return await self.llm.complete(
                prompt=prompt, temperature=0.3, max_tokens=1024
            )
