class AgentError(Exception):
    pass


class PlannerError(AgentError):
    pass


class ExecutorError(AgentError):
    pass


class ToolError(AgentError):
    pass


class LLMClientError(AgentError):
    pass


class CrawlerError(ToolError):
    pass


class RAGError(ToolError):
    pass


class CircuitBreakerOpenError(AgentError):
    """熔断器打开，拒绝调用"""
    def __init__(self, tool_name: str, retry_after: float = 0.0):
        self.tool_name = tool_name
        self.retry_after = retry_after
        super().__init__(f"Circuit breaker open for '{tool_name}', retry after {retry_after:.0f}s")


class FallbackError(AgentError):
    """所有降级步骤都失败"""
    def __init__(self, tool_name: str, errors: list[str] | None = None):
        self.tool_name = tool_name
        self.errors = errors or []
        super().__init__(f"All fallbacks exhausted for '{tool_name}': {len(self.errors)} failures")


class TimeoutError(AgentError):
    """操作超时"""
    def __init__(self, operation: str, timeout_s: float = 0.0):
        self.operation = operation
        self.timeout_s = timeout_s
        super().__init__(f"Operation '{operation}' timed out after {timeout_s:.1f}s")


class RateLimitError(AgentError):
    """速率限制"""
    def __init__(self, service: str, retry_after: float = 0.0):
        self.service = service
        self.retry_after = retry_after
        super().__init__(f"Rate limited by '{service}', retry after {retry_after:.0f}s")
