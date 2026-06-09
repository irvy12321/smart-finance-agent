"""
Chart Renderer - 纯渲染，无 LLM 调用
接收 Reasoner 输出的 ChartSpec，生成 matplotlib 图表
"""
from pathlib import Path

from app.core.reasoner import ChartSpec
from app.utils.logger import get_logger

logger = get_logger("chart_renderer")

# High-contrast color palette for dark UI
CHART_COLORS = ["#4FC3F7", "#66BB6A", "#FFA726", "#EF5350", "#AB47BC", "#26C6DA", "#FFCA28", "#EC407A"]


class ChartRenderer:
    """图表渲染器 - 将 ChartSpec 渲染为图片"""

    def __init__(self, output_dir: str = "output/charts"):
        self.output_dir = Path(output_dir)

    def _setup_style(self):
        """Apply light theme with high contrast for dark UI backgrounds"""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        plt.rcParams.update({
            "figure.facecolor": "#1e1e2e",
            "axes.facecolor": "#2d2d44",
            "axes.edgecolor": "#45475a",
            "axes.labelcolor": "#cdd6f4",
            "text.color": "#cdd6f4",
            "xtick.color": "#bac2de",
            "ytick.color": "#bac2de",
            "grid.color": "#45475a",
            "grid.alpha": 0.3,
            "axes.grid": True,
        })
        return plt

    def render(self, chart: ChartSpec, filename: str | None = None) -> str:
        """渲染单个图表，返回文件路径"""
        try:
            plt = self._setup_style()

            self.output_dir.mkdir(parents=True, exist_ok=True)

            if not chart.data:
                logger.warning(f"No data for chart: {chart.title}")
                return ""

            _fig, ax = plt.subplots(figsize=(10, 6))

            labels = [d.get("label", "") for d in chart.data]
            values = [float(d.get("value", 0)) for d in chart.data]
            colors = CHART_COLORS[:len(labels)]

            if chart.chart_type == "bar":
                bars = ax.bar(labels, values, color=colors, edgecolor="#1e1e2e", linewidth=0.5)
                ax.bar_label(bars, fmt="%.1f", color="#cdd6f4", fontsize=10)
            elif chart.chart_type == "line":
                ax.plot(labels, values, marker="o", linewidth=2.5, markersize=8, color="#4FC3F7")
                ax.fill_between(range(len(values)), values, alpha=0.15, color="#4FC3F7")
            elif chart.chart_type == "pie":
                wedges, texts, autotexts = ax.pie(
                    values, labels=labels, autopct="%1.1f%%", startangle=90,
                    colors=colors, textprops={"color": "#cdd6f4"}
                )
                for t in autotexts:
                    t.set_color("#1e1e2e")
                    t.set_fontweight("bold")
            elif chart.chart_type == "scatter":
                ax.scatter(range(len(values)), values, s=120, c=colors, edgecolors="#cdd6f4", linewidth=1.5)
                ax.set_xticks(range(len(labels)))
                ax.set_xticklabels(labels)
            else:
                ax.bar(labels, values, color=colors)

            ax.set_title(chart.title, fontsize=14, fontweight="bold", color="#cdd6f4", pad=15)
            ax.set_xlabel(chart.x_label, fontsize=11, color="#bac2de")
            ax.set_ylabel(chart.y_label, fontsize=11, color="#bac2de")
            plt.tight_layout()

            if not filename:
                safe_title = "".join(c if c.isalnum() else "_" for c in chart.title)[:30]
                filename = f"{safe_title}.png"

            filepath = self.output_dir / filename
            plt.savefig(filepath, dpi=150, bbox_inches="tight", facecolor="#1e1e2e")
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
