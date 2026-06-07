"""
增强追踪模块 - 并发安全 + Metrics 集成 + 生命周期追踪
"""
import time
import uuid
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from utils.logger import get_logger, LogContext

logger = get_logger("tracing")


@dataclass
class Span:
    """追踪跨度"""
    name: str
    trace_id: str
    parent_id: str | None = None
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    start_time: float = field(default_factory=time.perf_counter)
    end_time: float = 0.0
    duration_ms: float = 0.0
    metadata: dict = field(default_factory=dict)
    status: str = "ok"  # ok, error, timeout

    def finish(self):
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000

    def to_dict(self) -> dict:
        return {
            "span_id": self.span_id,
            "name": self.name,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "duration_ms": round(self.duration_ms, 2),
            "status": self.status,
            "metadata": self.metadata,
        }


class TraceContext:
    """并发安全的追踪上下文"""

    def __init__(self, trace_id: str | None = None):
        self.trace_id = trace_id or uuid.uuid4().hex[:12]
        self._lock = threading.Lock()
        self.spans: list[Span] = []
        self._current_span_id: str | None = None

        # 设置日志上下文
        LogContext.set(trace_id=self.trace_id)

    @contextmanager
    def span(self, name: str, **metadata):
        """创建追踪跨度 (并发安全)"""
        s = Span(
            name=name,
            trace_id=self.trace_id,
            parent_id=self._current_span_id,
            metadata=metadata,
        )

        with self._lock:
            self.spans.append(s)
            self._current_span_id = s.span_id

        LogContext.set(trace_id=self.trace_id)
        logger.debug(f"[trace:{self.trace_id}] {name} started")

        try:
            yield s
            s.status = "ok"
        except Exception as e:
            s.status = "error"
            s.metadata["error"] = str(e)
            raise
        finally:
            s.finish()
            logger.debug(
                f"[trace:{self.trace_id}] {name} finished "
                f"in {s.duration_ms:.1f}ms status={s.status}"
            )
            with self._lock:
                self._current_span_id = s.parent_id

    def add_event(self, name: str, **data):
        """添加事件标记"""
        with self._lock:
            self.spans.append(Span(
                name=f"event:{name}",
                trace_id=self.trace_id,
                metadata=data,
            ))

    def summary(self) -> dict:
        """获取追踪摘要"""
        with self._lock:
            total_ms = sum(s.duration_ms for s in self.spans if s.end_time > 0)
            return {
                "trace_id": self.trace_id,
                "total_ms": round(total_ms, 2),
                "span_count": len(self.spans),
                "error_count": sum(1 for s in self.spans if s.status == "error"),
                "spans": [s.to_dict() for s in self.spans],
            }


class PipelineTracker:
    """流水线级追踪器 - 追踪整个 Pipeline 的生命周期"""

    def __init__(self, trace_id: str, query: str):
        self.trace_id = trace_id
        self.query = query
        self.start_time = time.perf_counter()
        self._stages: list[dict] = []
        self._lock = threading.Lock()

    def record_stage(self, stage: str, agent: str, duration_ms: float,
                     tokens: int = 0, status: str = "ok", **extra):
        """记录阶段执行"""
        with self._lock:
            self._stages.append({
                "stage": stage,
                "agent": agent,
                "duration_ms": round(duration_ms, 2),
                "tokens": tokens,
                "status": status,
                **extra,
            })

    def get_summary(self) -> dict:
        """获取流水线摘要"""
        total_ms = (time.perf_counter() - self.start_time) * 1000
        total_tokens = sum(s.get("tokens", 0) for s in self._stages)
        error_count = sum(1 for s in self._stages if s["status"] != "ok")

        return {
            "trace_id": self.trace_id,
            "query": self.query[:100],
            "total_ms": round(total_ms, 2),
            "total_tokens": total_tokens,
            "stages": self._stages,
            "error_count": error_count,
        }

    def print_summary(self):
        """打印流水线摘要"""
        summary = self.get_summary()
        print(f"\n{'='*60}")
        print(f"  Pipeline Summary [{summary['trace_id']}]")
        print(f"{'='*60}")
        print(f"Query: {summary['query']}")
        print(f"Total: {summary['total_ms']/1000:.1f}s | Tokens: {summary['total_tokens']}")
        print(f"Stages: {len(summary['stages'])} | Errors: {summary['error_count']}")
        print(f"{'-'*60}")
        for s in summary["stages"]:
            icon = "OK" if s["status"] == "ok" else "ERR"
            print(f"  [{icon}] {s['stage']:15s} {s['agent']:12s} "
                  f"{s['duration_ms']/1000:6.1f}s {s['tokens']:5d}tok")
        print(f"{'='*60}\n")
