"""
Report API routes
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List

from app.utils.logger import get_logger

logger = get_logger("api.report")

router = APIRouter(prefix="/report", tags=["report"])


# ============================================================
# Pydantic Models
# ============================================================

class ReportResponse(BaseModel):
    """Response model for report"""
    task_id: str
    report_markdown: str = ""
    report_title: str = ""
    summary: str = ""
    key_findings: List[str] = []
    risk_factors: List[Dict[str, Any]] = []
    market_trends: List[str] = []
    recommendations: List[str] = []
    confidence: float = 0.0
    chart_paths: List[str] = []
    chart_specs: List[Dict[str, Any]] = []
    sources: List[Dict[str, Any]] = []
    dag_subtasks: List[Dict[str, Any]] = []
    task_states: Dict[str, Any] = {}
    elapsed: float = 0.0
    total_tasks: int = 0
    success_tasks: int = 0
    failed_tasks: int = 0
    plan_reasoning: str = ""
    reasoning_insights: List[str] = []
    updated_at: str = ""


class ReportSummaryResponse(BaseModel):
    """Response model for report summary"""
    task_id: str
    report_title: str = ""
    summary: str = ""
    key_findings: List[str] = []
    confidence: float = 0.0
    total_tasks: int = 0
    success_tasks: int = 0
    failed_tasks: int = 0


# ============================================================
# Task Storage (shared with task.py)
# ============================================================

# Import task storage from task module
# In production, this should be a proper database
from app.api.task import tasks_storage


# ============================================================
# API Routes
# ============================================================

@router.get("/{task_id}", response_model=ReportResponse)
async def get_report(task_id: str):
    """Get full research report for a task"""
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks_storage[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Task is not completed. Current status: {task['status']}")
    
    result = task.get("result", {})
    if not result:
        raise HTTPException(status_code=404, detail="No report available")
    
    return ReportResponse(
        task_id=task_id,
        **result
    )


@router.get("/{task_id}/summary", response_model=ReportSummaryResponse)
async def get_report_summary(task_id: str):
    """Get report summary for a task"""
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks_storage[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Task is not completed. Current status: {task['status']}")
    
    result = task.get("result", {})
    if not result:
        raise HTTPException(status_code=404, detail="No report available")
    
    return ReportSummaryResponse(
        task_id=task_id,
        report_title=result.get("report_title", ""),
        summary=result.get("summary", ""),
        key_findings=result.get("key_findings", []),
        confidence=result.get("confidence", 0.0),
        total_tasks=result.get("total_tasks", 0),
        success_tasks=result.get("success_tasks", 0),
        failed_tasks=result.get("failed_tasks", 0),
    )


@router.get("/{task_id}/markdown")
async def get_report_markdown(task_id: str):
    """Get report in markdown format"""
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks_storage[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Task is not completed. Current status: {task['status']}")
    
    result = task.get("result", {})
    if not result:
        raise HTTPException(status_code=404, detail="No report available")
    
    return {
        "task_id": task_id,
        "markdown": result.get("report_markdown", ""),
        "title": result.get("report_title", ""),
    }


@router.get("/{task_id}/charts")
async def get_report_charts(task_id: str):
    """Get chart specifications for a task"""
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks_storage[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Task is not completed. Current status: {task['status']}")
    
    result = task.get("result", {})
    if not result:
        raise HTTPException(status_code=404, detail="No report available")
    
    return {
        "task_id": task_id,
        "chart_paths": result.get("chart_paths", []),
        "chart_specs": result.get("chart_specs", []),
    }


@router.get("/{task_id}/analysis")
async def get_report_analysis(task_id: str):
    """Get detailed analysis for a task"""
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks_storage[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Task is not completed. Current status: {task['status']}")
    
    result = task.get("result", {})
    if not result:
        raise HTTPException(status_code=404, detail="No report available")
    
    return {
        "task_id": task_id,
        "key_findings": result.get("key_findings", []),
        "risk_factors": result.get("risk_factors", []),
        "market_trends": result.get("market_trends", []),
        "recommendations": result.get("recommendations", []),
        "confidence": result.get("confidence", 0.0),
        "reasoning_insights": result.get("reasoning_insights", []),
    }


@router.get("/{task_id}/sources")
async def get_report_sources(task_id: str):
    """Get data sources for a task"""
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks_storage[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Task is not completed. Current status: {task['status']}")
    
    result = task.get("result", {})
    if not result:
        raise HTTPException(status_code=404, detail="No report available")
    
    return {
        "task_id": task_id,
        "sources": result.get("sources", []),
        "dag_subtasks": result.get("dag_subtasks", []),
        "task_states": result.get("task_states", {}),
    }


@router.get("/{task_id}/process")
async def get_report_process(task_id: str):
    """Get agent process information for a task"""
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks_storage[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Task is not completed. Current status: {task['status']}")
    
    result = task.get("result", {})
    if not result:
        raise HTTPException(status_code=404, detail="No report available")
    
    return {
        "task_id": task_id,
        "plan_reasoning": result.get("plan_reasoning", ""),
        "dag_subtasks": result.get("dag_subtasks", []),
        "task_states": result.get("task_states", {}),
        "elapsed": result.get("elapsed", 0.0),
        "total_tasks": result.get("total_tasks", 0),
        "success_tasks": result.get("success_tasks", 0),
        "failed_tasks": result.get("failed_tasks", 0),
    }