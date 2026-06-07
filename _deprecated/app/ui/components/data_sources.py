"""
Data Sources — 自包含 HTML，通过 st.components.v1.html() 嵌入
"""
import streamlit as st
import streamlit.components.v1 as components
from app.ui.html_styles import data_sources_html


def render_data_sources(dag_subtasks=None, task_states=None, sources=None):
    dag_subtasks = dag_subtasks or []
    task_states = task_states or {}
    sources = sources or []

    crawler, news, rag, llm, other = [], [], [], [], []
    cats_map = {
        "crawler": crawler, "crawler_tool": crawler,
        "news_search": news, "news_tool": news,
        "rag_retrieve": rag, "rag_tool": rag,
        "llm_synthesize": llm,
    }
    for t in dag_subtasks:
        tool = t.get("tool", "")
        tid = t.get("id", "")
        ts = task_states.get(tid, {})
        entry = {"task_id": tid, "tool": tool, "description": t.get("desc", ""),
                 "status": ts.get("status", "pending"), "success": ts.get("success", False),
                 "duration_ms": ts.get("duration_ms", 0)}
        cats_map.get(tool, other).append(entry)

    emoji = {"🌐 Web Crawler": crawler, "📰 News Search": news,
             "📚 RAG Knowledge Base": rag, "🧠 LLM Synthesis": llm, "📄 Other Sources": other}
    categories = [(name, srcs) for name, srcs in emoji.items() if srcs]

    h = 120
    if categories:
        h += sum(80 + len(s) * 38 for _, s in categories)
    elif sources:
        h += 80 + len(sources) * 38

    components.html(
        data_sources_html(categories=categories, simple_sources=sources if not dag_subtasks else []),
        height=h,
        scrolling=False,
    )
