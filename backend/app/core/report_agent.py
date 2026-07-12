"""
Report Agent - 结构化研究报告生成
输出: summary (短文本) + structured_analysis (JSON)
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.core.agent_status import AgentEvent, EventBus
from app.core.executor import ExecutionResult
from app.core.prompt_manager import get_prompt
from app.core.reasoner import ReasoningResult
from app.infrastructure.llm_client import LiteLLMRouter, LLMClient
from app.infrastructure.otel import traced
from app.utils.logger import get_logger

logger = get_logger("report_agent")

_NUMERIC_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_.])-?\d[\d,]*(?:\.\d+)?%?(?![A-Za-z0-9_])"
)
_PLACEHOLDER_TEXT_RE = re.compile(
    r"(报告标题|来自数据的具体发现|另一个真实发现|趋势\s*\d+|建议\s*\d+|"
    r"\bReport Title\b|specific finding from data|another real finding|trend\s*\d+|"
    r"rec\s*\d+|finding\s*\d+|200字以内|简洁摘要|使用实际数据|"
    r"\bName\b|名称|\bbrief\b|简述)",
    re.IGNORECASE,
)
_PROMPT_ECHO_RE = re.compile(
    r"(You are a report generator|我是一个报告生成器|报告生成器|"
    r"Output ONLY valid JSON|只输出有效\s*JSON|Research question|Research data|"
    r"Generate structured analysis as JSON|CRITICAL RULES|关键规则|"
    r"key_findings|risk_factors|market_trends|recommendations|schema|结构如下)",
    re.IGNORECASE,
)


@dataclass
class StructuredAnalysis:
    """结构化分析结果"""

    key_findings: list[str] = field(default_factory=list)
    risk_factors: list[dict] = field(
        default_factory=list
    )  # [{"factor": "...", "severity": "high/medium/low", "description": "..."}]
    market_trends: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "key_findings": self.key_findings,
            "risk_factors": self.risk_factors,
            "market_trends": self.market_trends,
            "recommendations": self.recommendations,
        }


@dataclass
class ResearchReport:
    title: str
    summary: str  # 200字以内的短摘要
    analysis: StructuredAnalysis  # 结构化 JSON 分析
    sources: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    trace_id: str = ""

    def to_markdown(self, language: str = "en") -> str:
        """生成 Markdown 格式报告"""
        sources_md = ""
        for i, src in enumerate(self.sources, 1):
            sources_md += (
                f"{i}. **{src.get('tool', 'N/A')}** ({src.get('task_id', '')})\n"
            )

        findings_md = "\n".join(f"- {f}" for f in self.analysis.key_findings)
        risks_md = "\n".join(
            f"- **{r['factor']}** [{r.get('severity', 'medium')}]: {r.get('description', '')}"
            for r in self.analysis.risk_factors
        )
        trends_md = "\n".join(f"- {t}" for t in self.analysis.market_trends)
        recs_md = "\n".join(f"- {r}" for r in self.analysis.recommendations)

        timestamp = self.metadata.get("timestamp", datetime.now().isoformat())
        total_tasks = self.metadata.get("total_tasks", 0)
        success_tasks = self.metadata.get("success_tasks", 0)
        total_ms = self.metadata.get("total_ms", 0)

        if language == "zh":
            return f"""# {self.title}

## 摘要
{self.summary}

## 关键发现
{findings_md}

## 风险因素
{risks_md}

## 市场趋势
{trends_md}

## 建议
{recs_md}

## 数据来源
{sources_md}

---
*生成时间: {timestamp} | 任务: {success_tasks}/{total_tasks} 成功 | 耗时: {total_ms:.0f}ms*"""
        else:
            return f"""# {self.title}

## Summary
{self.summary}

## Key Findings
{findings_md}

## Risk Factors
{risks_md}

## Market Trends
{trends_md}

## Recommendations
{recs_md}

## Data Sources
{sources_md}

