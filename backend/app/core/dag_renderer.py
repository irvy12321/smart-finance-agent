"""
DAG Renderer - 任务依赖图可视化
纯观察层模块，不参与执行逻辑
使用 networkx + matplotlib 渲染有向图
"""
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger("dag_renderer")

STATUS_COLORS = {
    "pending": "#9E9E9E",
    "running": "#2196F3",
    "success": "#4CAF50",
    "failed": "#F44336",
    "skipped": "#FF9800",
}

TOOL_SHORT = {
    "news_search": "NEWS",
    "crawler": "WEB",
    "rag_retrieve": "RAG",
    "llm_synthesize": "LLM",
}


def render_dag(
    subtasks: list[dict],
    task_states: dict[str, dict] | None = None,
    output_path: str = "output/charts/dag_status.png",
) -> str:
    """
    渲染 DAG 有向图并保存为 PNG

    Args:
        subtasks: [{"id": str, "tool": str, "desc": str, "priority": int, "depends_on": list[str]}]
        task_states: {"task_id": {"status": "success", "duration_ms": 123.0, ...}}
        output_path: PNG 输出路径

    Returns:
        图片文件路径，失败时返回空字符串
    """
    try:
        import matplotlib
        import networkx as nx
        matplotlib.use("Agg")
        import matplotlib.patches as mpatches
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("networkx or matplotlib not installed, falling back to text DAG")
        return ""

    if not subtasks:
        return ""

    task_states = task_states or {}

    G = nx.DiGraph()
    node_labels = {}
    node_colors = []
    node_order = []

    for task in subtasks:
        tid = task["id"]
        tool = task.get("tool", "unknown")
        tag = TOOL_SHORT.get(tool, tool[:4].upper())
        label = f"{tid}\n[{tag}]"
        node_labels[tid] = label
        G.add_node(tid)
        node_order.append(tid)

        for dep_id in task.get("depends_on", []):
            if dep_id in {t["id"] for t in subtasks}:
                G.add_edge(dep_id, tid)

    for node in node_order:
        state_info = task_states.get(node, {})
        status = state_info.get("status", "pending")
        node_colors.append(STATUS_COLORS.get(status, STATUS_COLORS["pending"]))

    try:
        layers = _assign_layers(G, node_order)
        pos = _layered_layout(G, layers)
    except Exception:
        pos = nx.spring_layout(G, seed=42, k=2.0)

    fig, ax = plt.subplots(figsize=(max(10, len(node_order) * 2.5), max(5, len(node_order) * 1.2)))

    nx.draw_networkx_edges(
        G, pos, ax=ax,
        edge_color="#B0BEC5",
        arrows=True,
        arrowsize=20,
        arrowstyle="-|>",
        width=1.5,
        connectionstyle="arc3,rad=0.1",
        min_source_margin=25,
        min_target_margin=25,
    )

    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_color=node_colors,
        node_size=2200,
        edgecolors="#37474F",
        linewidths=1.5,
    )

    nx.draw_networkx_labels(
        G, pos, ax=ax,
        labels=node_labels,
        font_size=8,
        font_weight="bold",
        font_family="monospace",
    )

    for node in node_order:
        state_info = task_states.get(node, {})
        status = state_info.get("status", "pending")
        duration = state_info.get("duration_ms", 0)
        if status in ("success", "failed") and duration > 0:
            x, y = pos[node]
            label = f"{duration:.0f}ms"
            ax.text(
                x, y - 0.15, label,
                fontsize=7, ha="center", va="top",
                color="#546E7A", style="italic",
            )

    legend_patches = [
        mpatches.Patch(color=color, label=status.capitalize())
        for status, color in STATUS_COLORS.items()
    ]
    ax.legend(
        handles=legend_patches, loc="upper left",
        fontsize=8, framealpha=0.9, title="Task Status",
    )

    ax.set_title("Research Plan (DAG)", fontsize=14, fontweight="bold", pad=15)
    ax.axis("off")
    plt.tight_layout()

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    logger.info(f"DAG rendered: {out} ({len(node_order)} nodes)")
    return str(out)


def _assign_layers(G, node_order: list[str]) -> dict[str, int]:
    """BFS 分层：无入边节点在第0层，其余按最长路径分层"""
    layers = {}
    for node in node_order:
        if G.in_degree(node) == 0:
            layers[node] = 0

    changed = True
    while changed:
        changed = False
        for node in node_order:
            if node in layers:
                continue
            preds = list(G.predecessors(node))
            if all(p in layers for p in preds):
                layers[node] = max(layers[p] for p in preds) + 1 if preds else 0
                changed = True

    for node in node_order:
        if node not in layers:
            layers[node] = 0

    return layers


def _layered_layout(G, layers: dict[str, int]) -> dict:
    """从左到右分层布局"""
    from collections import defaultdict
    layer_groups = defaultdict(list)
    for node, layer in layers.items():
        layer_groups[layer].append(node)

    pos = {}
    max_layer = max(layer_groups.keys()) if layer_groups else 0
    x_spacing = 1.0 / (max_layer + 1) if max_layer > 0 else 0.5

    for layer, nodes in layer_groups.items():
        x = (layer + 0.5) * x_spacing
        n = len(nodes)
        y_spacing = 1.0 / (n + 1) if n > 1 else 0.5
        for i, node in enumerate(nodes):
            y = (i + 1) * y_spacing
            pos[node] = (x, y)

    return pos
