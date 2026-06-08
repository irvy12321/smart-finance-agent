"""
System API routes
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List
import time
from datetime import datetime

from app.utils.logger import get_logger
from app import storage

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
    planner: Dict[str, Any]
    executor: Dict[str, Any]
    reasoner: Dict[str, Any]
    report_agent: Dict[str, Any]
    orchestrator: Dict[str, Any]


class SystemConfigResponse(BaseModel):
    """Response model for system configuration"""
    model: str
    embedding: str
    features: Dict[str, bool]
    version: str


# ============================================================
# System State
# ============================================================

# System start time
system_start_time = time.time()

# Request tracking
request_count = 0
successful_requests = 0
failed_requests = 0
total_latency = 0.0


# ============================================================
# API Routes
# ============================================================

@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status():
    """Get system status"""
    try:
        uptime = time.time() - system_start_time
        
        return SystemStatusResponse(
            status="healthy",
            version="1.0.0",
            uptime=uptime,
            total_requests=request_count,
            success_rate=100.0 if request_count == 0 else (successful_requests / request_count) * 100,
            avg_latency_ms=0.0 if request_count == 0 else total_latency / request_count,
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_system_metrics():
    """Get system metrics"""
    try:
        tasks = storage.list_tasks()

        # Count tasks by status
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t["status"] == "completed")
        pending_tasks = sum(1 for t in tasks if t["status"] == "pending")
        running_tasks = sum(1 for t in tasks if t["status"] == "running")
        failed_tasks = sum(1 for t in tasks if t["status"] == "failed")

        return SystemMetricsResponse(
            total_requests=request_count,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            success_rate=100.0 if request_count == 0 else (successful_requests / request_count) * 100,
            avg_latency_ms=0.0 if request_count == 0 else total_latency / request_count,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            pending_tasks=pending_tasks,
            running_tasks=running_tasks,
            failed_tasks=failed_tasks,
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents", response_model=AgentStatusResponse)
async def get_agent_status():
    """Get agent status"""
    try:
        # In a real implementation, this would query the actual agent status
        # For now, return mock data
        return AgentStatusResponse(
            planner={
                "status": "ready",
                "total_calls": 0,
                "avg_latency_ms": 0.0,
                "success_rate": 100.0,
            },
            executor={
                "status": "ready",
                "total_calls": 0,
                "avg_latency_ms": 0.0,
                "success_rate": 100.0,
                "active_tasks": 0,
            },
            reasoner={
                "status": "ready",
                "total_calls": 0,
                "avg_latency_ms": 0.0,
                "success_rate": 100.0,
            },
            report_agent={
                "status": "ready",
                "total_calls": 0,
                "avg_latency_ms": 0.0,
                "success_rate": 100.0,
            },
            orchestrator={
                "status": "ready",
                "total_requests": request_count,
                "uptime": time.time() - system_start_time,
            },
        )
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config", response_model=SystemConfigResponse)
async def get_system_config():
    """Get system configuration"""
    try:
        return SystemConfigResponse(
            model="gpt-4",  # TODO: Get from actual config
            embedding="dev (hash)",  # TODO: Get from actual config
            features={
                "dashboard": True,
                "profiling": True,
                "recording": True,
                "streaming": True,
            },
            version="1.0.0",
        )
    except Exception as e:
        logger.error(f"Error getting system config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    global request_count
    request_count += 1


def record_request_success(latency_ms: float):
    """Record successful request"""
    global successful_requests, total_latency
    successful_requests += 1
    total_latency += latency_ms


def record_request_failure():
    """Record failed request"""
    global failed_requests
    failed_requests += 1