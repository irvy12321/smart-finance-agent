"""
Trace Replayer - 从保存的 trace 文件回放执行过程
不调用 LLM，纯日志回放
"""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from app.core.replay.trace_recorder import (
    TraceEvent,
    TraceSession,
    get_recorder,
)
from app.utils.logger import get_logger

logger = get_logger("trace_replayer")


@dataclass
class ReplayState:
    """回放状态"""

    current_task: str = ""
    completed_tasks: list[str] = field(default_factory=list)
    task_states: dict[str, dict] = field(default_factory=dict)
    progress: float = 0.0
    elapsed_ms: float = 0.0
    is_playing: bool = False
    is_paused: bool = False
    is_complete: bool = False


class TraceReplayer:
    """
    Trace 回放器 - 从保存的 trace 回放执行过程
    不调用 LLM，纯日志回放，支持 step-by-step 和自动播放
    """

    def __init__(self):
        self._session: TraceSession | None = None
        self._task_events: dict[str, list[TraceEvent]] = {}
        self._ordered_tasks: list[str] = []
        self._state = ReplayState()
        self._speed_factor = 1.0
        self._step_index = 0
        logger.info("TraceReplayer initialized")

    def load_session(self, session: TraceSession):
        """加载 trace 会话"""
        self._session = session
        self._task_events = session.get_task_events()
        self._ordered_tasks = session.get_ordered_tasks()
        self._state = ReplayState()
        self._step_index = 0
        logger.info(
            f"Loaded trace: {session.trace_id} ({len(self._ordered_tasks)} tasks)"
        )

    def load_from_file(self, filepath: str):
        """从文件加载 trace"""
        recorder = get_recorder()
        session = recorder.load_session(filepath)
        self.load_session(session)

    @property
    def state(self) -> ReplayState:
        return self._state

    @property
    def session(self) -> TraceSession | None:
        return self._session

    @property
    def is_loaded(self) -> bool:
        return self._session is not None

    async def replay(self, speed_factor: float = 1.0) -> AsyncIterator[dict]:
        """
        自动回放 - 按时间顺序逐 task 回放
        yield 事件供 UI 使用
        """
        if not self._session:
            return

        self._speed_factor = speed_factor
        self._state.is_playing = True
        self._state.is_complete = False

        total_tasks = len(self._ordered_tasks)

        yield {
            "type": "replay_start",
            "trace_id": self._session.trace_id,
            "query": self._session.query,
            "total_tasks": total_tasks,
        }

        for i, task_id in enumerate(self._ordered_tasks):
            if not self._state.is_playing:
                break

            # 等待暂停恢复
            while self._state.is_paused:
                await asyncio.sleep(0.1)

            events = self._task_events.get(task_id, [])
            start_event = next((e for e in events if e.event == "start"), None)
            end_event = next((e for e in events if e.event == "end"), None)

            # Task start
            if start_event:
                self._state.current_task = task_id
                self._state.task_states[task_id] = {
                    "tool": start_event.tool,
                    "status": "running",
                    "latency_ms": 0,
                    "success": False,
                }

                yield {
                    "type": "task_start",
                    "task_id": task_id,
                    "tool": start_event.tool,
                    "input": start_event.input_data,
                    "timestamp": start_event.timestamp,
                }

            # 模拟延迟 (按 speed_factor 缩放)
            if end_event and end_event.latency_ms > 0:
                delay = end_event.latency_ms / 1000 / self._speed_factor
                await asyncio.sleep(min(delay, 2.0))  # 最大 2 秒

            # Task end
            if end_event:
                self._state.task_states[task_id] = {
                    "tool": end_event.tool,
                    "status": "success" if end_event.success else "failed",
                    "latency_ms": end_event.latency_ms,
                    "success": end_event.success,
                    "output": end_event.output_data,
                    "error": end_event.error,
                }
                self._state.completed_tasks.append(task_id)

                yield {
                    "type": "task_end",
                    "task_id": task_id,
                    "tool": end_event.tool,
                    "success": end_event.success,
                    "latency_ms": end_event.latency_ms,
                    "output": str(end_event.output_data)[:300]
                    if end_event.output_data
                    else "",
                    "error": end_event.error,
                }

            self._state.progress = (i + 1) / total_tasks
            self._state.elapsed_ms = sum(
                ts.get("latency_ms", 0) for ts in self._state.task_states.values()
            )

        self._state.is_playing = False
        self._state.is_complete = True

        yield {
            "type": "replay_end",
            "trace_id": self._session.trace_id,
            "total_tasks": total_tasks,
            "success_count": self._session.success_count,
            "failed_count": self._session.failed_count,
            "total_ms": self._session.total_ms,
        }

    def step(self) -> dict | None:
        """
        单步回放 - 返回下一个 task 的事件
        不调用 LLM，纯数据回放
        """
        if not self._session:
            return None

        if self._step_index >= len(self._ordered_tasks):
            return None

        task_id = self._ordered_tasks[self._step_index]
        events = self._task_events.get(task_id, [])
        start_event = next((e for e in events if e.event == "start"), None)
        end_event = next((e for e in events if e.event == "end"), None)

        self._step_index += 1

        result = {
            "task_id": task_id,
            "step": self._step_index,
            "total_steps": len(self._ordered_tasks),
        }

        if start_event:
            result["start"] = {
                "tool": start_event.tool,
                "input": start_event.input_data,
                "timestamp": start_event.timestamp,
            }
            self._state.task_states[task_id] = {
                "tool": start_event.tool,
                "status": "running",
            }

        if end_event:
            result["end"] = {
                "tool": end_event.tool,
                "success": end_event.success,
                "latency_ms": end_event.latency_ms,
                "output": str(end_event.output_data)[:300]
                if end_event.output_data
                else "",
                "error": end_event.error,
            }
            self._state.task_states[task_id] = {
                "tool": end_event.tool,
                "status": "success" if end_event.success else "failed",
                "latency_ms": end_event.latency_ms,
                "success": end_event.success,
            }
            self._state.completed_tasks.append(task_id)

        self._state.progress = self._step_index / len(self._ordered_tasks)
        self._state.current_task = task_id

        return result

    def pause(self):
        """暂停回放"""
        self._state.is_paused = True

    def resume(self):
        """恢复回放"""
        self._state.is_paused = False

    def stop(self):
        """停止回放"""
        self._state.is_playing = False
        self._state.is_paused = False

    def reset(self):
        """重置回放状态"""
        self._step_index = 0
        self._state = ReplayState()

    def get_dag_data(self) -> dict:
        """获取 DAG 可视化数据"""
        if not self._session:
            return {"nodes": [], "edges": []}

        nodes = []
        edges = []

        for st in self._session.subtasks:
            task_id = st.get("id", "")
            tool = st.get("tool", "")
            state = self._state.task_states.get(task_id, {})
            status = state.get("status", "pending")

            nodes.append(
                {
                    "id": task_id,
                    "tool": tool,
                    "desc": st.get("desc", ""),
                    "status": status,
                    "latency_ms": state.get("latency_ms", 0),
                }
            )

            for dep in st.get("depends_on", []):
                edges.append({"from": dep, "to": task_id})

        return {"nodes": nodes, "edges": edges}

    def get_summary(self) -> dict:
        """获取回放摘要"""
        if not self._session:
            return {}

        return {
            "trace_id": self._session.trace_id,
            "query": self._session.query,
            "total_ms": self._session.total_ms,
            "total_tasks": len(self._ordered_tasks),
            "success_count": self._session.success_count,
            "failed_count": self._session.failed_count,
            "progress": self._state.progress,
            "is_playing": self._state.is_playing,
            "is_complete": self._state.is_complete,
        }


_replayer: TraceReplayer | None = None


def get_replayer() -> TraceReplayer:
    global _replayer
    if _replayer is None:
        _replayer = TraceReplayer()
    return _replayer
