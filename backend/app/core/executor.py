import asyncio
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from app.core.agent_status import (
    AgentEvent,
    EventBus,
    TaskStateTracker,
    TaskStatus,
)
from app.core.fallback_manager import FallbackManager
from app.core.planner import Plan, SubTask
from app.infrastructure.llm_client import LiteLLMRouter, LLMClient
from app.tools.base_tool import ToolResult
from app.tools.registry import ToolRegistry
from app.utils.circuit_breaker import CircuitBreakerManager
from app.utils.exceptions import CircuitBreakerOpenError
from app.utils.logger import get_logger
from app.utils.tracing import TraceContext

logger = get_logger("executor")

# 状态回调类型
StatusCallback = Callable[[str, TaskStatus, dict], Coroutine[Any, Any, None]]


@dataclass
class TaskResult:
    task_id: str
    tool_name: str
    success: bool
    data: Any = None
    error: str = ""
    duration_ms: float = 0.0
    status: TaskStatus = TaskStatus.SUCCESS


@dataclass
class ExecutionResult:
    plan: Plan
    task_results: list[TaskResult] = field(default_factory=list)
    final_answer: str = ""
    total_duration_ms: float = 0.0

    @property
    def success(self) -> bool:
        return all(r.success for r in self.task_results)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.task_results if r.success)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.task_results if not r.success)


