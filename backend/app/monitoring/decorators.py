"""
Decorators for automatic metrics collection

Usage:
    @track_agent_stage("planner")
    async def plan(self, query):
        ...

    @track_tool_call("news_search")
    async def execute(self, **params):
        ...
"""
import functools
import time
from typing import Callable

from app.monitoring.prometheus import (
    agent_calls_total,
    agent_errors_total,
    agent_in_progress,
    agent_stage_duration_seconds,
    tool_call_duration_seconds,
    tool_calls_total,
    tool_errors_total,
)


def track_agent_stage(stage_name: str) -> Callable:
    """
    Decorator to track Agent stage metrics.

    Records:
    - agent_calls_total: increment on each call
    - agent_stage_duration_seconds: observe execution time
    - agent_errors_total: increment on error
    - agent_in_progress: gauge for concurrent calls
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            agent_calls_total.labels(agent_name=stage_name).inc()
            agent_in_progress.labels(agent_name=stage_name).inc()

            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as exc:
                agent_errors_total.labels(
                    agent_name=stage_name,
                    error_type=type(exc).__name__,
                ).inc()
                raise
            finally:
                duration = time.perf_counter() - start
                agent_stage_duration_seconds.labels(stage=stage_name).observe(duration)
                agent_in_progress.labels(agent_name=stage_name).dec()

        return wrapper

    return decorator


def track_tool_call(tool_name: str) -> Callable:
    """
    Decorator to track Tool call metrics.

    Records:
    - tool_calls_total: increment on each call
    - tool_call_duration_seconds: observe execution time
    - tool_errors_total: increment on error
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            tool_calls_total.labels(tool_name=tool_name).inc()

            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as exc:
                tool_errors_total.labels(
                    tool_name=tool_name,
                    error_type=type(exc).__name__,
                ).inc()
                raise
            finally:
                duration = time.perf_counter() - start
                tool_call_duration_seconds.labels(tool_name=tool_name).observe(duration)

        return wrapper

    return decorator
