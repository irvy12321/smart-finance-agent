"""
Orchestrator - 3-Layer 架构 + 完整可观测性 + 容错降级
Layer 1: Planner (任务拆解)
Layer 2: Executor (并行执行)
Layer 3: Synthesizer (Reasoner → Report → Chart)
"""

import os
from dataclasses import dataclass
from typing import ClassVar

from app.core.agent_status import (
    AgentEvent,
    AgentStage,
    EventBus,
    TaskStateTracker,
    set_current_trace_id,
)
from app.core.chart_renderer import ChartRenderer
from app.core.executor import ExecutionResult, ExecutorAgent
from app.core.fallback_manager import FallbackManager
from app.core.observability.metrics import (
    get_metrics_summary,
    record_task_result,
)
from app.core.planner import Plan, PlannerAgent, SubTask
from app.core.reasoner import Reasoner, ReasoningResult
from app.core.report_agent import ReportAgent, ResearchReport
from app.infrastructure.llm_client import LiteLLMRouter, LLMClient
from app.infrastructure.smart_router import SmartRouter
from app.monitoring.prometheus import (
    agent_calls_total,
    agent_errors_total,
    agent_stage_duration_seconds,
)
from app.rag.memory import ConversationMemory
from app.tools.crawler_tool import CrawlerTool
from app.tools.financial_report_tool import FinancialAnalysisTool, FinancialReportTool
from app.tools.news_summary_tool import NewsAnalysisTool, NewsSummaryTool
from app.tools.news_tool import NewsTool
from app.tools.rag_tool import RAGTool
from app.tools.registry import ToolRegistry
from app.tools.research_tool import StockResearchTool
from app.tools.stock_price_tool import StockHistoryTool, StockPriceTool
from app.utils.logger import LogContext, get_logger
from app.utils.tracing import PipelineTracker, TraceContext

logger = get_logger("orchestrator")


@dataclass
class RunResult:
    query: str
    answer: str
    report: ResearchReport | None
    reasoning_result: ReasoningResult | None
    chart_paths: list[str]
    plan: Plan | None
    exec_result: ExecutionResult | None
    plan_reasoning: str
    subtask_count: int
    successful_tasks: int
    failed_tasks: int
    total_duration_ms: float
    trace_id: str