---
*Generated: {timestamp} | Tasks: {success_tasks}/{total_tasks} succeeded | Duration: {total_ms:.0f}ms*"""


REPORT_SYSTEM = """You are a report generator. Given research data, produce a REAL analysis based on the actual data provided.

Output ONLY valid JSON in this shape:
{"title":"Report Title","summary":"concise summary under 200 chars using ACTUAL data","key_findings":["specific finding from data","another real finding"],"risk_factors":[{"factor":"Name","severity":"high","description":"brief"}],"market_trends":["trend 1"],"recommendations":["rec 1"]}

CRITICAL RULES:
- NEVER copy schema labels or placeholder text into the answer.
- NEVER use placeholder text like "finding 1", "发现1", "trend 1", "rec 1" - always use REAL data from the context
- summary must contain actual information, not templates
- key_findings must reference specific numbers, companies, or facts from the data
- If data is limited, summarize what IS available rather than inventing placeholders
- You MUST NOT generate, estimate, or invent any numeric value. Only cite numbers present in the context.
- You MUST NOT fill in missing data. If a field is null/missing, explicitly state "data not available".
- All conclusions must reference specific numbers from the provided context.
- If any input is labelled is_mock=true (or carries a SIMULATED DATA warning), you MUST add: "This analysis includes simulated data and is not suitable for investment decisions."
- YOU MUST reply in the specified language: {language}"""

REPORT_SYSTEM_ZH = """你是一个报告生成器。根据提供的研究数据，生成基于实际数据的真实分析。

只输出这种格式的有效 JSON：
{"title":"报告标题","summary":"200字以内的简洁摘要，使用实际数据","key_findings":["来自数据的具体发现","另一个真实发现"],"risk_factors":[{"factor":"名称","severity":"high","description":"简述"}],"market_trends":["趋势1"],"recommendations":["建议1"]}

关键规则：
- 绝对不要把结构说明、字段说明或占位符复制到答案里。
- 绝对不要使用"发现1"、"趋势1"、"建议1"这样的占位符，始终使用上下文中的真实数据
- 摘要必须包含实际信息，而非模板
- 关键发现必须引用数据中的具体数字、公司或事实
- 如果数据有限，总结已有内容而非编造占位符
- 禁止生成、估算或编造任何数值，只能引用上下文中出现的数字。
- 禁止填补缺失数据。如果某字段为空/缺失，明确声明“数据不可用”。
- 所有结论必须引用上下文中的具体数字。
- 如果任何输入被标记为 is_mock=true（或带有 SIMULATED DATA 警告），必须加上：“本分析包含模拟数据，不适用于投资决策。”
- 必须使用中文回复"""

REPORT_SYSTEM_EN = """You are a report generator. Given research data, produce a REAL analysis based on the actual data provided.

Output ONLY valid JSON in this shape:
{"title":"Report Title","summary":"concise summary under 200 chars using ACTUAL data","key_findings":["specific finding from data","another real finding"],"risk_factors":[{"factor":"Name","severity":"high","description":"brief"}],"market_trends":["trend 1"],"recommendations":["rec 1"]}

