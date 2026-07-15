import asyncio
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
        event_types = [
            call.args[0].event_type for call in event_bus.emit.await_args_list
        ]
        assert "pipeline_start" in event_types
        assert "pipeline_end" in event_types
        pipeline_end = next(
            call.args[0]
            for call in event_bus.emit.await_args_list
            if call.args[0].event_type == "pipeline_end"
        )
        assert pipeline_end.data["status"] == "success"
        assert pipeline_end.data["subtask_count"] == 2
        assert pipeline_end.data["success_count"] == 2


@pytest.mark.asyncio
async def test_streaming_unsubscribes_task_events_when_execution_is_cancelled():
    from app.core.agent_status import (
        EventBus,
        get_current_trace_id,
        reset_current_trace_id,
        set_current_trace_id,
    )
    from app.core.orchestrator import Orchestrator

    class _Memory:
        def add_user_message(self, query):
            pass

    class _StateTracker:
        def reset(self):
            pass

    class _SmartRouter:
        def assess(self, query):
            return _make_route_decision()

        def update_reliability(self, tool_name, success):
            pass

    class _Router:
        def __init__(self):
            self.token_budget = MagicMock()
            self.bound_tokens: list[object] = []
            self.reset_tokens: list[object] = []

        def set_route_model(self, model):
            token = object()
            self.bound_tokens.append(token)
            return token

        def reset_route_model(self, token):
            self.reset_tokens.append(token)

    class _Executor:
        async def execute(self, plan):
            raise asyncio.CancelledError

    bus = EventBus()
    router = _Router()
    orch = Orchestrator.__new__(Orchestrator)
    orch.event_bus = bus
    orch.memory = _Memory()
    orch.state_tracker = _StateTracker()
    orch.router = router
    orch.smart_router = _SmartRouter()
    orch.planner = MagicMock()
    orch.planner.plan = AsyncMock(return_value=_make_plan())
    orch.executor = _Executor()

    outer_token = set_current_trace_id("outer-stream")
    stream = orch.run_with_streaming("Analyze AAPL", language="en")

    try:
        assert (await stream.__anext__())["stage"] == "planning"
        assert (await stream.__anext__())["stage"] == "plan_ready"
        assert (await stream.__anext__())["stage"] == "executing"

        with pytest.raises(asyncio.CancelledError):
            await stream.__anext__()

        assert get_current_trace_id() == "outer-stream"
        assert bus.subscriber_count("task_start") == 0
        assert bus.subscriber_count("task_complete") == 0
        assert router.reset_tokens == router.bound_tokens
    finally:
        reset_current_trace_id(outer_token)

    emitted = [
        event for event in bus.get_history() if event.event_type == "pipeline_end"
    ]
    assert emitted[-1].data["status"] == "cancelled"


@pytest.mark.asyncio
async def test_orchestrator_route_model_is_reset_after_each_pipeline_stage():
    from app.core.agent_status import (
        get_current_trace_id,
        reset_current_trace_id,
        set_current_trace_id,
    )

    plan = _make_plan()
    exec_result = _make_exec_result(plan)
    reasoning_result = _make_reasoning_result()
    report = _make_report()
    route = _make_route_decision()
    event_bus = _make_event_bus()
    state_tracker = _make_state_tracker()

    class _Router:
        def __init__(self):
            self.token_budget = MagicMock()
            self.bound_tokens: list[object] = []
            self.reset_tokens: list[object] = []

        def set_route_model(self, model):
            token = object()
            self.bound_tokens.append(token)
            return token

        def reset_route_model(self, token):
            self.reset_tokens.append(token)

    mock_smart_router = MagicMock()
    mock_smart_router.assess.return_value = route

    mock_planner = MagicMock()
    mock_planner.plan = AsyncMock(return_value=plan)

    mock_executor = MagicMock()
    mock_executor.execute = AsyncMock(return_value=exec_result)

    mock_reasoner = MagicMock()
    mock_reasoner.reason_with_critique = AsyncMock(return_value=reasoning_result)

    mock_report_agent = MagicMock()
    mock_report_agent.generate = AsyncMock(return_value=report)

    mock_chart_renderer = MagicMock()
    mock_chart_renderer.render_all.return_value = []

    router = _Router()

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
        mock_router_cls.get_instance.return_value = router
        mock_eb_cls.get_instance.return_value = event_bus
        mock_st_cls.get_instance.return_value = state_tracker

        from app.core.orchestrator import Orchestrator

        orch = Orchestrator(use_router=True)
        outer_token = set_current_trace_id("outer-run")
        try:
            await orch.run("Analyze AAPL stock price")
            assert get_current_trace_id() == "outer-run"
        finally:
            reset_current_trace_id(outer_token)

    assert len(router.bound_tokens) == 3
    assert router.reset_tokens == router.bound_tokens


