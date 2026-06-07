"""
Chart Agent - 财务数据可视化
基于研究数据生成图表配置，支持 matplotlib/plotly
通过 EventBus 与其他 Agent 解耦通信
"""
import json
from dataclasses import dataclass
from app.infrastructure.llm_client import LLMClient, LiteLLMRouter
from app.core.agent_status import EventBus, AgentEvent
from app.utils.logger import get_logger

logger = get_logger("chart_agent")


@dataclass
class ChartSpec:
    """图表规格"""
    chart_type: str  # "bar", "line", "pie", "scatter"
    title: str
    x_label: str
    y_label: str
    data: list[dict]
    description: str

    def to_dict(self) -> dict:
        return {
            "chart_type": self.chart_type,
            "title": self.title,
            "x_label": self.x_label,
            "y_label": self.y_label,
            "data": self.data,
            "description": self.description,
        }


@dataclass
class ChartResult:
    """图表生成结果"""
    charts: list[ChartSpec]
    summary: str


CHART_SYSTEM = """You are a financial data visualization expert. Given research data, output chart specifications as JSON.

CRITICAL: You MUST output ONLY valid JSON. No markdown, no explanation, no code fences. Just raw JSON.

Output format:
{"charts":[{"chart_type":"bar","title":"Revenue Comparison","x_label":"Quarter","y_label":"Revenue ($M)","data":[{"label":"Q1","value":100},{"label":"Q2","value":150},{"label":"Q3","value":200}],"description":"Quarterly revenue trend"}],"summary":"Brief summary"}

Chart types: "bar" (comparison), "line" (trend), "pie" (proportion), "scatter" (correlation)

Rules:
1. Output ONLY the JSON object, nothing else
2. Each chart data must have at least 3 data points
3. Use numeric values only (no strings in value field)
4. Keep labels concise (under 20 chars)
5. Maximum 3 charts"""


