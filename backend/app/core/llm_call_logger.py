"""
LLM 调用日志 - prompt/response 脱敏后持久化到 SQLite (llm_call_logs 表)

- LLM_CALL_LOG_ENABLED (默认 true) 控制开关
- LLM_CALL_LOG_MAX_LEN (默认 4000) 控制单字段截断长度
- sanitize(): 脱敏 API key / Bearer token / 常见 secret 赋值
- log_llm_call(): 永不抛异常, 日志失败不影响主流程
"""

import json
import os

from app.utils.logger import get_logger
from app.utils.redaction import redact_sensitive_text

logger = get_logger("llm_call_logger")


def _enabled() -> bool:
    return os.getenv("LLM_CALL_LOG_ENABLED", "true").lower() in ("1", "true", "yes")


def _max_len() -> int:
    try:
        return int(os.getenv("LLM_CALL_LOG_MAX_LEN", "4000"))
    except ValueError:
        return 4000


def sanitize(text: str) -> str:
    """脱敏 + 截断文本, 用于持久化前处理"""
    if not text:
        return ""
    text = redact_sensitive_text(text)
    max_len = _max_len()
    if len(text) > max_len:
        text = text[:max_len] + f"...[truncated {len(text) - max_len} chars]"
    return text


def _serialize_messages(messages: list[dict]) -> str:
    parts = [f"[{m.get('role', '?')}] {m.get('content', '')}" for m in messages]
    return "\n".join(parts)


def log_llm_call(
    agent_name: str,
    model: str,
    messages: list[dict],
    response: str = "",
    usage: dict | None = None,
    latency_ms: float = 0.0,
    trace_id: str = "",
    status: str = "ok",
    error: str = "",
) -> None:
    """持久化一次 LLM 调用 (脱敏后)。任何异常只记 warning, 不向上传播。"""
    if not _enabled():
        return
    try:
        from app import storage

        usage = usage or {}
        storage.insert_llm_call_log(
            trace_id=trace_id,
            agent_name=agent_name,
            model=model,
            prompt=sanitize(_serialize_messages(messages)),
            response=sanitize(response),
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            total_tokens=int(usage.get("total_tokens", 0)),
            latency_ms=float(latency_ms),
            status=status,
            error=sanitize(error),
        )
    except Exception as e:
        logger.warning(f"Failed to persist LLM call log: {e}")


def get_llm_call_logs(trace_id: str | None = None, limit: int = 100) -> list[dict]:
    """查询 LLM 调用日志 (按时间倒序)"""
    from app import storage

    return storage.list_llm_call_logs(trace_id=trace_id, limit=limit)


def dump_llm_call_logs_json(trace_id: str | None = None, limit: int = 100) -> str:
    return json.dumps(
        get_llm_call_logs(trace_id=trace_id, limit=limit), ensure_ascii=False
    )
