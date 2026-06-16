"""
Metrics Dashboard - 轻量级指标聚合器
从现有数据源聚合指标，不修改主流程
数据源: MetricsCollector / EventBus / TaskStateTracker
"""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field

from app.core.observability.metrics import get_metrics_summary
from app.utils.logger import get_logger

logger = get_logger("metrics_dashboard")


@dataclass
class PipelineRun:
    """单次 pipeline 运行记录"""

    trace_id: str
    query: str
    start_time: float
    end_time: float = 0.0
    total_ms: float = 0.0
    subtask_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    agent_latencies: dict[str, float] = field(default_factory=dict)
    tool_calls: list[dict] = field(default_factory=list)
    dag_size: int = 0
    status: str = "running"


class MetricsDashboard:
    """
    指标聚合器 - 从现有系统收集指标
    线程安全，不影响主流程
    """

    _instance: "MetricsDashboard | None" = None
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
        self._runs: list[PipelineRun] = []
        self._max_runs = 100
        self._current_run: PipelineRun | None = None
        self._event_buffer: list[dict] = []
        self._initialized = True

        logger.info("MetricsDashboard initialized")

    def start_run(self, trace_id: str, query: str):
        """记录 pipeline 开始"""
        with self._lock:
            run = PipelineRun(
                trace_id=trace_id,
                query=query,
                start_time=time.time(),
            )
            self._current_run = run

    def record_agent_latency(self, agent_name: str, latency_ms: float):
        """记录 agent 延迟"""
        with self._lock:
            if self._current_run:
                self._current_run.agent_latencies[agent_name] = latency_ms

    def record_tool_call(
        self, tool_name: str, success: bool, duration_ms: float, task_id: str = ""
    ):
        """记录 tool 调用"""
        with self._lock:
            if self._current_run:
                self._current_run.tool_calls.append(
                    {
                        "tool": tool_name,
                        "success": success,
                        "duration_ms": duration_ms,
                        "task_id": task_id,
                        "timestamp": time.time(),
                    }
                )

    def end_run(
        self,
        trace_id: str,
        subtask_count: int = 0,
        success_count: int = 0,
        failed_count: int = 0,
        dag_size: int = 0,
    ):
        """记录 pipeline 结束"""
        with self._lock:
            if self._current_run and self._current_run.trace_id == trace_id:
                self._current_run.end_time = time.time()
                self._current_run.total_ms = (
                    self._current_run.end_time - self._current_run.start_time
                ) * 1000
                self._current_run.subtask_count = subtask_count
                self._current_run.success_count = success_count
                self._current_run.failed_count = failed_count
                self._current_run.dag_size = dag_size
                self._current_run.status = "success" if failed_count == 0 else "partial"

                self._runs.append(self._current_run)
                if len(self._runs) > self._max_runs:
                    self._runs = self._runs[-self._max_runs :]
                self._current_run = None

    def ingest_from_metrics_collector(self):
        """从 MetricsCollector 同步数据"""
        summary = get_metrics_summary()
        return summary

    def get_agent_latency_stats(self) -> dict[str, dict]:
        """获取各 agent 延迟统计"""
        agent_data = defaultdict(lambda: {"latencies": [], "total_ms": 0, "calls": 0})

        for run in self._runs:
            for agent, latency in run.agent_latencies.items():
                agent_data[agent]["latencies"].append(latency)
                agent_data[agent]["total_ms"] += latency
                agent_data[agent]["calls"] += 1

        result = {}
        for agent, data in agent_data.items():
            lats = data["latencies"]
            result[agent] = {
                "avg_ms": data["total_ms"] / max(data["calls"], 1),
                "min_ms": min(lats) if lats else 0,
                "max_ms": max(lats) if lats else 0,
                "calls": data["calls"],
                "p50_ms": sorted(lats)[len(lats) // 2] if lats else 0,
            }
        return result

    def get_tool_stats(self) -> dict[str, dict]:
        """获取各 tool 调用统计"""
        tool_data = defaultdict(
            lambda: {"calls": 0, "success": 0, "failure": 0, "total_ms": 0}
        )

        for run in self._runs:
            for tc in run.tool_calls:
                tool = tc["tool"]
                tool_data[tool]["calls"] += 1
                if tc["success"]:
                    tool_data[tool]["success"] += 1
                else:
                    tool_data[tool]["failure"] += 1
                tool_data[tool]["total_ms"] += tc["duration_ms"]

        result = {}
        for tool, data in tool_data.items():
            result[tool] = {
                "calls": data["calls"],
                "success": data["success"],
                "failure": data["failure"],
                "success_rate": data["success"] / max(data["calls"], 1) * 100,
                "avg_ms": data["total_ms"] / max(data["calls"], 1),
            }
        return result

    def get_system_stats(self) -> dict:
        """获取系统级统计"""
        if not self._runs:
            return {
                "total_requests": 0,
                "success_rate": 0,
                "avg_dag_size": 0,
                "avg_duration_ms": 0,
                "total_tool_calls": 0,
                "total_success": 0,
                "total_failed": 0,
            }

        total = len(self._runs)
        success_runs = sum(1 for r in self._runs if r.status == "success")
        total_tool_calls = sum(len(r.tool_calls) for r in self._runs)
        total_success = sum(r.success_count for r in self._runs)
        total_failed = sum(r.failed_count for r in self._runs)

        return {
            "total_requests": total,
            "success_rate": success_runs / max(total, 1) * 100,
            "avg_dag_size": sum(r.dag_size for r in self._runs) / max(total, 1),
            "avg_duration_ms": sum(r.total_ms for r in self._runs) / max(total, 1),
            "total_tool_calls": total_tool_calls,
            "total_success": total_success,
            "total_failed": total_failed,
        }

    def get_error_trend(self) -> list[dict]:
        """获取错误趋势 (最近 N 次运行)"""
        trend = []
        for run in self._runs[-20:]:
            errors = sum(1 for tc in run.tool_calls if not tc["success"])
            trend.append(
                {
                    "trace_id": run.trace_id[:8],
                    "errors": errors,
                    "total": len(run.tool_calls),
                    "timestamp": run.start_time,
                }
            )
        return trend

    def get_recent_runs(self, limit: int = 10) -> list[dict]:
        """获取最近的运行记录"""
        result = []
        for run in self._runs[-limit:]:
            result.append(
                {
                    "trace_id": run.trace_id[:8],
                    "query": run.query[:50],
                    "total_ms": run.total_ms,
                    "subtask_count": run.subtask_count,
                    "success_count": run.success_count,
                    "failed_count": run.failed_count,
                    "status": run.status,
                    "tool_calls": len(run.tool_calls),
                }
            )
        return result

    def get_full_dashboard_data(self) -> dict:
        """获取完整的 dashboard 数据"""
        return {
            "agent_latencies": self.get_agent_latency_stats(),
            "tool_stats": self.get_tool_stats(),
            "system": self.get_system_stats(),
            "error_trend": self.get_error_trend(),
            "recent_runs": self.get_recent_runs(),
            "metrics_collector": self.ingest_from_metrics_collector(),
        }


# 便捷函数
_dashboard: MetricsDashboard | None = None


def get_dashboard() -> MetricsDashboard:
    global _dashboard
    if _dashboard is None:
        _dashboard = MetricsDashboard()
    return _dashboard
