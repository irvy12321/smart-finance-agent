from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.smart_router import RouteDecision


def _make_event_bus():
    """Create a mock EventBus with async emit."""
    bus = MagicMock()
    bus.emit = AsyncMock()
    bus.get_history.return_value = []
    bus.subscribe = MagicMock()
    bus.unsubscribe = MagicMock()
    return bus


def _make_state_tracker():
    """Create a mock TaskStateTracker."""
    tracker = MagicMock()
    tracker.get_all_states.return_value = {}
    tracker.reset = MagicMock()
    tracker.record_task_start = MagicMock()
    tracker.record_task_end = MagicMock()
    return tracker


def _make_route_decision():
    """Create a mock RouteDecision."""
    return RouteDecision(
        complexity=0.5,
        task_type="financial_analysis",
        plan_hint="standard",
        selected_model="default",
        reasoning="Test routing",
        tool_scores={"stock_price": 0.8, "news_search": 0.7, "llm_synthesize": 0.9},
    )


def _make_plan():
    """Create a mock Plan with subtasks."""
    from app.core.planner import Plan, SubTask

    subtasks = [
        SubTask(
            task_id="t1",
            tool_name="stock_price",
            params={"symbol": "AAPL"},
            description="Get stock price",
            priority=1,
        ),
        SubTask(
            task_id="t2",
            tool_name="llm_synthesize",
            params={"prompt": "Synthesize results"},
            description="Synthesize",
            depends_on=["t1"],
            priority=1,
        ),
    ]
    return Plan(
        original_query="Test query", subtasks=subtasks, reasoning="Test reasoning"
    )


def _make_exec_result(plan):
    """Create a mock ExecutionResult."""
    from app.core.executor import ExecutionResult, TaskResult

    task_results = [
        TaskResult(
            task_id="t1", tool_name="stock_price", success=True, duration_ms=100
        ),
        TaskResult(
            task_id="t2", tool_name="llm_synthesize", success=True, duration_ms=200
        ),
    ]
    return ExecutionResult(
        plan=plan,
        task_results=task_results,
        final_answer="AAPL analysis complete",
        total_duration_ms=300,
    )


def _make_reasoning_result():
    """Create a mock ReasoningResult."""
    result = MagicMock()
    result.confidence = 0.85
    result.key_insights = ["insight1", "insight2"]
    result.chart_specs = []
    return result


def _make_report():
    """Create a mock ResearchReport."""
    report = MagicMock()
    report.title = "Test Report"
    report.summary = "Test report summary"
    report.to_markdown.return_value = "# Test Report\n## Summary\nThis is a test report"
    report.analysis.key_findings = ["finding1", "finding2"]
    report.analysis.risk_factors = []
    report.analysis.market_trends = ["trend1"]
    report.analysis.recommendations = ["recommendation1"]
    return report


@pytest.mark.asyncio
async def test_orchestrator_initialization():
    with (
        patch("app.core.orchestrator.LLMClient") as mock_llm,
        patch("app.core.orchestrator.ToolRegistry"),
        patch("app.core.orchestrator.PlannerAgent"),
        patch("app.core.orchestrator.ExecutorAgent"),
        patch("app.core.orchestrator.Reasoner"),
        patch("app.core.orchestrator.ReportAgent"),
        patch("app.core.orchestrator.ChartRenderer"),
        patch("app.core.orchestrator.FallbackManager"),
        patch("app.core.orchestrator.ConversationMemory"),
        patch("app.core.orchestrator.EventBus") as mock_event_bus,
        patch("app.core.orchestrator.TaskStateTracker") as mock_tracker,
        patch("app.core.orchestrator.LiteLLMRouter") as mock_router,
        patch("app.core.orchestrator.SmartRouter"),
    ):
        mock_llm.get_instance.return_value = MagicMock()
        mock_router.get_instance.return_value = MagicMock()
        mock_event_bus.get_instance.return_value = _make_event_bus()
        mock_tracker.get_instance.return_value = _make_state_tracker()

        from app.core.orchestrator import Orchestrator

        orch = Orchestrator(use_router=True)

        assert orch is not None
        assert orch.planner is not None
        assert orch.executor is not None
        assert orch.reasoner is not None
        assert orch.report_agent is not None