CRITICAL RULES:
- NEVER copy schema labels or placeholder text into the answer.
- NEVER use placeholder text like "finding 1", "发现1", "trend 1", "rec 1" - always use REAL data from the context
- summary must contain actual information, not templates
- key_findings must reference specific numbers, companies, or facts from the data
- If data is limited, summarize what IS available rather than inventing placeholders
- You MUST NOT generate, estimate, or invent any numeric value. Only cite numbers present in the context.
- You MUST NOT fill in missing data. If a field is null/missing, explicitly state "data not available".
- All conclusions must reference specific numbers from the provided context.
- If any input is labelled is_mock=true (or carries a SIMULATED DATA warning), you MUST add: "This analysis includes simulated data and is not suitable for investment decisions."
- You MUST reply in English"""


class ReportAgent:
    def __init__(
        self, llm_client: LLMClient | None = None, router: LiteLLMRouter | None = None
    ):
        self.router = router
        self.llm = llm_client or LLMClient.get_instance()
        self.event_bus = EventBus.get_instance()

    @traced("report_agent.generate")
    async def generate(
        self,
        query: str,
        exec_result: ExecutionResult,
        reasoning_result: ReasoningResult | None = None,
        trace_id: str = "",
        language: str = "en",
    ) -> ResearchReport:
        """生成结构化研究报告"""
        logger.info(f"Generating research report (language={language})...")
        await self.event_bus.emit(
            AgentEvent(
                event_type="report_start",
                agent_name="report",
                data={"query": query[:100]},
            )
        )

        # 收集成功任务数据
        sources = []
        data_parts = []
        for tr in exec_result.task_results:
            if tr.success and tr.data:
                sources.append(
                    {
                        "task_id": tr.task_id,
                        "tool": tr.tool_name,
                        "duration_ms": tr.duration_ms,
                    }
                )
                data_parts.append(f"[{tr.tool_name}] {self._format_data(tr.data)}")

        # 推理上下文
        if reasoning_result:
            data_parts.append(f"[reasoning] {reasoning_result.reasoning}")
            if reasoning_result.key_insights:
                data_parts.append(
                    f"[insights] {', '.join(reasoning_result.key_insights)}"
                )

        context = "\n\n".join(data_parts)
        prompt = (
            f"Research question: {query}\n\n"
            f"Research data:\n{context}\n\n"
            f"Generate structured analysis as JSON."
        )

        # Select system prompt based on language
        system_prompt = get_prompt(
            "report",
            f"system_{language}" if language in ("zh", "en") else "system_en",
            default=REPORT_SYSTEM_ZH if language == "zh" else REPORT_SYSTEM_EN,
        )

        try:
            logger.info(
                f"Calling LLM for report generation (prompt length: {len(prompt)} chars)"
            )
            if self.router:
                response = await asyncio.wait_for(
                    self.router.complete(
                        "report", prompt=prompt, system=system_prompt, max_tokens=2000
                    ),
                    timeout=120,
                )
            else:
                response = await asyncio.wait_for(
                    self.llm.complete(
                        prompt=prompt,
                        system=system_prompt,
                        temperature=0.5,
                        max_tokens=2000,
                    ),
                    timeout=120,
                )
            logger.info(f"LLM response received ({len(response)} chars)")

            report_data = self._parse_response(response)
            report_data = self._remove_unsupported_numbers(
                report_data, allowed_numbers=self._extract_number_tokens(prompt)
            )
            report_data = self._sanitize_report_data(
                report_data,
                query=query,
                exec_result=exec_result,
                reasoning_result=reasoning_result,
                language=language,
            )

            analysis = StructuredAnalysis(
                key_findings=report_data.get("key_findings", []),
                risk_factors=report_data.get("risk_factors", []),
                market_trends=report_data.get("market_trends", []),
                recommendations=report_data.get("recommendations", []),
            )

            report = ResearchReport(
                title=report_data.get("title", f"Research: {query[:50]}"),
                summary=report_data.get("summary", exec_result.final_answer[:200]),
                analysis=analysis,
                sources=sources,
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "total_tasks": len(exec_result.task_results),
                    "success_tasks": exec_result.success_count,
                    "failed_tasks": exec_result.failed_count,
                    "total_ms": exec_result.total_duration_ms,
                },
                trace_id=trace_id,
            )

            await self.event_bus.emit(
                AgentEvent(
                    event_type="report_complete",
                    agent_name="report",
                    data={"title": report.title, "sources_count": len(sources)},
                )
            )

            logger.info(f"Report generated: {report.title}")
            return report

        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return ResearchReport(
                title=f"Research: {query[:50]}",
                summary=exec_result.final_answer[:200]
                if exec_result.final_answer
                else "No results",
                analysis=StructuredAnalysis(),
                sources=sources,
                metadata={"timestamp": datetime.now().isoformat(), "error": str(e)},
                trace_id=trace_id,
            )

    def _parse_response(self, response: str) -> dict:
        text = response.strip()

        logger.debug(f"Report response ({len(text)} chars): {text[:300]}")

        if "```" in text:
            lines = text.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            text = "\n".join(lines).strip()

        data = self._load_first_json_object(text)
        if data is None:
            logger.warning("No valid JSON object found in report response")
            return {}

        # Ensure summary is a string, not a JSON object
        if isinstance(data.get("summary"), dict):
            data["summary"] = json.dumps(data["summary"], ensure_ascii=False)[:200]
        elif isinstance(data.get("summary"), str) and data["summary"].startswith("{"):
            # Try to parse as JSON and extract meaningful text
            try:
                summary_obj = json.loads(data["summary"])
                if "summary" in summary_obj:
                    data["summary"] = summary_obj["summary"]
            except Exception:
                pass
        return data

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
        strings = cls._collect_strings(data)
        if not strings:
            return False
        placeholder_count = sum(
            1 for value in strings if cls._is_placeholder_text(value)
        )
        return placeholder_count >= max(2, len(strings) // 2)

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

    def _sanitize_report_data(
        self,
        data: dict,
        query: str,
        exec_result: ExecutionResult,
        reasoning_result: ReasoningResult | None,
        language: str,
    ) -> dict:
        cleaned = dict(data or {})

        fallback = self._fallback_report_data(
            query=query,
            exec_result=exec_result,
            reasoning_result=reasoning_result,
            language=language,
        )

        title = cleaned.get("title")
        if not isinstance(title, str) or self._is_placeholder_text(title):
            cleaned["title"] = fallback["title"]

        summary = cleaned.get("summary")
        if not isinstance(summary, str) or self._is_placeholder_text(summary):
            cleaned["summary"] = fallback["summary"]

        cleaned["key_findings"] = (
            self._clean_string_list(cleaned.get("key_findings"))
            or fallback["key_findings"]
        )
        cleaned["market_trends"] = (
            self._clean_string_list(cleaned.get("market_trends"))
            or fallback["market_trends"]
        )
        cleaned["recommendations"] = (
            self._clean_string_list(cleaned.get("recommendations"))
            or fallback["recommendations"]
        )
        cleaned["risk_factors"] = (
            self._clean_risk_factors(cleaned.get("risk_factors"))
            or fallback["risk_factors"]
        )

        return cleaned

    @classmethod
    def _clean_string_list(cls, value) -> list[str]:
        if not isinstance(value, list):
            return []
        cleaned = []
        for item in value:
            if not isinstance(item, str):
                continue
            text = item.strip()
            if text and not cls._is_placeholder_text(text):
                cleaned.append(text)
        return cleaned

    @classmethod
    def _clean_risk_factors(cls, value) -> list[dict]:
        if not isinstance(value, list):
            return []
        cleaned = []
        for item in value:
            if isinstance(item, str):
                if not cls._is_placeholder_text(item):
                    cleaned.append(
                        {"factor": item, "severity": "medium", "description": item}
                    )
                continue
            if not isinstance(item, dict):
                continue

            factor = str(item.get("factor") or item.get("name") or "").strip()
            description = str(item.get("description") or item.get("text") or "").strip()
            severity = str(item.get("severity") or "medium").lower()
            if severity not in {"high", "medium", "low"}:
                severity = "medium"
            if (
                factor
                and description
                and not cls._is_placeholder_text(factor)
                and not cls._is_placeholder_text(description)
            ):
                cleaned.append(
                    {
                        "factor": factor,
                        "severity": severity,
                        "description": description,
                    }
                )
        return cleaned

    @staticmethod
    def _fallback_report_data(
        query: str,
        exec_result: ExecutionResult,
        reasoning_result: ReasoningResult | None,
        language: str,
    ) -> dict:
        final_answer = (exec_result.final_answer or "").strip()
        reasoning = (reasoning_result.reasoning if reasoning_result else "").strip()
        insights = [
            insight
            for insight in (reasoning_result.key_insights if reasoning_result else [])
            if isinstance(insight, str) and insight.strip()
        ]

        summary_source = final_answer or reasoning
        if summary_source:
            summary = summary_source[:200]
        elif language == "zh":
            summary = (
                "研究流程已完成，但工具结果中没有足够的可落地文本用于生成完整摘要。"
            )
        else:
            summary = "Research completed, but tool results did not include enough grounded text for a full summary."

        key_findings = insights[:3]
        if not key_findings:
            successful_tools = [
                result.tool_name
                for result in exec_result.task_results
                if result.success
            ]
            if successful_tools:
                if language == "zh":
                    key_findings = [
                        f"已完成数据收集工具：{', '.join(successful_tools[:5])}。"
                    ]
                else:
                    key_findings = [
                        f"Completed data collection tools: {', '.join(successful_tools[:5])}."
                    ]
            elif language == "zh":
                key_findings = ["没有从已完成工具中获得可验证的关键发现。"]
            else:
                key_findings = [
                    "No verifiable key findings were returned by completed tools."
                ]

        if language == "zh":
            title = f"研究报告：{query[:40]}"
            recommendations = ["请先核对数据源和报告生成日志，再将结果用于进一步分析。"]
            risk_factors = [
                {
                    "factor": "数据完整性",
                    "severity": "medium",
                    "description": "当前报告包含后端兜底内容，说明模型输出缺少足够的结构化、可验证分析。",
                }
            ]
            market_trends = ["市场趋势未从工具结果中形成可靠结论。"]
        else:
            title = f"Research Report: {query[:40]}"
            recommendations = [
                "Verify data sources and report-generation logs before using this result for further analysis."
            ]
            risk_factors = [
                {
                    "factor": "Data completeness",
                    "severity": "medium",
                    "description": "This report used deterministic fallback content because the model output lacked enough grounded structured analysis.",
                }
            ]
            market_trends = [
                "No reliable market trend conclusion was produced from tool results."
            ]

        return {
            "title": title,
            "summary": summary,
            "key_findings": key_findings,
            "risk_factors": risk_factors,
            "market_trends": market_trends,
            "recommendations": recommendations,
        }

    @staticmethod
    def _is_placeholder_text(value: str) -> bool:
        text = (value or "").strip()
        return (
            not text
            or bool(_PLACEHOLDER_TEXT_RE.search(text))
            or bool(_PROMPT_ECHO_RE.search(text))
        )

    @staticmethod
    def _format_data(data) -> str:
        if isinstance(data, str):
            return data[:500]
        if isinstance(data, dict):
            return json.dumps(data, ensure_ascii=False, indent=2)[:500]
        return str(data)[:500]

    @classmethod
    def _extract_number_tokens(cls, text: str) -> set[str]:
        return {
            normalized
            for match in _NUMERIC_TOKEN_RE.finditer(text or "")
            if (normalized := cls._normalize_number_token(match.group(0)))
        }

    @staticmethod
    def _normalize_number_token(token: str) -> str:
        raw = token.strip()
        if not raw:
            return ""
        has_percent = raw.endswith("%")
        raw = raw[:-1] if has_percent else raw
        raw = raw.replace(",", "")
        try:
            number = Decimal(raw)
        except (InvalidOperation, ValueError):
            return token
        normalized = format(number.normalize(), "f")
        if "." in normalized:
            normalized = normalized.rstrip("0").rstrip(".")
        if normalized == "-0":
            normalized = "0"
        return f"{normalized}%" if has_percent else normalized

    @classmethod
    def _remove_unsupported_numbers(cls, value, allowed_numbers: set[str]):
        if isinstance(value, str):
            return _NUMERIC_TOKEN_RE.sub(
                lambda match: (
                    match.group(0)
                    if cls._normalize_number_token(match.group(0)) in allowed_numbers
                    else "[unsupported number removed]"
                ),
                value,
            )
        if isinstance(value, list):
            return [
                cls._remove_unsupported_numbers(item, allowed_numbers) for item in value
            ]
        if isinstance(value, dict):
            return {
                key: cls._remove_unsupported_numbers(item, allowed_numbers)
                for key, item in value.items()
            }
        return value