@pytest.mark.asyncio
async def test_streaming_emits_pipeline_lifecycle_events():
    from app.core.agent_status import EventBus
    from app.core.orchestrator import Orchestrator

    class _Memory:
        turn_count = 0

        def add_user_message(self, query):
            pass

        def add_assistant_message(self, message, metadata=None):
            pass

        def archive_to_long_term(self, text, metadata=None):
            pass

        def retrieve_long_term(self, query, top_k=3):
            return []

    class _StateTracker:
        def reset(self):
            pass

        def get_all_states(self):
            return {}

    class _SmartRouter:
        def assess(self, query):
            return _make_route_decision()

        def update_reliability(self, tool_name, success):
            pass

    class _Router:
        token_budget = MagicMock()

        def set_route_model(self, model):
            return object()

        def reset_route_model(self, token):
            pass

    plan = _make_plan()
    exec_result = _make_exec_result(plan)
    reasoning_result = _make_reasoning_result()
    report = _make_report()

    bus = EventBus()
    orch = Orchestrator.__new__(Orchestrator)
    orch.event_bus = bus
    orch.memory = _Memory()
    orch.state_tracker = _StateTracker()
    orch.router = _Router()
    orch.smart_router = _SmartRouter()
    orch.planner = MagicMock()
    orch.planner.plan = AsyncMock(return_value=plan)
    orch.executor = MagicMock()
    orch.executor.execute = AsyncMock(return_value=exec_result)
    orch.reasoner = MagicMock()
    orch.reasoner.reason_with_critique = AsyncMock(return_value=reasoning_result)
    orch.report_agent = MagicMock()
    orch.report_agent.generate = AsyncMock(return_value=report)
    orch.chart_renderer = MagicMock()
    orch.chart_renderer.render_all.return_value = []
    orch._fallback_mgr = MagicMock()

    events = [event async for event in orch.run_with_streaming("Analyze AAPL")]

    assert events[-1]["stage"] == "complete"
    lifecycle = [
        event.event_type
        for event in bus.get_history(limit=20)
        if event.event_type in {"pipeline_start", "pipeline_end"}
    ]
    assert lifecycle == ["pipeline_start", "pipeline_end"]
    pipeline_end = [
        event
        for event in bus.get_history(limit=20)
        if event.event_type == "pipeline_end"
    ][-1]
    assert pipeline_end.data["status"] == "success"
    assert pipeline_end.data["success_count"] == 2


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
        assert mock_fb.execute_with_fallback.await_args.kwargs["skip_tools"] == {
            "stock_price"
        }


