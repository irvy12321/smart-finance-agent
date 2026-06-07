"""
Key Findings — 自包含 HTML，通过 st.components.v1.html() 嵌入
"""
import streamlit as st
import streamlit.components.v1 as components
from app.ui.html_styles import key_findings_html


def _derive_cards(key_findings, risk_factors, market_trends, recommendations, confidence, task_states):
    cards = []
    if key_findings:
        cards.append({"title": "Key Findings", "value": str(len(key_findings)),
                       "description": key_findings[0][:100] if key_findings else "", "indicator": "positive"})
    if risk_factors:
        hi = sum(1 for r in risk_factors if r.get("severity") == "high")
        cards.append({"title": "Risk Factors", "value": str(len(risk_factors)),
                       "description": f"{hi} high-severity risks identified" if hi else "Risk assessment complete",
                       "indicator": "negative" if hi > 0 else "neutral"})
    if market_trends:
        cards.append({"title": "Market Trends", "value": str(len(market_trends)),
                       "description": market_trends[0][:100] if market_trends else "", "indicator": "positive"})
    if recommendations:
        cards.append({"title": "Recommendations", "value": str(len(recommendations)),
                       "description": recommendations[0][:100] if recommendations else "", "indicator": "neutral"})
    if confidence > 0:
        cl = "High" if confidence >= 0.7 else "Medium" if confidence >= 0.4 else "Low"
        cards.append({"title": "Confidence", "value": f"{confidence:.0%}",
                       "description": f"Analysis confidence level: {cl}",
                       "indicator": "positive" if confidence >= 0.7 else "neutral"})
    ok = sum(1 for ts in task_states.values() if ts.get("success"))
    total = len(task_states)
    if total > 0:
        cards.append({"title": "Data Sources", "value": f"{ok}/{total}",
                       "description": f"{ok} of {total} data sources successfully retrieved",
                       "indicator": "positive" if ok == total else "neutral"})
    return cards[:6]


def render_key_findings(
    key_findings=None, risk_factors=None, market_trends=None,
    recommendations=None, confidence=0.0, task_states=None,
):
    task_states = task_states or {}
    cards = _derive_cards(
        key_findings or [], risk_factors or [], market_trends or [],
        recommendations or [], confidence, task_states,
    )
    h = 120 if not cards else 280
    components.html(key_findings_html(cards=cards), height=h, scrolling=False)
