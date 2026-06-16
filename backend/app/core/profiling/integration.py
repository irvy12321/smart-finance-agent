"""
Profiling Integration - 无侵入式 EventBus 集成
在 app 启动时激活，自动将事件转发给 LatencyProfiler
"""

from app.core.agent_status import AgentEvent, EventBus
from app.core.profiling.latency_profiler import get_profiler
from app.utils.logger import get_logger

logger = get_logger("profiling_integration")


class ProfilingIntegration:
    """
    通过 EventBus 订阅自动采集延迟数据
    零侵入: 不修改 Orchestrator / Executor / Planner
    """

    def __init__(self):
        self.profiler = get_profiler()
        self.event_bus = EventBus.get_instance()
        self._active = False

    def activate(self):
        """激活事件订阅"""
        if self._active:
            return
        self.event_bus.subscribe("*", self._on_event)
        self._active = True
        logger.info("Profiling integration activated")

    def deactivate(self):
        """停用事件订阅"""
        if not self._active:
            return
        self.event_bus.unsubscribe("*", self._on_event)
        self._active = False
        logger.info("Profiling integration deactivated")

    async def _on_event(self, event: AgentEvent):
        """将 EventBus 事件转发给 profiler"""
        try:
            self.profiler.record_event(event.event_type, event.data)
        except Exception as e:
            logger.error(f"Profiling event handler error: {e}")


_integration: ProfilingIntegration | None = None


def get_profiling_integration() -> ProfilingIntegration:
    global _integration
    if _integration is None:
        _integration = ProfilingIntegration()
    return _integration


def activate_profiling():
    """便捷函数: 激活 profiling 集成"""
    integration = get_profiling_integration()
    integration.activate()
    return integration
