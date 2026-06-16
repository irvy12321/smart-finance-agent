"""
Prometheus metrics definitions for Smart Finance Agent

Metrics categories:
- HTTP: request count, duration, errors
- Agent: stage duration, calls, tokens
- Tool: call count, duration, errors, circuit breaker
- RAG: retrieval duration, hits, documents
- LLM: request count, duration, tokens, errors
"""

from prometheus_client import Counter, Gauge, Histogram, Info

# =============================================================================
# HTTP Metrics
# =============================================================================

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["endpoint", "method", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["endpoint", "method"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

http_errors_total = Counter(
    "http_errors_total",
    "Total HTTP errors (4xx + 5xx)",
    ["endpoint", "method", "status_code"],
)

# =============================================================================
# Agent Metrics
# =============================================================================

agent_stage_duration_seconds = Histogram(
    "agent_stage_duration_seconds",
    "Agent stage duration in seconds",
    ["stage"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

agent_calls_total = Counter(
    "agent_calls_total",
    "Total agent calls",
    ["agent_name"],
)

agent_errors_total = Counter(
    "agent_errors_total",
    "Total agent errors",
    ["agent_name", "error_type"],
)

agent_tokens_total = Counter(
    "agent_tokens_total",
    "Total tokens consumed by agent",
    ["agent_name"],
)

agent_in_progress = Gauge(
    "agent_in_progress",
    "Number of agent calls currently in progress",
    ["agent_name"],
)

# =============================================================================
# Tool Metrics
# =============================================================================

tool_calls_total = Counter(
    "tool_calls_total",
    "Total tool calls",
    ["tool_name"],
)

tool_call_duration_seconds = Histogram(
    "tool_call_duration_seconds",
    "Tool call duration in seconds",
    ["tool_name"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

tool_errors_total = Counter(
    "tool_errors_total",
    "Total tool errors",
    ["tool_name", "error_type"],
)

tool_circuit_breaker_state = Gauge(
    "tool_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["tool_name"],
)

# =============================================================================
# RAG Metrics
# =============================================================================

rag_retrieve_duration_seconds = Histogram(
    "rag_retrieve_duration_seconds",
    "RAG retrieval duration in seconds",
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)

rag_hits_total = Counter(
    "rag_hits_total",
    "Total RAG retrieval hits",
)

rag_documents_total = Gauge(
    "rag_documents_total",
    "Total documents in RAG vector store",
)

rag_embed_duration_seconds = Histogram(
    "rag_embed_duration_seconds",
    "RAG embedding duration in seconds",
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

# =============================================================================
# LLM Metrics
# =============================================================================

llm_requests_total = Counter(
    "llm_requests_total",
    "Total LLM requests",
    ["model"],
)

llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds",
    "LLM request duration in seconds",
    ["model"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

llm_errors_total = Counter(
    "llm_errors_total",
    "Total LLM errors",
    ["model", "error_type"],
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total tokens consumed by LLM",
    ["model", "type"],
)

llm_in_progress = Gauge(
    "llm_in_progress",
    "Number of LLM requests currently in progress",
    ["model"],
)

# =============================================================================
# System Metrics
# =============================================================================

app_info = Info(
    "app",
    "Application information",
)
