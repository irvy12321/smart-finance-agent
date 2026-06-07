"""
增强日志模块 - 结构化输出 + trace_id 关联 + 并发安全
"""
import logging
import sys
import json
import threading
from datetime import datetime


class StructuredFormatter(logging.Formatter):
    """结构化 JSON 日志格式"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # 提取额外字段
        if hasattr(record, "trace_id"):
            log_entry["trace_id"] = record.trace_id
        if hasattr(record, "agent_name"):
            log_entry["agent"] = record.agent_name
        if hasattr(record, "task_id"):
            log_entry["task_id"] = record.task_id
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        if hasattr(record, "tokens"):
            log_entry["tokens"] = record.tokens
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """文本日志格式 (开发用)"""

    def format(self, record: logging.LogRecord) -> str:
        trace_part = ""
        if hasattr(record, "trace_id"):
            trace_part = f" [trace:{record.trace_id}]"
        agent_part = ""
        if hasattr(record, "agent_name"):
            agent_part = f" [{record.agent_name}]"

        return (
            f"[{datetime.fromtimestamp(record.created).strftime('%H:%M:%S')}] "
            f"{record.levelname:5s} [{record.name}]{trace_part}{agent_part} "
            f"{record.getMessage()}"
        )


# 全局配置
_log_format = "text"  # "text" or "json"
_configured = False


def configure_logging(log_format: str = "text", level: int = logging.DEBUG):
    """全局日志配置"""
    global _log_format, _configured
    _log_format = log_format
    _configured = True

    root = logging.getLogger()
    root.setLevel(level)

    # 清除现有 handler
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    if log_format == "json":
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(TextFormatter())

    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """获取 logger，自动配置"""
    if not _configured:
        configure_logging()
    return logging.getLogger(name)


class LogContext:
    """日志上下文 - 在并发环境中传递 trace_id 等信息"""

    _local = threading.local()

    @classmethod
    def set(cls, **kwargs):
        for k, v in kwargs.items():
            setattr(cls._local, k, v)

    @classmethod
    def get(cls, key: str, default=None):
        return getattr(cls._local, key, default)

    @classmethod
    def clear(cls):
        cls._local.__dict__.clear()

    @classmethod
    def get_extra(cls) -> dict:
        """获取当前上下文的额外字段"""
        return {
            k: v for k, v in cls._local.__dict__.items()
            if not k.startswith("_")
        }


def log_with_context(logger_name: str, level: str, message: str, **extra):
    """带上下文的日志记录"""
    logger = get_logger(logger_name)
    log_func = getattr(logger, level, logger.info)

    # 合并上下文和额外字段
    context = LogContext.get_extra()
    context.update(extra)

    # 创建 LogRecord 并附加额外字段
    record = logger.makeRecord(
        logger.name,
        getattr(logging, level.upper(), logging.INFO),
        "(log)",
        0,
        message,
        (),
        None,
    )
    for k, v in context.items():
        setattr(record, k, v)

    logger.handle(record)
