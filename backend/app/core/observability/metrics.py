"""
增强指标收集器 - 并发安全 + Agent 集成 + 实时统计
"""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field

from app.utils.logger import get_logger

logger = get_logger("metrics")


@dataclass
class MetricPoint:
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: dict[str, str] = field(default_factory=dict)
    trace_id: str = ""


class MetricsCollector:
    """并发安全的指标收集器"""

    _instance: "MetricsCollector | None" = None
    _lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._metrics = []
                    cls._instance._counters = defaultdict(float)
                    cls._instance._gauges = {}
                    cls._instance._histograms = defaultdict(list)
        return cls._instance

    def record(self, name: str, value: float, trace_id: str = "", **tags):
        """记录指标点"""
        with self._lock:
            self._metrics.append(
                MetricPoint(
                    name=name,
                    value=value,
                    tags=tags,
                    trace_id=trace_id,
                )
            )
            self._counters[name] += value

    def gauge(self, name: str, value: float, **tags):
        """设置仪表值"""
        with self._lock:
            self._gauges[name] = {"value": value, "tags": tags, "time": time.time()}

    def histogram(self, name: str, value: float):
        """记录直方图值"""
        with self._lock:
            self._histograms[name].append(value)

    def get_counter(self, name: str) -> float:
        with self._lock:
            return self._counters.get(name, 0)

    def get_gauge(self, name: str) -> dict | None:
        with self._lock:
            return self._gauges.get(name)

    def get_histogram_stats(self, name: str) -> dict:
        """获取直方图统计"""
        with self._lock:
            values = list(self._histograms.get(name, ()))
        return self._histogram_stats_from_values(values)

    def get_agent_summary(self) -> dict[str, dict]:
        """获取各 Agent 的指标摘要"""
        with self._lock:
            agent_stats = defaultdict(
                lambda: {"calls": 0, "tokens": 0, "errors": 0, "total_ms": 0}
            )
            for m in self._metrics:
                agent = m.tags.get("agent", "unknown")
                if m.name == "agent_call":
                    agent_stats[agent]["calls"] += 1
                elif m.name == "agent_tokens":
                    agent_stats[agent]["tokens"] += m.value
                elif m.name == "agent_error":
                    agent_stats[agent]["errors"] += 1
                elif m.name == "agent_latency":
                    agent_stats[agent]["total_ms"] += m.value
            return dict(agent_stats)

    def get_all(self) -> dict:
        """获取所有指标"""
        with self._lock:
            counters = dict(self._counters)
            gauges = dict(self._gauges)
            histograms = {
                name: self._histogram_stats_from_values(list(values))
                for name, values in self._histograms.items()
            }
            agent_summary = self._agent_summary_unlocked()

        return {
            "counters": counters,
            "gauges": gauges,
            "histograms": histograms,
            "agent_summary": agent_summary,
        }

    def clear(self):
        with self._lock:
            self._metrics.clear()
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()

    @staticmethod
    def _histogram_stats_from_values(values: list[float]) -> dict:
        if not values:
            return {"count": 0}

        sorted_values = sorted(values)
        p50_idx = len(sorted_values) // 2
        p99_idx = min(len(sorted_values) - 1, int(len(sorted_values) * 0.99))
        return {
            "count": len(sorted_values),
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "avg": sum(sorted_values) / len(sorted_values),
            "p50": sorted_values[p50_idx],
            "p99": sorted_values[p99_idx],
        }

    def _agent_summary_unlocked(self) -> dict[str, dict]:
        agent_stats = defaultdict(
            lambda: {"calls": 0, "tokens": 0, "errors": 0, "total_ms": 0}
        )
        for m in self._metrics:
            agent = m.tags.get("agent", "unknown")
            if m.name == "agent_call":
                agent_stats[agent]["calls"] += 1
            elif m.name == "agent_tokens":
                agent_stats[agent]["tokens"] += m.value
            elif m.name == "agent_error":
                agent_stats[agent]["errors"] += 1
            elif m.name == "agent_latency":
                agent_stats[agent]["total_ms"] += m.value
        return dict(agent_stats)


# 便捷函数
_metrics = MetricsCollector()


def record_metric(name: str, value: float, trace_id: str = "", **tags):
    _metrics.record(name, value, trace_id=trace_id, **tags)


def record_agent_call(
    agent_name: str, tokens: int, latency_ms: float, trace_id: str = ""
):
    """记录 Agent 调用指标"""
    _metrics.record("agent_call", 1, trace_id=trace_id, agent=agent_name)
    _metrics.record("agent_tokens", tokens, trace_id=trace_id, agent=agent_name)
    _metrics.record("agent_latency", latency_ms, trace_id=trace_id, agent=agent_name)
    _metrics.histogram(f"agent.{agent_name}.latency", latency_ms)
    _metrics.histogram(f"agent.{agent_name}.tokens", tokens)


def record_agent_error(agent_name: str, error: str, trace_id: str = ""):
    """记录 Agent 错误"""
    _metrics.record("agent_error", 1, trace_id=trace_id, agent=agent_name, error=error)


def record_task_result(
    task_id: str, tool: str, success: bool, duration_ms: float, trace_id: str = ""
):
    """记录任务结果"""
    status = "success" if success else "failed"
    _metrics.record(
        "task_result", 1, trace_id=trace_id, task_id=task_id, tool=tool, status=status
    )
    _metrics.histogram(f"task.{tool}.latency", duration_ms)


def get_metrics_summary() -> dict:
    return _metrics.get_all()
