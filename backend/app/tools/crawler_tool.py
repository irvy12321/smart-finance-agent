import re
import aiohttp
from bs4 import BeautifulSoup

from app.tools.base_tool import BaseTool, ToolResult
from app.infrastructure.config import get_crawler_config
from app.utils.logger import get_logger
from app.utils.exceptions import CrawlerError

logger = get_logger("crawler_tool")


class CrawlerTool(BaseTool):
    name = "crawler"
    description = "Fetches and extracts text content from a given URL"

    def __init__(self):
        self.config = get_crawler_config()

    async def execute(self, **kwargs) -> ToolResult:
        url = kwargs.get("url", "")
        if not url:
            return ToolResult(success=False, error="No URL provided", tool_name=self.name)

        try:
            content = await self._fetch(url)
            cleaned = self._clean_text(content)
            if len(cleaned) > self.config.max_content_length:
                cleaned = cleaned[: self.config.max_content_length] + "..."

            logger.info(f"Fetched {len(cleaned)} chars from {url}")
            return ToolResult(
                success=True,
                data={"url": url, "content": cleaned, "length": len(cleaned)},
                tool_name=self.name,
            )
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                logger.warning(f"URL not found (404): {url} - returning fallback message")
                return ToolResult(
                    success=True,
                    data={"url": url, "content": f"[Content unavailable: page not found at {url}]", "length": 0},
                    tool_name=self.name,
                )
            logger.error(f"Crawler failed for {url}: {e}")
            return ToolResult(success=False, error=str(e), tool_name=self.name)
        except Exception as e:
            logger.error(f"Crawler failed for {url}: {e}")
            return ToolResult(success=False, error=str(e), tool_name=self.name)

    async def _fetch(self, url: str) -> str:
        headers = {"User-Agent": self.config.user_agent}
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as resp:
                resp.raise_for_status()
                return await resp.text()

    @staticmethod
    def _clean_text(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    async def fallback_execute(self, **kwargs) -> ToolResult:
        """crawler 降级: 返回提示消息"""
        url = kwargs.get("url", "unknown")
        logger.warning(f"Crawler fallback for: {url}")
        return ToolResult(
            success=True,
            data={"url": url, "content": f"[Fallback] Unable to fetch content from {url}", "length": 0},
            tool_name=self.name,
        )
