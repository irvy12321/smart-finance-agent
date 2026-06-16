"""
对话记忆管理 - 短期工作记忆 + 长期知识库
- 短期记忆: 最近N轮对话，FIFO淘汰
- 长期记忆: 向量化存储，语义检索
"""

from collections import deque
from dataclasses import dataclass, field

from app.rag.retriever import Retriever
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
    - short_term: 滑动窗口，保留最近 N 轮对话
    - long_term: FAISS 向量存储，支持语义检索
    """

    def __init__(self, max_short_term: int = 10, retriever: Retriever | None = None):
        self.short_term: deque[MemoryItem] = deque(maxlen=max_short_term * 2)
        self.long_term = retriever or Retriever()
        self._turn_count = 0

    def add_user_message(self, content: str):
        """添加用户消息到短期记忆"""
        self.short_term.append(MemoryItem(role="user", content=content))
        self._turn_count += 1

    def add_assistant_message(self, content: str, metadata: dict | None = None):
        """添加助手消息到短期记忆"""
        self.short_term.append(
            MemoryItem(role="assistant", content=content, metadata=metadata or {})
        )

    def add_task_result(self, task_id: str, tool_name: str, content: str):
        """添加任务结果到短期记忆"""
        self.short_term.append(
            MemoryItem(
                role="task_result",
                content=content,
                metadata={"task_id": task_id, "tool": tool_name},
            )
        )

    def archive_to_long_term(self, text: str, metadata: dict | None = None):
        """将重要内容归档到长期记忆 (向量存储)"""
        self.long_term.add_document(text, metadata)
        logger.info(f"Archived to long-term memory: {text[:50]}...")

    def get_short_term_context(self, max_tokens: int = 2000) -> str:
        """获取短期记忆上下文 (用于 LLM prompt)"""
        lines = []
        total_len = 0
        for item in reversed(self.short_term):
            line = f"[{item.role}] {item.content}"
            if total_len + len(line) > max_tokens:
                break
            lines.insert(0, line)
            total_len += len(line)
        return "\n".join(lines)

    def retrieve_long_term(self, query: str, top_k: int = 3) -> list[dict]:
        """从长期记忆中语义检索"""
        return self.long_term.retrieve(query, top_k=top_k)

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
        logger.info("Short-term memory cleared")

    def clear_all(self):
        self.short_term.clear()
        self.long_term = Retriever()
        self._turn_count = 0
        logger.info("All memory cleared")