@pytest.mark.asyncio
async def test_orchestrator_run_pipeline():
    plan = _make_plan()
    exec_result = _make_exec_result(plan)
    reasoning_result = _make_reasoning_result()
    report = _make_report()
    route = _make_route_decision()
    event_bus = _make_event_bus()
    state_tracker = _make_state_tracker()

    mock_smart_router = MagicMock()
    mock_smart_router.assess.return_value = route

    mock_planner = MagicMock()
    mock_planner.plan = AsyncMock(return_value=plan)

    mock_executor = MagicMock()
    mock_executor.execute = AsyncMock(return_value=exec_result)

    mock_reasoner = MagicMock()
    mock_reasoner.reason = AsyncMock(return_value=reasoning_result)
    mock_reasoner.reason_with_critique = AsyncMock(return_value=reasoning_result)

    mock_report_agent = MagicMock()
    mock_report_agent.generate = AsyncMock(return_value=report)

    mock_chart_renderer = MagicMock()
    mock_chart_renderer.render_all.return_value = []

    with (
        patch("app.core.orchestrator.LLMClient") as mock_llm_cls,
        patch("app.core.orchestrator.ToolRegistry"),
        patch("app.core.orchestrator.PlannerAgent", return_value=mock_planner),
        patch("app.core.orchestrator.ExecutorAgent", return_value=mock_executor),
        patch("app.core.orchestrator.Reasoner", return_value=mock_reasoner),
        patch("app.core.orchestrator.ReportAgent", return_value=mock_report_agent),
        patch("app.core.orchestrator.ChartRenderer", return_value=mock_chart_renderer),
        patch("app.core.orchestrator.FallbackManager"),
        patch("app.core.orchestrator.ConversationMemory"),
        patch("app.core.orchestrator.EventBus") as mock_eb_cls,
        patch("app.core.orchestrator.TaskStateTracker") as mock_st_cls,
        patch("app.core.orchestrator.LiteLLMRouter") as mock_router_cls,
        patch("app.core.orchestrator.SmartRouter", return_value=mock_smart_router),
    ):
        mock_llm_cls.get_instance.return_value = MagicMock()
        mock_router_cls.get_instance.return_value = MagicMock()
        mock_eb_cls.get_instance.return_value = event_bus
        mock_st_cls.get_instance.return_value = state_tracker

        from app.core.orchestrator import Orchestrator

        orch = Orchestrator(use_router=False)

        result = await orch.run("Analyze AAPL stock price")

        assert result is not None
        assert result.query == "Analyze AAPL stock price"
        assert result.answer == "AAPL analysis complete"
        assert result.plan is not None
        assert result.exec_result is not None
        assert result.reasoning_result is not None
        assert result.report is not None
        assert result.subtask_count == 2
        assert result.successful_tasks == 2
        assert result.failed_tasks == 0


@pytest.mark.asyncio
async def test_planner_agent():
    with patch("app.core.planner.LLMClient") as mock_llm_class:
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(
            return_value='{"reasoning": "test", "subtasks": [{"task_id": "t1", "tool_name": "stock_price", "params": {"symbol": "AAPL"}, "description": "Get price", "priority": 1, "tool_priority_score": 0.9, "reasoning": "best tool", "confidence": 0.85}]}'
        )
        mock_llm_class.get_instance.return_value = mock_llm

        from app.core.planner import PlannerAgent

        planner = PlannerAgent(mock_llm, None)

        plan = await planner.plan("What is AAPL stock price?")

        assert plan is not None
        assert len(plan.subtasks) > 0
        assert plan.subtasks[0].task_id == "t1"
        assert plan.subtasks[0].tool_name == "stock_price"


