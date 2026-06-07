"""
Hero Section — 自包含 HTML，通过 st.components.v1.html() 嵌入
"""
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
from app.ui.html_styles import hero_html


def render_hero_section(
    title: str = None,
    subtitle: str = None,
    updated_at: str = None,
    sources_count: int = 0,
    confidence: float = 0.0,
    status: str = "ready",
):
    components.html(
        hero_html(
            title=title or "Smart Finance Research Platform",
            subtitle=subtitle or "AI-Powered Financial Intelligence",
            updated_at=updated_at or datetime.now().strftime("%Y-%m-%d %H:%M"),
            sources_count=sources_count,
            confidence=confidence,
            status=status,
        ),
        height=230,
        scrolling=False,
    )
