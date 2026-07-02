"""
OpenTelemetry 集成 - tracer + span 管理

设计原则:
- opentelemetry 未安装或 OTEL_ENABLED != true 时全部降级为 no-op, 零开销
- otel_span(): 上下文管理器, 与现有 TraceContext.span 并行使用
- traced(): 装饰器, 给 Agent 主方法加 span (支持 async / sync)
- 导出器: 默认不导出; 设置 OTEL_EXPORTER_OTLP_ENDPOINT 时用 OTLP,
  设置 OTEL_CONSOLE_EXPORT=true 时用 Console
"""

import functools
import inspect
import os
import threading
from contextlib import contextmanager

from app.utils.logger import get_logger

logger = get_logger("otel")

try:
    from opentelemetry import trace as _ot_trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )

    _OTEL_INSTALLED = True
except ImportError:  # opentelemetry 未安装 -> no-op
    _OTEL_INSTALLED = False

_SERVICE_NAME = "smart-finance-agent"

_lock = threading.Lock()
_initialized = False
_tracer = None


def otel_enabled() -> bool:
    return _OTEL_INSTALLED and os.getenv("OTEL_ENABLED", "").lower() in (
        "1",
        "true",
        "yes",
    )


def _init_tracer():
    """惰性初始化全局 TracerProvider (线程安全, 只执行一次)"""
    global _initialized, _tracer
    if _initialized:
        return _tracer
    with _lock:
        if _initialized:
            return _tracer
        if not otel_enabled():
            _initialized = True
            return None
        try:
            provider = TracerProvider(
                resource=Resource.create({"service.name": _SERVICE_NAME})
            )
            otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
            if otlp_endpoint:
                try:
                    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                        OTLPSpanExporter,
                    )

                    provider.add_span_processor(
                        BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
                    )
                    logger.info(f"OTel OTLP exporter enabled: {otlp_endpoint}")
                except ImportError:
                    logger.warning(
                        "OTEL_EXPORTER_OTLP_ENDPOINT set but otlp exporter not installed"
                    )
            if os.getenv("OTEL_CONSOLE_EXPORT", "").lower() in ("1", "true", "yes"):
                provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
            _ot_trace.set_tracer_provider(provider)
            _tracer = _ot_trace.get_tracer(_SERVICE_NAME)
            logger.info("OpenTelemetry tracer initialized")
        except Exception as e:  # 初始化失败降级为 no-op, 不影响主流程
            logger.warning(f"OTel init failed, falling back to no-op: {e}")
            _tracer = None
        _initialized = True
        return _tracer


@contextmanager
def otel_span(name: str, **attributes):
    """创建 OTel span 的上下文管理器; OTel 不可用时为 no-op"""
    tracer = _init_tracer()
    if tracer is None:
        yield None
        return
    with tracer.start_as_current_span(name) as span:
        for key, value in attributes.items():
            if isinstance(value, (str, bool, int, float)):
                span.set_attribute(key, value)
            else:
                span.set_attribute(key, str(value)[:256])
        yield span


def traced(name: str | None = None):
    """给函数加 OTel span 的装饰器 (支持 async / sync)"""

    def decorator(func):
        span_name = name or f"{func.__module__}.{func.__qualname__}"

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                with otel_span(span_name):
                    return await func(*args, **kwargs)

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with otel_span(span_name):
                return func(*args, **kwargs)

        return sync_wrapper

    return decorator
