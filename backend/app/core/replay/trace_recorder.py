"""
Trace Recorder - 通过 EventBus 订阅零侵入记录执行 trace
不修改 Orchestrator / Executor / Planner
"""
import json
import time
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.agent_status import EventBus, AgentEvent
from app.utils.logger import get_logger

logger = get_logger("trace_recorder")


@dataclass
class TraceEvent:
    """单条 trace 事件"""
    task_id: str
    event: str  # "start" | "end" | "pipeline_start" | "pipeline_end"
    timestamp: float
    wall_time: str
    tool: str = ""
    input_data: Any = None
    output_data: Any = None
    success: bool = True
    latency_ms: float = 0.0
    error: str = ""
    round_num: int = 0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "event": self.event,
            "timestamp": self.timestamp,
            "wall_time": self.wall_time,
            "tool": self.tool,
            "input_data": str(self.input_data)[:500] if self.input_data else None,
            "output_data": str(self.output_data)[:500] if self.output_data else None,
            "success": self.success,
            "latency_ms": round(self.latency_ms, 2),
            "error": self.error,
            "round_num": self.round_num,
            "metadata": self.metadata,
        }


@dataclass
class TraceSession:
    """一次完整的 trace 会话"""
    trace_id: str
    query: str
    start_time: float
    end_time: float = 0.0
    total_ms: float = 0.0
    events: list[TraceEvent] = field(default_factory=list)
    subtasks: list[dict] = field(default_factory=list)
    final_answer: str = ""
    success_count: int = 0
    failed_count: int = 0

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "query": self.query,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_ms": round(self.total_ms, 2),
            "events": [e.to_dict() for e in self.events],
            "subtasks": self.subtasks,
            "final_answer": self.final_answer[:1000] if self.final_answer else "",
            "success_count": self.success_count,
            "failed_count": self.failed_count,
        }

    def get_task_events(self) -> dict[str, list[TraceEvent]]:
        """按 task_id 分组事件"""
        grouped: dict[str, list[TraceEvent]] = {}
        for e in self.events:
            if e.task_id not in grouped:
                grouped[e.task_id] = []
            grouped[e.task_id].append(e)
        return grouped

    def get_ordered_tasks(self) -> list[str]:
        """按开始时间排序的 task_id 列表"""
        seen = set()
        ordered = []
        for e in self.events:
            if e.event == "start" and e.task_id not in seen:
                seen.add(e.task_id)
                ordered.append(e.task_id)
        return ordered


