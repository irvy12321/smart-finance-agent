"""
Market Analysis — 自包含 HTML，通过 st.components.v1.html() 嵌入
图表使用 base64 内联，无需外部文件引用。
"""
import os
import base64
import streamlit as st
import streamlit.components.v1 as components
from app.ui.html_styles import market_analysis_html


def _img_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def render_market_analysis(
    report_markdown: str = None,
    chart_paths: list[str] = None,
    chart_specs: list[dict] = None,
    answer: str = None,
):
    chart_paths = chart_paths or []
    chart_specs = chart_specs or []

    charts = []
    for i, p in enumerate(chart_paths):
        if not p or not os.path.exists(p):
            continue
        spec = chart_specs[i] if i < len(chart_specs) else {}
        charts.append({
            "src": _img_to_base64(p),
            "title": spec.get("title", ""),
            "description": spec.get("description", ""),
        })

    # report_markdown 含 Markdown，转为简单 HTML 段落
    report_html = ""
    if report_markdown:
        report_html = "".join(f"<p style='margin-bottom:0.8rem;'>{ln}</p>" for ln in report_markdown.split("\n") if ln.strip())

    h = 120
    if report_html or answer:
        h += 180
    h += len(charts) * 320

    components.html(
        market_analysis_html(report_html=report_html, charts=charts, answer=answer or ""),
        height=h,
        scrolling=False,
    )
