"""
Report Agent - 结构化研究报告生成
输出: summary (短文本) + structured_analysis (JSON)
"""
import json
from datetime import datetime
from dataclasses import dataclass, field
from infrastructure.llm_client import LLMClient, LiteLLMRouter
from core.agent_status import EventBus, AgentEvent
from core.executor import ExecutionResult, TaskResult
from core.reasoner import ReasoningResult
from utils.logger import get_logger

logger = get_logger("report_agent")


@dataclass
class StructuredAnalysis:
    """结构化分析结果"""
    key_findings: list[str] = field(default_factory=list)
    risk_factors: list[dict] = field(default_factory=list)  # [{"factor": "...", "severity": "high/medium/low", "description": "..."}]
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

    def to_markdown(self) -> str:
        """生成 Markdown 格式报告"""
        sources_md = ""
        for i, src in enumerate(self.sources, 1):
            sources_md += f"{i}. **{src.get('tool', 'N/A')}** ({src.get('task_id', '')})\n"

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
*生成时间: {timestamp} | 任务: {success_tasks}/{total_tasks} 成功 | 耗时: {total_ms:.0f}ms | Trace: {self.trace_id}*"""


REPORT_SYSTEM = """You are a report generator. Given research data, produce structured analysis as JSON.

Output ONLY valid JSON:
{"title":"Report Title","summary":"under 200 chars","key_findings":["finding 1","finding 2"],"risk_factors":[{"factor":"Name","severity":"high","description":"brief"}],"market_trends":["trend 1"],"recommendations":["rec 1"]}

Rules: summary < 200 chars. 3-5 findings. Each risk has severity (high/medium/low). 2-3 trends. 2-3 recommendations."""


class ReportAgent:
    def __init__(self, llm_client: LLMClient | None = None, router: LiteLLMRouter | None = None):
        self.router = router
        self.llm = llm_client or LLMClient.get_instance()
        self.event_bus = EventBus.get_instance()

    async def generate(
        self,
        query: str,
        exec_result: ExecutionResult,
        reasoning_result: ReasoningResult | None = None,
        trace_id: str = "",
    ) -> ResearchReport:
        """生成结构化研究报告"""
        logger.info("Generating research report...")
        await self.event_bus.emit(AgentEvent(
            event_type="report_start",
            agent_name="report",
            data={"query": query[:100]},
        ))

        # 收集成功任务数据
        sources = []
        data_parts = []
        for tr in exec_result.task_results:
            if tr.success and tr.data:
                sources.append({
                    "task_id": tr.task_id,
                    "tool": tr.tool_name,
                    "duration_ms": tr.duration_ms,
                })
                data_parts.append(f"[{tr.tool_name}] {self._format_data(tr.data)}")

        # 推理上下文
        if reasoning_result:
            data_parts.append(f"[reasoning] {reasoning_result.reasoning}")
            if reasoning_result.key_insights:
                data_parts.append(f"[insights] {', '.join(reasoning_result.key_insights)}")

        context = "\n\n".join(data_parts)
        prompt = (
            f"Research question: {query}\n\n"
            f"Research data:\n{context}\n\n"
            f"Generate structured analysis as JSON."
        )

        try:
            if self.router:
                response = await self.router.complete(
                    "report", prompt=prompt, system=REPORT_SYSTEM, max_tokens=2000,
                )
            else:
                response = await self.llm.complete(
                    prompt=prompt, system=REPORT_SYSTEM, temperature=0.5, max_tokens=2000,
                )

            report_data = self._parse_response(response)

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

            await self.event_bus.emit(AgentEvent(
                event_type="report_complete",
                agent_name="report",
                data={"title": report.title, "sources_count": len(sources)},
            ))

            logger.info(f"Report generated: {report.title}")
            return report

        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return ResearchReport(
                title=f"Research: {query[:50]}",
                summary=exec_result.final_answer[:200] if exec_result.final_answer else "No results",
                analysis=StructuredAnalysis(),
                sources=sources,
                metadata={"timestamp": datetime.now().isoformat(), "error": str(e)},
                trace_id=trace_id,
            )

    def _parse_response(self, response: str) -> dict:
        import re
        text = response.strip()

        logger.debug(f"Report response ({len(text)} chars): {text[:300]}")

        if "```" in text:
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

        # 找到 JSON 对象
        start = text.find("{")
        if start == -1:
            logger.warning("No JSON object found")
            return {"title": "Research Report", "summary": text[:200], "key_findings": [text[:200]]}

        # 匹配闭合括号
        depth = 0
        end = -1
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end == -1:
            end = text.rfind("}") + 1

        json_str = text[start:end]
        json_str = re.sub(r",\s*([}\]])", r"\1", json_str)
        json_str = re.sub(r"[\x00-\x1f\x7f]", "", json_str)

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed: {e}")
            return {"title": "Research Report", "summary": text[:200], "key_findings": [text[:200]]}

    @staticmethod
    def _format_data(data) -> str:
        if isinstance(data, str):
            return data[:500]
        if isinstance(data, dict):
            return json.dumps(data, ensure_ascii=False, indent=2)[:500]
        return str(data)[:500]
