"""
Agent Research Process — 自包含 HTML，通过 st.components.v1.html() 嵌入
"""
import streamlit as st
import streamlit.components.v1 as components
from app.ui.html_styles import agent_process_html


def _build_stages(
    plan_reasoning, dag_subtasks, task_states, reasoning_confidence,
    reasoning_insights, elapsed, total_tasks, success_tasks, failed_tasks,
):
    stages = []

    ps = "complete" if dag_subtasks else "pending"
    pd = f"{len(dag_subtasks)} subtasks generated"
    if plan_reasoning:
        pd += f" | {plan_reasoning[:120]}"
    stages.append({"name": "Planner", "description": "Task decomposition and strategy selection",
                    "detail": pd, "status": ps, "icon": "📋"})

    if task_states:
        es = "complete" if all(
            ts.get("status") in ("success", "failed", "skipped") for ts in task_states.values()
        ) else "running"
    else:
        es = "pending"
    ed = ""
    if task_states:
        done = sum(1 for ts in task_states.values() if ts.get("status") in ("success", "failed", "skipped"))
        ed = f"{done}/{total_tasks} tasks completed"
    stages.append({"name": "Executor", "description": "Parallel DAG-based task execution with fallback chains",
                    "detail": ed, "status": es, "icon": "⚡"})

    if reasoning_confidence > 0:
        rs = "complete"
        rd = f"Confidence: {reasoning_confidence:.0%}"
        if reasoning_insights:
            rd += f" | {len(reasoning_insights)} insights"
    elif task_states:
        rs, rd = "running", "Analyzing execution results..."
    else:
        rs, rd = "pending", ""
    stages.append({"name": "Reasoner", "description": "Multi-step reasoning and insight extraction",
                    "detail": rd, "status": rs, "icon": "🧠"})

    if success_tasks > 0 and elapsed > 0:
        rps = "complete"
        rpd = f"Generated in {elapsed:.1f}s | {success_tasks}/{total_tasks} sources"
    elif task_states:
        rps, rpd = "running", "Compiling structured report..."
    else:
        rps, rpd = "pending", ""
    stages.append({"name": "Report", "description": "Structured financial research report generation",
                    "detail": rpd, "status": rps, "icon": "📄"})

    return stages


def render_agent_process(
    plan_reasoning="", dag_subtasks=None, task_states=None,
    reasoning_confidence=0.0, reasoning_insights=None,
    elapsed=0.0, total_tasks=0, success_tasks=0, failed_tasks=0,
):
    dag_subtasks = dag_subtasks or []
    task_states = task_states or {}
    reasoning_insights = reasoning_insights or []

    stages = _build_stages(
        plan_reasoning, dag_subtasks, task_states,
        reasoning_confidence, reasoning_insights,
        elapsed, total_tasks, success_tasks, failed_tasks,
    )

    h = 280 + len(reasoning_insights) * 45
    if dag_subtasks and task_states:
        h += 60 + len(dag_subtasks) * 38

    components.html(
        agent_process_html(
            stages=stages,
            insights=reasoning_insights,
            dag_subtasks=dag_subtasks,
            task_states=task_states,
        ),
        height=h,
        scrolling=False,
    )
