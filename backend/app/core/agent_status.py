"""
Agent 状态管理 - EventBus + 状态机
支持任务状态跟踪和实时事件回调
"""

import asyncio
import contextvars
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.utils.logger import get_logger

logger = get_logger("agent_status")

# Per-run trace id, isolated per asyncio task (and inherited by child tasks /
# asyncio.gather). Lets the process-wide EventBus / TaskStateTracker singletons
# keep concurrent runs from overwriting each other's state, without threading a
# trace id through every call site. Empty string = "no active run" (the shared
# default bucket, used by non-streaming callers and existing tests).
_CURRENT_TRACE_ID: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_trace_id", default=""
)


def set_current_trace_id(trace_id: str) -> None:
    """Bind the current asyncio task (this run) to a trace id."""
    _CURRENT_TRACE_ID.set(trace_id)


def get_current_trace_id() -> str:
    return _CURRENT_TRACE_ID.get()


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
        # Stamp the originating run so subscribers can filter out events from
        # other concurrent runs sharing this process-wide bus.
        if not event.trace_id:
            event.trace_id = _CURRENT_TRACE_ID.get()
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

    State is partitioned by the current run's trace id (see
    ``set_current_trace_id``) so concurrent runs sharing this process-wide
    singleton no longer overwrite each other or wipe each other on ``reset()``.
    Callers with no active run fall back to a shared "" bucket, preserving the
    previous single-run behaviour.
    """

    _instance: "TaskStateTracker | None" = None

    # Cap retained trace buckets so a long-lived process doesn't grow unbounded
    # (each completed run leaves one bucket behind). Oldest buckets are evicted
    # first; well past any realistic in-flight concurrency.
    _max_traces = 256

    def __init__(self):
        self._states_by_trace: dict[str, dict[str, TaskStatus]] = {}
        self._details_by_trace: dict[str, dict[str, dict]] = {}

    @classmethod
    def get_instance(cls) -> "TaskStateTracker":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _bucket(self) -> str:
        trace_id = _CURRENT_TRACE_ID.get()
        if trace_id not in self._states_by_trace and (
            len(self._states_by_trace) >= self._max_traces
        ):
            oldest = next(iter(self._states_by_trace))
            self._states_by_trace.pop(oldest, None)
            self._details_by_trace.pop(oldest, None)
        return trace_id

    def _states(self) -> dict[str, TaskStatus]:
        return self._states_by_trace.setdefault(self._bucket(), {})

    def _details(self) -> dict[str, dict]:
        return self._details_by_trace.setdefault(self._bucket(), {})

    def set_status(self, task_id: str, status: TaskStatus, detail: dict | None = None):
        self._states()[task_id] = status
        if detail:
            self._details()[task_id] = detail
        logger.info(f"Task {task_id} -> {status.value}")

    def get_status(self, task_id: str) -> TaskStatus:
        return self._states().get(task_id, TaskStatus.PENDING)

    def get_all_states(self) -> dict[str, str]:
        return {tid: s.value for tid, s in self._states().items()}

    def get_all_details(self) -> dict[str, dict]:
        return dict(self._details())

    def summary(self) -> dict[str, int]:
        counts = {}
        for status in self._states().values():
            counts[status.value] = counts.get(status.value, 0) + 1
        return counts

    def reset(self):
        """Clear only the current run's state, leaving other runs untouched."""
        trace_id = _CURRENT_TRACE_ID.get()
        self._states_by_trace.pop(trace_id, None)
        self._details_by_trace.pop(trace_id, None)
