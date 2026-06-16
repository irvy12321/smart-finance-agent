import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

MOCK_WARNING = "SIMULATED DATA - NOT FOR INVESTMENT"


def mock_enabled() -> bool:
    """Whether tools may serve simulated data as a fallback.

    Defaults to False: real data sources that are unavailable must surface an
    explicit error rather than silently returning fabricated numbers.
    """
    return os.getenv("ALLOW_MOCK_DATA", "false").lower() in ("1", "true", "yes")


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: str = ""
    tool_name: str = ""
    source: str = "unknown"
    is_mock: bool = False
    warning: str = ""

    def __str__(self):
        if self.success:
            tag = " [MOCK]" if self.is_mock else ""
            return f"[{self.tool_name}]{tag} OK: {str(self.data)[:200]}"
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
