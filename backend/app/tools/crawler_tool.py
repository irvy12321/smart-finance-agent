import re
from urllib.parse import urlparse

import aiohttp
from bs4 import BeautifulSoup

from app.infrastructure.config import get_crawler_config
from app.tools.base_tool import BaseTool, ToolResult
from app.tools.cache import get_cache
from app.utils.logger import get_logger

logger = get_logger("crawler_tool")

# 缓存 TTL 配置
CRAWLER_CACHE_TTL = 300  # 爬虫缓存 300 秒

# Blocked IP ranges (SSRF protection)
_BLOCKED_HOSTS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "169.254.169.254",  # cloud metadata
    "metadata.google.internal",
}
_BLOCKED_CIDRS = [
    ("10.0.0.0", 8),
    ("172.16.0.0", 12),
    ("192.168.0.0", 16),
    ("169.254.0.0", 16),
]


def _ip_to_int(ip: str) -> int:
    parts = ip.split(".")
    return (
        (int(parts[0]) << 24)
        | (int(parts[1]) << 16)
        | (int(parts[2]) << 8)
        | int(parts[3])
    )


def _is_private_ip(host: str) -> bool:
    """Check if a hostname resolves to a private/reserved IP."""
    import ipaddress

    try:
        addr = ipaddress.ip_address(host)
        return (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
        )
    except ValueError:
        return False


def _validate_url(url: str) -> str | None:
    """Validate URL for SSRF safety. Returns error message or None if safe."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return f"Blocked scheme: {parsed.scheme}. Only http/https allowed."
    hostname = parsed.hostname or ""
    if not hostname:
        return "No hostname in URL."
    if hostname.lower() in _BLOCKED_HOSTS:
        return f"Blocked host: {hostname}"
    if _is_private_ip(hostname):
        return f"Blocked private/reserved IP: {hostname}"
    return None


class CrawlerTool(BaseTool):
    name = "crawler"
    description = "Fetches and extracts text content from a given URL"

    def __init__(self):
        self.config = get_crawler_config()
        self._cache = get_cache()

    async def execute(self, **kwargs) -> ToolResult:
        url = kwargs.get("url", "")
        if not url:
            return ToolResult(
                success=False, error="No URL provided", tool_name=self.name
            )

        # SSRF protection
        ssrf_error = _validate_url(url)
        if ssrf_error:
            logger.warning(f"SSRF blocked for URL {url}: {ssrf_error}")
            return ToolResult(success=False, error=ssrf_error, tool_name=self.name)

        # 检查缓存
        cache_key = f"crawler:{url}"
        hit, cached_result = self._cache.get(cache_key)
        if hit:
            logger.debug(f"Crawler cache hit: {url}")
            return cached_result

        try:
            content = await self._fetch(url)
            cleaned = self._clean_text(content)
            if len(cleaned) > self.config.max_content_length:
                cleaned = cleaned[: self.config.max_content_length] + "..."

            logger.info(f"Fetched {len(cleaned)} chars from {url}")
            result = ToolResult(
                success=True,
                data={"url": url, "content": cleaned, "length": len(cleaned)},
                tool_name=self.name,
            )

            # 存入缓存
            self._cache.set(cache_key, result, ttl=CRAWLER_CACHE_TTL)

            return result
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                logger.warning(
                    f"URL not found (404): {url} - returning fallback message"
                )
                return ToolResult(
                    success=True,
                    data={
                        "url": url,
                        "content": f"[Content unavailable: page not found at {url}]",
                        "length": 0,
                    },
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
        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.get(url, headers=headers) as resp,
        ):
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
            data={
                "url": url,
                "content": f"[Fallback] Unable to fetch content from {url}",
                "length": 0,
            },
            tool_name=self.name,
        )
