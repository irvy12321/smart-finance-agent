"""
Executive Summary — 自包含 HTML，通过 st.components.v1.html() 嵌入
"""
import streamlit as st
import streamlit.components.v1 as components
from app.ui.html_styles import executive_summary_html


def render_executive_summary(summary: str, key_findings: list[str] = None):
    content = executive_summary_html(summary=summary or "", findings=key_findings)
    h = 200 if not summary else 180 + len(key_findings or []) * 55
    components.html(content, height=h, scrolling=False)
