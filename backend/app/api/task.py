"""
Task API routes
"""
import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field
from typing import Dict, Any, List
import uuid
from datetime import datetime

from app.utils.logger import get_logger
from app import storage

logger = get_logger("api.task")

router = APIRouter(prefix="/task", tags=["task"])


# ============================================================
# Pydantic Models
# ============================================================

class TaskCreateRequest(BaseModel):
    """Request model for creating a new task"""
    query: str = Field(..., min_length=10, max_length=1000, description="Research query")
    priority: int = Field(default=1, ge=1, le=5, description="Task priority (1-5)")


class TaskCreateResponse(BaseModel):
    """Response model for task creation"""
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    """Response model for task status"""
    task_id: str
    status: str  # pending, running, completed, failed
    progress: float = 0.0  # 0-100
    current_stage: str = ""
    message: str = ""


class SubTaskInfo(BaseModel):
    """Information about a subtask"""
    id: str
    tool: str
    desc: str
    priority: int = 1
    depends_on: List[str] = []
    status: str = "pending"
    duration_ms: float = 0.0


class TaskResultResponse(BaseModel):
    """Response model for task result"""
    task_id: str
    status: str
    query: str
    answer: str = ""
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
    events: List[Dict[str, Any]] = []
    updated_at: str = ""


class TaskListResponse(BaseModel):
    """Response model for task list"""
    tasks: List[Dict[str, Any]]


# ============================================================
# Helper: Get orchestrator from app.state
# ============================================================

def _get_orchestrator(request: Request):
    """Get orchestrator from app.state"""
    orch = getattr(request.app.state, "orchestrator", None)
    if not orch:
        raise RuntimeError("Orchestrator not initialized. Check server startup logs.")
    return orch


# ============================================================
# API Routes
# ============================================================

