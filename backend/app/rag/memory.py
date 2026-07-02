"""
对话记忆管理 - 三层记忆
- 短期记忆: 滑动窗口 (最近N轮), 溢出部分折叠进滚动摘要
- 长期记忆: LongTermMemory (FAISS 向量存储, 独立持久化, 语义检索)
- 用户画像: app.core.memory (SQLite user_profiles 表)
"""

from collections import deque
from dataclasses import dataclass, field

from app.infrastructure.config import get_memory_config
from app.utils.logger import get_logger

logger = get_logger("memory")


@dataclass
class MemoryItem:
    role: str  # "user" | "assistant" | "system" | "task_result"
    content: str
    metadata: dict = field(default_factory=dict)


class ConversationMemory:
    """
    对话记忆管理器
    - short_term: 滑动窗口, 保留最近 N 轮对话; 溢出折叠进 rolling summary
    - long_term: LongTermMemory 向量存储, 支持语义检索
    """

    def __init__(self, max_short_term: int | None = None, long_term=None):
        config = get_memory_config()
        self._max_items = (max_short_term or config.short_term_max_turns) * 2
        self._summary_max_chars = config.summary_max_chars
        self.short_term: deque[MemoryItem] = deque()
        self.summary = ""  # 滚动摘要: 滑出窗口的对话压缩残留
        if long_term is None:
            from app.core.memory import LongTermMemory

            long_term = LongTermMemory.get_instance()
        self.long_term = long_term
        self._turn_count = 0

    def _append(self, item: MemoryItem):
        """入窗; 满则将最旧条目折叠进滚动摘要"""
        while len(self.short_term) >= self._max_items:
            evicted = self.short_term.popleft()
            snippet = f"[{evicted.role}] {evicted.content[:120]}"
            self.summary = (self.summary + "\n" + snippet).strip()
            if len(self.summary) > self._summary_max_chars:
                self.summary = self.summary[-self._summary_max_chars :]
        self.short_term.append(item)

    def add_user_message(self, content: str):
        """添加用户消息到短期记忆"""
        self._append(MemoryItem(role="user", content=content))
        self._turn_count += 1

    def add_assistant_message(self, content: str, metadata: dict | None = None):
        """添加助手消息到短期记忆"""
        self._append(
            MemoryItem(role="assistant", content=content, metadata=metadata or {})
        )

    def add_task_result(self, task_id: str, tool_name: str, content: str):
        """添加任务结果到短期记忆"""
        self._append(
            MemoryItem(
                role="task_result",
                content=content,
                metadata={"task_id": task_id, "tool": tool_name},
            )
        )

    def archive_to_long_term(self, text: str, metadata: dict | None = None):
        """将重要内容归档到长期记忆 (向量存储)"""
        self.long_term.store_memory(text, metadata)

    def get_short_term_context(self, max_tokens: int = 2000) -> str:
        """获取短期记忆上下文 (滚动摘要 + 滑动窗口, 用于 LLM prompt)"""
        lines = []
        total_len = 0
        for item in reversed(self.short_term):
            line = f"[{item.role}] {item.content}"
            if total_len + len(line) > max_tokens:
                break
            lines.insert(0, line)
            total_len += len(line)
        if self.summary and total_len + len(self.summary) <= max_tokens:
            lines.insert(0, f"[earlier summary]\n{self.summary}")
        return "\n".join(lines)

    def retrieve_long_term(self, query: str, top_k: int = 3) -> list[dict]:
        """从长期记忆中语义检索"""
        return self.long_term.recall(query, top_k=top_k)

    def get_combined_context(
        self, query: str, short_tokens: int = 1500, long_term_top_k: int = 3
    ) -> str:
        """获取混合上下文: 短期记忆 + 长期记忆检索结果"""
        parts = []

        # 短期记忆
        short_ctx = self.get_short_term_context(max_tokens=short_tokens)
        if short_ctx:
            parts.append(f"=== 最近对话 ===\n{short_ctx}")

        # 长期记忆语义检索
        long_results = self.retrieve_long_term(query, top_k=long_term_top_k)
        if long_results:
            long_parts = [r["text"] for r in long_results]
            parts.append("=== 相关知识 ===\n" + "\n---\n".join(long_parts))

        return "\n\n".join(parts) if parts else ""

    @property
    def turn_count(self) -> int:
        return self._turn_count

    def clear_short_term(self):
        self.short_term.clear()
        self.summary = ""
        logger.info("Short-term memory cleared")

    def clear_all(self):
        self.short_term.clear()
        self.summary = ""
        self._turn_count = 0
        logger.info("All memory cleared (long-term store retained on disk)")