class TraceRecorder:
    """
    Trace 记录器 - 通过 EventBus 订阅自动记录
    线程安全，零侵入
    """
    _instance: "TraceRecorder | None" = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._active = False
        self._current_session: TraceSession | None = None
        self._sessions: list[TraceSession] = []
        self._max_sessions = 50
        self._storage_path = Path("output/replay_traces")
        self._task_starts: dict[str, float] = {}
        self._event_bus = EventBus.get_instance()
        self._initialized = True
        logger.info("TraceRecorder initialized")

    def activate(self):
        """激活记录"""
        if self._active:
            return
        self._event_bus.subscribe("*", self._on_event)
        self._active = True
        logger.info("TraceRecorder activated")

    def deactivate(self):
        """停用记录"""
        if not self._active:
            return
        self._event_bus.unsubscribe("*", self._on_event)
        self._active = False
        logger.info("TraceRecorder deactivated")

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def current_session(self) -> TraceSession | None:
        return self._current_session

    async def _on_event(self, event: AgentEvent):
        """处理 EventBus 事件"""
        if not self._active:
            return

        try:
            etype = event.event_type
            data = event.data
            now = time.time()

            if etype == "pipeline_start":
                self._current_session = TraceSession(
                    trace_id=event.trace_id or datetime.now().strftime("%Y%m%d_%H%M%S"),
                    query=data.get("query", ""),
                    start_time=now,
                )
                self._current_session.events.append(TraceEvent(
                    task_id="pipeline",
                    event="pipeline_start",
                    timestamp=now,
                    wall_time=datetime.now().isoformat(),
                    metadata={"query": data.get("query", "")[:200]},
                ))

            elif etype == "plan_ready" and self._current_session:
                self._current_session.subtasks = data.get("subtasks", [])

            elif etype == "task_start" and self._current_session:
                task_id = data.get("task_id", "")
                tool = data.get("tool", "")
                self._task_starts[task_id] = now
                self._current_session.events.append(TraceEvent(
                    task_id=task_id,
                    event="start",
                    timestamp=now,
                    wall_time=datetime.now().isoformat(),
                    tool=tool,
                    input_data=data.get("description", ""),
                    metadata={"round": data.get("round", 0)},
                ))

            elif etype == "task_complete" and self._current_session:
                task_id = data.get("task_id", "")
                tool = data.get("tool", "")
                success = data.get("success", False)
                duration_ms = data.get("duration_ms", 0)
                start_ts = self._task_starts.pop(task_id, now)

                self._current_session.events.append(TraceEvent(
                    task_id=task_id,
                    event="end",
                    timestamp=now,
                    wall_time=datetime.now().isoformat(),
                    tool=tool,
                    output_data=data.get("data", ""),
                    success=success,
                    latency_ms=duration_ms,
                    error=data.get("error", ""),
                    round_num=data.get("round", 0),
                ))

                if success:
                    self._current_session.success_count += 1
                else:
                    self._current_session.failed_count += 1

            elif etype == "execution_complete" and self._current_session:
                pass  # Will be handled by pipeline_end

            elif etype == "pipeline_end" and self._current_session:
                self._current_session.end_time = now
                self._current_session.total_ms = (now - self._current_session.start_time) * 1000
                self._current_session.events.append(TraceEvent(
                    task_id="pipeline",
                    event="pipeline_end",
                    timestamp=now,
                    wall_time=datetime.now().isoformat(),
                    latency_ms=self._current_session.total_ms,
                ))

                self._sessions.append(self._current_session)
                if len(self._sessions) > self._max_sessions:
                    self._sessions = self._sessions[-self._max_sessions:]

                logger.info(
                    f"Trace recorded: {self._current_session.trace_id} "
                    f"({len(self._current_session.events)} events, "
                    f"{self._current_session.total_ms:.0f}ms)"
                )
                self._current_session = None

        except Exception as e:
            logger.error(f"TraceRecorder event handler error: {e}")

    def get_sessions(self) -> list[TraceSession]:
        """获取所有记录的会话"""
        return list(self._sessions)

    def get_latest_session(self) -> TraceSession | None:
        """获取最新会话"""
        return self._sessions[-1] if self._sessions else None

    def save_session(self, session: TraceSession, filepath: str = None) -> str:
        """保存会话到 JSON 文件"""
        self._storage_path.mkdir(parents=True, exist_ok=True)

        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = str(self._storage_path / f"trace_{timestamp}_{session.trace_id[:8]}.json")

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)

        logger.info(f"Trace saved to {filepath}")
        return filepath

    def load_session(self, filepath: str) -> TraceSession:
        """从 JSON 文件加载会话"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        events = []
        for e in data.get("events", []):
            events.append(TraceEvent(
                task_id=e["task_id"],
                event=e["event"],
                timestamp=e["timestamp"],
                wall_time=e["wall_time"],
                tool=e.get("tool", ""),
                input_data=e.get("input_data"),
                output_data=e.get("output_data"),
                success=e.get("success", True),
                latency_ms=e.get("latency_ms", 0),
                error=e.get("error", ""),
                round_num=e.get("round_num", 0),
                metadata=e.get("metadata", {}),
            ))

        session = TraceSession(
            trace_id=data["trace_id"],
            query=data["query"],
            start_time=data["start_time"],
            end_time=data.get("end_time", 0),
            total_ms=data.get("total_ms", 0),
            events=events,
            subtasks=data.get("subtasks", []),
            final_answer=data.get("final_answer", ""),
            success_count=data.get("success_count", 0),
            failed_count=data.get("failed_count", 0),
        )

        logger.info(f"Trace loaded from {filepath}: {len(events)} events")
        return session

    def list_saved_traces(self) -> list[dict]:
        """列出所有保存的 trace 文件"""
        if not self._storage_path.exists():
            return []

        traces = []
        for filepath in sorted(self._storage_path.glob("trace_*.json"), reverse=True):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                traces.append({
                    "filepath": str(filepath),
                    "trace_id": data.get("trace_id", ""),
                    "query": data.get("query", "")[:80],
                    "total_ms": data.get("total_ms", 0),
                    "event_count": len(data.get("events", [])),
                    "success_count": data.get("success_count", 0),
                    "failed_count": data.get("failed_count", 0),
                })
            except Exception:
                pass

        return traces


_recorder: TraceRecorder | None = None


def get_recorder() -> TraceRecorder:
    global _recorder
    if _recorder is None:
        _recorder = TraceRecorder()
    return _recorder
