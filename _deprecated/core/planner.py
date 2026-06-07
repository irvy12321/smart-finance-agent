import json
from dataclasses import dataclass, field
from infrastructure.llm_client import LLMClient, LiteLLMRouter
from infrastructure.smart_router import RouteDecision
from utils.logger import get_logger
from utils.exceptions import PlannerError

logger = get_logger("planner")


@dataclass
class SubTask:
    task_id: str
    tool_name: str
    params: dict
    description: str
    depends_on: list[str] = field(default_factory=list)
    priority: int = 1  # 1=最高优先级, 数字越大优先级越低
    # 增强字段 (向后兼容，不影响 Executor)
    tool_priority_score: float = 0.0
    reasoning: str = ""
    confidence: float = 0.0


@dataclass
class Plan:
    original_query: str
    subtasks: list[SubTask]
    reasoning: str = ""
    # 增强字段
    route_decision: RouteDecision | None = None

    def get_sorted_subtasks(self) -> list[SubTask]:
        """按优先级排序 (priority 值小的先执行)"""
        return sorted(self.subtasks, key=lambda t: t.priority)


PLANNER_SYSTEM = """You are a research planning agent. Given a user's research question, break it down into actionable sub-tasks.

Available tools:
- "crawler": Fetch web content. Params: {"url": "<url>"}. Use well-known URLs only (e.g., https://www.sec.gov, https://en.wikipedia.org). Avoid company IR pages that may change.
- "news_search": Search recent news. Params: {"query": "<search query>"}. PREFERRED for current events and market sentiment.
- "rag_retrieve": Search local knowledge base. Params: {"query": "<search query>"}. Use for historical context and prior analysis.
- "llm_synthesize": Synthesize information. Params: {"prompt": "<synthesis prompt>"}. Always include as final task.

You MUST respond with valid JSON only, no other text. Format:
{
  "reasoning": "brief explanation of plan",
  "subtasks": [
    {
      "task_id": "task_1",
      "tool_name": "news_search",
      "params": {"query": "Tesla Q4 2024 earnings report analysis"},
      "description": "Search for recent Tesla earnings news",
      "priority": 3,
      "tool_priority_score": 0.9,
      "reasoning": "news_search is best for current earnings data",
      "confidence": 0.85
    },
    {
      "task_id": "task_2",
      "tool_name": "rag_retrieve",
      "params": {"query": "Tesla financial analysis"},
      "description": "Retrieve related local documents",
      "priority": 3,
      "tool_priority_score": 0.7,
      "reasoning": "local docs may have historical context",
      "confidence": 0.6
    },
    {
      "task_id": "task_3",
      "tool_name": "llm_synthesize",
      "params": {"prompt": "Based on the following information, provide a comprehensive analysis..."},
      "description": "Synthesize all findings into final report",
      "depends_on": ["task_1", "task_2"],
      "priority": 1,
      "tool_priority_score": 0.95,
      "reasoning": "final synthesis is always needed",
      "confidence": 0.9
    }
  ]
}

Rules:
1. Create 2-5 subtasks
2. Prefer news_search over crawler (crawler may fail for dynamic pages)
3. The final task should be llm_synthesize that depends on all prior tasks
4. Make search queries specific and relevant
5. Priority: 1=highest (synthesize), 2=medium (reasoning), 3=normal (data gathering)
6. tool_priority_score: 0-1, how well the tool matches the task
7. reasoning: brief explanation of why this tool was chosen
8. confidence: 0-1, estimated probability of task success"""

PLAN_SIZE_HINTS = {
    "simple": "Create exactly 2 subtasks: one data gathering task + one llm_synthesize task. Keep it minimal.",
    "standard": "Create 3-4 subtasks: 2-3 data gathering tasks + one llm_synthesize task.",
    "detailed": "Create 4-5 subtasks: 3-4 data gathering tasks covering different angles + one llm_synthesize task. Be thorough.",
}


