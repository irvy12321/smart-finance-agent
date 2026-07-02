"""
三层记忆系统
- 短期记忆: 滑动窗口 + 滚动摘要 (rag/memory.ConversationMemory)
- 长期记忆: FAISS 向量存储, 语义检索 (本模块 LongTermMemory,
  复用 rag/vector_store + rag/embed + rag/chunker, 独立持久化目录,
  与 RAG 知识库隔离)
- 用户画像: SQLite user_profiles 表, 确定性规则提取 (不用 LLM)
"""

import json
import re
import threading
from pathlib import Path

from app.infrastructure.config import get_memory_config
from app.rag.chunker import chunk_text
from app.rag.embed import create_embedder
from app.rag.vector_store import VectorStore
from app.utils.logger import get_logger

logger = get_logger("long_term_memory")


def _memory_persist_dir() -> str:
    return str(Path(__file__).parent.parent.parent / "data" / "memory" / "vector_store")


class LongTermMemory:
    """长期记忆: 向量化存储 + 语义召回, 独立于 RAG 知识库"""

    _instance: "LongTermMemory | None" = None

    def __init__(self, persist_dir: str | None = None):
        self._write_lock = threading.Lock()
        config = get_memory_config()
        self.enabled = config.long_term_enabled
        self.top_k = config.long_term_top_k
        self.embedder = create_embedder()
        self.store = VectorStore(
            dim=self.embedder.dim,
            persist_dir=persist_dir or _memory_persist_dir(),
            embedder=self.embedder,
        )
        self.store.load()
        logger.info(
            f"LongTermMemory initialized: enabled={self.enabled}, "
            f"loaded={self.store.size} vectors"
        )

    @classmethod
    def get_instance(cls) -> "LongTermMemory":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def store_memory(self, text: str, metadata: dict | None = None) -> None:
        """归档一条记忆 (切块 → 向量化 → 持久化)。失败只记 warning。"""
        if not self.enabled or not text:
            return
        try:
            chunks = chunk_text(text)
            if not chunks:
                return
            embeddings = self.embedder.embed_batch(chunks)
            with self._write_lock:
                self.store.add(embeddings, chunks, [metadata or {}] * len(chunks))
                self.store.save()
            logger.info(f"Stored long-term memory: {text[:50]}...")
        except Exception as e:
            logger.warning(f"LongTermMemory.store_memory failed: {e}")

    def recall(self, query: str, top_k: int | None = None) -> list[dict]:
        """语义召回相关记忆"""
        if not self.enabled or self.store.size == 0:
            return []
        try:
            query_vec = self.embedder.embed_text(query)
            results = self.store.search(query_vec, top_k=top_k or self.top_k)
            return [r for r in results if r.get("score", 0) > 0]
        except Exception as e:
            logger.warning(f"LongTermMemory.recall failed: {e}")
            return []

    def recall_context(self, query: str, top_k: int | None = None) -> str:
        """召回结果拼接为 prompt 上下文片段"""
        results = self.recall(query, top_k=top_k)
        if not results:
            return ""
        return "\n---\n".join(r["text"] for r in results)


# ── 用户画像 (确定性规则提取, 不用 LLM) ────────────────────────

_TICKER_RE = re.compile(
    r"\b(AAPL|TSLA|GOOGL|MSFT|AMZN|NVDA|META|BABA|JD|BIDU|AMD|INTC|NFLX)\b",
    re.IGNORECASE,
)
_TOPIC_KEYWORDS = {
    "earnings": r"(?i)(earnings|financial report|财报|营收|利润)",
    "price": r"(?i)(price|quote|股价|行情|涨跌)",
    "news": r"(?i)(news|新闻|资讯)",
    "analysis": r"(?i)(analysis|invest|分析|投资|估值)",
}
_MAX_PROFILE_ITEMS = 10


def update_user_profile(user_id: int, message: str, language: str = "en") -> None:
    """从用户消息中确定性提取兴趣信号, 合并到 user_profiles 表。永不抛异常。"""
    if user_id is None or not message:
        return
    config = get_memory_config()
    if not config.user_profile_enabled:
        return
    try:
        from app import storage

        profile = storage.get_user_profile(user_id) or {}
        tickers: list[str] = profile.get("tickers", [])
        for t in _TICKER_RE.findall(message):
            t = t.upper()
            if t not in tickers:
                tickers.append(t)
        topics: list[str] = profile.get("topics", [])
        for topic, pattern in _TOPIC_KEYWORDS.items():
            if re.search(pattern, message) and topic not in topics:
                topics.append(topic)
        profile.update(
            {
                "tickers": tickers[-_MAX_PROFILE_ITEMS:],
                "topics": topics[-_MAX_PROFILE_ITEMS:],
                "language": language,
                "query_count": int(profile.get("query_count", 0)) + 1,
            }
        )
        storage.upsert_user_profile(user_id, profile)
    except Exception as e:
        logger.warning(f"update_user_profile failed: {e}")


def get_user_profile(user_id: int) -> dict:
    try:
        from app import storage

        return storage.get_user_profile(user_id) or {}
    except Exception as e:
        logger.warning(f"get_user_profile failed: {e}")
        return {}


def format_user_profile(profile: dict, language: str = "en") -> str:
    """用户画像 → prompt 注入片段 (空画像返回空串)"""
    if not profile or not (profile.get("tickers") or profile.get("topics")):
        return ""
    tickers = ", ".join(profile.get("tickers", []))
    topics = ", ".join(profile.get("topics", []))
    if language == "zh":
        parts = ["[用户画像]"]
        if tickers:
            parts.append(f"关注标的: {tickers}")
        if topics:
            parts.append(f"关注主题: {topics}")
    else:
        parts = ["[User Profile]"]
        if tickers:
            parts.append(f"Watched tickers: {tickers}")
        if topics:
            parts.append(f"Topics of interest: {topics}")
    return "\n".join(parts)


def profile_to_json(profile: dict) -> str:
    return json.dumps(profile, ensure_ascii=False)