@pytest.mark.asyncio
async def test_executor_agent():
    event_bus = _make_event_bus()
    state_tracker = _make_state_tracker()

    with (
        patch("app.core.executor.ToolRegistry") as mock_registry_cls,
        patch("app.core.executor.EventBus") as mock_eb_cls,
        patch("app.core.executor.TaskStateTracker") as mock_st_cls,
        patch("app.core.executor.FallbackManager"),
        patch("app.core.executor.CircuitBreakerManager"),
    ):
        mock_registry = MagicMock()
        mock_tool = MagicMock()
        mock_tool.execute = AsyncMock(
            return_value=MagicMock(success=True, data={"result": "success"}, error="")
        )
        mock_registry.get.return_value = mock_tool
        mock_registry_cls.return_value = mock_registry

        mock_eb_cls.get_instance.return_value = event_bus
        mock_st_cls.get_instance.return_value = state_tracker

        from app.core.executor import ExecutorAgent
        from app.core.planner import Plan, SubTask

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value="Synthesized answer")
        executor = ExecutorAgent(mock_registry, mock_llm, None)

        subtask = SubTask(
            task_id="t1",
            tool_name="stock_price",
            params={"symbol": "AAPL"},
            description="Get price",
            priority=1,
        )
        plan = Plan(original_query="Test", subtasks=[subtask])

        result = await executor.execute(plan)

        assert result is not None
        assert len(result.task_results) > 0


@pytest.mark.asyncio
async def test_executor_tool_timeout_routes_to_fallback():
    """A hanging tool is timed out and routed to the fallback chain instead of
    blocking the whole execution round."""
    import asyncio

    from app.tools.base_tool import ToolResult

    event_bus = _make_event_bus()
    state_tracker = _make_state_tracker()

    async def _slow_execute(**kwargs):
        await asyncio.sleep(5.0)
        return MagicMock(success=True, data="late", error="")

    with (
        patch("app.core.executor.EventBus") as mock_eb_cls,
        patch("app.core.executor.TaskStateTracker") as mock_st_cls,
        patch("app.core.executor.FallbackManager") as mock_fb_cls,
        patch("app.core.executor.CircuitBreakerManager"),
    ):
        mock_tool = MagicMock()
        mock_tool.execute = _slow_execute
        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_tool

        mock_fb = MagicMock()
        mock_fb.execute_with_fallback = AsyncMock(
            return_value=(
                ToolResult(success=False, error="exhausted", tool_name="stock_price"),
                "stock_price",
            )
        )
        mock_fb_cls.return_value = mock_fb

        mock_eb_cls.get_instance.return_value = event_bus
        mock_st_cls.get_instance.return_value = state_tracker

        from app.core.executor import ExecutorAgent
        from app.core.planner import Plan, SubTask

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value="synth")
        executor = ExecutorAgent(mock_registry, mock_llm, None, tool_timeout=0.05)

        subtask = SubTask(
            task_id="t1",
            tool_name="stock_price",
            params={"symbol": "AAPL"},
            description="Get price",
            priority=1,
        )
        plan = Plan(original_query="Test", subtasks=[subtask])

        result = await executor.execute(plan)

        t1 = next(r for r in result.task_results if r.task_id == "t1")
        assert t1.success is False
        mock_fb.execute_with_fallback.assert_awaited()


def test_planner_valid_tools_derived_from_registry():
    """Valid tool set is taken from the registry-derived names plus the always
    available llm_synthesize; unsupplied falls back to the static default."""
    from app.core.planner import PlannerAgent

    planner = PlannerAgent(
        llm_client=MagicMock(), router=None, valid_tools={"stock_price"}
    )
    assert planner.valid_tools == {"stock_price", "llm_synthesize"}

    default_planner = PlannerAgent(llm_client=MagicMock(), router=None)
    assert default_planner.valid_tools == PlannerAgent._DEFAULT_VALID_TOOLS


def test_tool_registry():
    from app.tools.registry import ToolRegistry

    # Reset singleton for test isolation
    ToolRegistry._instance = None
    ToolRegistry._tools = {}

    registry = ToolRegistry()
    assert registry is not None

    # Test basic functionality
    mock_tool = MagicMock()
    mock_tool.name = "test_tool"
    mock_tool.to_schema.return_value = {
        "name": "test_tool",
        "description": "A test tool",
    }
    registry.register(mock_tool)

    assert "test_tool" in registry
    assert registry.get("test_tool") == mock_tool
    assert len(registry.list_tools()) == 1

    # Clean up singleton
    ToolRegistry._instance = None
    ToolRegistry._tools = {}


def test_fallback_manager():
    from app.core.fallback_manager import FallbackManager

    mock_registry = MagicMock()
    mock_llm = MagicMock()
    mock_router = MagicMock()

    manager = FallbackManager(mock_registry, mock_llm, mock_router)

    assert manager is not None
    assert manager.registry == mock_registry
    assert manager.llm == mock_llm
    assert manager.router == mock_router