@pytest.mark.asyncio
async def test_executor_skips_non_synthesis_task_when_dependency_failed():
    from app.core.agent_status import TaskStatus
    from app.tools.base_tool import ToolResult

    event_bus = _make_event_bus()
    state_tracker = _make_state_tracker()

    with (
        patch("app.core.executor.EventBus") as mock_eb_cls,
        patch("app.core.executor.TaskStateTracker") as mock_st_cls,
        patch("app.core.executor.FallbackManager") as mock_fb_cls,
        patch("app.core.executor.CircuitBreakerManager"),
    ):
        failing_tool = MagicMock()
        failing_tool.execute = AsyncMock(
            return_value=ToolResult(
                success=False, error="primary failed", tool_name="stock_price"
            )
        )
        dependent_tool = MagicMock()
        dependent_tool.execute = AsyncMock(return_value=MagicMock(success=True))

        mock_registry = MagicMock()
        mock_registry.get.side_effect = lambda name: {
            "stock_price": failing_tool,
            "financial_report": dependent_tool,
        }.get(name)

        mock_fb = MagicMock()
        mock_fb.execute_with_fallback = AsyncMock(
            return_value=(
                ToolResult(
                    success=False, error="fallback failed", tool_name="stock_price"
                ),
                "stock_price",
            )
        )
        mock_fb_cls.return_value = mock_fb

        mock_eb_cls.get_instance.return_value = event_bus
        mock_st_cls.get_instance.return_value = state_tracker

        from app.core.executor import ExecutorAgent
        from app.core.planner import Plan, SubTask

        executor = ExecutorAgent(mock_registry, MagicMock(), None)
        plan = Plan(
            original_query="Test",
            subtasks=[
                SubTask(
                    task_id="t1",
                    tool_name="stock_price",
                    params={"symbol": "AAPL"},
                    description="Failing upstream",
                ),
                SubTask(
                    task_id="t2",
                    tool_name="financial_report",
                    params={"symbol": "AAPL"},
                    description="Should not run without t1",
                    depends_on=["t1"],
                ),
            ],
        )

        result = await executor.execute(plan)

        t2 = next(r for r in result.task_results if r.task_id == "t2")
        assert t2.status == TaskStatus.SKIPPED
        assert "dependencies failed" in t2.error
        dependent_tool.execute.assert_not_called()


@pytest.mark.asyncio
async def test_executor_synthesis_receives_failed_dependency_context():
    from app.tools.base_tool import ToolResult

    event_bus = _make_event_bus()
    state_tracker = _make_state_tracker()

    with (
        patch("app.core.executor.EventBus") as mock_eb_cls,
        patch("app.core.executor.TaskStateTracker") as mock_st_cls,
        patch("app.core.executor.FallbackManager") as mock_fb_cls,
        patch("app.core.executor.CircuitBreakerManager"),
    ):
        failing_tool = MagicMock()
        failing_tool.execute = AsyncMock(
            return_value=ToolResult(
                success=False, error="price unavailable", tool_name="stock_price"
            )
        )
        mock_registry = MagicMock()
        mock_registry.get.return_value = failing_tool

        mock_fb = MagicMock()
        mock_fb.execute_with_fallback = AsyncMock(
            return_value=(
                ToolResult(
                    success=False, error="fallback unavailable", tool_name="stock_price"
                ),
                "stock_price",
            )
        )
        mock_fb_cls.return_value = mock_fb

        mock_eb_cls.get_instance.return_value = event_bus
        mock_st_cls.get_instance.return_value = state_tracker

        from app.core.executor import ExecutorAgent
        from app.core.planner import Plan, SubTask

        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value="partial answer")
        executor = ExecutorAgent(mock_registry, mock_llm, None)
        plan = Plan(
            original_query="Test",
            subtasks=[
                SubTask(
                    task_id="t1",
                    tool_name="stock_price",
                    params={"symbol": "AAPL"},
                    description="Failing upstream",
                ),
                SubTask(
                    task_id="t2",
                    tool_name="llm_synthesize",
                    params={"prompt": "Summarize"},
                    description="Synthesize partial result",
                    depends_on=["t1"],
                ),
            ],
        )

        result = await executor.execute(plan)

        assert result.final_answer == "partial answer"
        prompt = mock_llm.complete.await_args.kwargs["prompt"]
        assert "Unavailable dependency results" in prompt
        assert "fallback unavailable" in prompt


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
