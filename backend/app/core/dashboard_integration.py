"""
Dashboard Integration - 无侵入式集成
通过 EventBus 订阅自动收集指标，不修改 Orchestrator
"""
from app.core.agent_status import AgentEvent, EventBus
from app.core.metrics_dashboard import get_dashboard
from app.utils.logger import get_logger

logger = get_logger("dashboard_integration")


class DashboardIntegration:
    """
    通过 EventBus 订阅自动收集指标
    在 app 启动时初始化，不影响主流程
    """

    def __init__(self):
        self.dashboard = get_dashboard()
        self.event_bus = EventBus.get_instance()
        self._active = False

    def activate(self):
        """激活事件订阅"""
        if self._active:
            return

        self.event_bus.subscribe("*", self._on_event)
        self._active = True
        logger.info("Dashboard integration activated")

    def deactivate(self):
        """停用事件订阅"""
        if not self._active:
            return

        self.event_bus.unsubscribe("*", self._on_event)
        self._active = False
        logger.info("Dashboard integration deactivated")

    async def _on_event(self, event: AgentEvent):
        """处理所有事件"""
        try:
            etype = event.event_type
            data = event.data

            if etype == "pipeline_start":
                self.dashboard.start_run(
                    trace_id=event.trace_id,
                    query=data.get("query", ""),
                )

            elif etype == "execution_start":
                pass  # Future: track execution phase

            elif etype == "task_start":
                pass  # Task started, will be tracked on completion

            elif etype == "task_complete":
                self.dashboard.record_tool_call(
                    tool_name=data.get("tool", "unknown"),
                    success=data.get("success", False),
                    duration_ms=data.get("duration_ms", 0),
                    task_id=data.get("task_id", ""),
                )

            elif etype == "pipeline_end":
                self.dashboard.end_run(
                    trace_id=event.trace_id,
                    subtask_count=data.get("subtask_count", 0),
                    success_count=data.get("success_count", 0),
                    failed_count=data.get("failed_count", 0),
                    dag_size=data.get("dag_size", 0),
                )

        except Exception as e:
            logger.error(f"Dashboard event handler error: {e}")


_integration: DashboardIntegration | None = None


def get_integration() -> DashboardIntegration:
    global _integration
    if _integration is None:
        _integration = DashboardIntegration()
    return _integration


def activate_dashboard():
    """便捷函数: 激活 dashboard 集成"""
    integration = get_integration()
    integration.activate()
    return integration
