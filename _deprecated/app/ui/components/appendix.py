"""
Appendix — 自包含 HTML，通过 st.components.v1.html() 嵌入
"""
import streamlit as st
import streamlit.components.v1 as components
from app.ui.html_styles import appendix_html


def render_appendix(
    events=None, task_states=None, elapsed=0.0,
    total_tasks=0, success_tasks=0, failed_tasks=0,
):
    events = events or []
    task_states = task_states or {}

    h = 160
    if events:
        h += 120 + len(events) * 22
    if task_states:
        h += 80 + len(task_states) * 38

    components.html(
        appendix_html(
            events=events, task_states=task_states,
            elapsed=elapsed, total_tasks=total_tasks,
            success_tasks=success_tasks, failed_tasks=failed_tasks,
        ),
        height=h,
        scrolling=False,
    )