class ExecutorAgent:
    def __init__(
        self,
        tool_registry: ToolRegistry | None = None,
        llm_client: LLMClient | None = None,
        router: LiteLLMRouter | None = None,
    ):
        self.registry = tool_registry or ToolRegistry()
        self.router = router
        self.llm = llm_client or LLMClient.get_instance()
        self.state_tracker = TaskStateTracker.get_instance()
        self.event_bus = EventBus.get_instance()
        self.circuit_breaker_mgr = CircuitBreakerManager()
        self.fallback_mgr = FallbackManager(
            tool_registry=self.registry,
            llm_client=self.llm,
            router=self.router,
        )

    async def execute(self, plan: Plan) -> ExecutionResult:
        trace = TraceContext()
        result = ExecutionResult(plan=plan)

        logger.info(f"Executing plan with {len(plan.subtasks)} subtasks")
        await self.event_bus.emit(AgentEvent(
            event_type="execution_start",
            agent_name="executor",
            data={"task_count": len(plan.subtasks)},
        ))

        with trace.span("execute_plan"):
            task_graph = self._build_task_graph(plan.subtasks)
            completed: dict[str, TaskResult] = {}
            round_num = 0

            while task_graph:
                # 找到所有依赖已完成的任务
                ready = [
                    tid for tid, deps in task_graph.items()
                    if all(d in completed for d in deps)
                ]

                if not ready:
                    # 死锁恢复: 尝试移除不可满足的依赖后重排
                    recoverable = self._try_resolve_deadlock(task_graph, completed)
                    if recoverable:
                        ready = recoverable
                        logger.warning(f"Deadlock recovered: {len(ready)} tasks unlocked")
                    else:
                        logger.error("Deadlock detected in task graph, skipping remaining tasks")
                        for tid in task_graph:
                            self.state_tracker.set_status(tid, TaskStatus.SKIPPED)
                            result.task_results.append(TaskResult(
                                task_id=tid, tool_name="unknown", success=False,
                                error="Deadlock: unresolvable dependencies", status=TaskStatus.SKIPPED,
                            ))
                        break

                round_num += 1
                logger.info(f"Execution round {round_num}: {len(ready)} tasks (parallel)")

                # 并行执行本轮所有就绪任务
                with trace.span("parallel_batch", tasks=ready, round=round_num):
                    batch_results = await asyncio.gather(
                        *[self._execute_task(plan.subtasks, tid, completed, trace) for tid in ready],
                        return_exceptions=True,
                    )

                for tid, res in zip(ready, batch_results, strict=False):
                    if isinstance(res, Exception):
                        tr = TaskResult(
                            task_id=tid, tool_name="unknown", success=False,
                            error=str(res), status=TaskStatus.FAILED,
                        )
                        self.state_tracker.set_status(tid, TaskStatus.FAILED, {"error": str(res)})
                    else:
                        tr = res
                        self.state_tracker.set_status(tid, tr.status, {
                            "duration_ms": tr.duration_ms, "tool": tr.tool_name,
                        })

                    result.task_results.append(tr)
                    completed[tid] = tr

                    await self.event_bus.emit(AgentEvent(
                        event_type="task_complete",
                        agent_name="executor",
                        data={
                            "task_id": tid, "tool": tr.tool_name,
                            "success": tr.success, "duration_ms": tr.duration_ms,
                            "round": round_num,
                        },
                    ))
                    del task_graph[tid]

            # 提取最终答案
            if any(t.tool_name == "llm_synthesize" and t.success for t in result.task_results):
                synth = next(t for t in result.task_results if t.tool_name == "llm_synthesize" and t.success)
                result.final_answer = synth.data
            else:
                result.final_answer = await self._auto_synthesize(plan, result.task_results, trace)

        result.total_duration_ms = trace.summary()["total_ms"]
        logger.info(
            f"Execution complete in {result.total_duration_ms:.0f}ms "
            f"(success={result.success_count}, failed={result.failed_count})"
        )

        await self.event_bus.emit(AgentEvent(
            event_type="execution_complete",
            agent_name="executor",
            data={
                "total_ms": result.total_duration_ms,
                "success": result.success_count,
                "failed": result.failed_count,
            },
        ))

        return result

    async def _execute_task(
        self,
        subtasks: list[SubTask],
        task_id: str,
        completed: dict[str, TaskResult],
        trace: TraceContext,
    ) -> TaskResult:
        task = next((t for t in subtasks if t.task_id == task_id), None)
        if not task:
            return TaskResult(task_id=task_id, tool_name="unknown", success=False, error="Task not found")

        start = time.perf_counter()
        self.state_tracker.set_status(task_id, TaskStatus.RUNNING)

        logger.info(f"Executing {task.task_id}: {task.tool_name} - {task.description}")

        await self.event_bus.emit(AgentEvent(
            event_type="task_start",
            agent_name="executor",
            data={"task_id": task.task_id, "tool": task.tool_name, "description": task.description},
        ))

        if task.tool_name == "llm_synthesize":
            result = await self._run_synthesize(task, completed, trace)
        else:
            tool = self.registry.get(task.tool_name)
            if not tool:
                return TaskResult(
                    task_id=task.task_id, tool_name=task.tool_name,
                    success=False, error=f"Tool '{task.tool_name}' not found in registry",
                    status=TaskStatus.FAILED,
                )

            params = dict(task.params)
            # 注入依赖任务的输出作为上下文
            if task.depends_on:
                context_parts = []
                for dep_id in task.depends_on:
                    dep_result = completed.get(dep_id)
                    if dep_result and dep_result.success and dep_result.data:
                        context_parts.append(f"[{dep_id}] {dep_result.data}")
                if context_parts and "query" in params:
                    params["query"] = params["query"] + "\n\nContext from prior tasks:\n" + "\n".join(context_parts)

            # === 熔断器检查 ===
            breaker = self.circuit_breaker_mgr.get_breaker(task.tool_name)
            try:
                breaker.check_or_raise()
            except CircuitBreakerOpenError as e:
                logger.warning(f"[trace:{trace.trace_id}] Circuit breaker OPEN for {task.tool_name}: {e}")
                # 熔断时直接走降级
                result = await self._execute_with_fallback(task, params, trace)
                result.duration_ms = (time.perf_counter() - start) * 1000
                return result

            # === 正常执行 + 降级 ===
            with trace.span(f"tool_{task.tool_name}", task_id=task.task_id):
                try:
                    tool_result = await tool.execute(**params)
                except Exception as e:
                    logger.error(f"[trace:{trace.trace_id}] Tool {task.tool_name} exception: {e}")
                    tool_result = ToolResult(success=False, error=str(e), tool_name=task.tool_name)

            if tool_result.success:
                breaker.record_success()
                result = TaskResult(
                    task_id=task.task_id, tool_name=task.tool_name,
                    success=True, data=tool_result.data, status=TaskStatus.SUCCESS,
                )
            else:
                breaker.record_failure()
                logger.info(f"[trace:{trace.trace_id}] Tool {task.tool_name} failed, trying fallback...")
                result = await self._execute_with_fallback(task, params, trace)

        result.duration_ms = (time.perf_counter() - start) * 1000
        return result

    async def _execute_with_fallback(
        self, task: SubTask, params: dict, trace: TraceContext
    ) -> TaskResult:
        """执行降级链"""
        try:
            fallback_result, used_tool = await self.fallback_mgr.execute_with_fallback(
                task.tool_name, params, trace_id=trace.trace_id,
            )
            if fallback_result.success:
                is_degraded = used_tool != task.tool_name
                return TaskResult(
                    task_id=task.task_id,
                    tool_name=task.tool_name,
                    success=True,
                    data=fallback_result.data,
                    status=TaskStatus.DEGRADED if is_degraded else TaskStatus.SUCCESS,
                )
            else:
                return TaskResult(
                    task_id=task.task_id,
                    tool_name=task.tool_name,
                    success=False,
                    error=fallback_result.error,
                    status=TaskStatus.FAILED,
                )
        except Exception as e:
            logger.error(f"[trace:{trace.trace_id}] Fallback also failed for {task.tool_name}: {e}")
            return TaskResult(
                task_id=task.task_id,
                tool_name=task.tool_name,
                success=False,
                error=f"Primary + fallback failed: {e}",
                status=TaskStatus.FAILED,
            )

    async def _run_synthesize(
        self, task: SubTask, completed: dict[str, TaskResult], trace: TraceContext
    ) -> TaskResult:
        context_parts = []
        for dep_id in task.depends_on:
            dep = completed.get(dep_id)
            if dep and dep.success and dep.data:
                context_parts.append(f"=== {dep.tool_name} ({dep.task_id}) ===\n{self._format_data(dep.data)}")

        if not context_parts:
            for _dep_id, dep in completed.items():
                if dep.success and dep.data:
                    context_parts.append(f"=== {dep.tool_name} ({dep.task_id}) ===\n{self._format_data(dep.data)}")

        synthesis_prompt = task.params.get("prompt", "Analyze and summarize the following information:")
        full_prompt = f"{synthesis_prompt}\n\n" + "\n\n".join(context_parts) if context_parts else synthesis_prompt

        with trace.span("llm_synthesize", task_id=task.task_id):
            if self.router:
                answer = await self.router.complete(
                    "executor",
                    prompt=full_prompt,
                    system="You are a research analyst. Provide a clear, structured, and comprehensive analysis based on the provided data.",
                    max_tokens=4096,
                )
            else:
                answer = await self.llm.complete(
                    prompt=full_prompt,
                    system="You are a research analyst. Provide a clear, structured, and comprehensive analysis based on the provided data.",
                    temperature=0.3,
                    max_tokens=4096,
                )

        return TaskResult(task_id=task.task_id, tool_name="llm_synthesize", success=True, data=answer, status=TaskStatus.SUCCESS)

    async def _auto_synthesize(
        self, plan: Plan, results: list[TaskResult], trace: TraceContext
    ) -> str:
        context_parts = []
        for r in results:
            if r.success and r.data:
                context_parts.append(f"=== {r.tool_name} ({r.task_id}) ===\n{self._format_data(r.data)}")

        if not context_parts:
            return "No successful task results to synthesize."

        prompt = (
            f"Based on the following research results about: {plan.original_query}\n\n"
            + "\n\n".join(context_parts)
            + "\n\nPlease provide a comprehensive, well-structured analysis answering the user's question."
        )

        with trace.span("auto_synthesize"):
            if self.router:
                return await self.router.complete("executor", prompt=prompt, max_tokens=4096)
            else:
                return await self.llm.complete(prompt=prompt, temperature=0.3, max_tokens=4096)

    @staticmethod
    def _build_task_graph(subtasks: list[SubTask]) -> dict[str, list[str]]:
        return {st.task_id: list(st.depends_on) for st in subtasks}

    @staticmethod
    def _format_data(data: Any) -> str:
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            import json
            return json.dumps(data, ensure_ascii=False, indent=2)
        return str(data)

    @staticmethod
    def _try_resolve_deadlock(
        task_graph: dict[str, list[str]], completed: dict[str, TaskResult]
    ) -> list[str] | None:
        """
        死锁恢复: 尝试移除不可满足的依赖，解锁可执行任务
        如果所有未完成依赖都已失败/跳过，则移除这些依赖并返回可执行任务列表
        """
        unlockable = []
        for tid, deps in task_graph.items():
            unresolved = [
                d for d in deps
                if d not in completed and d in task_graph
            ]
            if not unresolved:
                # 检查是否有失败/跳过的依赖（允许继续）
                failed_deps = [
                    d for d in deps
                    if d in completed and not completed[d].success
                ]
                if failed_deps and all(d in completed for d in deps if d not in task_graph):
                    unlockable.append(tid)

        if unlockable:
            logger.info(f"Deadlock recovery: unlocking {len(unlockable)} tasks with failed deps")
            return unlockable
        return None
