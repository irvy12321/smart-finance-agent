import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.agent_status import TaskStatus
from app.core.executor import ExecutorAgent
from app.core.fallback_manager import FallbackManager
from app.core.planner import SubTask
from app.tools.base_tool import ToolResult
from app.utils.circuit_breaker import BreakerState, CircuitBreaker
from app.utils.tracing import TraceContext


class _Registry:
    def __init__(self, tools):
        self.tools = tools

    def get(self, name):
        return self.tools.get(name)


class _BreakerRegistry:
    def __init__(self, configs=None):
        self.configs = configs or {}
        self.breakers = {}

    def get_breaker(self, name):
        if name not in self.breakers:
            threshold, recovery = self.configs.get(name, (5, 60.0))
            self.breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=threshold,
                recovery_timeout=recovery,
            )
        return self.breakers[name]


def test_default_breaker_policy_is_unchanged():
    breaker = CircuitBreaker(name="defaults")

    assert breaker.failure_threshold == 5
    assert breaker.recovery_timeout == 60.0
    assert breaker.half_open_max == 1


def _tool(result=None, side_effect=None):
    tool = MagicMock()
    tool.execute = AsyncMock(return_value=result, side_effect=side_effect)
    return tool


async def _execute_crawler_task(registry, breaker_mgr):
    executor = ExecutorAgent(
        registry,
        MagicMock(),
        None,
        tool_timeout=0.05,
        fallback_step_timeout=0.05,
    )
    executor.circuit_breaker_mgr = breaker_mgr
    executor.fallback_mgr = FallbackManager(
        tool_registry=registry,
        circuit_breaker_mgr=breaker_mgr,
        step_timeout=0.05,
    )
    executor.state_tracker = MagicMock()
    executor.event_bus = MagicMock()
    executor.event_bus.emit = AsyncMock()

    task = SubTask(
        task_id="t1",
        tool_name="crawler",
        params={"url": "https://example.com"},
        description="Fetch a page",
    )
    return await executor._execute_task([task], "t1", {}, TraceContext())


@pytest.mark.asyncio
async def test_primary_failure_is_not_called_again_and_backup_is_degraded():
    primary = _tool(ToolResult(success=False, error="down", tool_name="crawler"))
    backup = _tool(
        ToolResult(success=True, data={"source": "news"}, tool_name="news_search")
    )
    registry = _Registry({"crawler": primary, "news_search": backup})

    result = await _execute_crawler_task(registry, _BreakerRegistry())

    assert primary.execute.await_count == 1
    assert backup.execute.await_count == 1
    assert result.success is True
    assert result.status == TaskStatus.DEGRADED


@pytest.mark.asyncio
async def test_open_primary_is_never_called():
    primary = _tool(ToolResult(success=True, data="unexpected", tool_name="crawler"))
    backup = _tool(ToolResult(success=True, data="news", tool_name="news_search"))
    breakers = _BreakerRegistry()
    primary_breaker = breakers.get_breaker("crawler")
    for _ in range(primary_breaker.failure_threshold):
        primary_breaker.record_failure()

    result = await _execute_crawler_task(
        _Registry({"crawler": primary, "news_search": backup}), breakers
    )

    primary.execute.assert_not_awaited()
    backup.execute.assert_awaited_once()
    assert result.status == TaskStatus.DEGRADED


@pytest.mark.asyncio
async def test_timed_out_backup_continues_and_records_metrics_by_tool():
    async def _slow(**_kwargs):
        await asyncio.sleep(1)
        return ToolResult(success=True, data="late", tool_name="news_search")

    news = _tool(side_effect=_slow)
    rag = _tool(ToolResult(success=True, data="rag", tool_name="rag_retrieve"))
    manager = FallbackManager(
        tool_registry=_Registry({"news_search": news, "rag_retrieve": rag}),
        circuit_breaker_mgr=_BreakerRegistry(),
        step_timeout=0.01,
    )

    with (
        patch("app.core.fallback_manager.tool_calls_total") as calls,
        patch("app.core.fallback_manager.tool_call_duration_seconds") as durations,
        patch("app.core.fallback_manager.tool_errors_total") as errors,
    ):
        result, used = await manager.execute_with_fallback(
            "crawler", {"url": "https://example.com"}, skip_tools={"crawler"}
        )

    assert result.success is True
    assert used == "rag_retrieve"
    news.execute.assert_awaited_once()
    rag.execute.assert_awaited_once()
    calls.labels.assert_any_call(tool_name="news_search")
    calls.labels.assert_any_call(tool_name="rag_retrieve")
    durations.labels.assert_any_call(tool_name="news_search")
    errors.labels.assert_any_call(tool_name="news_search", error_type="TimeoutError")


