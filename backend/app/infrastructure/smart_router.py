"""
Smart Router - 查询复杂度评估 + 任务类型分类 + 工具优先级评分 + 模型选择
纯决策模块，不修改任何执行逻辑
"""
from dataclasses import dataclass, field
from app.infrastructure.config import SmartRouterConfig, get_smart_router_config
from app.utils.logger import get_logger

logger = get_logger("smart_router")

COMPLEXITY_KEYWORDS = {
    "high": [
        "compare", "analyze", "evaluate", "risk", "forecast", "implications",
        "comprehensive", "detailed", "multi-factor", "correlation", "strategy",
        "assessment", "investment", "portfolio", "diversification", "volatility",
    ],
    "medium": [
        "summary", "overview", "trend", "performance", "report", "latest",
        "quarterly", "annual", "revenue", "earnings", "growth", "market",
    ],
    "low": [
        "what is", "price of", "current", "news about", "define", "who is",
        "when did", "how much", "today",
    ],
}

TOOL_PATTERNS = {
    "rag_retrieve": [
        "explain", "history", "background", "definition", "based on",
        "previous", "prior", "knowledge", "document", "analysis of",
    ],
    "news_search": [
        "latest", "recent", "news", "today", "current", "breaking",
        "announcement", "update", "just", "this week", "this month",
    ],
    "crawler": [
        "sec filing", "website", "url", "page", "document from",
        "official", "report from", "data from",
    ],
}

TIME_PATTERNS = [
    "today", "yesterday", "this week", "this month", "this year",
    "last quarter", "q1", "q2", "q3", "q4", "2024", "2025", "2026",
    "latest", "recent", "current",
]

TASK_TYPE_TOOL_MAP = {
    "rag": ["rag_retrieve", "llm_synthesize"],
    "crawler": ["news_search", "crawler", "llm_synthesize"],
    "llm": ["llm_synthesize"],
    "hybrid": ["news_search", "rag_retrieve", "crawler", "llm_synthesize"],
}


@dataclass
class RouteDecision:
    """路由决策结果"""
    complexity: float = 0.0
    task_type: str = "llm"
    tool_scores: dict[str, float] = field(default_factory=dict)
    selected_model: str = ""
    fallback_models: list[str] = field(default_factory=list)
    plan_hint: str = "standard"
    reasoning: str = ""


