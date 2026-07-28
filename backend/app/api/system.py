"""
System API routes
"""

import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import storage
from app.api.error_utils import safe_internal_detail
from app.auth.dependencies import require_role
from app.auth.models import UserResponse
from app.auth.roles import Role
from app.core.observability.metrics import get_metrics_summary
from app.monitoring.request_stats import get_http_stats, record_http_request
from app.utils.logger import get_logger

logger = get_logger("api.system")

router = APIRouter(prefix="/system", tags=["system"])


# ============================================================
# Pydantic Models
# ============================================================


class SystemStatusResponse(BaseModel):
    """Response model for system status"""

    status: str
    version: str
    uptime: float
    total_requests: int
    success_rate: float
    avg_latency_ms: float
    timestamp: str


class SystemMetricsResponse(BaseModel):
    """Response model for system metrics"""

    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    avg_latency_ms: float
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    running_tasks: int
    failed_tasks: int
    timestamp: str


class AgentStatusResponse(BaseModel):
    """Response model for agent status"""

    planner: dict[str, Any]
    executor: dict[str, Any]
    reasoner: dict[str, Any]
    report_agent: dict[str, Any]
    orchestrator: dict[str, Any]


class SystemConfigResponse(BaseModel):
    """Response model for system configuration"""

    model: str
    embedding: str
    features: dict[str, bool]
    version: str


# ============================================================
# System State
# ============================================================

# System start time
system_start_time = time.time()

# ============================================================
# API Routes
# ============================================================


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status():
    """Get system status"""
    try:
        uptime = time.time() - system_start_time
        http_stats = get_http_stats()

        return SystemStatusResponse(
            status="healthy",
            version="1.0.0",
            uptime=uptime,
            total_requests=http_stats.total_requests,
            success_rate=http_stats.success_rate,
            avg_latency_ms=http_stats.avg_latency_ms,
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error getting system status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=safe_internal_detail("Failed to get system status")
        ) from e


@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_system_metrics(
    current_user: UserResponse = Depends(require_role(Role.ADMIN)),
):
    """Get system metrics"""
    try:
        tasks = storage.list_tasks()
        http_stats = get_http_stats()

        # Count tasks by status
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t["status"] == "completed")
        pending_tasks = sum(1 for t in tasks if t["status"] == "pending")
        running_tasks = sum(1 for t in tasks if t["status"] == "running")
        failed_tasks = sum(1 for t in tasks if t["status"] == "failed")

        return SystemMetricsResponse(
            total_requests=http_stats.total_requests,
            successful_requests=http_stats.successful_requests,
            failed_requests=http_stats.failed_requests,
            success_rate=http_stats.success_rate,
            avg_latency_ms=http_stats.avg_latency_ms,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            pending_tasks=pending_tasks,
            running_tasks=running_tasks,
            failed_tasks=failed_tasks,
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=safe_internal_detail("Failed to get system metrics")
        ) from e


@router.get("/agents", response_model=AgentStatusResponse)
async def get_agent_status(
    current_user: UserResponse = Depends(require_role(Role.ADMIN)),
):
    """Get agent status"""
    try:
        agent_summary = get_metrics_summary().get("agent_summary", {})
        http_stats = get_http_stats()
        tasks = storage.list_tasks()

        def summary(name: str) -> dict[str, Any]:
            data = agent_summary.get(name, {})
            calls = int(data.get("calls", 0))
            errors = int(data.get("errors", 0))
            total_ms = float(data.get("total_ms", 0))
            return {
                "status": "ready",
                "total_calls": calls,
                "avg_latency_ms": total_ms / calls if calls else 0.0,
                "success_rate": ((calls - errors) / calls * 100) if calls else 100.0,
            }

        executor_calls = int(
            get_metrics_summary().get("counters", {}).get("task_result", 0)
        )
        completed_runs = sum(1 for task in tasks if task.get("status") == "completed")
        return AgentStatusResponse(
            planner=summary("planner"),
            executor={
                "status": "ready",
                "total_calls": executor_calls,
                "avg_latency_ms": 0.0,
                "success_rate": 100.0,
                "active_tasks": 0,
            },
            reasoner=summary("reasoner"),
            report_agent=summary("report"),
            orchestrator={
                "status": "ready",
                "total_calls": completed_runs,
                "total_requests": http_stats.total_requests,
                "avg_latency_ms": 0.0,
                "success_rate": 100.0,
                "uptime": time.time() - system_start_time,
            },
        )
    except Exception as e:
        logger.error(f"Error getting agent status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=safe_internal_detail("Failed to get agent status")
        ) from e


@router.get("/config", response_model=SystemConfigResponse)
async def get_system_config(
    current_user: UserResponse = Depends(require_role(Role.ADMIN)),
):
    """Get system configuration"""
    try:
        from app.infrastructure.config import (
            get_embedding_config,
            get_llm_config,
        )

        llm_cfg = get_llm_config()
        embed_cfg = get_embedding_config()
        if embed_cfg.mode == "prod":
            embedding_label = "prod (BM25 lexical)"
        else:
            embedding_label = "dev (hash)"

        return SystemConfigResponse(
            model=llm_cfg.model,
            embedding=embedding_label,
            features={
                "dashboard": True,
                "profiling": True,
                "recording": False,
                "streaming": True,
            },
            version="1.0.0",
        )
    except Exception as e:
        logger.error(f"Error getting system config: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=safe_internal_detail("Failed to get system config")
        ) from e


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime": time.time() - system_start_time,
    }


@router.get("/version")
async def get_version():
    """Get system version"""
    return {
        "version": "1.0.0",
        "build": "2026.06.05",
        "api_version": "v1",
    }


# ============================================================
# Helper Functions
# ============================================================


def increment_request_count():
    """Increment request count"""
    record_http_request(200, 0.0)


def record_request_success(latency_ms: float):
    """Record successful request"""
    record_http_request(200, latency_ms)


def record_request_failure():
    """Record failed request"""
    record_http_request(500, 0.0)


@router.get("/cache")
async def get_cache_stats(
    current_user: UserResponse = Depends(require_role(Role.ADMIN)),
):
    """Get cache statistics"""
    from app.tools.cache import get_cache_stats

    return get_cache_stats()


@router.post("/cache/clear")
async def clear_cache(
    current_user: UserResponse = Depends(require_role(Role.ADMIN)),
):
    """Clear all cache entries"""
    from app.tools.cache import get_cache

    cache = get_cache()
    cleared = cache.clear()
    return {"message": f"Cleared {cleared} cache entries"}


@router.get("/auth-health")
async def auth_health(
    current_user: UserResponse = Depends(require_role(Role.ADMIN)),
):
    """JWT secret health check without exposing secret-derived material."""
    import os

    secret = os.getenv("JWT_SECRET_KEY", "")
    return {
        "status": "ok" if secret else "error",
        "jwt_secret_configured": bool(secret),
        "jwt_secret_min_length_ok": len(secret) >= 32,
    }