@pytest.mark.asyncio
async def test_open_backup_is_skipped_without_invocation():
    news = _tool(ToolResult(success=True, data="unexpected", tool_name="news_search"))
    rag = _tool(ToolResult(success=True, data="rag", tool_name="rag_retrieve"))
    breakers = _BreakerRegistry({"news_search": (1, 1e9)})
    breakers.get_breaker("news_search").record_failure()
    manager = FallbackManager(
        tool_registry=_Registry({"news_search": news, "rag_retrieve": rag}),
        circuit_breaker_mgr=breakers,
        step_timeout=0.05,
    )

    result, used = await manager.execute_with_fallback(
        "crawler", {"url": "https://example.com"}, skip_tools={"crawler"}
    )

    assert result.success is True
    assert used == "rag_retrieve"
    news.execute.assert_not_awaited()
    rag.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_all_backup_steps_exhausted_returns_failure_details():
    news = _tool(ToolResult(success=False, error="news down", tool_name="news_search"))
    rag = _tool(ToolResult(success=False, error="rag down", tool_name="rag_retrieve"))
    manager = FallbackManager(
        tool_registry=_Registry({"news_search": news, "rag_retrieve": rag}),
        circuit_breaker_mgr=_BreakerRegistry(),
        step_timeout=0.05,
    )
    manager._fallback_static_crawler = AsyncMock(
        return_value=ToolResult(success=False, error="static down", tool_name="static")
    )

    result, used = await manager.execute_with_fallback(
        "crawler", {"url": "https://example.com"}, skip_tools={"crawler"}
    )

    assert result.success is False
    assert used == "crawler"
    assert "news down" in result.error
    assert "rag down" in result.error
    assert "static down" in result.error


@pytest.mark.asyncio
async def test_half_open_backup_success_closes_its_breaker():
    news = _tool(ToolResult(success=True, data="news", tool_name="news_search"))
    breakers = _BreakerRegistry({"news_search": (1, 0.01)})
    breaker = breakers.get_breaker("news_search")
    breaker.record_failure()
    breaker._last_failure_time -= 1
    assert breaker.state == BreakerState.HALF_OPEN
    manager = FallbackManager(
        tool_registry=_Registry({"news_search": news}),
        circuit_breaker_mgr=breakers,
        step_timeout=0.05,
    )

    result, used = await manager.execute_with_fallback(
        "crawler", {"url": "https://example.com"}, skip_tools={"crawler"}
    )

    assert result.success is True
    assert used == "news_search"
    assert breaker.state == BreakerState.CLOSED


@pytest.mark.asyncio
async def test_half_open_backup_failure_reopens_and_continues():
    news = _tool(
        ToolResult(success=False, error="probe failed", tool_name="news_search")
    )
    rag = _tool(ToolResult(success=True, data="rag", tool_name="rag_retrieve"))
    breakers = _BreakerRegistry({"news_search": (1, 0.01)})
    breaker = breakers.get_breaker("news_search")
    breaker.record_failure()
    breaker._last_failure_time -= 1
    assert breaker.state == BreakerState.HALF_OPEN
    manager = FallbackManager(
        tool_registry=_Registry({"news_search": news, "rag_retrieve": rag}),
        circuit_breaker_mgr=breakers,
        step_timeout=0.05,
    )

    result, used = await manager.execute_with_fallback(
        "crawler", {"url": "https://example.com"}, skip_tools={"crawler"}
    )

    assert result.success is True
    assert used == "rag_retrieve"
    assert breaker.state == BreakerState.OPEN


@pytest.mark.asyncio
async def test_backup_breaker_states_are_isolated_by_tool():
    news = _tool(ToolResult(success=False, error="news down", tool_name="news_search"))
    rag = _tool(ToolResult(success=True, data="rag", tool_name="rag_retrieve"))
    breakers = _BreakerRegistry({"news_search": (1, 1e9), "rag_retrieve": (1, 1e9)})
    manager = FallbackManager(
        tool_registry=_Registry({"news_search": news, "rag_retrieve": rag}),
        circuit_breaker_mgr=breakers,
        step_timeout=0.05,
    )

    result, used = await manager.execute_with_fallback(
        "crawler", {"url": "https://example.com"}, skip_tools={"crawler"}
    )

    assert result.success is True
    assert used == "rag_retrieve"
    assert breakers.get_breaker("news_search").state == BreakerState.OPEN
    assert breakers.get_breaker("rag_retrieve").state == BreakerState.CLOSED
