"""
Task API routes
"""

import asyncio
import contextlib
import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app import storage
from app.auth.dependencies import get_current_user, require_role
from app.auth.models import UserResponse
from app.auth.roles import Role
from app.utils.logger import get_logger

logger = get_logger("api.task")

router = APIRouter(prefix="/task", tags=["task"])

# Keep strong references to fire-and-forget background tasks so they are not
# garbage-collected mid-execution.
_background_tasks: set[asyncio.Task] = set()


# ============================================================
# Pydantic Models
# ============================================================


class TaskCreateRequest(BaseModel):
    """Request model for creating a new task"""

    query: str = Field(
        ..., min_length=10, max_length=1000, description="Research query"
    )
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
    depends_on: list[str] = []
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
    key_findings: list[str] = []
    risk_factors: list[dict[str, Any]] = []
    market_trends: list[str] = []
    recommendations: list[str] = []
    confidence: float = 0.0
    chart_paths: list[str] = []
    chart_specs: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    dag_subtasks: list[dict[str, Any]] = []
    task_states: dict[str, Any] = {}
    elapsed: float = 0.0
    total_tasks: int = 0
    success_tasks: int = 0
    failed_tasks: int = 0
    plan_reasoning: str = ""
    reasoning_insights: list[str] = []
    events: list[dict[str, Any]] = []
    updated_at: str = ""


class TaskListResponse(BaseModel):
    """Response model for task list"""

    tasks: list[dict[str, Any]]


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
async def create_task(
    request: TaskCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(require_role(Role.ADMIN, Role.ANALYST)),
):
    """Create a new research task (Admin/Analyst only)"""
    try:
        task_id = str(uuid.uuid4())[:8]

        # Store task in SQLite with user_id
        storage.create_task(
            task_id, request.query, request.priority, user_id=current_user.id
        )

        logger.info(
            f"Created task {task_id} for user {current_user.username}: {request.query[:50]}..."
        )

        return TaskCreateResponse(
            task_id=task_id,
            status="pending",
            message=f"Task created successfully. Use /api/task/{task_id}/run to start execution.",
        )
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: UserResponse = Depends(require_role(Role.ADMIN, Role.ANALYST)),
):
    """Get task status (Admin/Analyst only)"""
    task = storage.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    owner_id = storage.get_task_owner(task_id)
    if owner_id is not None and owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return TaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        progress=task["progress"],
        current_stage=task["current_stage"],
        message=task.get("message", f"Task is {task['status']}"),
    )


@router.post("/{task_id}/run")
async def run_task(
    task_id: str,
    request: Request,
    current_user: UserResponse = Depends(require_role(Role.ADMIN, Role.ANALYST)),
):
    """Execute a research task (Admin/Analyst only)"""
    task = storage.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    owner_id = storage.get_task_owner(task_id)
    if owner_id is not None and owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if task["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Task is already {task['status']}")

    # Get language from Accept-Language header
    language = request.headers.get("accept-language", "en")
    language = "zh" if language.startswith("zh") else "en"

    # Get orchestrator from app.state
    orchestrator = _get_orchestrator(request)

    # Start task execution in background using asyncio.create_task
    bg_task = asyncio.create_task(
        execute_task_background(task_id, orchestrator, language)
    )
    _background_tasks.add(bg_task)
    bg_task.add_done_callback(_background_tasks.discard)

    return {"message": "Task execution started", "task_id": task_id}


@router.get("/{task_id}/result", response_model=TaskResultResponse)
async def get_task_result(
    task_id: str,
    current_user: UserResponse = Depends(require_role(Role.ADMIN, Role.ANALYST)),
):
    """Get task result (Admin/Analyst only)"""
    task = storage.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    owner_id = storage.get_task_owner(task_id)
    if owner_id is not None and owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if task["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Task is not completed. Current status: {task['status']}",
        )

    result = task.get("result", {})
    if not result:
        logger.warning(f"[task:{task_id}] Task completed but no result available")
        # Return a minimal result instead of 404
        return TaskResultResponse(
            task_id=task_id,
            status="completed",
            query=task["query"],
            answer="Research completed but no detailed results available.",
        )

    logger.info(
        f"[task:{task_id}] Returning result with {len(result.get('key_findings', []))} findings"
    )
    return TaskResultResponse(
        task_id=task_id, status="completed", query=task["query"], **result
    )


