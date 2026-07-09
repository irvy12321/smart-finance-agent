import pytest

from app.core.agent_status import AgentEvent
from app.core.dashboard_integration import DashboardIntegration
from app.core.metrics_dashboard import MetricsDashboard


def test_dashboard_tracks_concurrent_runs_by_trace_id():
    dashboard = MetricsDashboard.__new__(MetricsDashboard)
    dashboard._initialized = False
    MetricsDashboard.__init__(dashboard)

    dashboard.start_run("trace-a", "Analyze AAPL")
    dashboard.start_run("trace-b", "Analyze MSFT")

    dashboard.record_tool_call("stock_price", True, 12.0, trace_id="trace-a")
    dashboard.record_tool_call("news_search", False, 20.0, trace_id="trace-b")
    dashboard.record_agent_latency("planner", 5.0, trace_id="trace-a")
    dashboard.record_agent_latency("planner", 7.0, trace_id="trace-b")

    dashboard.end_run("trace-a", subtask_count=1, success_count=1, failed_count=0)
    dashboard.end_run("trace-b", subtask_count=1, success_count=0, failed_count=1)

    recent = dashboard.get_recent_runs(limit=5)
    assert [run["trace_id"] for run in recent] == ["trace-a", "trace-b"]

    tool_stats = dashboard.get_tool_stats()
    assert tool_stats["stock_price"]["success"] == 1
    assert tool_stats["news_search"]["failure"] == 1

    latency_stats = dashboard.get_agent_latency_stats()
    assert latency_stats["planner"]["calls"] == 2
    assert latency_stats["planner"]["avg_ms"] == 6.0


def test_dashboard_discards_unknown_end_run():
    dashboard = MetricsDashboard.__new__(MetricsDashboard)
    dashboard._initialized = False
    MetricsDashboard.__init__(dashboard)

    dashboard.end_run("missing-trace")

    assert dashboard.get_system_stats()["total_requests"] == 0


def test_dashboard_caps_retained_runs():
    dashboard = MetricsDashboard.__new__(MetricsDashboard)
    dashboard._initialized = False
    MetricsDashboard.__init__(dashboard)
    dashboard._max_runs = 2

    for trace_id in ("trace-1", "trace-2", "trace-3"):
        dashboard.start_run(trace_id, trace_id)
        dashboard.end_run(trace_id)

    recent = dashboard.get_recent_runs(limit=10)

    assert [run["trace_id"] for run in recent] == ["trace-2", "trace-3"]


@pytest.mark.asyncio
async def test_dashboard_integration_records_tool_call_for_event_trace():
    dashboard = MetricsDashboard.__new__(MetricsDashboard)
    dashboard._initialized = False
    MetricsDashboard.__init__(dashboard)

    integration = DashboardIntegration.__new__(DashboardIntegration)
    integration.dashboard = dashboard
    integration.event_bus = None
    integration._active = False

    await integration._on_event(
        AgentEvent(
            event_type="pipeline_start",
            agent_name="orchestrator",
            trace_id="trace-a",
            data={"query": "Analyze AAPL"},
        )
    )
    await integration._on_event(
        AgentEvent(
            event_type="pipeline_start",
            agent_name="orchestrator",
            trace_id="trace-b",
            data={"query": "Analyze MSFT"},
        )
    )
    await integration._on_event(
        AgentEvent(
            event_type="task_complete",
            agent_name="executor",
            trace_id="trace-a",
            data={"tool": "stock_price", "success": True, "duration_ms": 10},
        )
    )
    await integration._on_event(
        AgentEvent(
            event_type="pipeline_end",
            agent_name="orchestrator",
            trace_id="trace-a",
            data={"subtask_count": 1, "success_count": 1, "failed_count": 0},
        )
    )
    await integration._on_event(
        AgentEvent(
            event_type="pipeline_end",
            agent_name="orchestrator",
            trace_id="trace-b",
            data={"subtask_count": 1, "success_count": 0, "failed_count": 0},
        )
    )

    recent = dashboard.get_recent_runs(limit=2)

    assert recent[0]["trace_id"] == "trace-a"
    assert recent[0]["tool_calls"] == 1
    assert recent[1]["trace_id"] == "trace-b"
    assert recent[1]["tool_calls"] == 0