class SmartRouter:
    """
    智能路由器
    - 查询复杂度评分 (0-1)
    - 任务类型分类 (rag / crawler / llm / hybrid)
    - 工具优先级评分
    - 模型选择 + fallback 链
    - 工具可靠性追踪 (EMA)
    """

    def __init__(self, config: SmartRouterConfig | None = None):
        self.config = config or get_smart_router_config()
        self.tool_reliability: dict[str, float] = dict(self.config.tool_reliability)
        logger.info(
            f"SmartRouter initialized: thresholds={self.config.complexity_thresholds} "
            f"tools={list(self.tool_reliability.keys())}"
        )

    def assess(self, query: str) -> RouteDecision:
        """核心评估: query → RouteDecision"""
        complexity = self._score_complexity(query)
        task_type = self._classify_task_type(query)
        tool_scores = self._score_tools(query)
        model = self._select_model(complexity)
        fallbacks = self._get_fallbacks(model)
        plan_hint = self._get_plan_hint(complexity)
        reasoning = self._build_reasoning(complexity, task_type, tool_scores, plan_hint)

        decision = RouteDecision(
            complexity=complexity,
            task_type=task_type,
            tool_scores=tool_scores,
            selected_model=model,
            fallback_models=fallbacks,
            plan_hint=plan_hint,
            reasoning=reasoning,
        )

        logger.info(
            f"Route: complexity={complexity:.2f} type={task_type} "
            f"hint={plan_hint} model={model}"
        )
        return decision

    def update_reliability(self, tool_name: str, success: bool):
        """根据执行结果更新工具可靠性 (EMA 平滑)"""
        if tool_name not in self.tool_reliability:
            return
        alpha = self.config.reliability_alpha
        result = 1.0 if success else 0.0
        old = self.tool_reliability[tool_name]
        self.tool_reliability[tool_name] = alpha * result + (1 - alpha) * old
        logger.debug(
            f"Tool '{tool_name}' reliability: {old:.3f} -> {self.tool_reliability[tool_name]:.3f} "
            f"(result={'success' if success else 'failed'})"
        )

    def get_tool_availability_text(self) -> str:
        """生成工具可用性信息文本 (供 Planner prompt 注入)"""
        lines = ["Tool reliability (real-time):"]
        for tool, score in sorted(self.tool_reliability.items(), key=lambda x: -x[1]):
            bar = "+" * int(score * 10)
            lines.append(f"  - {tool}: {score:.0%} [{bar}]")
        return "\n".join(lines)

    def _score_complexity(self, query: str) -> float:
        """查询复杂度评分 (0-1)"""
        score = 0.0
        q_lower = query.lower()

        # 长度贡献: 0-0.3
        length_score = min(len(query) / 500, 0.3)
        score += length_score

        # 关键词贡献: 0-0.35
        keyword_score = 0.0
        for word in COMPLEXITY_KEYWORDS["high"]:
            if word in q_lower:
                keyword_score += 0.07
        for word in COMPLEXITY_KEYWORDS["medium"]:
            if word in q_lower:
                keyword_score += 0.04
        for phrase in COMPLEXITY_KEYWORDS["low"]:
            if phrase in q_lower:
                keyword_score -= 0.05
        score += max(0, min(keyword_score, 0.35))

        # 多工具需求: 0-0.2
        matched_tools = 0
        for patterns in TOOL_PATTERNS.values():
            if any(p in q_lower for p in patterns):
                matched_tools += 1
        if matched_tools >= 3:
            score += 0.2
        elif matched_tools >= 2:
            score += 0.12
        elif matched_tools >= 1:
            score += 0.05

        # 时间引用: 0-0.15
        time_hits = sum(1 for p in TIME_PATTERNS if p in q_lower)
        score += min(time_hits * 0.05, 0.15)

        return min(max(score, 0.0), 1.0)

    def _classify_task_type(self, query: str) -> str:
        """任务类型分类"""
        q_lower = query.lower()
        matched_tools = set()

        for tool, patterns in TOOL_PATTERNS.items():
            if any(p in q_lower for p in patterns):
                matched_tools.add(tool)

        if len(matched_tools) >= 2:
            return "hybrid"
        if "rag_retrieve" in matched_tools:
            return "rag"
        if "crawler" in matched_tools or "news_search" in matched_tools:
            return "crawler"
        return "llm"

    def _score_tools(self, query: str) -> dict[str, float]:
        """工具优先级评分 (0-1): 关键词匹配 * 可靠度"""
        q_lower = query.lower()
        scores = {}

        for tool, patterns in TOOL_PATTERNS.items():
            # 关键词匹配分
            hits = sum(1 for p in patterns if p in q_lower)
            match_score = min(hits * 0.3, 1.0)

            # 乘以可靠度
            reliability = self.tool_reliability.get(tool, 0.5)
            scores[tool] = round(match_score * reliability, 3)

        # llm_synthesize 总是可用 (作为综合工具)
        scores["llm_synthesize"] = round(
            self.tool_reliability.get("llm_synthesize", 0.95), 3
        )

        return scores

    def _select_model(self, complexity: float) -> str:
        """根据复杂度选择模型"""
        thresholds = self.config.complexity_thresholds
        if complexity >= thresholds.get("high", 0.7):
            return self.config.high_quality_model
        elif complexity >= thresholds.get("medium", 0.3):
            return self.config.standard_model
        return self.config.lightweight_model

    def _get_fallbacks(self, primary_model: str) -> list[str]:
        """获取 fallback 模型链"""
        return [m for m in self.config.fallback_models if m != primary_model]

    def _get_plan_hint(self, complexity: float) -> str:
        """规划建议"""
        if complexity >= 0.7:
            return "detailed"
        if complexity >= 0.3:
            return "standard"
        return "simple"

    def _build_reasoning(
        self, complexity: float, task_type: str,
        tool_scores: dict[str, float], plan_hint: str,
    ) -> str:
        """构建路由推理说明"""
        top_tools = sorted(tool_scores.items(), key=lambda x: -x[1])[:3]
        tool_str = ", ".join(f"{t}({s:.2f})" for t, s in top_tools)
        return (
            f"Complexity={complexity:.2f} ({plan_hint}), "
            f"Type={task_type}, "
            f"Top tools=[{tool_str}]"
        )
