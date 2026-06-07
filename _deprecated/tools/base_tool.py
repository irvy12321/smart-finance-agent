from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: str = ""
    tool_name: str = ""

    def __str__(self):
        if self.success:
            return f"[{self.tool_name}] OK: {str(self.data)[:200]}"
        return f"[{self.tool_name}] ERROR: {self.error}"


class BaseTool(ABC):
    name: str = "base_tool"
    description: str = ""

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        pass

    async def fallback_execute(self, **kwargs) -> ToolResult:
        """降级执行: 默认返回失败，子类可覆盖"""
        return ToolResult(
            success=False,
            error=f"No fallback defined for '{self.name}'",
            tool_name=self.name,
        )

    def to_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
        }