class Orchestrator:
    """
    3-Layer 多Agent协同调度器
    Layer 1: Planner → Plan { SubTasks }
    Layer 2: Executor → ExecutionResult { TaskResults }
    Layer 3: Synthesizer → Reasoner → Report → Chart
    """

    def __init__(self, use_router: bool = True):
        self.event_bus = EventBus.get_instance()
        self.state_tracker = TaskStateTracker.get_instance()

        self.llm = LLMClient.get_instance()
        self.router = LiteLLMRouter.get_instance() if use_router else None

        self.registry = ToolRegistry()
        self._register_tools()

        # Smart Router (查询复杂度评估 + 工具选择)
        self.smart_router = SmartRouter()

        # Layer 1: Planner
        self.planner = PlannerAgent(self.llm, self.router)
        # Layer 2: Executor
        self.executor = ExecutorAgent(self.registry, self.llm, self.router)
        # Layer 3: Synthesizer (Reasoner + Report + Chart)
        self.reasoner = Reasoner(self.llm, self.router)
        self.report_agent = ReportAgent(self.llm, self.router)
        self.chart_renderer = ChartRenderer()

        # Fallback Manager (降级链管理)
        self._fallback_mgr = FallbackManager(
            tool_registry=self.registry,
            llm_client=self.llm,
            router=self.router,
        )

        self.memory = ConversationMemory()

        logger.info(
            f"Orchestrator initialized (3-layer, router={'enabled' if use_router else 'disabled'})"
        )

    def _register_tools(self):
        # Read API keys from environment
        news_api_key = os.getenv("NEWS_API_KEY", "")
        alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY", "")
        fmp_api_key = os.getenv("FMP_API_KEY", "")

        tools = [
            CrawlerTool(),
            NewsTool(api_key=news_api_key),
            RAGTool(),
            StockPriceTool(api_key=alpha_vantage_key),
            StockHistoryTool(api_key=alpha_vantage_key),
            FinancialReportTool(api_key=fmp_api_key),
            FinancialAnalysisTool(api_key=fmp_api_key),
            NewsSummaryTool(api_key=news_api_key),
            NewsAnalysisTool(),  # NewsAnalysisTool uses NewsSummaryTool internally
            StockResearchTool(),  # full grounded single-stock pipeline as one DAG node
        ]
        for tool in tools:
            self.registry.register(tool)

    async def run(self, query: str) -> RunResult:
        """3-Layer 流水线: SmartRoute → Plan → Execute → Synthesize"""
        trace = TraceContext()
        set_current_trace_id(trace.trace_id)
        tracker = PipelineTracker(trace.trace_id, query)
        LogContext.set(trace_id=trace.trace_id, agent_name="orchestrator")

        logger.info(f"Pipeline started: {query[:80]}...")
        self.memory.add_user_message(query)
        self.state_tracker.reset()

        if self.router:
            self.router.token_budget.reset()

        await self.event_bus.emit(
            AgentEvent(
                event_type="pipeline_start",
                agent_name="orchestrator",
                data={"query": query},
                trace_id=trace.trace_id,
            )
        )

        # Layer 0: Smart Routing Assessment
        import time

        t0 = time.perf_counter()
        route = self.smart_router.assess(query)
        routing_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            f"Route: complexity={route.complexity:.2f} type={route.task_type} "
            f"hint={route.plan_hint} model={route.selected_model} ({routing_ms:.0f}ms)"
        )

        # 临时覆盖 planner 模型 (根据复杂度)
        if self.router:
            self.router.set_agent_model_override("planner", route.selected_model)

        # Layer 1: Planning (带容错)
        t0 = time.perf_counter()
        with trace.span("planning"):
            await self._emit_stage(AgentStage.PLANNING)
            try:
                plan = await self.planner.plan(query, route_decision=route)
                agent_calls_total.labels(agent_name="planner").inc()
            except Exception as e:
                logger.error(
                    f"[trace:{trace.trace_id}] Planning failed, using fallback plan: {e}"
                )
                agent_errors_total.labels(
                    agent_name="planner", error_type=type(e).__name__
                ).inc()
                plan = self._create_fallback_plan(query)
        planning_ms = (time.perf_counter() - t0) * 1000
        agent_stage_duration_seconds.labels(stage="planner").observe(planning_ms / 1000)
        tracker.record_stage("planning", "planner", planning_ms, status="ok")

        # 清除 planner 模型 override
        if self.router:
            self.router.clear_model_overrides()

        # Layer 2: Execution (带容错)
        t0 = time.perf_counter()
        with trace.span("execution"):
            await self._emit_stage(AgentStage.EXECUTING)
            try:
                exec_result = await self.executor.execute(plan)
                agent_calls_total.labels(agent_name="executor").inc()
            except Exception as e:
                logger.error(f"[trace:{trace.trace_id}] Execution failed: {e}")
                agent_errors_total.labels(
                    agent_name="executor", error_type=type(e).__name__
                ).inc()
                exec_result = ExecutionResult(
                    plan=plan,
                    final_answer=f"Execution failed: {e}",
                )
        execution_ms = (time.perf_counter() - t0) * 1000
        agent_stage_duration_seconds.labels(stage="executor").observe(
            execution_ms / 1000
        )

        # 记录任务结果 metrics + 更新工具可靠性
        for tr in exec_result.task_results:
            record_task_result(
                task_id=tr.task_id,
                tool=tr.tool_name,
                success=tr.success,
                duration_ms=tr.duration_ms,
                trace_id=trace.trace_id,
            )
            if tr.tool_name != "llm_synthesize":
                self.smart_router.update_reliability(tr.tool_name, tr.success)
        tracker.record_stage("execution", "executor", execution_ms, status="ok")

        # Layer 3: Synthesizer (Reasoner → Report → Chart) (每阶段独立容错)
        reasoning_result = None
        report = None
        chart_paths = []

        t0 = time.perf_counter()
        with trace.span("synthesizer"):
            # 3a: Reasoning (带容错)
            await self._emit_stage(AgentStage.REASONING)
            if exec_result.final_answer:
                try:
                    reasoning_result = await self.reasoner.reason(
                        context=exec_result.final_answer,
                        question=query,
                    )
                    agent_calls_total.labels(agent_name="reasoner").inc()
                except Exception as e:
                    logger.error(
                        f"[trace:{trace.trace_id}] Reasoning failed, using fallback: {e}"
                    )
                    agent_errors_total.labels(
                        agent_name="reasoner", error_type=type(e).__name__
                    ).inc()
                    fallback_data = await self._fallback_mgr.fallback_reasoner(
                        exec_result.final_answer,
                        query,
                    )
                    reasoning_result = ReasoningResult(**fallback_data)

            # 3b: Report Generation (带容错)
            await self._emit_stage(AgentStage.REPORTING)
            try:
                report = await self.report_agent.generate(
                    query=query,
                    exec_result=exec_result,
                    reasoning_result=reasoning_result,
                    trace_id=trace.trace_id,
                )
                agent_calls_total.labels(agent_name="reporter").inc()
            except Exception as e:
                logger.error(
                    f"[trace:{trace.trace_id}] Report generation failed, using fallback: {e}"
                )
                agent_errors_total.labels(
                    agent_name="reporter", error_type=type(e).__name__
                ).inc()
                from app.core.report_agent import StructuredAnalysis

                fallback_data = await self._fallback_mgr.fallback_report(
                    query,
                    exec_result.final_answer,
                )
                report = ResearchReport(
                    title=fallback_data["title"],
                    summary=fallback_data["summary"],
                    analysis=StructuredAnalysis(
                        key_findings=fallback_data.get("key_findings", []),
                        risk_factors=fallback_data.get("risk_factors", []),
                        market_trends=fallback_data.get("market_trends", []),
                        recommendations=fallback_data.get("recommendations", []),
                    ),
                    trace_id=trace.trace_id,
                )

            # 3c: Chart Rendering (no LLM call, already safe)
            if reasoning_result and reasoning_result.chart_specs:
                try:
                    chart_paths = self.chart_renderer.render_all(
                        reasoning_result.chart_specs
                    )
                    logger.info(f"Rendered {len(chart_paths)} charts")
                except Exception as e:
                    logger.warning(
                        f"[trace:{trace.trace_id}] Chart rendering failed: {e}"
                    )
                    chart_paths = []

            # No-external-data fallback: cap confidence + prepend disclaimer
            self._apply_fallback_disclaimer(plan, report, reasoning_result)
        synthesizer_ms = (time.perf_counter() - t0) * 1000
        tracker.record_stage(
            "synthesizer", "reasoner+report", synthesizer_ms, status="ok"
        )

        # 归档记忆
        if report:
            self.memory.add_assistant_message(report.summary, {"title": report.title})
            self.memory.archive_to_long_term(
                f"Q: {query}\n\nSummary: {report.summary}\n\nFindings: {', '.join(report.analysis.key_findings)}",
                {"source": "report", "trace_id": trace.trace_id},
            )

        await self._emit_stage(AgentStage.COMPLETE)

        successful = sum(1 for r in exec_result.task_results if r.success)
        failed = sum(1 for r in exec_result.task_results if not r.success)

        # 打印流水线摘要
        tracker.print_summary()

        return RunResult(
            query=query,
            answer=exec_result.final_answer,
            report=report,
            reasoning_result=reasoning_result,
            chart_paths=chart_paths,
            plan=plan,
            exec_result=exec_result,
            plan_reasoning=plan.reasoning,
            subtask_count=len(plan.subtasks),
            successful_tasks=successful,
            failed_tasks=failed,
            total_duration_ms=trace.summary()["total_ms"],
            trace_id=trace.trace_id,
        )

    async def run_with_streaming(self, query: str, language: str = "en"):
        """流式输出 (供 UI 使用) - 带容错"""
        trace = TraceContext()
        set_current_trace_id(trace.trace_id)
        self._current_language = language  # Store language for later use

        self.memory.add_user_message(query)
        self.state_tracker.reset()

        if self.router:
            self.router.token_budget.reset()

        # Layer 0: Smart Routing
        yield {
            "stage": "planning",
            "message": "Analyzing question complexity and selecting strategy...",
        }
        route = self.smart_router.assess(query)

        # 临时覆盖 planner 模型
        if self.router:
            self.router.set_agent_model_override("planner", route.selected_model)

        # Layer 1: Planning (带容错)
        with trace.span("planning"):
            try:
                plan = await self.planner.plan(query, route_decision=route)
            except Exception as e:
                logger.error(f"Planning failed, using fallback plan: {e}")
                plan = self._create_fallback_plan(query)
                yield {
                    "stage": "plan_fallback",
                    "message": f"Planning failed: {e}, using fallback plan",
                }

        # 清除 override
        if self.router:
            self.router.clear_model_overrides()

        yield {
            "stage": "plan_ready",
            "message": f"Plan: {len(plan.subtasks)} subtasks",
            "reasoning": plan.reasoning,
            "subtasks": [
                {
                    "id": st.task_id,
                    "tool": st.tool_name,
                    "desc": st.description,
                    "priority": st.priority,
                    "depends_on": list(st.depends_on),
                    "tool_priority_score": st.tool_priority_score,
                    "task_reasoning": st.reasoning,
                    "confidence": st.confidence,
                }
                for st in plan.get_sorted_subtasks()
            ],
            "route": {
                "complexity": route.complexity,
                "task_type": route.task_type,
                "plan_hint": route.plan_hint,
                "selected_model": route.selected_model,
                "reasoning": route.reasoning,
            },
        }

        # Layer 2: Execution (带容错)
        yield {"stage": "executing", "message": "Executing research tasks..."}

        _task_events: list[dict] = []

        async def _on_task_start(event: AgentEvent):
            if event.trace_id and event.trace_id != trace.trace_id:
                return  # event belongs to another concurrent run
            if event.event_type == "task_start":
                _task_events.append(
                    {
                        "type": "task_start",
                        "task_id": event.data.get("task_id", ""),
                        "tool": event.data.get("tool", ""),
                        "description": event.data.get("description", ""),
                    }
                )

        async def _on_task_complete(event: AgentEvent):
            if event.trace_id and event.trace_id != trace.trace_id:
                return  # event belongs to another concurrent run
            if event.event_type == "task_complete":
                _task_events.append(
                    {
                        "type": "task_complete",
                        "task_id": event.data.get("task_id", ""),
                        "tool": event.data.get("tool", ""),
                        "success": event.data.get("success", False),
                        "duration_ms": event.data.get("duration_ms", 0),
                    }
                )

        self.event_bus.subscribe("task_start", _on_task_start)
        self.event_bus.subscribe("task_complete", _on_task_complete)

        # Set executor language
        self.executor._current_language = getattr(self, "_current_language", "en")

        with trace.span("execution"):
            try:
                exec_result = await self.executor.execute(plan)
            except Exception as e:
                logger.error(f"Execution failed: {e}")
                exec_result = ExecutionResult(
                    plan=plan,
                    final_answer=f"Execution failed: {e}",
                )

        self.event_bus.unsubscribe("task_start", _on_task_start)
        self.event_bus.unsubscribe("task_complete", _on_task_complete)

        # 按序 yield 收集到的 task 事件
        for te in _task_events:
            if te["type"] == "task_start":
                yield {
                    "stage": "task_start",
                    "task_id": te["task_id"],
                    "tool": te["tool"],
                    "description": te["description"],
                }
            elif te["type"] == "task_complete":
                if te["tool"] != "llm_synthesize":
                    self.smart_router.update_reliability(te["tool"], te["success"])
                yield {
                    "stage": "task_done",
                    "task_id": te["task_id"],
                    "tool": te["tool"],
                    "success": te["success"],
                    "duration_ms": te["duration_ms"],
                    "status": "success" if te["success"] else "failed",
                }

        # Layer 3: Synthesizer (每阶段独立容错)
        yield {"stage": "reasoning", "message": "Reasoning + chart spec generation..."}
        reasoning_result = None
        if exec_result.final_answer:
            try:
                reasoning_result = await self.reasoner.reason(
                    context=exec_result.final_answer,
                    question=query,
                    language=getattr(self, "_current_language", "en"),
                )
                if plan.is_fallback:
                    reasoning_result.confidence = min(
                        reasoning_result.confidence, self._FALLBACK_MAX_CONFIDENCE
                    )
                yield {
                    "stage": "reasoning_done",
                    "confidence": reasoning_result.confidence,
                    "insights": reasoning_result.key_insights,
                    "charts_count": len(reasoning_result.chart_specs),
                }
            except Exception as e:
                logger.error(f"Reasoning failed, using fallback: {e}")
                fallback_data = await self._fallback_mgr.fallback_reasoner(
                    exec_result.final_answer,
                    query,
                )
                reasoning_result = ReasoningResult(**fallback_data)
                yield {
                    "stage": "reasoning_fallback",
                    "message": f"Reasoning failed: {e}",
                }

        yield {"stage": "reporting", "message": "Generating structured report..."}
        report = None
        try:
            report = await self.report_agent.generate(
                query=query,
                exec_result=exec_result,
                reasoning_result=reasoning_result,
                trace_id=trace.trace_id,
                language=getattr(self, "_current_language", "en"),
            )
        except Exception as e:
            logger.error(f"Report generation failed, using fallback: {e}")
            from app.core.report_agent import StructuredAnalysis

            fallback_data = await self._fallback_mgr.fallback_report(
                query,
                exec_result.final_answer,
            )
            report = ResearchReport(
                title=fallback_data["title"],
                summary=fallback_data["summary"],
                analysis=StructuredAnalysis(
                    key_findings=fallback_data.get("key_findings", []),
                    risk_factors=fallback_data.get("risk_factors", []),
                    market_trends=fallback_data.get("market_trends", []),
                    recommendations=fallback_data.get("recommendations", []),
                ),
                trace_id=trace.trace_id,
            )
            yield {"stage": "report_fallback", "message": f"Report failed: {e}"}

        # No-external-data fallback: cap confidence + prepend disclaimer
        self._apply_fallback_disclaimer(plan, report, reasoning_result)

        # Chart rendering (带容错)
        chart_paths = []
        if reasoning_result and reasoning_result.chart_specs:
            try:
                chart_paths = self.chart_renderer.render_all(
                    reasoning_result.chart_specs
                )
            except Exception as e:
                logger.warning(f"Chart rendering failed: {e}")

        # Memory archival
        if report:
            self.memory.add_assistant_message(report.summary, {"title": report.title})
            self.memory.archive_to_long_term(
                f"Q: {query}\n\n{report.summary}",
                {"source": "report"},
            )

        yield {
            "stage": "complete",
            "answer": exec_result.final_answer,
            "report_markdown": report.to_markdown(
                language=getattr(self, "_current_language", "en")
            )
            if report
            else "",
            "report_title": report.title if report else "",
            "chart_paths": chart_paths,
            "chart_specs": [
                {
                    "chart_type": c.chart_type,
                    "title": c.title,
                    "x_label": c.x_label,
                    "y_label": c.y_label,
                    "data": c.data,
                    "description": c.description,
                }
                for c in (reasoning_result.chart_specs if reasoning_result else [])
            ],
            "total_duration_ms": trace.summary()["total_ms"],
            "trace_id": trace.trace_id,
            "task_states": self.state_tracker.get_all_states(),
        }

    async def _emit_stage(self, stage: AgentStage):
        await self.event_bus.emit(
            AgentEvent(
                event_type="stage_change",
                agent_name="orchestrator",
                data={"stage": stage.value},
            )
        )

    def get_llm_stats(self) -> dict:
        stats = self.llm.get_stats()
        if self.router:
            stats["router"] = self.router.get_stats()
        stats["metrics"] = get_metrics_summary()
        return stats

    def get_monitoring_status(self) -> dict:
        """获取完整监控状态"""
        llm_stats = self.get_llm_stats()
        return {
            "llm": llm_stats,
            "event_history": len(self.event_bus.get_history()),
            "task_states": self.state_tracker.get_all_states(),
            "memory_turns": self.memory.turn_count,
        }

    def get_memory_context(self, query: str) -> str:
        return self.memory.get_combined_context(query)

    # Max confidence for a report produced without any external data.
    _FALLBACK_MAX_CONFIDENCE = 0.2
    _FALLBACK_DISCLAIMER: ClassVar[dict[str, str]] = {
        "zh": (
            "⚠️ 注意：本报告未能获取任何外部数据，仅基于大模型既有知识生成，"
            "可信度低，不可作为投资依据。\n\n"
        ),
        "en": (
            "WARNING: This report was generated WITHOUT any external data "
            "(planning failed and a knowledge-only fallback was used). "
            "Treat its confidence as low and do not rely on it for "
            "investment decisions.\n\n"
        ),
    }

    def _create_fallback_plan(self, query: str) -> Plan:
        """创建降级计划: 单个 llm_synthesize 任务"""
        logger.warning(f"Creating fallback plan for: {query[:60]}")
        return Plan(
            original_query=query,
            subtasks=[
                SubTask(
                    task_id="fallback_1",
                    tool_name="llm_synthesize",
                    params={
                        "prompt": f"Answer this question based on your knowledge: {query}"
                    },
                    description="Fallback: LLM synthesis without external data",
                    priority=1,
                    confidence=self._FALLBACK_MAX_CONFIDENCE,
                )
            ],
            reasoning="Fallback plan: primary planning failed",
            is_fallback=True,
        )

    def _apply_fallback_disclaimer(self, plan, report, reasoning_result) -> None:
        """Cap confidence and prepend a disclaimer when no external data exists.

        Applies when planning fell back to a knowledge-only plan, or when every
        data-gathering task failed (only ``llm_synthesize`` succeeded).
        """
        if not getattr(plan, "is_fallback", False):
            return
        language = getattr(self, "_current_language", "en")
        disclaimer = self._FALLBACK_DISCLAIMER.get(
            language, self._FALLBACK_DISCLAIMER["en"]
        )
        if reasoning_result is not None:
            reasoning_result.confidence = min(
                reasoning_result.confidence, self._FALLBACK_MAX_CONFIDENCE
            )
        if report is not None and not report.summary.startswith(("⚠️", "WARNING")):
            report.summary = disclaimer + report.summary
