"""
Chart Renderer - 纯渲染，无 LLM 调用
接收 Reasoner 输出的 ChartSpec，生成 matplotlib 图表
"""
import json
from pathlib import Path
from app.core.reasoner import ChartSpec
from app.utils.logger import get_logger

logger = get_logger("chart_renderer")


class ChartRenderer:
    """图表渲染器 - 将 ChartSpec 渲染为图片"""

    def __init__(self, output_dir: str = "output/charts"):
        self.output_dir = Path(output_dir)

    def render(self, chart: ChartSpec, filename: str | None = None) -> str:
        """渲染单个图表，返回文件路径"""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            self.output_dir.mkdir(parents=True, exist_ok=True)

            if not chart.data:
                logger.warning(f"No data for chart: {chart.title}")
                return ""

            fig, ax = plt.subplots(figsize=(10, 6))

            labels = [d.get("label", "") for d in chart.data]
            values = [float(d.get("value", 0)) for d in chart.data]

            if chart.chart_type == "bar":
                bars = ax.bar(labels, values, color=["#2196F3", "#4CAF50", "#FF9800", "#F44336", "#9C27B0"][:len(labels)])
                ax.bar_label(bars, fmt="%.1f")
            elif chart.chart_type == "line":
                ax.plot(labels, values, marker="o", linewidth=2, markersize=8)
                ax.fill_between(range(len(values)), values, alpha=0.1)
            elif chart.chart_type == "pie":
                ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
            elif chart.chart_type == "scatter":
                ax.scatter(range(len(values)), values, s=100, c="#2196F3")
                ax.set_xticks(range(len(labels)))
                ax.set_xticklabels(labels)
            else:
                ax.bar(labels, values)

            ax.set_title(chart.title, fontsize=14, fontweight="bold")
            ax.set_xlabel(chart.x_label)
            ax.set_ylabel(chart.y_label)
            plt.tight_layout()

            if not filename:
                safe_title = "".join(c if c.isalnum() else "_" for c in chart.title)[:30]
                filename = f"{safe_title}.png"

            filepath = self.output_dir / filename
            plt.savefig(filepath, dpi=150, bbox_inches="tight")
            plt.close()

            logger.info(f"Chart saved: {filepath}")
            return str(filepath)

        except ImportError:
            logger.warning("matplotlib not installed, skipping render")
            return ""
        except Exception as e:
            logger.error(f"Chart render failed: {e}")
            return ""

    def render_all(self, charts: list[ChartSpec]) -> list[str]:
        """批量渲染图表"""
        paths = []
        for i, chart in enumerate(charts):
            if chart.data:
                path = self.render(chart, f"chart_{i+1}.png")
                if path:
                    paths.append(path)
        return paths

    @staticmethod
    def chart_spec_to_dict(chart: ChartSpec) -> dict:
        """ChartSpec 转 dict (用于 JSON 序列化)"""
        return {
            "chart_type": chart.chart_type,
            "title": chart.title,
            "x_label": chart.x_label,
            "y_label": chart.y_label,
            "data": chart.data,
            "description": chart.description,
        }
