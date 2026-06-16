"""
Agent 状态管理 - EventBus + 状态机
支持任务状态跟踪和实时事件回调
"""

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.utils.logger import get_logger

logger = get_logger("agent_status")


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    DEGRADED = "degraded"  # 降级成功 (使用了 fallback)


class AgentStage(Enum):
    PLANNING = "planning"
    EXECUTING = "executing"
    REASONING = "reasoning"
    REPORTING = "reporting"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class AgentEvent:
    event_type: str
    agent_name: str
    data: dict[str, Any] = field(default_factory=dict)
    trace_id: str = ""


# 回调类型: async def callback(event: AgentEvent) -> None
EventCallback = Callable[[AgentEvent], Coroutine[Any, Any, None]]


class EventBus:
    """
    异步事件总线 - 支持 Agent 间通信和 UI 状态更新
    """

    _instance: "EventBus | None" = None

    def __init__(self):
        self._subscribers: dict[str, list[EventCallback]] = {}
        self._event_history: list[AgentEvent] = []
        self._max_history = 500

    @classmethod
    def get_instance(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def subscribe(self, event_type: str, callback: EventCallback):
        """订阅事件"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to event: {event_type}")

    def unsubscribe(self, event_type: str, callback: EventCallback):
        """取消订阅"""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                cb for cb in self._subscribers[event_type] if cb != callback
            ]

    async def emit(self, event: AgentEvent):
        """发布事件 (异步通知所有订阅者)"""
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history :]

        callbacks = self._subscribers.get(event.event_type, [])
        # 通配符订阅
        callbacks += self._subscribers.get("*", [])

        if callbacks:
            tasks = [self._safe_call(cb, event) for cb in callbacks]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_call(self, callback: EventCallback, event: AgentEvent):
        try:
            await callback(event)
        except Exception as e:
            logger.error(f"Event callback error for {event.event_type}: {e}")

    def get_history(
        self, event_type: str | None = None, limit: int = 50
    ) -> list[AgentEvent]:
        """获取事件历史"""
        events = self._event_history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def clear(self):
        self._event_history.clear()


class TaskStateTracker:
    """
    任务状态跟踪器 - 记录每个子任务的执行状态
    """

    _instance: "TaskStateTracker | None" = None

    def __init__(self):
        self._task_states: dict[str, TaskStatus] = {}
        self._task_details: dict[str, dict] = {}

    @classmethod
    def get_instance(cls) -> "TaskStateTracker":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_status(self, task_id: str, status: TaskStatus, detail: dict | None = None):
        self._task_states[task_id] = status
        if detail:
            self._task_details[task_id] = detail
        logger.info(f"Task {task_id} -> {status.value}")

    def get_status(self, task_id: str) -> TaskStatus:
        return self._task_states.get(task_id, TaskStatus.PENDING)

    def get_all_states(self) -> dict[str, str]:
        return {tid: s.value for tid, s in self._task_states.items()}

    def get_all_details(self) -> dict[str, dict]:
        return dict(self._task_details)

    def summary(self) -> dict[str, int]:
        counts = {}
        for status in self._task_states.values():
            counts[status.value] = counts.get(status.value, 0) + 1
        return counts

    def reset(self):
        self._task_states.clear()
        self._task_details.clear()
