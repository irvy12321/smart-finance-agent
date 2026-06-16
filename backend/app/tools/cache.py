"""
缓存模块 - 统一缓存接口

支持:
- 内存 TTL Cache (默认)
- Redis TTL Cache (可选)

使用方式:
    from app.tools.cache import cached, get_cache_stats

    @cached(ttl=60)
    async def fetch_stock_price(symbol: str):
        ...
"""

import hashlib
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.utils.logger import get_logger

logger = get_logger("cache")


@dataclass
class CacheEntry:
    """缓存条目"""

    key: str
    value: Any
    created_at: float
    ttl: int  # 秒
    hits: int = 0

    @property
    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at


class MemoryTTLCache:
    """
    内存 TTL Cache - 线程安全，LRU 淘汰

    特点:
    - 基于 TTL 自动过期
    - LRU 淘汰策略
    - 线程安全
    - 命中率统计
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.Lock()

        # 统计
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> tuple[bool, Any]:
        """
        获取缓存值

        Returns:
            (hit: bool, value: Any)
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                return False, None

            if entry.is_expired:
                del self._cache[key]
                self._misses += 1
                return False, None

            # 更新访问顺序和命中次数
            entry.hits += 1
            self._cache.move_to_end(key)
            self._hits += 1
            return True, entry.value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """设置缓存值"""
        with self._lock:
            # 如果已存在，先删除
            if key in self._cache:
                del self._cache[key]

            # 检查容量，淘汰最旧的
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)

            self._cache[key] = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                ttl=ttl or self._default_ttl,
            )

    def delete(self, key: str) -> bool:
        """删除缓存条目"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> int:
        """清空缓存"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def cleanup_expired(self) -> int:
        """清理过期条目"""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() if entry.is_expired
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)

    @property
    def size(self) -> int:
        """当前缓存大小"""
        return len(self._cache)

    @property
    def stats(self) -> dict:
        """缓存统计"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0

        return {
            "size": self.size,
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
            "total_requests": total,
        }


# 全局缓存实例
_global_cache: MemoryTTLCache | None = None


def get_cache(max_size: int = 1000, default_ttl: int = 300) -> MemoryTTLCache:
    """获取全局缓存实例"""
    global _global_cache
    if _global_cache is None:
        _global_cache = MemoryTTLCache(max_size=max_size, default_ttl=default_ttl)
    return _global_cache


def get_cache_stats() -> dict:
    """获取缓存统计"""
    return get_cache().stats


def make_cache_key(*args, **kwargs) -> str:
    """生成缓存键"""
    key_parts = [str(a) for a in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    key_str = "|".join(key_parts)
    return hashlib.md5(key_str.encode()).hexdigest()


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    缓存装饰器

    Usage:
        @cached(ttl=60, key_prefix="stock")
        async def get_stock_price(symbol: str):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache()

            # 生成缓存键
            cache_key = (
                f"{key_prefix}:{make_cache_key(*args, **kwargs)}"
                if key_prefix
                else make_cache_key(*args, **kwargs)
            )

            # 尝试从缓存获取
            hit, value = cache.get(cache_key)
            if hit:
                logger.debug(f"Cache hit: {cache_key}")
                return value

            # 缓存未命中，执行函数
            logger.debug(f"Cache miss: {cache_key}")
            result = await func(*args, **kwargs)

            # 存入缓存
            cache.set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator


import functools  # noqa: E402
