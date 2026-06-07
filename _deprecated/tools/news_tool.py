import aiohttp
from tools.base_tool import BaseTool, ToolResult
from utils.logger import get_logger

logger = get_logger("news_tool")


class NewsTool(BaseTool):
    name = "news_search"
    description = "Searches for recent news articles via a public news API"

    NEWS_API_URL = "https://newsapi.org/v2/everything"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        if not query:
            return ToolResult(success=False, error="No query provided", tool_name=self.name)

        if not self.api_key:
            return await self._fallback(query)

        try:
            return await self._search_newsapi(query)
        except Exception as e:
            logger.warning(f"NewsAPI failed: {e}, using fallback")
            return await self._fallback(query)

    async def _search_newsapi(self, query: str) -> ToolResult:
        params = {"q": query, "language": "en", "sortBy": "publishedAt", "pageSize": 5, "apiKey": self.api_key}
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(self.NEWS_API_URL, params=params) as resp:
                data = await resp.json()
                articles = data.get("articles", [])
                results = [
                    {"title": a.get("title", ""), "description": a.get("description", ""), "url": a.get("url", "")}
                    for a in articles
                ]
                return ToolResult(success=True, data=results, tool_name=self.name)

    async def _fallback(self, query: str) -> ToolResult:
        results = [
            {"title": f"[Simulated] Latest news about: {query}", "description": "This is simulated news data for MVP. Configure NEWS_API_KEY for real results.", "url": ""},
        ]
        return ToolResult(success=True, data=results, tool_name=self.name)

    async def fallback_execute(self, **kwargs) -> ToolResult:
        """news 降级: 使用内部 fallback"""
        query = kwargs.get("query", "")
        logger.warning(f"News fallback for: {query}")
        return await self._fallback(query)
