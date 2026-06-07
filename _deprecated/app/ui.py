"""
Smart Finance Research Platform
Financial Research Report UI - Bloomberg/Goldman Sachs/Morningstar inspired
"""
import asyncio
import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from core.orchestrator import Orchestrator
from core.dag_renderer import render_dag
from core.chart_renderer import ChartRenderer
from core.reasoner import ChartSpec
from core.metrics_dashboard import get_dashboard
from core.dashboard_integration import activate_dashboard
from core.profiling import get_profiler
from core.profiling.integration import activate_profiling
from core.replay import get_recorder, get_replayer
from rag.retriever import Retriever
from tools.rag_tool import get_retriever

from app.ui_components import (
    inject_theme,
    kpi_row,
    section_header,
    empty_state,
    status_badge,
    render_sidebar_navigation,
)

from app.ui.components import (
    render_hero_section,
    render_executive_summary,
    render_key_findings,
    render_market_analysis,
    render_agent_process,
    render_data_sources,
    render_appendix,
)

# ============================================================
# Page Configuration
# ============================================================
st.set_page_config(
    page_title="Smart Finance Research Platform",
    page_icon="\U0001F4CA",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme()

# ============================================================
# Session State
# ============================================================
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = Orchestrator(use_router=True)
if "history" not in st.session_state:
    st.session_state.history = []
if "task_log" not in st.session_state:
    st.session_state.task_log = []
if "current_report" not in st.session_state:
    st.session_state.current_report = None
if "dashboard_active" not in st.session_state:
    st.session_state.dashboard_active = False
if "profiling_active" not in st.session_state:
    st.session_state.profiling_active = False
if "recorder_active" not in st.session_state:
    st.session_state.recorder_active = False
if "current_dag_subtasks" not in st.session_state:
    st.session_state.current_dag_subtasks = []
if "current_task_states" not in st.session_state:
    st.session_state.current_task_states = {}
if "report_data" not in st.session_state:
    st.session_state.report_data = {}


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ============================================================
# Page: Research Report (Primary)
# ============================================================
def page_research_report():
    """Main financial research report view."""
    data = st.session_state.report_data

    if not data:
        # Show empty state with hero
        render_hero_section()
        render_executive_summary(None)
        render_key_findings()
        render_market_analysis()
        render_agent_process()
        render_data_sources()
        render_appendix()
        return

    # Extract data
    report_md = data.get("report_markdown", "")
    report_title = data.get("report_title", "")
    answer = data.get("answer", "")
    summary = data.get("summary", "")
    key_findings = data.get("key_findings", [])
    risk_factors = data.get("risk_factors", [])
    market_trends = data.get("market_trends", [])
    recommendations = data.get("recommendations", [])
    confidence = data.get("confidence", 0.0)
    chart_paths = data.get("chart_paths", [])
    chart_specs = data.get("chart_specs", [])
    sources = data.get("sources", [])
    dag_subtasks = data.get("dag_subtasks", [])
    task_states = data.get("task_states", {})
    elapsed = data.get("elapsed", 0.0)
    total_tasks = data.get("total_tasks", 0)
    success_tasks = data.get("success_tasks", 0)
    failed_tasks = data.get("failed_tasks", 0)
    plan_reasoning = data.get("plan_reasoning", "")
    reasoning_insights = data.get("reasoning_insights", [])
    events = data.get("events", [])
    updated_at = data.get("updated_at", "")

    # Section 1: Hero
    render_hero_section(
        title=report_title or "Financial Research Report",
        subtitle=summary or "AI-Powered Multi-Agent Financial Analysis",
        updated_at=updated_at,
        sources_count=len(sources) or len(dag_subtasks),
        confidence=confidence,
        status="complete",
    )

    # Section 2: Executive Summary
    render_executive_summary(
        summary=summary,
        key_findings=key_findings,
    )

    # Section 3: Key Findings
    render_key_findings(
        key_findings=key_findings,
        risk_factors=risk_factors,
        market_trends=market_trends,
        recommendations=recommendations,
        confidence=confidence,
        task_states=task_states,
    )

    # Section 4: Market Analysis (Charts + Report)
    render_market_analysis(
        report_markdown=report_md,
        chart_paths=chart_paths,
        chart_specs=chart_specs,
        answer=answer,
    )

    # Section 5: Agent Research Process
    render_agent_process(
        plan_reasoning=plan_reasoning,
        dag_subtasks=dag_subtasks,
        task_states=task_states,
        reasoning_confidence=confidence,
        reasoning_insights=reasoning_insights,
        elapsed=elapsed,
        total_tasks=total_tasks,
        success_tasks=success_tasks,
        failed_tasks=failed_tasks,
    )

    # Section 6: Data Sources
    render_data_sources(
        dag_subtasks=dag_subtasks,
        task_states=task_states,
        sources=sources,
    )

    # Section 7: Appendix
    render_appendix(
        events=events,
        task_states=task_states,
        elapsed=elapsed,
        total_tasks=total_tasks,
        success_tasks=success_tasks,
        failed_tasks=failed_tasks,
    )


# ============================================================
# Page: Research (Query Input + Execution)
# ============================================================
def page_research():
    """Research query input and pipeline execution."""
    st.markdown("""
    <div style="
        border-bottom: 2px solid #6366f1;
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
    ">
        <h2 style="
            color: #f0f0f5;
            font-size: 1.5rem;
            font-weight: 700;
            margin: 0;
            letter-spacing: -0.02em;
        ">New Research Query</h2>
    </div>
    """, unsafe_allow_html=True)

    # Query Input
    st.markdown(f"""
    <div style="
        background: #1a1a2e;
        border: 1px solid #2a2a3e;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    ">
    """, unsafe_allow_html=True)

    query = st.text_input(
        "Research Query",
        placeholder="Enter your financial research question (e.g., 'Analyze the impact of AI adoption on semiconductor sector valuations')",
        label_visibility="collapsed",
    )

    col_input, col_btn = st.columns([4, 1])
    with col_btn:
        run_clicked = st.button("Run Research", use_container_width=True, type="primary")

    st.markdown("</div>", unsafe_allow_html=True)

    # Query History
    if st.session_state.history:
        st.markdown("""
        <h3 style="
            color: #e0e0e0;
            font-size: 1.1rem;
            font-weight: 600;
            margin: 1.5rem 0 1rem 0;
        ">Recent Queries</h3>
        """, unsafe_allow_html=True)

        for msg in reversed(st.session_state.history[-5:]):
            st.markdown(f"""
            <div style="
                background: #1a1a2e;
                border: 1px solid #2a2a3e;
                border-radius: 8px;
                padding: 0.75rem 1rem;
                margin-bottom: 0.5rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
            ">
                <span style="color: #c0c0d0; font-size: 0.9rem;">{msg['content']}</span>
                <span style="color: #94a3b8; font-size: 0.75rem;">{msg.get('timestamp', '')[:16]}</span>
            </div>
            """, unsafe_allow_html=True)

    if not query or not run_clicked:
        return

    # Record query
    st.session_state.history.append({
        "role": "user",
        "content": query,
        "timestamp": datetime.now().isoformat(),
    })

    # Execute Research Pipeline
    render_hero_section(
        title="Researching...",
        subtitle=query,
        status="running",
    )

    progress_placeholder = st.empty()
    status_text = st.empty()

    with st.spinner("Executing multi-agent research pipeline..."):
        start_time = time.time()

        async def do_research():
            orchestrator = st.session_state.orchestrator
            results = []
            async for event in orchestrator.run_with_streaming(query):
                results.append(event)
                # Update progress
                stage = event.get("stage", "")
                if stage == "planning":
                    status_text.markdown(
                        "<p style='color: #2563eb; font-weight: 500;'>Planning: Analyzing complexity and selecting strategy...</p>",
                        unsafe_allow_html=True,
                    )
                elif stage == "plan_ready":
                    subtask_count = len(event.get("subtasks", []))
                    status_text.markdown(
                        f"<p style='color: #2563eb; font-weight: 500;'>Plan ready: {subtask_count} subtasks identified. Executing...</p>",
                        unsafe_allow_html=True,
                    )
                elif stage == "task_done":
                    tid = event.get("task_id", "")
                    success = event.get("success", False)
                    icon = "\u2705" if success else "\u274C"
                    status_text.markdown(
                        f"<p style='color: #8888a0;'>{icon} Task {tid} completed</p>",
                        unsafe_allow_html=True,
                    )
                elif stage == "reasoning":
                    status_text.markdown(
                        "<p style='color: #2563eb; font-weight: 500;'>Reasoning: Extracting insights and generating charts...</p>",
                        unsafe_allow_html=True,
                    )
                elif stage == "reporting":
                    status_text.markdown(
                        "<p style='color: #2563eb; font-weight: 500;'>Report: Compiling structured research report...</p>",
                        unsafe_allow_html=True,
                    )
            return results

        profiler = get_profiler()
        with profiler.profile(query):
            events = run_async(do_research())
        elapsed = time.time() - start_time

    status_text.empty()
    progress_placeholder.empty()

    # Parse events
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

    # Try to extract from the orchestrator's report object
    try:
        # Re-parse from report data if available
        for event in events:
            if event.get("stage") == "complete":
                # The report data is embedded in the complete event
                break
    except Exception:
        pass

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
                    # Parse risk factor format: **Name** [severity]: description
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

    # Render charts
    chart_paths = []
    if chart_specs_raw:
        chart_renderer = ChartRenderer()
        for i, spec_dict in enumerate(chart_specs_raw):
            chart_spec = ChartSpec(
                chart_type=spec_dict.get("chart_type", "bar"),
                title=spec_dict.get("title", ""),
                x_label=spec_dict.get("x_label", ""),
                y_label=spec_dict.get("y_label", ""),
                data=spec_dict.get("data", []),
                description=spec_dict.get("description", ""),
            )
            if chart_spec.data:
                try:
                    path = chart_renderer.render(chart_spec, f"research_chart_{i+1}.png")
                    if path and os.path.exists(path):
                        chart_paths.append(path)
                except Exception:
                    pass

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

    # Save to session state
    st.session_state.current_dag_subtasks = dag_subtasks
    st.session_state.current_task_states = task_states
    st.session_state.current_report = report_md
    st.session_state.report_data = {
        "report_markdown": report_md,
        "report_title": report_md.split("\n")[0].lstrip("# ").strip() if report_md else query[:60],
        "answer": answer,
        "summary": summary,
        "key_findings": key_findings,
        "risk_factors": risk_factors,
        "market_trends": market_trends,
        "recommendations": recommendations,
        "confidence": reasoning_confidence,
        "chart_paths": chart_paths,
        "chart_specs": chart_specs_raw,
        "sources": sources,
        "dag_subtasks": dag_subtasks,
        "task_states": task_states,
        "elapsed": elapsed,
        "total_tasks": total_tasks,
        "success_tasks": success_tasks,
        "failed_tasks": failed_tasks,
        "plan_reasoning": plan_reasoning,
        "reasoning_insights": reasoning_insights,
        "events": events,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    # Show success and redirect
    st.success(f"Research completed in {elapsed:.1f}s. View the report below.")

    # Render the report inline
    page_research_report()


# ============================================================
# Page: System Overview
# ============================================================
def page_system_overview():
    st.markdown("""
    <div style="
        border-bottom: 2px solid #6366f1;
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
    ">
        <h2 style="
            color: #f0f0f5;
            font-size: 1.5rem;
            font-weight: 700;
            margin: 0;
            letter-spacing: -0.02em;
        ">System Overview</h2>
        <p style="color: #64748b; font-size: 0.9rem; margin: 0.25rem 0 0 0;">
            Real-time pipeline monitoring and performance metrics
        </p>
    </div>
    """, unsafe_allow_html=True)

    dashboard = get_dashboard()
    from core.observability.metrics import MetricsCollector
    collector = MetricsCollector()
    collector_data = collector.get_all()
    sys_stats = dashboard.get_system_stats()
    llm_stats = st.session_state.orchestrator.get_llm_stats()

    kpi_row([
        {"label": "Total Requests", "value": str(sys_stats["total_requests"])},
        {"label": "Success Rate", "value": f"{sys_stats['success_rate']:.1f}%"},
        {"label": "Avg Latency", "value": f"{sys_stats['avg_duration_ms']:.0f}ms"},
        {"label": "Tool Calls", "value": str(sys_stats.get("total_tool_calls", 0))},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    col_left, col_right = st.columns(2)

    with col_left:
        section_header("Agent Latency", "Avg response time")
        agent_latency = dashboard.get_agent_latency_stats()
        if agent_latency:
            import pandas as pd
            latency_df = pd.DataFrame([
                {"Agent": agent, "Avg Latency (ms)": data["avg_ms"]}
                for agent, data in agent_latency.items()
            ])
            st.bar_chart(latency_df.set_index("Agent"))
        else:
            empty_state("Run a query to collect agent latency data")

    with col_right:
        section_header("Tool Usage", "Call distribution")
        tool_stats = dashboard.get_tool_stats()
        if tool_stats:
            import pandas as pd
            calls_df = pd.DataFrame([
                {"Tool": tool, "Calls": data["calls"]}
                for tool, data in tool_stats.items()
            ])
            st.bar_chart(calls_df.set_index("Tool"))
        else:
            empty_state("Run a query to collect tool usage data")

    st.markdown("<br>", unsafe_allow_html=True)

    section_header("Agent Performance", "Detailed breakdown")
    agent_summary = collector_data.get("agent_summary", {})
    if agent_summary:
        for agent, stats in agent_summary.items():
            st.markdown(f"""
            <div style="
                background: #1a1a2e;
                border: 1px solid #2a2a3e;
                border-radius: 8px;
                padding: 0.75rem 1rem;
                margin-bottom: 0.4rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
            ">
                <span style="color: #e0e0e0; font-weight: 600; font-size: 0.9rem;">{agent}</span>
                <div style="display: flex; gap: 1.5rem;">
                    <span style="color: #8888a0; font-size: 0.8rem;">Calls: <strong style="color: #f0f0f5;">{stats.get('calls', 0)}</strong></span>
                    <span style="color: #8888a0; font-size: 0.8rem;">Tokens: <strong style="color: #f0f0f5;">{stats.get('tokens', 0):,}</strong></span>
                    <span style="color: #8888a0; font-size: 0.8rem;">Errors: <strong style="color: #ef4444;">{stats.get('errors', 0)}</strong></span>
                    <span style="color: #8888a0; font-size: 0.8rem;">Latency: <strong style="color: #f0f0f5;">{stats.get('total_ms', 0):.0f}ms</strong></span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        empty_state("No agent metrics collected yet")

    with st.expander("Raw Metrics Data", expanded=False):
        st.json(collector_data)


# ============================================================
# Page: DAG Execution
# ============================================================
def page_dag_execution():
    st.markdown("""
    <div style="
        border-bottom: 2px solid #6366f1;
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
    ">
        <h2 style="
            color: #f0f0f5;
            font-size: 1.5rem;
            font-weight: 700;
            margin: 0;
            letter-spacing: -0.02em;
        ">DAG Execution</h2>
        <p style="color: #64748b; font-size: 0.9rem; margin: 0.25rem 0 0 0;">
            Task dependency graph and execution status
        </p>
    </div>
    """, unsafe_allow_html=True)

    dag_subtasks = st.session_state.current_dag_subtasks
    task_states = st.session_state.current_task_states

    if not dag_subtasks:
        empty_state("No DAG data available. Run a research query first.", "\U0001F517")
        return

    total_tasks = len(dag_subtasks)
    completed = sum(1 for ts in task_states.values() if ts.get("status") in ("success", "failed", "skipped"))
    success = sum(1 for ts in task_states.values() if ts.get("success"))
    failed = sum(1 for ts in task_states.values() if ts.get("status") in ("failed", "skipped"))

    kpi_row([
        {"label": "Total Tasks", "value": str(total_tasks)},
        {"label": "Completed", "value": str(completed)},
        {"label": "Success", "value": str(success)},
        {"label": "Failed", "value": str(failed)},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    col_dag, col_details = st.columns([2, 1])

    with col_dag:
        section_header("Dependency Graph")
        try:
            dag_path = render_dag(dag_subtasks, task_states)
            if dag_path and os.path.exists(dag_path):
                st.image(dag_path, use_container_width=True)
            else:
                _render_text_dag(dag_subtasks, task_states)
        except Exception:
            _render_text_dag(dag_subtasks, task_states)

    with col_details:
        section_header("Task Status")
        for task in dag_subtasks:
            tid = task["id"]
            ts = task_states.get(tid, {})
            status = ts.get("status", "pending")
            duration = ts.get("duration_ms", 0)

            status_colors = {
                "success": "#059669",
                "failed": "#dc2626",
                "running": "#2563eb",
                "pending": "#94a3b8",
                "skipped": "#d97706",
                "degraded": "#ea580c",
            }
            color = status_colors.get(status, "#94a3b8")

            st.markdown(f"""
            <div style="
                background: #1a1a2e;
                border: 1px solid #2a2a3e;
                border-radius: 8px;
                padding: 0.75rem 1rem;
                margin-bottom: 0.5rem;
                border-left: 3px solid {color};
            ">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <code style="color: #3b82f6; font-size: 0.8rem;">{tid}</code>
                        <span style="color: #64748b; font-size: 0.75rem; margin-left: 0.5rem;">{task['tool']}</span>
                    </div>
                    {status_badge(status)}
                </div>
                <div style="color: #94a3b8; font-size: 0.75rem; margin-top: 4px;">{task.get('desc', '')}</div>
            </div>
            """, unsafe_allow_html=True)

    finished_tasks = {tid: ts for tid, ts in task_states.items() if ts.get("duration_ms", 0) > 0}
    if finished_tasks:
        st.markdown("<br>", unsafe_allow_html=True)
        section_header("Task Duration", "Execution time breakdown")
        import pandas as pd
        chart_data = {
            tid: ts["duration_ms"]
            for tid, ts in sorted(finished_tasks.items(), key=lambda x: x[1]["duration_ms"], reverse=True)
        }
        st.bar_chart(chart_data)


def _render_text_dag(subtasks: list[dict], task_states: dict):
    """Text DAG fallback"""
    for task in subtasks:
        tid = task["id"]
        ts = task_states.get(tid, {})
        status = ts.get("status", "pending")
        duration = ts.get("duration_ms", 0)
        deps = task.get("depends_on", [])
        dep_text = f" \u2190 {', '.join(deps)}" if deps else ""
        dur_text = f" ({duration:.0f}ms)" if duration > 0 else ""

        st.markdown(f"""
        <div style="
            background: #1a1a2e;
            border: 1px solid #2a2a3e;
            border-radius: 8px;
            padding: 0.75rem 1rem;
            margin-bottom: 0.4rem;
        ">
            <code style="color: #3b82f6;">{tid}</code>
            <span style="color: #64748b;">[{task['tool']}]</span>
            {status_badge(status)}
            <span style="color: #94a3b8; font-size: 0.8rem;">{task.get('desc', '')}{dep_text}{dur_text}</span>
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# Page: Metrics Dashboard
# ============================================================
def page_metrics_dashboard():
    st.markdown("""
    <div style="
        border-bottom: 2px solid #6366f1;
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
    ">
        <h2 style="
            color: #f0f0f5;
            font-size: 1.5rem;
            font-weight: 700;
            margin: 0;
            letter-spacing: -0.02em;
        ">Metrics Dashboard</h2>
        <p style="color: #64748b; font-size: 0.9rem; margin: 0.25rem 0 0 0;">
            System performance analytics
        </p>
    </div>
    """, unsafe_allow_html=True)

    dashboard = get_dashboard()
    from core.observability.metrics import MetricsCollector
    collector = MetricsCollector()
    collector_data = collector.get_all()

    sys_stats = dashboard.get_system_stats()
    kpi_row([
        {"label": "Total Requests", "value": str(sys_stats["total_requests"])},
        {"label": "Success Rate", "value": f"{sys_stats['success_rate']:.1f}%"},
        {"label": "Avg DAG Size", "value": f"{sys_stats['avg_dag_size']:.1f}"},
        {"label": "Avg Duration", "value": f"{sys_stats['avg_duration_ms']:.0f}ms"},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        section_header("Error Rate Trend")
        error_trend = dashboard.get_error_trend()
        if error_trend:
            import pandas as pd
            trend_df = pd.DataFrame([
                {"Run": t["trace_id"], "Errors": t["errors"]}
                for t in error_trend
            ])
            st.line_chart(trend_df.set_index("Run"))
        else:
            empty_state("No error trend data yet")

    with col2:
        section_header("Tool Success Rate")
        tool_stats = dashboard.get_tool_stats()
        if tool_stats:
            for tool, data in tool_stats.items():
                rate = data["success_rate"]
                st.progress(rate / 100, text=f"{tool}: {rate:.1f}%")
        else:
            empty_state("No tool usage data yet")

    with st.expander("Raw Metrics Data", expanded=False):
        st.json(collector_data)


# ============================================================
# Page: Trace Replay
# ============================================================
def page_trace_replay():
    st.markdown("""
    <div style="
        border-bottom: 2px solid #6366f1;
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
    ">
        <h2 style="
            color: #f0f0f5;
            font-size: 1.5rem;
            font-weight: 700;
            margin: 0;
            letter-spacing: -0.02em;
        ">Trace Replay</h2>
        <p style="color: #64748b; font-size: 0.9rem; margin: 0.25rem 0 0 0;">
            Replay recorded DAG executions without LLM calls
        </p>
    </div>
    """, unsafe_allow_html=True)

    recorder = get_recorder()
    replayer = get_replayer()

    saved_traces = recorder.list_saved_traces()

    if not saved_traces:
        sessions = recorder.get_sessions()
        if sessions:
            section_header("In-Memory Traces")
            for i, sess in enumerate(sessions):
                col_info, col_action = st.columns([3, 1])
                with col_info:
                    st.markdown(f"""
                    <div style="
                        background: #1a1a2e;
                        border: 1px solid #2a2a3e;
                        border-radius: 8px;
                        padding: 1rem;
                    ">
                        <div style="            color: #f0f0f5;
            font-weight: 500;
        ">{sess.query[:60]}</div>
        <div style="color: #6b7280; font-size: 0.8rem; margin-top: 4px;">
                            Trace: {sess.trace_id[:8]} | {sess.total_ms:.0f}ms | {len(sess.events)} events
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_action:
                    if st.button("Load", key=f"load_mem_{i}"):
                        replayer.load_session(sess)
                        st.session_state.replay_loaded = True
                        st.rerun()
        else:
            empty_state("No saved traces. Enable trace recording and run a query first.", "\U0001F504")
        return

    section_header("Saved Traces")
    trace_options = [
        f"{t['trace_id'][:8]} - {t['query']} ({t['total_ms']:.0f}ms)"
        for t in saved_traces
    ]

    selected_idx = st.selectbox("Select trace", range(len(saved_traces)), format_func=lambda i: trace_options[i])

    col_load, col_info = st.columns([1, 3])
    with col_load:
        if st.button("Load Trace"):
            filepath = saved_traces[selected_idx]["filepath"]
            replayer.load_from_file(filepath)
            st.session_state.replay_loaded = True
            st.rerun()

    with col_info:
        trace_info = saved_traces[selected_idx]
        st.markdown(f"""
        <span style='color: #64748b;'>
            Trace: <code>{trace_info['trace_id'][:8]}</code> |
            Duration: {trace_info['total_ms']:.0f}ms |
            Events: {trace_info['event_count']}
        </span>
        """, unsafe_allow_html=True)

    st.markdown("---")

    if not replayer.is_loaded:
        empty_state("Load a trace to start replay", "\U0001F504")
        return

    summary = replayer.get_summary()

    section_header("Replay Controls")
    col_play, col_step, col_reset = st.columns(3)
    with col_play:
        if st.button("Auto Replay"):
            st.session_state.replay_running = True
            st.rerun()
    with col_step:
        if st.button("Next Step"):
            result = replayer.step()
            if result:
                if "replay_steps" not in st.session_state:
                    st.session_state.replay_steps = []
                st.session_state.replay_steps.append(result)
            st.rerun()
    with col_reset:
        if st.button("Reset"):
            replayer.reset()
            st.session_state.replay_steps = []
            st.session_state.replay_running = False
            st.rerun()

    kpi_row([
        {"label": "Progress", "value": f"{summary.get('progress', 0)*100:.0f}%"},
        {"label": "Tasks", "value": str(summary.get("total_tasks", 0))},
        {"label": "Success", "value": str(summary.get("success_count", 0))},
        {"label": "Failed", "value": str(summary.get("failed_count", 0))},
    ])

    with st.expander("Trace Summary", expanded=False):
        if replayer.session:
            st.json(replayer.session.to_dict())


# ============================================================
# Page: Latency Profiling
# ============================================================
def page_latency_profiling():
    st.markdown("""
    <div style="
        border-bottom: 2px solid #6366f1;
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
    ">
        <h2 style="
            color: #f0f0f5;
            font-size: 1.5rem;
            font-weight: 700;
            margin: 0;
            letter-spacing: -0.02em;
        ">Latency Profiling</h2>
        <p style="color: #64748b; font-size: 0.9rem; margin: 0.25rem 0 0 0;">
            Pipeline performance bottleneck analysis
        </p>
    </div>
    """, unsafe_allow_html=True)

    profiler = get_profiler()
    reports = profiler.get_all_reports()

    if not reports:
        empty_state("No profiling data. Run a query with profiling activated.", "\U0001F52C")
        return

    report_options = [
        f"{r.trace_id[:8]} - {r.query[:40]} ({r.total_latency_ms:.0f}ms)"
        for r in reports
    ]
    selected = st.selectbox("Report", range(len(reports)), index=len(reports) - 1, format_func=lambda i: report_options[i])
    report = reports[selected]

    kpi_row([
        {"label": "Total Latency", "value": f"{report.total_latency_ms:.0f}ms"},
        {"label": "Bottleneck", "value": report.bottleneck_stage},
        {"label": "Tasks", "value": f"{report.success_count}/{report.subtask_count}"},
        {"label": "Failed", "value": str(report.failed_count)},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    col_stages, col_tools = st.columns(2)

    with col_stages:
        section_header("Stage Latency", "Breakdown by pipeline stage")
        import pandas as pd
        stages = {
            "Routing": report.routing_latency_ms,
            "Planner": report.planner_latency_ms,
            "Executor": report.executor_latency_ms,
            "Reasoner": report.reasoner_latency_ms,
            "Report": report.report_latency_ms,
        }
        stage_df = pd.DataFrame([
            {"Stage": stage, "Latency (ms)": latency}
            for stage, latency in stages.items() if latency > 0
        ])
        if not stage_df.empty:
            st.bar_chart(stage_df.set_index("Stage"))

    with col_tools:
        section_header("Tool Latency", "Breakdown by tool")
        if report.tool_latency:
            tool_df = pd.DataFrame([
                {"Tool": tool, "Latency (ms)": latency}
                for tool, latency in sorted(report.tool_latency.items(), key=lambda x: -x[1])
            ])
            st.bar_chart(tool_df.set_index("Tool"))

    with st.expander("Raw Profiling Report", expanded=False):
        st.json(report.to_dict())


# ============================================================
# Sidebar
# ============================================================
with st.sidebar:
    page = render_sidebar_navigation()

    st.markdown("<div style='margin: 1rem 0; border-top: 1px solid #2a2a3e;'></div>", unsafe_allow_html=True)

    st.markdown(
        "<p style='color: #6b7280; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem;'>System Status</p>",
        unsafe_allow_html=True,
    )

    if not st.session_state.dashboard_active:
        if st.button("Enable Dashboard", key="btn_dashboard"):
            activate_dashboard()
            st.session_state.dashboard_active = True
            st.rerun()
    else:
        st.markdown(
            "<div style='color: #10b981; font-size: 0.8rem; margin-bottom: 0.5rem;'>\u25CF Dashboard Active</div>",
            unsafe_allow_html=True,
        )

    if not st.session_state.profiling_active:
        if st.button("Enable Profiling", key="btn_profiling"):
            activate_profiling()
            st.session_state.profiling_active = True
            st.rerun()
    else:
        st.markdown(
            "<div style='color: #10b981; font-size: 0.8rem; margin-bottom: 0.5rem;'>\u25CF Profiling Active</div>",
            unsafe_allow_html=True,
        )

    recorder = get_recorder()
    if not st.session_state.recorder_active:
        if st.button("Enable Recording", key="btn_recorder"):
            recorder.activate()
            st.session_state.recorder_active = True
            st.rerun()
    else:
        st.markdown(
            "<div style='color: #10b981; font-size: 0.8rem; margin-bottom: 0.5rem;'>\u25CF Recording Active</div>",
            unsafe_allow_html=True,
        )
        sessions = recorder.get_sessions()
        if sessions and st.button("Save Latest Trace", key="btn_save_trace"):
            filepath = recorder.save_session(sessions[-1])
            st.success("Saved")

    st.markdown("<div style='margin: 1rem 0; border-top: 1px solid #2a2a3e;'></div>", unsafe_allow_html=True)

    st.markdown(
        "<p style='color: #6b7280; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem;'>Configuration</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='color: #8888a0; font-size: 0.8rem;'>Model: <code style='color: #8888a0; background: #1a1a2e; padding: 1px 6px; border-radius: 4px; font-size: 0.75rem;'>{st.session_state.orchestrator.llm.config.model}</code></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='color: #8888a0; font-size: 0.8rem;'>Embedding: <code style='color: #8888a0; background: #1a1a2e; padding: 1px 6px; border-radius: 4px; font-size: 0.75rem;'>dev (hash)</code></div>",
        unsafe_allow_html=True,
    )

    if page == "Research":
        st.markdown("<div style='margin: 1rem 0; border-top: 1px solid #2a2a3e;'></div>", unsafe_allow_html=True)
        st.markdown(
            "<p style='color: #6b7280; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem;'>Knowledge Base</p>",
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader("Upload documents", type=["txt", "md"], accept_multiple_files=True, key="file_uploader")
        if uploaded:
            retriever = get_retriever()
            for f in uploaded:
                content = f.read().decode("utf-8")
                retriever.add_document(content, {"source": f.name})
            st.success(f"Indexed {len(uploaded)} document(s)")


# ============================================================
# Page Router
# ============================================================
if page == "Research Report":
    page_research_report()
elif page == "Research":
    page_research()
elif page == "System Overview":
    page_system_overview()
elif page == "DAG Execution":
    page_dag_execution()
elif page == "Metrics Dashboard":
    page_metrics_dashboard()
elif page == "Trace Replay":
    page_trace_replay()
elif page == "Latency Profiling":
    page_latency_profiling()
