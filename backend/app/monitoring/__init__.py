"""
Monitoring module - Prometheus metrics collection
"""

from app.monitoring.prometheus import (
    agent_calls_total,
    agent_errors_total,
    # Agent metrics
    agent_stage_duration_seconds,
    agent_tokens_total,
    # System metrics
    app_info,
    http_errors_total,
    http_request_duration_seconds,
    # HTTP metrics
    http_requests_total,
    llm_errors_total,
    llm_request_duration_seconds,
    # LLM metrics
    llm_requests_total,
    llm_tokens_total,
    rag_documents_total,
    rag_hits_total,
    # RAG metrics
    rag_retrieve_duration_seconds,
    tool_call_duration_seconds,
    # Tool metrics
    tool_calls_total,
    tool_circuit_breaker_state,
    tool_errors_total,
)

__all__ = [
    "agent_calls_total",
    "agent_errors_total",
    # Agent
    "agent_stage_duration_seconds",
    "agent_tokens_total",
    # System
    "app_info",
    "http_errors_total",
    "http_request_duration_seconds",
    # HTTP
    "http_requests_total",
    "llm_errors_total",
    "llm_request_duration_seconds",
    # LLM
    "llm_requests_total",
    "llm_tokens_total",
    "rag_documents_total",
    "rag_hits_total",
    # RAG
    "rag_retrieve_duration_seconds",
    "tool_call_duration_seconds",
    # Tool
    "tool_calls_total",
    "tool_circuit_breaker_state",
    "tool_errors_total",
]
