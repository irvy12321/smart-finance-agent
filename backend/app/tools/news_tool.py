import aiohttp

from app.tools.base_tool import BaseTool, ToolResult
from app.tools.cache import get_cache
from app.utils.logger import get_logger

logger = get_logger("news_tool")

# 缓存 TTL 配置
NEWS_CACHE_TTL = 300  # 新闻缓存 300 秒


class NewsTool(BaseTool):
    name = "news_search"
    description = "Searches for recent news articles via a public news API"

    NEWS_API_URL = "https://newsapi.org/v2/everything"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self._cache = get_cache()

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        if not query:
            return ToolResult(
                success=False, error="No query provided", tool_name=self.name
            )

        # 检查缓存
        cache_key = f"news:{query}"
        hit, cached_result = self._cache.get(cache_key)
        if hit:
            logger.debug(f"News cache hit: {query}")
            return cached_result

        if not self.api_key:
            result = await self._fallback(query)
        else:
            try:
                result = await self._search_newsapi(query)
            except Exception as e:
                logger.warning(f"NewsAPI failed: {e}, using fallback")
                result = await self._fallback(query)

        # 存入缓存
        if result.success:
            self._cache.set(cache_key, result, ttl=NEWS_CACHE_TTL)

        return result

    async def _search_newsapi(self, query: str) -> ToolResult:
        params = {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 5,
            "apiKey": self.api_key,
        }
        timeout = aiohttp.ClientTimeout(total=15)
        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.get(self.NEWS_API_URL, params=params) as resp,
        ):
            data = await resp.json()
            articles = data.get("articles", [])
            results = [
                {
                    "title": a.get("title", ""),
                    "description": a.get("description", ""),
                    "url": a.get("url", ""),
                }
                for a in articles
            ]
            return ToolResult(success=True, data=results, tool_name=self.name)

    async def _fallback(self, query: str) -> ToolResult:
        results = [
            {
                "title": f"[Simulated] Latest news about: {query}",
                "description": "This is simulated news data for MVP. Configure NEWS_API_KEY for real results.",
                "url": "",
            },
        ]
        return ToolResult(success=True, data=results, tool_name=self.name)

    async def fallback_execute(self, **kwargs) -> ToolResult:
        """news 降级: 使用内部 fallback"""
        query = kwargs.get("query", "")
        logger.warning(f"News fallback for: {query}")
        return await self._fallback(query)