class ChartAgent:
    """
    财务图表生成 Agent
    - 通过 EventBus 接收任务完成事件
    - 使用 LiteLLMRouter 调用 LLM
    - 生成图表规格 (可被前端渲染)
    """

    def __init__(self, llm_client: LLMClient | None = None, router: LiteLLMRouter | None = None):
        self.router = router
        self.llm = llm_client or LLMClient.get_instance()
        self.event_bus = EventBus.get_instance()
        self._last_result: ChartResult | None = None

        # 注册事件监听
        self.event_bus.subscribe("report_complete", self._on_report_complete)

    async def _on_report_complete(self, event: AgentEvent):
        """监听报告完成事件，自动触发图表生成"""
        logger.info("Report complete, chart generation can be triggered")

    async def generate(self, research_data: str, query: str) -> ChartResult:
        """生成财务图表"""
        logger.info(f"Generating charts for: {query[:60]}...")

        await self.event_bus.emit(AgentEvent(
            event_type="chart_start",
            agent_name="chart",
            data={"query": query[:100]},
        ))

        prompt = (
            f"## Research Question\n{query}\n\n"
            f"## Research Data\n{research_data}\n\n"
            f"Generate chart specifications as JSON based on the above data."
        )

        try:
            if self.router:
                response = await self.router.complete(
                    "chart", prompt=prompt, system=CHART_SYSTEM, max_tokens=3000,
                )
            else:
                response = await self.llm.complete(
                    prompt=prompt, system=CHART_SYSTEM, temperature=0.3, max_tokens=3000,
                )

            # 调试日志
            logger.debug(f"Chart LLM response ({len(response)} chars): {response[:300]}")

            result = self._parse_response(response)
            self._last_result = result

            await self.event_bus.emit(AgentEvent(
                event_type="chart_complete",
                agent_name="chart",
                data={"charts_count": len(result.charts)},
            ))

            logger.info(f"Generated {len(result.charts)} charts")
            return result

        except Exception as e:
            logger.error(f"Chart generation failed: {e}")
            return ChartResult(charts=[], summary=f"图表生成失败: {e}")

    def _parse_response(self, response: str) -> ChartResult:
        import re
        text = response.strip()

        # 移除 markdown 代码块
        if "```" in text:
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

        # 提取最外层 JSON 对象
        start = text.find("{")
        if start == -1:
            logger.warning(f"No JSON object found in response: {text[:200]}")
            return ChartResult(charts=[], summary="LLM 未返回 JSON 格式")

        # 找到匹配的闭合括号
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

        # 清理常见格式问题
        json_str = re.sub(r",\s*([}\]])", r"\1", json_str)  # 尾随逗号
        json_str = re.sub(r"[\x00-\x1f\x7f]", "", json_str)  # 控制字符

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            # 二次清理: 尝试修复常见 LLM 输出问题
            json_str2 = json_str.replace("'", '"')  # 单引号替换
            json_str2 = re.sub(r',\s*([}\]])', r'\1', json_str2)  # 再次去尾逗号
            try:
                data = json.loads(json_str2)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse failed after cleanup: {e}")
                logger.debug(f"Attempted JSON: {json_str[:300]}")
                return self._fallback_parse(text)

        charts = []
        for chart_data in data.get("charts", []):
            if not isinstance(chart_data, dict):
                continue
            raw_data = chart_data.get("data", [])
            # 过滤无效数据点
            valid_data = [
                d for d in raw_data
                if isinstance(d, dict) and "label" in d and "value" in d
            ]
            charts.append(ChartSpec(
                chart_type=str(chart_data.get("chart_type", "bar")),
                title=str(chart_data.get("title", "")),
                x_label=str(chart_data.get("x_label", "")),
                y_label=str(chart_data.get("y_label", "")),
                data=valid_data,
                description=str(chart_data.get("description", "")),
            ))

        return ChartResult(charts=charts, summary=str(data.get("summary", "")))

    def _fallback_parse(self, text: str) -> ChartResult:
        """降级解析: 尝试从文本中提取图表信息"""
        import re
        charts = []

        # 尝试匹配 chart_type 和 title
        types = re.findall(r'"chart_type"\s*:\s*"(\w+)"', text)
        titles = re.findall(r'"title"\s*:\s*"([^"]+)"', text)

        for i, (ctype, title) in enumerate(zip(types, titles)):
            # 提取该图表的 data 数组
            data_pattern = r'"data"\s*:\s*\[(.*?)\]'
            data_matches = re.findall(data_pattern, text, re.DOTALL)
            chart_data = []
            if i < len(data_matches):
                items = re.findall(r'"label"\s*:\s*"([^"]+)".*?"value"\s*:\s*([\d.]+)', data_matches[i])
                chart_data = [{"label": l, "value": float(v)} for l, v in items]

            charts.append(ChartSpec(
                chart_type=ctype,
                title=title,
                x_label="", y_label="",
                data=chart_data,
                description="",
            ))

        if charts:
            logger.info(f"Fallback parsed {len(charts)} charts")
        return ChartResult(charts=charts, summary="图表数据降级解析")

    def get_last_result(self) -> ChartResult | None:
        return self._last_result

    def render_matplotlib(self, chart: ChartSpec, output_path: str) -> str:
        """使用 matplotlib 渲染图表"""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(10, 6))

            labels = [d.get("label", "") for d in chart.data]
            values = [d.get("value", 0) for d in chart.data]

            if chart.chart_type == "bar":
                ax.bar(labels, values)
            elif chart.chart_type == "line":
                ax.plot(labels, values, marker="o")
            elif chart.chart_type == "pie":
                ax.pie(values, labels=labels, autopct="%1.1f%%")
            elif chart.chart_type == "scatter":
                ax.scatter(range(len(values)), values)

            ax.set_title(chart.title)
            ax.set_xlabel(chart.x_label)
            ax.set_ylabel(chart.y_label)

            plt.tight_layout()
            plt.savefig(output_path, dpi=150, bbox_inches="tight")
            plt.close()

            logger.info(f"Chart saved to: {output_path}")
            return output_path

        except ImportError:
            logger.warning("matplotlib not installed, skipping render")
            return ""
        except Exception as e:
            logger.error(f"Chart render failed: {e}")
            return ""
