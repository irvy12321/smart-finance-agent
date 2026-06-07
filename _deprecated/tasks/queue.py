import asyncio
from collections import deque
from typing import Any


class TaskQueue:
    def __init__(self):
        self._queue: deque = deque()
        self._event = asyncio.Event()

    def put(self, item: Any):
        self._queue.append(item)
        self._event.set()

    async def get(self) -> Any:
        while not self._queue:
            self._event.clear()
            await self._event.wait()
        return self._queue.popleft()

    def __len__(self):
        return len(self._queue)

    def empty(self) -> bool:
        return len(self._queue) == 0