@router.get("/list", response_model=TaskListResponse)
async def list_tasks(
    current_user: UserResponse = Depends(require_role(Role.ADMIN, Role.ANALYST)),
):
    """List tasks for current user (Admin/Analyst only)"""
    task_list = storage.list_tasks(user_id=current_user.id)
    return TaskListResponse(tasks=task_list)


# ============================================================
# Background Task Execution
# ============================================================


async def execute_task_background(task_id: str, orchestrator, language: str = "en"):
    """Execute task in background with overall timeout"""

    task = storage.get_task(task_id)
    if not task:
        logger.error(f"[task:{task_id}] Task not found in storage")
        return

    query = task["query"]

    try:
        if language == "zh":
            storage.update_task(
                task_id,
                status="running",
                current_stage="planning",
                progress=10.0,
                message="正在规划研究任务...",
            )
        else:
            storage.update_task(
                task_id, status="running", current_stage="planning", progress=10.0
            )

        logger.info(
            f"[task:{task_id}] Starting execution: {query[:80]}... (lang={language})"
        )

        # Run with overall timeout (900s)
        events = []
        last_event_time = datetime.now().timestamp()
        pipeline_start_time = datetime.now().timestamp()
        current_progress = 10.0
        current_stage = "planning"

        async def _progress_updater():
            """Background task to update progress during long operations"""
            nonlocal current_progress
            while True:
                await asyncio.sleep(5)
                elapsed = datetime.now().timestamp() - pipeline_start_time
                # Gradually increase progress during long operations
                if current_stage == "planning" and elapsed > 30:
                    current_progress = min(current_progress + 2.0, 25.0)
                    msg = (
                        "正在规划中..."
                        if language == "zh"
                        else "Planning in progress..."
                    )
                    storage.update_task(task_id, progress=current_progress, message=msg)
                elif current_stage == "executing" and elapsed > 60:
                    current_progress = min(current_progress + 3.0, 75.0)
                    msg = (
                        f"执行中 {current_progress:.0f}%"
                        if language == "zh"
                        else f"Executing {current_progress:.0f}%"
                    )
                    storage.update_task(task_id, progress=current_progress, message=msg)
                elif current_stage == "reasoning" and elapsed > 120:
                    current_progress = min(current_progress + 2.0, 88.0)
                    msg = "分析中..." if language == "zh" else "Analyzing..."
                    storage.update_task(task_id, progress=current_progress, message=msg)
                elif current_stage == "reporting" and elapsed > 180:
                    current_progress = min(current_progress + 1.0, 95.0)
                    msg = (
                        "生成报告中..." if language == "zh" else "Generating report..."
                    )
                    storage.update_task(task_id, progress=current_progress, message=msg)

        progress_task = asyncio.create_task(_progress_updater())

        async def _run_pipeline():
            nonlocal last_event_time, current_progress, current_stage
            async for event in orchestrator.run_with_streaming(
                query, language=language
            ):
                events.append(event)
                last_event_time = datetime.now().timestamp()
                elapsed = last_event_time - pipeline_start_time
                stage = event.get("stage", "")
                logger.debug(
                    f"[task:{task_id}] Event #{len(events)}: stage={stage} elapsed={elapsed:.1f}s"
                )

                # Update task progress based on events
                stage = event.get("stage", "")
                if stage == "planning":
                    current_stage = "planning"
                    current_progress = 10.0
                    msg = "正在规划..." if language == "zh" else "Planning..."
                    storage.update_task(
                        task_id, progress=10.0, current_stage="planning", message=msg
                    )
                    logger.info(f"[task:{task_id}] Stage: planning")
                elif stage == "plan_ready":
                    current_stage = "executing"
                    current_progress = 30.0
                    msg = (
                        "正在执行研究..."
                        if language == "zh"
                        else "Executing research..."
                    )
                    storage.update_task(
                        task_id, progress=30.0, current_stage="executing", message=msg
                    )
                    subtask_count = len(event.get("subtasks", []))
                    logger.info(
                        f"[task:{task_id}] Plan ready: {subtask_count} subtasks"
                    )
                elif stage == "task_done":
                    task = storage.get_task(task_id)
                    current_progress = (
                        min(task["progress"] + 10.0, 80.0) if task else 40.0
                    )
                    msg = (
                        f"已完成 {current_progress:.0f}%"
                        if language == "zh"
                        else f"Progress {current_progress:.0f}%"
                    )
                    storage.update_task(task_id, progress=current_progress, message=msg)
                    success = event.get("success", False)
                    tool = event.get("tool", "")
                    logger.info(
                        f"[task:{task_id}] Subtask done: tool={tool} success={success}"
                    )
                elif stage == "reasoning":
                    current_stage = "reasoning"
                    current_progress = 85.0
                    msg = (
                        "正在分析结果..."
                        if language == "zh"
                        else "Analyzing results..."
                    )
                    storage.update_task(
                        task_id, progress=85.0, current_stage="reasoning", message=msg
                    )
                    logger.info(f"[task:{task_id}] Stage: reasoning")
                elif stage == "reporting":
                    current_stage = "reporting"
                    current_progress = 90.0
                    msg = (
                        "正在生成报告..."
                        if language == "zh"
                        else "Generating report..."
                    )
                    storage.update_task(
                        task_id, progress=90.0, current_stage="reporting", message=msg
                    )
                    logger.info(f"[task:{task_id}] Stage: reporting")
                elif stage == "complete":
                    current_stage = "completed"
                    current_progress = 100.0
                    msg = "研究完成" if language == "zh" else "Research completed"
                    storage.update_task(
                        task_id, progress=100.0, current_stage="completed", message=msg
                    )
                    logger.info(f"[task:{task_id}] Stage: complete")
                elif stage == "plan_fallback":
                    logger.warning(f"[task:{task_id}] Using fallback plan")
                elif stage == "reasoning_fallback":
                    logger.warning(f"[task:{task_id}] Using fallback reasoning")
                elif stage == "report_fallback":
                    logger.warning(f"[task:{task_id}] Using fallback report")

        await asyncio.wait_for(_run_pipeline(), timeout=900)

        # Cancel progress updater
        progress_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await progress_task

        # Process events and create result
        result = process_events(events, query, language)
        storage.update_task_result(task_id, result, events)

        logger.info(f"[task:{task_id}] Completed successfully. Events: {len(events)}")

    except asyncio.TimeoutError:
        # Cancel progress updater
        progress_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await progress_task
        elapsed = datetime.now().timestamp() - pipeline_start_time
        logger.error(
            f"[task:{task_id}] Timed out after {elapsed:.0f}s (last event {datetime.now().timestamp() - last_event_time:.0f}s ago). Events collected: {len(events)}"
        )
        timeout_msg = (
            "研究超时，请尝试简化查询或重试。"
            if language == "zh"
            else "Research pipeline timed out. Please try a simpler query or try again later."
        )
        storage.update_task_failure(task_id, "failed", "timeout", timeout_msg)
    except Exception as e:
        # Cancel progress updater
        progress_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await progress_task
        elapsed = datetime.now().timestamp() - pipeline_start_time
        logger.error(
            f"[task:{task_id}] Failed after {elapsed:.0f}s with error: {type(e).__name__}: {e}",
            exc_info=True,
        )
        storage.update_task_failure(
            task_id,
            "failed",
            "error",
            f"Task failed: {type(e).__name__}: {str(e)[:200]}",
        )