class PlannerAgent:
    def __init__(self, llm_client: LLMClient | None = None, router: LiteLLMRouter | None = None):
        self.router = router
        self.llm = llm_client or LLMClient.get_instance()

    async def plan(self, query: str, route_decision: RouteDecision | None = None) -> Plan:
        logger.info(f"Planning for query: {query[:80]}...")

        try:
            # 构建增强 system prompt
            enhanced_system = self._build_enhanced_system(route_decision)

            if self.router:
                response = await self.router.complete(
                    "planner",
                    prompt=f"User research question: {query}",
                    system=enhanced_system,
                )
            else:
                response = await self.llm.complete(
                    prompt=f"User research question: {query}",
                    system=enhanced_system,
                    temperature=0.2,
                )

            plan_data = self._parse_response(response)
            subtasks = self._build_subtasks(plan_data, route_decision)

            plan = Plan(
                original_query=query,
                subtasks=subtasks,
                reasoning=plan_data.get("reasoning", ""),
                route_decision=route_decision,
            )

            logger.info(f"Plan created: {len(subtasks)} subtasks")
            for st in subtasks:
                logger.info(
                    f"  - {st.task_id}: {st.tool_name} (priority={st.priority}, "
                    f"score={st.tool_priority_score:.2f}, conf={st.confidence:.2f}) -> {st.description}"
                )

            return plan

        except Exception as e:
            logger.error(f"Planning failed: {e}")
            raise PlannerError(f"Failed to create plan: {e}") from e

    def _build_enhanced_system(self, route_decision: RouteDecision | None = None) -> str:
        """构建增强 system prompt (动态注入工具可用性 + plan size hint)"""
        parts = [PLANNER_SYSTEM]

        if route_decision:
            # 注入工具可靠性信息
            tool_section = (
                "\n\n--- TOOL RELIABILITY (use to adjust tool_priority_score and confidence) ---\n"
                f"Query complexity: {route_decision.complexity:.2f}\n"
                f"Task type: {route_decision.task_type}\n"
            )
            for tool, score in sorted(
                route_decision.tool_scores.items(), key=lambda x: -x[1]
            ):
                tool_section += f"  {tool}: reliability={score:.0%}\n"
            parts.append(tool_section)

            # 注入 plan size hint
            hint = route_decision.plan_hint
            if hint in PLAN_SIZE_HINTS:
                parts.append(f"\n--- PLAN SIZE HINT ---\n{PLAN_SIZE_HINTS[hint]}")

        return "\n".join(parts)

    def _parse_response(self, response: str) -> dict:
        text = response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
            raise PlannerError(f"Cannot parse planner response as JSON: {text[:200]}")

    def _build_subtasks(
        self, plan_data: dict, route_decision: RouteDecision | None = None
    ) -> list[SubTask]:
        """构建 SubTask 列表，解析增强字段，用 route_decision 校准"""
        tool_scores = route_decision.tool_scores if route_decision else {}
        subtasks = []

        for item in plan_data.get("subtasks", []):
            tool_name = item.get("tool_name", "llm_synthesize")

            # 解析增强字段，缺失时用 route_decision 填充默认值
            priority_score = item.get("tool_priority_score", 0.0)
            if priority_score == 0.0 and tool_name in tool_scores:
                priority_score = tool_scores[tool_name]

            confidence = item.get("confidence", 0.0)
            if confidence == 0.0:
                # 默认置信度 = 工具可靠度 * 0.9
                reliability = tool_scores.get(tool_name, 0.7)
                confidence = round(reliability * 0.9, 2)

            reasoning = item.get("reasoning", "")

            subtasks.append(SubTask(
                task_id=item.get("task_id", f"task_{len(subtasks)+1}"),
                tool_name=tool_name,
                params=item.get("params", {}),
                description=item.get("description", ""),
                depends_on=item.get("depends_on", []),
                priority=item.get("priority", 3),
                tool_priority_score=round(priority_score, 3),
                reasoning=reasoning,
                confidence=confidence,
            ))

        return subtasks
