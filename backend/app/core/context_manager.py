"""
Context 管理器 - 对话历史压缩 (滑动窗口 + 截断式摘要)
- 最近 keep_recent 条消息原样保留
- 更早的消息压缩为一条 system 摘要 (每条截取头部片段, 总长受限)
- 单条超长消息截断到 max_message_chars
确定性纯文本操作, 不调 LLM。
"""

from app.utils.logger import get_logger

logger = get_logger("context_manager")


class ContextManager:
    def __init__(
        self,
        keep_recent: int = 6,
        max_message_chars: int = 2000,
        summary_max_chars: int = 1200,
    ):
        self.keep_recent = keep_recent
        self.max_message_chars = max_message_chars
        self.summary_max_chars = summary_max_chars

    def _truncate(self, text: str) -> str:
        if len(text) <= self.max_message_chars:
            return text
        return text[: self.max_message_chars] + "...[truncated]"

    def compress_history(self, messages: list[dict]) -> list[dict]:
        """压缩对话历史: 早期消息折叠为摘要 + 最近消息滑动窗口"""
        if len(messages) <= self.keep_recent:
            return [
                {**m, "content": self._truncate(m.get("content", ""))} for m in messages
            ]

        older = messages[: -self.keep_recent]
        recent = messages[-self.keep_recent :]

        snippets = []
        total = 0
        for m in older:
            snippet = f"[{m.get('role', '?')}] {m.get('content', '')[:150]}"
            if total + len(snippet) > self.summary_max_chars:
                break
            snippets.append(snippet)
            total += len(snippet)

        compressed: list[dict] = []
        if snippets:
            compressed.append(
                {
                    "role": "system",
                    "content": "[Earlier conversation summary]\n" + "\n".join(snippets),
                }
            )
        compressed.extend(
            {**m, "content": self._truncate(m.get("content", ""))} for m in recent
        )
        logger.debug(
            f"Compressed history: {len(messages)} msgs -> {len(compressed)} "
            f"({len(older)} folded)"
        )
        return compressed