def process_events(events: list, query: str, language: str = "en") -> dict[str, Any]:
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
                "status": event.get(
                    "status", "success" if event.get("success") else "failed"
                ),
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
            if line_stripped.startswith("## 摘要") or line_stripped.startswith(
                "## Summary"
            ):
                current_section = "summary"
                continue
            elif line_stripped.startswith("## 关键发现") or line_stripped.startswith(
                "## Key Findings"
            ):
                current_section = "findings"
                continue
            elif line_stripped.startswith("## 风险因素") or line_stripped.startswith(
                "## Risk Factors"
            ):
                current_section = "risks"
                continue
            elif line_stripped.startswith("## 市场趋势") or line_stripped.startswith(
                "## Market Trends"
            ):
                current_section = "trends"
                continue
            elif line_stripped.startswith("## 建议") or line_stripped.startswith(
                "## Recommendations"
            ):
                current_section = "recommendations"
                continue
            elif line_stripped.startswith("## 数据来源") or line_stripped.startswith(
                "## Data Sources"
            ):
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
                    risk_factors.append(
                        {"factor": item, "severity": "medium", "description": item}
                    )
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

    # If still no answer, try to get from task results
    if not answer:
        for event in events:
            if event.get("stage") == "task_done" and event.get("success"):
                # This is a completed task, but we need the actual data
                pass

    # If we have report_md but no parsed findings, try to extract from answer
    if not key_findings and answer:
        # Try to extract key findings from answer if it contains numbered lists
        lines = answer.split("\n")
        for line in lines:
            line_stripped = line.strip()
            if line_stripped.startswith(("1.", "2.", "3.", "4.", "5.", "- ", "* ")):
                item = line_stripped.lstrip("0123456789.-* ").strip()
                if item and len(item) > 10:  # Only add meaningful items
                    key_findings.append(item)

    summary = summary.strip()

    # Compute task stats
    total_tasks = len(dag_subtasks)
    success_tasks = sum(1 for ts in task_states.values() if ts.get("success"))
    failed_tasks = sum(
        1 for ts in task_states.values() if ts.get("status") in ("failed", "skipped")
    )

    # Get plan reasoning
    plan_reasoning = ""
    for event in events:
        if event.get("stage") == "plan_ready":
            plan_reasoning = event.get("reasoning", "")
            break

    return {
        "answer": answer,
        "report_markdown": report_md,
        "report_title": report_md.split("\n")[0].lstrip("# ").strip()
        if report_md
        else query[:60],
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


# ============================================================
# SSE Endpoint for Real-time Workflow Visualization
# ============================================================


@router.get("/{task_id}/stream")
async def stream_task_events(
    task_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    SSE endpoint for real-time task execution updates.

    Events:
    - connected: Connection established
    - plan_ready: Task plan generated with subtasks
    - task_start: Individual task started
    - task_complete: Individual task completed
    - stage_change: Pipeline stage changed
    - complete: All tasks completed
    - error: Error occurred
    """
    # Verify task ownership
    owner_id = storage.get_task_owner(task_id)
    if owner_id is not None and owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    task = storage.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        """Generate SSE events"""
        # Send connection confirmation
        yield f"event: connected\ndata: {json.dumps({'task_id': task_id, 'status': task['status']})}\n\n"

        # If task is already completed, send stored events
        if task["status"] in ("completed", "failed"):
            events_json = task.get("events_json", "[]")
            try:
                events = json.loads(events_json) if events_json else []
                for event in events:
                    stage = event.get("stage", "unknown")
                    yield f"event: {stage}\ndata: {json.dumps(event)}\n\n"
            except (json.JSONDecodeError, TypeError):
                pass

            yield f"event: complete\ndata: {json.dumps({'stage': 'complete', 'status': task['status']})}\n\n"
            return

        # For running tasks, poll for updates
        last_progress = -1
        last_stage = ""
        last_events_count = 0

        while True:
            try:
                # Get current task state
                current_task = storage.get_task(task_id)
                if not current_task:
                    yield f"event: error\ndata: {json.dumps({'error': 'Task not found'})}\n\n"
                    break

                # Send progress update if changed
                current_progress = current_task.get("progress", 0)
                current_stage = current_task.get("current_stage", "")

                if current_progress != last_progress or current_stage != last_stage:
                    yield f"event: stage_change\ndata: {json.dumps({'stage': current_stage, 'progress': current_progress})}\n\n"
                    last_progress = current_progress
                    last_stage = current_stage

                # Send new events
                events_json = current_task.get("events_json", "[]")
                try:
                    events = json.loads(events_json) if events_json else []
                    new_events = events[last_events_count:]
                    for event in new_events:
                        stage = event.get("stage", "unknown")
                        yield f"event: {stage}\ndata: {json.dumps(event)}\n\n"
                    last_events_count = len(events)
                except (json.JSONDecodeError, TypeError):
                    pass

                # Check if task is done
                if current_task["status"] in ("completed", "failed"):
                    yield f"event: complete\ndata: {json.dumps({'stage': 'complete', 'status': current_task['status']})}\n\n"
                    break

                # Wait before next poll
                await asyncio.sleep(1)

                # Send heartbeat every 30 seconds
                yield ": heartbeat\n\n"

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"SSE error for task {task_id}: {e}")
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
