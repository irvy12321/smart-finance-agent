"""
Metrics collectors for RAG and LLM operations

These collectors provide context managers and helper functions
for tracking RAG retrieval and LLM call metrics.
"""

import time
from contextlib import contextmanager

from app.monitoring.prometheus import (
    llm_errors_total,
    llm_in_progress,
    llm_request_duration_seconds,
    llm_requests_total,
    llm_tokens_total,
    rag_documents_total,
    rag_embed_duration_seconds,
    rag_hits_total,
    rag_retrieve_duration_seconds,
)


class RAGMetricsCollector:
    """Collector for RAG (Retrieval Augmented Generation) metrics"""

    @staticmethod
    @contextmanager
    def track_retrieval():
        """Context manager to track RAG retrieval duration"""
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            rag_retrieve_duration_seconds.observe(duration)

    @staticmethod
    @contextmanager
    def track_embedding():
        """Context manager to track embedding duration"""
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            rag_embed_duration_seconds.observe(duration)

    @staticmethod
    def record_hits(count: int) -> None:
        """Record number of retrieval hits"""
        if count > 0:
            rag_hits_total.inc(count)

    @staticmethod
    def set_documents(count: int) -> None:
        """Set current document count in vector store"""
        rag_documents_total.set(count)


class LLMMetricsCollector:
    """Collector for LLM (Large Language Model) call metrics"""

    @staticmethod
    @contextmanager
    def track_request(model: str):
        """
        Context manager to track LLM request metrics.

        Args:
            model: Model name (e.g., "openai/gpt-4", "deepseek-chat")
        """
        llm_requests_total.labels(model=model).inc()
        llm_in_progress.labels(model=model).inc()

        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            llm_request_duration_seconds.labels(model=model).observe(duration)
            llm_in_progress.labels(model=model).dec()

    @staticmethod
    def record_error(model: str, error_type: str) -> None:
        """Record LLM call error"""
        llm_errors_total.labels(model=model, error_type=error_type).inc()

    @staticmethod
    def record_tokens(
        model: str, prompt_tokens: int, completion_tokens: int, total_tokens: int
    ) -> None:
        """Record token consumption"""
        llm_tokens_total.labels(model=model, type="prompt").inc(prompt_tokens)
        llm_tokens_total.labels(model=model, type="completion").inc(completion_tokens)
        llm_tokens_total.labels(model=model, type="total").inc(total_tokens)
