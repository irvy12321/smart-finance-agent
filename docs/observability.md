# Smart Finance Agent - Observability Guide

## Overview

This guide explains the production observability stack for Smart Finance Agent, including Prometheus metrics, Grafana dashboards, and monitoring setup.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
├─────────────────────────────────────────────────────────────┤
│  PrometheusMiddleware (HTTP metrics)                        │
│    ↓                                                        │
│  /metrics endpoint (Prometheus scrape target)              │
│                                                            │
│  Monitoring Module:                                        │
│    ├── prometheus.py (24 metrics definitions)              │
│    ├── middleware.py (HTTP request tracking)               │
│    └── routes.py (/metrics endpoint)                      │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────┐     ┌─────────────────────┐
│   Prometheus        │     │   Grafana           │
│   (scrape /metrics) │────→│   (Dashboard)       │
└─────────────────────┘     └─────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Start Application

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. Verify Metrics Endpoint

```bash
curl http://localhost:8000/metrics
```

### 4. Start Monitoring Stack

```bash
export GRAFANA_ADMIN_PASSWORD='replace-with-a-strong-password'
docker-compose -f docker-compose.monitoring.yml up -d
```

### 5. Access Services

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin / value of `GRAFANA_ADMIN_PASSWORD`)

## Metrics Reference

### HTTP Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `http_requests_total` | Counter | endpoint, method, status_code | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | endpoint, method | Request duration |
| `http_errors_total` | Counter | endpoint, method, status_code | Total HTTP errors |

### Agent Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `agent_stage_duration_seconds` | Histogram | stage | Agent stage duration |
| `agent_calls_total` | Counter | agent_name | Total agent calls |
| `agent_errors_total` | Counter | agent_name, error_type | Total agent errors |
| `agent_tokens_total` | Counter | agent_name | Total tokens consumed |

### Tool Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `tool_calls_total` | Counter | tool_name | Total tool calls |
| `tool_call_duration_seconds` | Histogram | tool_name | Tool call duration |
| `tool_errors_total` | Counter | tool_name, error_type | Total tool errors |

### RAG Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `rag_retrieve_duration_seconds` | Histogram | - | Retrieval duration |
| `rag_hits_total` | Counter | - | Total retrieval hits |
| `rag_documents_total` | Gauge | - | Documents in store |

### LLM Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `llm_requests_total` | Counter | model | Total LLM requests |
| `llm_request_duration_seconds` | Histogram | model | LLM request duration |
| `llm_errors_total` | Counter | model, error_type | Total LLM errors |
| `llm_tokens_total` | Counter | model, type | Total tokens |

## Grafana Dashboard

The pre-configured dashboard includes:

1. **HTTP Overview**
   - Request Rate (QPS)
   - Error Rate (%)
   - Latency P95
   - Total Requests

2. **HTTP Details**
   - Request Rate by Endpoint
   - Request Duration (P50/P95/P99)

3. **Agent Performance**
   - Agent Stage Duration
   - Agent Calls Total

4. **Tool Performance**
   - Tool Call Duration
   - Tool Calls Total

5. **RAG Performance**
   - Retrieval Duration
   - Documents Total
   - Hits Rate

6. **LLM Performance**
   - Request Duration by Model
   - Token Usage by Model

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GRAFANA_ADMIN_PASSWORD` | required | Grafana admin password |
| `ENVIRONMENT` | development | Environment name |

## Troubleshooting

### Metrics not appearing

1. Check if backend is running: `curl http://localhost:8000/ping`
2. Check metrics endpoint: `curl http://localhost:8000/metrics`
3. Verify Prometheus target: http://localhost:9090/targets

### Grafana not loading dashboards

1. Check Grafana logs: `docker logs sfa-grafana`
2. Verify provisioning files are mounted correctly
3. Check datasource configuration

### High memory usage

The metrics collector uses in-memory storage. For production:

1. Set appropriate retention period in Prometheus
2. Monitor `prometheus_tsdb_head_series` metric
3. Consider using remote storage for long-term data
