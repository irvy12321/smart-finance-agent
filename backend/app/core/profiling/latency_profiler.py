"""
Latency Profiler - Pipeline 全链路延迟分析
通过 EventBus 订阅零侵入采集，不修改执行逻辑
"""

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from app.utils.logger import get_logger

logger = get_logger("latency_profiler")


@dataclass
class StageRecord:
    """单阶段记录"""

    name: str
    start_time: float
    end_time: float = 0.0
    duration_ms: float = 0.0
    status: str = "ok"

    def finish(self):
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000


@dataclass
class ToolCallRecord:
    """单次 tool 调用记录"""

    tool_name: str
    task_id: str
    start_time: float
    end_time: float = 0.0
    duration_ms: float = 0.0
    success: bool = True

    def finish(self, success: bool = True):
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.success = success


@dataclass
class ProfilingReport:
    """Profiling 报告"""

    trace_id: str
    query: str
    total_latency_ms: float = 0.0
    planner_latency_ms: float = 0.0
    executor_latency_ms: float = 0.0
    reasoner_latency_ms: float = 0.0
    report_latency_ms: float = 0.0
    routing_latency_ms: float = 0.0
    tool_latency: dict[str, float] = field(default_factory=dict)
    tool_calls: list[dict] = field(default_factory=list)
    stage_breakdown: list[dict] = field(default_factory=list)
    bottleneck_stage: str = ""
    bottleneck_tool: str = ""
    subtask_count: int = 0
    success_count: int = 0
    failed_count: int = 0

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "query": self.query[:100],
            "total_latency_ms": round(self.total_latency_ms, 2),
            "planner_latency_ms": round(self.planner_latency_ms, 2),
            "executor_latency_ms": round(self.executor_latency_ms, 2),
            "reasoner_latency_ms": round(self.reasoner_latency_ms, 2),
            "report_latency_ms": round(self.report_latency_ms, 2),
            "routing_latency_ms": round(self.routing_latency_ms, 2),
            "tool_latency": {k: round(v, 2) for k, v in self.tool_latency.items()},
            "tool_calls": self.tool_calls,
            "stage_breakdown": self.stage_breakdown,
            "bottleneck_stage": self.bottleneck_stage,
            "bottleneck_tool": self.bottleneck_tool,
            "subtask_count": self.subtask_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
        }

    def print_report(self):
        """打印可读报告"""
        print(f"\n{'=' * 60}")
        print(f"  LATENCY PROFILING REPORT [{self.trace_id}]")
        print(f"{'=' * 60}")
        print(f"Query: {self.query[:80]}")
        print(f"Total: {self.total_latency_ms:.0f}ms")
        print(f"{'-' * 60}")
        print(f"  Routing:   {self.routing_latency_ms:>8.0f}ms")
        print(f"  Planner:   {self.planner_latency_ms:>8.0f}ms")
        print(f"  Executor:  {self.executor_latency_ms:>8.0f}ms")
        print(f"  Reasoner:  {self.reasoner_latency_ms:>8.0f}ms")
        print(f"  Report:    {self.report_latency_ms:>8.0f}ms")
        if self.tool_latency:
            print(f"{'-' * 60}")
            print("  Tool Latencies:")
            for tool, ms in sorted(self.tool_latency.items(), key=lambda x: -x[1]):
                print(f"    {tool:20s} {ms:>8.0f}ms")
        print(f"{'-' * 60}")
        print(f"  Bottleneck: {self.bottleneck_stage}")
        if self.bottleneck_tool:
            print(f"  Slowest Tool: {self.bottleneck_tool}")
        print(
            f"  Tasks: {self.subtask_count} total, {self.success_count} ok, {self.failed_count} failed"
        )
        print(f"{'=' * 60}\n")


