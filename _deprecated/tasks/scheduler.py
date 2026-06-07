import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine
from utils.logger import get_logger

logger = get_logger("scheduler")


@dataclass
class ScheduledTask:
    task_id: str
    coro_factory: Callable[[], Coroutine]
    priority: int = 0
    result: Any = None
    error: str = ""
    done: bool = False


class TaskScheduler:
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._results: dict[str, ScheduledTask] = {}

    def add_task(self, task: ScheduledTask):
        self._queue.put_nowait((-task.priority, task.task_id, task))

    async def run_all(self) -> dict[str, ScheduledTask]:
        semaphore = asyncio.Semaphore(self.max_concurrent)
        tasks = []

        async def _run(task: ScheduledTask):
            async with semaphore:
                try:
                    task.result = await task.coro_factory()
                    task.done = True
                except Exception as e:
                    task.error = str(e)
                    task.done = True
                    logger.error(f"Task {task.task_id} failed: {e}")

        while not self._queue.empty():
            _, _, task = self._queue.get_nowait()
            self._results[task.task_id] = task
            tasks.append(asyncio.create_task(_run(task)))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        return self._results