@router.post("/create", response_model=TaskCreateResponse)
async def create_task(request: TaskCreateRequest, background_tasks: BackgroundTasks):
    """Create a new research task"""
    try:
        task_id = str(uuid.uuid4())[:8]

        # Store task in SQLite
        storage.create_task(task_id, request.query, request.priority)

        logger.info(f"Created task {task_id} for query: {request.query[:50]}...")

        return TaskCreateResponse(
            task_id=task_id,
            status="pending",
            message=f"Task created successfully. Use /api/task/{task_id}/run to start execution."
        )
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Get task status"""
    task = storage.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        progress=task["progress"],
        current_stage=task["current_stage"],
        message=task.get("message", f"Task is {task['status']}")
    )


@router.post("/{task_id}/run")
async def run_task(task_id: str, background_tasks: BackgroundTasks, request: Request):
    """Execute a research task"""
    task = storage.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Task is already {task['status']}")

    # Get orchestrator from app.state
    orchestrator = _get_orchestrator(request)

    # Start task execution in background
    background_tasks.add_task(execute_task_background, task_id, orchestrator)

    return {"message": "Task execution started", "task_id": task_id}


@router.get("/{task_id}/result", response_model=TaskResultResponse)
async def get_task_result(task_id: str):
    """Get task result"""
    task = storage.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Task is not completed. Current status: {task['status']}")

    result = task.get("result", {})
    if not result:
        raise HTTPException(status_code=404, detail="No result available")

    return TaskResultResponse(
        task_id=task_id,
        status="completed",
        query=task["query"],
        **result
    )


@router.get("/list", response_model=TaskListResponse)
async def list_tasks():
    """List all tasks"""
    task_list = storage.list_tasks()
    return TaskListResponse(tasks=task_list)


# ============================================================
# Background Task Execution
# ============================================================

async def execute_task_background(task_id: str, orchestrator):
    """Execute task in background with overall timeout"""

    task = storage.get_task(task_id)
    if not task:
        logger.error(f"[task:{task_id}] Task not found in storage")
        return

    query = task["query"]

    try:
        storage.update_task(task_id, status="running", current_stage="planning", progress=10.0)

        logger.info(f"[task:{task_id}] Starting execution: {query[:80]}...")

        # Run with overall timeout (180s)
        events = []
        last_event_time = datetime.now().timestamp()

        async def _run_pipeline():
            nonlocal last_event_time
            async for event in orchestrator.run_with_streaming(query):
                events.append(event)
                last_event_time = datetime.now().timestamp()

                # Update task progress based on events
                stage = event.get("stage", "")
                if stage == "planning":
                    storage.update_task(task_id, progress=10.0, current_stage="planning")
                    logger.info(f"[task:{task_id}] Stage: planning")
                elif stage == "plan_ready":
                    storage.update_task(task_id, progress=30.0, current_stage="executing")
                    subtask_count = len(event.get("subtasks", []))
                    logger.info(f"[task:{task_id}] Plan ready: {subtask_count} subtasks")
                elif stage == "task_done":
                    task = storage.get_task(task_id)
                    new_progress = min(task["progress"] + 10.0, 80.0) if task else 40.0
                    storage.update_task(task_id, progress=new_progress)
                    success = event.get("success", False)
                    tool = event.get("tool", "")
                    logger.info(f"[task:{task_id}] Subtask done: tool={tool} success={success}")
                elif stage == "reasoning":
                    storage.update_task(task_id, progress=85.0, current_stage="reasoning")
                    logger.info(f"[task:{task_id}] Stage: reasoning")
                elif stage == "reporting":
                    storage.update_task(task_id, progress=90.0, current_stage="reporting")
                    logger.info(f"[task:{task_id}] Stage: reporting")
                elif stage == "complete":
                    storage.update_task(task_id, progress=100.0, current_stage="completed")
                    logger.info(f"[task:{task_id}] Stage: complete")
                elif stage == "plan_fallback":
                    logger.warning(f"[task:{task_id}] Using fallback plan")
                elif stage == "reasoning_fallback":
                    logger.warning(f"[task:{task_id}] Using fallback reasoning")
                elif stage == "report_fallback":
                    logger.warning(f"[task:{task_id}] Using fallback report")

        await asyncio.wait_for(_run_pipeline(), timeout=600)

        # Process events and create result
        result = process_events(events, query)
        storage.update_task_result(task_id, result, events)

        logger.info(f"[task:{task_id}] Completed successfully. Events: {len(events)}")

    except asyncio.TimeoutError:
        elapsed = datetime.now().timestamp() - last_event_time
        logger.error(f"[task:{task_id}] Timed out after 180s (last event {elapsed:.0f}s ago). Events collected: {len(events)}")
        storage.update_task_failure(task_id, "failed", "timeout", "Research pipeline timed out. Please try a simpler query or try again later.")
    except Exception as e:
        logger.error(f"[task:{task_id}] Failed with error: {type(e).__name__}: {e}", exc_info=True)
        storage.update_task_failure(task_id, "failed", "error", f"Task failed: {type(e).__name__}: {str(e)[:200]}")


def process_events(events: list, query: str) -> Dict[str, Any]:
    """Process streaming events and create result"""
    task_states = {}
    dag_subtasks = []
    report_md = ""
    answer = ""
    reasoning_confidence = 0.0
    reasoning_insights = []
    chart_specs_raw = []
    
    for event in events:
        stage = event.get("stage", "")
        if stage == "plan_ready":
            dag_subtasks = event.get("subtasks", [])
        elif stage == "task_start":
            tid = event.get("task_id", "")
            if tid in {t["id"] for t in dag_subtasks}:
                task_states[tid] = {
                    "tool": event.get("tool", ""),
                    "status": "running",
                    "success": False,
                    "duration_ms": 0,
                }
        elif stage == "task_done":
            tid = event.get("task_id", "")
            task_states[tid] = {
                "tool": event.get("tool", ""),
                "success": event.get("success", False),
                "duration_ms": event.get("duration_ms", 0),
                "status": event.get("status", "success" if event.get("success") else "failed"),
            }
        elif stage == "reasoning_done":
            reasoning_confidence = event.get("confidence", 0)
            reasoning_insights = event.get("insights", [])
        elif stage == "complete":
            answer = event.get("answer", "")
            report_md = event.get("report_markdown", "")
            chart_specs_raw = event.get("chart_specs", [])
    
    # Extract structured data from report
    summary = ""
    key_findings = []
    risk_factors = []
    market_trends = []
    recommendations = []
    sources = []
    
    # Parse structured data from report markdown
    if report_md:
        lines = report_md.split("\n")
        current_section = None
        for line in lines:
            line_stripped = line.strip()
            if line_stripped.startswith("## 摘要") or line_stripped.startswith("## Summary"):
                current_section = "summary"
                continue
            elif line_stripped.startswith("## 关键发现") or line_stripped.startswith("## Key Findings"):
                current_section = "findings"
                continue
            elif line_stripped.startswith("## 风险因素") or line_stripped.startswith("## Risk Factors"):
                current_section = "risks"
                continue
            elif line_stripped.startswith("## 市场趋势") or line_stripped.startswith("## Market Trends"):
                current_section = "trends"
                continue
            elif line_stripped.startswith("## 建议") or line_stripped.startswith("## Recommendations"):
                current_section = "recommendations"
                continue
            elif line_stripped.startswith("## 数据来源") or line_stripped.startswith("## Data Sources"):
                current_section = "sources"
                continue
            elif line_stripped.startswith("#") or line_stripped.startswith("---"):
                if current_section and line_stripped.startswith("#"):
                    current_section = None
                continue
            
            if line_stripped.startswith("- ") or line_stripped.startswith("* "):
                item = line_stripped[2:].strip()
                if current_section == "findings":
                    key_findings.append(item)
                elif current_section == "risks":
                    risk_factors.append({"factor": item, "severity": "medium", "description": item})
                elif current_section == "trends":
                    market_trends.append(item)
                elif current_section == "recommendations":
                    recommendations.append(item)
                elif current_section == "sources":
                    sources.append({"tool": item, "task_id": "", "duration_ms": 0})
            elif current_section == "summary" and line_stripped:
                summary += line_stripped + " "
    
    summary = summary.strip()

    # If no answer was found from events, try to extract from any available data
    if not answer and not report_md:
        for event in events:
            if event.get("answer"):
                answer = event["answer"]
                break

    summary = summary.strip()
    
    # Compute task stats
    total_tasks = len(dag_subtasks)
    success_tasks = sum(1 for ts in task_states.values() if ts.get("success"))
    failed_tasks = sum(1 for ts in task_states.values() if ts.get("status") in ("failed", "skipped"))
    
    # Get plan reasoning
    plan_reasoning = ""
    for event in events:
        if event.get("stage") == "plan_ready":
            plan_reasoning = event.get("reasoning", "")
            break
    
    return {
        "answer": answer,
        "report_markdown": report_md,
        "report_title": report_md.split("\n")[0].lstrip("# ").strip() if report_md else query[:60],
        "summary": summary,
        "key_findings": key_findings,
        "risk_factors": risk_factors,
        "market_trends": market_trends,
        "recommendations": recommendations,
        "confidence": reasoning_confidence,
        "chart_paths": [],  # TODO: Implement chart rendering
        "chart_specs": chart_specs_raw,
        "sources": sources,
        "dag_subtasks": dag_subtasks,
        "task_states": task_states,
        "elapsed": 0.0,  # TODO: Calculate elapsed time
        "total_tasks": total_tasks,
        "success_tasks": success_tasks,
        "failed_tasks": failed_tasks,
        "plan_reasoning": plan_reasoning,
        "reasoning_insights": reasoning_insights,
        "events": events,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }