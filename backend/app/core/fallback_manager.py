"""
Fallback Manager - 降级链管理器
定义每个 tool/agent 的降级策略
所有失败必须记录 trace_id + log
"""

from typing import Any

from app.tools.base_tool import ToolResult
from app.utils.logger import get_logger

logger = get_logger("fallback_manager")


class FallbackManager:
    """
    降级链管理器

    降级链:
    crawler  → news_search → rag_retrieve → 静态消息
    news     → rag_retrieve → 静态消息
    rag      → llm_summary → 静态消息
    llm      → low_cost_retry → 静态消息
    reasoner → basic_analysis
    report   → plain_text_summary
    """

    def __init__(self, tool_registry=None, llm_client=None, router=None):
        self.registry = tool_registry
        self.llm = llm_client
        self.router = router

    async def execute_with_fallback(
        self,
        tool_name: str,
        params: dict[str, Any],
        trace_id: str = "",
    ) -> tuple[ToolResult, str]:
        """
        执行工具，失败时沿降级链尝试

        Returns:
            (ToolResult, used_tool_name) - 结果和实际使用的工具名
        """
        chain = self._get_fallback_chain(tool_name)
        errors = []

        for step_tool, step_fn in chain:
            try:
                result = await step_fn(params)
                if result.success:
                    if step_tool != tool_name:
                        logger.info(
                            f"[trace:{trace_id}] Fallback: {tool_name} -> {step_tool} succeeded"
                        )
                    return result, step_tool
                else:
                    errors.append(f"{step_tool}: {result.error}")
            except Exception as e:
                errors.append(f"{step_tool}: {e}")
                logger.warning(
                    f"[trace:{trace_id}] Fallback step '{step_tool}' failed: {e}"
                )

        logger.error(
            f"[trace:{trace_id}] All fallbacks exhausted for '{tool_name}': {errors}"
        )
        return ToolResult(
            success=False,
            error=f"All fallbacks exhausted for '{tool_name}'",
            tool_name=tool_name,
        ), tool_name

    def _get_fallback_chain(self, tool_name: str) -> list[tuple[str, Any]]:
        """获取工具的降级链"""
        chains = {
            "crawler": self._chain_crawler,
            "news_search": self._chain_news,
            "rag_retrieve": self._chain_rag,
            "llm_synthesize": self._chain_llm,
        }
        return chains.get(tool_name, [(tool_name, self._direct_execute(tool_name))])

    def _direct_execute(self, tool_name: str):
        """直接执行工具"""

        async def _exec(params):
            tool = self.registry.get(tool_name) if self.registry else None
            if tool:
                return await tool.execute(**params)
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' not found",
                tool_name=tool_name,
            )

        return _exec

    @property
    def _chain_crawler(self) -> list[tuple[str, Any]]:
        """crawler → news_search → rag_retrieve → 静态消息"""
        return [
            ("crawler", self._direct_execute("crawler")),
            ("news_search", self._fallback_news_from_crawler),
            ("rag_retrieve", self._fallback_rag_generic),
            ("static", self._fallback_static_crawler),
        ]

    @property
    def _chain_news(self) -> list[tuple[str, Any]]:
        """news_search → rag_retrieve → 静态消息"""
        return [
            ("news_search", self._direct_execute("news_search")),
            ("rag_retrieve", self._fallback_rag_generic),
            ("static", self._fallback_static_news),
        ]

    @property
    def _chain_rag(self) -> list[tuple[str, Any]]:
        """rag_retrieve → llm_summary → 静态消息"""
        return [
            ("rag_retrieve", self._direct_execute("rag_retrieve")),
            ("llm_summary", self._fallback_llm_summary),
            ("static", self._fallback_static_rag),
        ]

    @property
    def _chain_llm(self) -> list[tuple[str, Any]]:
        """llm_synthesize → low_cost_retry → 静态消息"""
        return [
            ("llm_synthesize", self._direct_execute("llm_synthesize")),
            ("llm_low_cost", self._fallback_llm_low_cost),
            ("static", self._fallback_static_llm),
        ]

    # === Fallback step implementations ===

    async def _fallback_news_from_crawler(self, params: dict) -> ToolResult:
        """crawler 失败 → 用 news_search 搜索相同主题"""
        tool = self.registry.get("news_search") if self.registry else None
        if not tool:
            return ToolResult(
                success=False,
                error="news_search not available",
                tool_name="news_search",
            )
        query = params.get("query", params.get("url", ""))
        return await tool.execute(query=query)

    async def _fallback_rag_generic(self, params: dict) -> ToolResult:
        """通用 RAG 降级"""
        tool = self.registry.get("rag_retrieve") if self.registry else None
        if not tool:
            return ToolResult(
                success=False,
                error="rag_retrieve not available",
                tool_name="rag_retrieve",
            )
        query = params.get("query", "")
        return await tool.execute(query=query)

    async def _fallback_llm_summary(self, params: dict) -> ToolResult:
        """RAG 失败 → 用 LLM 生成摘要"""
        query = params.get("query", "")
        if not self.router and not self.llm:
            return ToolResult(
                success=False, error="No LLM available", tool_name="llm_summary"
            )
        try:
            prompt = (
                f"Based on your knowledge, provide a brief summary about: {query}\n"
                "If you don't have specific information, say so."
            )
            if self.router:
                answer = await self.router.complete(
                    "executor", prompt=prompt, max_tokens=512
                )
            else:
                answer = await self.llm.complete(
                    prompt=prompt, temperature=0.3, max_tokens=512
                )
            return ToolResult(success=True, data=answer, tool_name="llm_summary")
        except Exception as e:
            return ToolResult(success=False, error=str(e), tool_name="llm_summary")

    async def _fallback_llm_low_cost(self, params: dict) -> ToolResult:
        """LLM 失败 → 低开销模型重试"""
        prompt = params.get("prompt", "")
        if not self.router and not self.llm:
            return ToolResult(
                success=False, error="No LLM available", tool_name="llm_low_cost"
            )
        try:
            if self.router:
                answer = await self.router.complete(
                    "executor",
                    prompt=prompt,
                    max_tokens=1024,
                )
            else:
                answer = await self.llm.complete(
                    prompt=prompt,
                    temperature=0.2,
                    max_tokens=1024,
                )
            return ToolResult(success=True, data=answer, tool_name="llm_low_cost")
        except Exception as e:
            return ToolResult(success=False, error=str(e), tool_name="llm_low_cost")

    async def _fallback_static_crawler(self, params: dict) -> ToolResult:
        """crawler 最终降级: 返回静态消息"""
        url = params.get("url", "unknown")
        return ToolResult(
            success=True,
            data={
                "url": url,
                "content": f"[Fallback] Unable to fetch content from {url}",
                "length": 0,
            },
            tool_name="static",
        )

    async def _fallback_static_news(self, params: dict) -> ToolResult:
        """news 最终降级: 返回静态消息"""
        query = params.get("query", "unknown")
        return ToolResult(
            success=True,
            data=[
                {
                    "title": f"[Fallback] No news available for: {query}",
                    "description": "News service unavailable",
                    "url": "",
                }
            ],
            tool_name="static",
        )

    async def _fallback_static_rag(self, params: dict) -> ToolResult:
        """RAG 最终降级: 返回静态消息"""
        query = params.get("query", "unknown")
        return ToolResult(
            success=True,
            data={
                "results": [],
                "message": f"[Fallback] No local knowledge for: {query}",
            },
            tool_name="static",
        )

    async def _fallback_static_llm(self, params: dict) -> ToolResult:
        """LLM 最终降级: 返回静态消息"""
        return ToolResult(
            success=True,
            data="[Fallback] LLM service temporarily unavailable. Please try again later.",
            tool_name="static",
        )

    # === Agent-level fallbacks (for orchestrator) ===

    async def fallback_reasoner(self, context: str, question: str) -> dict:
        """reasoner 失败 → 基础分析"""
        logger.warning("Using reasoner fallback: basic analysis")
        return {
            "reasoning": f"Basic analysis for: {question[:100]}. Context available: {len(context)} chars.",
            "critique": "Fallback analysis - detailed reasoning unavailable",
            "confidence": 0.3,
            "key_insights": [f"Query: {question[:80]}"],
            "charts": [],
        }

    async def fallback_report(self, query: str, answer: str) -> dict:
        """report 失败 → 纯文本摘要"""
        logger.warning("Using report fallback: plain text summary")
        return {
            "title": f"Research: {query[:50]}",
            "summary": answer[:200] if answer else "No results available",
            "key_findings": [answer[:200]] if answer else ["No findings"],
            "risk_factors": [],
            "market_trends": [],
            "recommendations": ["Retry for detailed analysis"],
        }
