from app.tools.base_tool import BaseTool
from app.utils.logger import get_logger

logger = get_logger("tool_registry")


class ToolRegistry:
    _instance: "ToolRegistry | None" = None
    _tools: dict[str, BaseTool] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
        return cls._instance

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        return [t.to_schema() for t in self._tools.values()]

    def get_all(self) -> dict[str, BaseTool]:
        return dict(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
