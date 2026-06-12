"""
Monitoring module - Prometheus metrics collection
"""
from app.monitoring.prometheus import (
    # HTTP metrics
    http_requests_total,
    http_request_duration_seconds,
    http_errors_total,
    # Agent metrics
    agent_stage_duration_seconds,
    agent_calls_total,
    agent_errors_total,
    agent_tokens_total,
    # Tool metrics
    tool_calls_total,
    tool_call_duration_seconds,
    tool_errors_total,
    tool_circuit_breaker_state,
    # RAG metrics
    rag_retrieve_duration_seconds,
    rag_hits_total,
    rag_documents_total,
    # LLM metrics
    llm_requests_total,
    llm_request_duration_seconds,
    llm_errors_total,
    llm_tokens_total,
    # System metrics
    app_info,
)

__all__ = [
    # HTTP
    "http_requests_total",
    "http_request_duration_seconds",
    "http_errors_total",
    # Agent
    "agent_stage_duration_seconds",
    "agent_calls_total",
    "agent_errors_total",
    "agent_tokens_total",
    # Tool
    "tool_calls_total",
    "tool_call_duration_seconds",
    "tool_errors_total",
    "tool_circuit_breaker_state",
    # RAG
    "rag_retrieve_duration_seconds",
    "rag_hits_total",
    "rag_documents_total",
    # LLM
    "llm_requests_total",
    "llm_request_duration_seconds",
    "llm_errors_total",
    "llm_tokens_total",
    # System
    "app_info",
]