class LatencyProfiler:
    """
    延迟 Profiler - 通过 EventBus 事件零侵入采集
    线程安全，不影响主流程
    """

    _instance: "LatencyProfiler | None" = None
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
        self._pipeline_start: float = 0.0
        self._trace_id: str = ""
        self._query: str = ""

        self._stages: dict[str, StageRecord] = {}
        self._tool_calls: dict[str, ToolCallRecord] = {}
        self._completed_tools: list[ToolCallRecord] = []

        self._reports: list[ProfilingReport] = []
        self._max_reports = 50
        self._initialized = True

        logger.info("LatencyProfiler initialized")

    @contextmanager
    def profile(self, query: str, trace_id: str = ""):
        """
        上下文管理器 - 包装 pipeline 执行自动采集延迟

        Usage:
            profiler = get_profiler()
            with profiler.profile("query") as p:
                result = await orchestrator.run("query")
                # profiling data auto-collected via EventBus
        """
        self.start(query, trace_id)
        try:
            yield self
        finally:
            self.finish()

    def start(self, query: str, trace_id: str = ""):
        """开始 profiling"""
        self._pipeline_start = time.perf_counter()
        self._trace_id = trace_id or "local"
        self._query = query
        self._stages.clear()
        self._tool_calls.clear()
        self._completed_tools.clear()
        self._active = True

        self._stages["pipeline"] = StageRecord(
            name="pipeline",
            start_time=self._pipeline_start,
        )
        logger.debug(f"Profiling started for: {query[:60]}")

    def finish(self) -> ProfilingReport:
        """结束 profiling，生成报告"""
        if not self._active:
            return ProfilingReport(trace_id="", query="")

        pipeline_end = time.perf_counter()
        self._stages["pipeline"].end_time = pipeline_end
        self._stages["pipeline"].duration_ms = (
            pipeline_end - self._pipeline_start
        ) * 1000

        report = self._build_report()
        self._reports.append(report)
        if len(self._reports) > self._max_reports:
            self._reports = self._reports[-self._max_reports :]

        self._active = False
        logger.debug(
            f"Profiling finished: {report.total_latency_ms:.0f}ms, bottleneck={report.bottleneck_stage}"
        )
        return report

    def mark_stage_start(self, stage_name: str):
        """标记阶段开始"""
        if not self._active:
            return
        self._stages[stage_name] = StageRecord(
            name=stage_name,
            start_time=time.perf_counter(),
        )

    def mark_stage_end(self, stage_name: str, status: str = "ok"):
        """标记阶段结束"""
        if not self._active:
            return
        stage = self._stages.get(stage_name)
        if stage:
            stage.finish()
            stage.status = status

    def mark_tool_start(self, task_id: str, tool_name: str):
        """标记 tool 调用开始"""
        if not self._active:
            return
        self._tool_calls[task_id] = ToolCallRecord(
            tool_name=tool_name,
            task_id=task_id,
            start_time=time.perf_counter(),
        )

    def mark_tool_end(self, task_id: str, success: bool = True):
        """标记 tool 调用结束"""
        if not self._active:
            return
        tc = self._tool_calls.pop(task_id, None)
        if tc:
            tc.finish(success)
            self._completed_tools.append(tc)

    def record_event(self, event_type: str, data: dict[str, Any]):
        """
        处理 EventBus 事件 - 自动提取时间戳
        由 ProfilingIntegration 调用
        """
        if not self._active:
            return

        if event_type == "stage_change":
            stage = data.get("stage", "")
            if stage == "planning":
                self.mark_stage_start("planner")
            elif stage == "executing":
                if "planner" in self._stages and self._stages["planner"].end_time == 0:
                    self.mark_stage_end("planner")
                self.mark_stage_start("executor")
            elif stage == "reasoning":
                if (
                    "executor" in self._stages
                    and self._stages["executor"].end_time == 0
                ):
                    self.mark_stage_end("executor")
                self.mark_stage_start("reasoner")
            elif stage == "reporting":
                if (
                    "reasoner" in self._stages
                    and self._stages["reasoner"].end_time == 0
                ):
                    self.mark_stage_end("reasoner")
                self.mark_stage_start("report")
            elif (
                stage == "complete"
                and "report" in self._stages
                and self._stages["report"].end_time == 0
            ):
                self.mark_stage_end("report")

        elif event_type == "task_start":
            task_id = data.get("task_id", "")
            tool = data.get("tool", "")
            if task_id and tool:
                self.mark_tool_start(task_id, tool)

        elif event_type == "task_complete":
            task_id = data.get("task_id", "")
            success = data.get("success", False)
            if task_id:
                self.mark_tool_end(task_id, success)

    def _build_report(self) -> ProfilingReport:
        """构建 profiling 报告"""
        pipeline = self._stages.get("pipeline")
        total_ms = pipeline.duration_ms if pipeline else 0

        planner_ms = (
            self._stages["planner"].duration_ms if "planner" in self._stages else 0
        )
        executor_ms = (
            self._stages["executor"].duration_ms if "executor" in self._stages else 0
        )
        reasoner_ms = (
            self._stages["reasoner"].duration_ms if "reasoner" in self._stages else 0
        )
        report_ms = (
            self._stages["report"].duration_ms if "report" in self._stages else 0
        )

        # Tool latency aggregation
        tool_latency: dict[str, float] = {}
        tool_call_details: list[dict] = []
        for tc in self._completed_tools:
            tool_latency[tc.tool_name] = (
                tool_latency.get(tc.tool_name, 0) + tc.duration_ms
            )
            tool_call_details.append(
                {
                    "task_id": tc.task_id,
                    "tool": tc.tool_name,
                    "duration_ms": round(tc.duration_ms, 2),
                    "success": tc.success,
                }
            )

        # Stage breakdown
        stage_breakdown = []
        for name, stage in self._stages.items():
            if name == "pipeline":
                continue
            if stage.duration_ms > 0:
                pct = (stage.duration_ms / total_ms * 100) if total_ms > 0 else 0
                stage_breakdown.append(
                    {
                        "name": name,
                        "duration_ms": round(stage.duration_ms, 2),
                        "percent": round(pct, 1),
                        "status": stage.status,
                    }
                )
        stage_breakdown.sort(key=lambda x: -x["duration_ms"])

        # Bottleneck
        stage_latencies = {
            "planner": planner_ms,
            "executor": executor_ms,
            "reasoner": reasoner_ms,
            "report": report_ms,
        }
        bottleneck_stage = (
            max(stage_latencies, key=stage_latencies.get) if stage_latencies else ""
        )

        bottleneck_tool = ""
        if tool_latency:
            bottleneck_tool = max(tool_latency, key=tool_latency.get)

        success_count = sum(1 for tc in self._completed_tools if tc.success)
        failed_count = sum(1 for tc in self._completed_tools if not tc.success)

        return ProfilingReport(
            trace_id=self._trace_id,
            query=self._query,
            total_latency_ms=total_ms,
            planner_latency_ms=planner_ms,
            executor_latency_ms=executor_ms,
            reasoner_latency_ms=reasoner_ms,
            report_latency_ms=report_ms,
            routing_latency_ms=0,
            tool_latency=tool_latency,
            tool_calls=tool_call_details,
            stage_breakdown=stage_breakdown,
            bottleneck_stage=bottleneck_stage,
            bottleneck_tool=bottleneck_tool,
            subtask_count=len(self._completed_tools),
            success_count=success_count,
            failed_count=failed_count,
        )

    def get_latest_report(self) -> ProfilingReport | None:
        """获取最新报告"""
        return self._reports[-1] if self._reports else None

    def get_all_reports(self) -> list[ProfilingReport]:
        """获取所有报告"""
        return list(self._reports)

    def get_reports_as_dicts(self) -> list[dict]:
        """获取所有报告 (dict 格式)"""
        return [r.to_dict() for r in self._reports]


_profiler: LatencyProfiler | None = None


def get_profiler() -> LatencyProfiler:
    global _profiler
    if _profiler is None:
        _profiler = LatencyProfiler()
    return _profiler
