"""
UI Components - Financial Research Report Theme
Dark professional style (Bloomberg Terminal / Goldman Sachs inspired)
"""
import streamlit as st


# ============================================================
# Financial Research Theme CSS - Dark Professional
# ============================================================
RESEARCH_THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ===== Design Tokens ===== */
:root {
    --sfa-bg:            #0a0a0f;
    --sfa-bg-card:       #1a1a2e;
    --sfa-bg-sub:        #12121a;
    --sfa-bg-card-alt:   #16162a;
    --sfa-border:        #2a2a3e;
    --sfa-border-light:  #1e1e2e;
    --sfa-primary:       #6366f1;
    --sfa-primary-light: #818cf8;
    --sfa-text:          #f0f0f5;
    --sfa-text-body:     #e0e0e0;
    --sfa-text-secondary:#8888a0;
    --sfa-text-tertiary: #a0a0b0;
    --sfa-text-muted:    #6b7280;
    --sfa-success:       #10b981;
    --sfa-success-bg:    #065f46;
    --sfa-error:         #ef4444;
    --sfa-error-bg:      #7f1d1d;
    --sfa-warning:       #f59e0b;
    --sfa-warning-bg:    #78350f;
    --sfa-running:       #6366f1;
    --sfa-running-bg:    #312e81;
    --sfa-degraded:      #f97316;
    --sfa-degraded-bg:   #7c2d12;
    --sfa-radius:        8px;
    --sfa-radius-lg:     12px;
    --sfa-radius-xl:     16px;
}

/* ===== Global ===== */
.stApp {
    background-color: var(--sfa-bg) !important;
    color: var(--sfa-text-body) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

/* ===== Sidebar ===== */
[data-testid="stSidebar"] {
    background-color: var(--sfa-bg-sub) !important;
    border-right: 1px solid var(--sfa-border-light) !important;
}

[data-testid="stSidebar"] .stRadio > div > label {
    color: var(--sfa-text-tertiary) !important;
}

[data-testid="stSidebar"] .stRadio > div > label[data-checked="true"] {
    color: var(--sfa-primary) !important;
    background-color: rgba(99, 102, 241, 0.1) !important;
    border-radius: var(--sfa-radius) !important;
    padding: 8px 12px !important;
}

/* ===== Headers ===== */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Inter', sans-serif !important;
    color: var(--sfa-text) !important;
    font-weight: 600 !important;
    letter-spacing: -0.02em !important;
}

h1 { font-size: 1.8rem !important; margin-bottom: 0.5rem !important; }
h2 { font-size: 1.4rem !important; margin-bottom: 0.4rem !important; }
h3 { font-size: 1.1rem !important; margin-bottom: 0.3rem !important; }

/* ===== Metrics ===== */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, var(--sfa-bg-card) 0%, var(--sfa-bg-card-alt) 100%) !important;
    border: 1px solid var(--sfa-border) !important;
    border-radius: var(--sfa-radius-lg) !important;
    padding: 20px 24px !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3) !important;
}

[data-testid="stMetric"] label {
    color: var(--sfa-text-secondary) !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}

[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: var(--sfa-text) !important;
    font-size: 1.8rem !important;
    font-weight: 700 !important;
}

[data-testid="stMetric"] [data-testid="stMetricDelta"] {
    font-size: 0.85rem !important;
}

/* ===== Expanders ===== */
.streamlit-expanderHeader {
    background-color: var(--sfa-bg-card) !important;
    border: 1px solid var(--sfa-border) !important;
    border-radius: var(--sfa-radius-lg) !important;
    color: var(--sfa-text-body) !important;
    font-weight: 500 !important;
}

.streamlit-expanderContent {
    background-color: var(--sfa-bg-sub) !important;
    border: 1px solid var(--sfa-border) !important;
    border-top: none !important;
    border-radius: 0 0 var(--sfa-radius-lg) var(--sfa-radius-lg) !important;
}

/* ===== Tabs ===== */
.stTabs [data-baseweb="tab-list"] {
    background-color: var(--sfa-bg-card) !important;
    border-radius: var(--sfa-radius-lg) !important;
    padding: 4px !important;
    gap: 4px !important;
    border: 1px solid var(--sfa-border) !important;
}

.stTabs [data-baseweb="tab"] {
    background-color: transparent !important;
    color: var(--sfa-text-secondary) !important;
    border-radius: var(--sfa-radius) !important;
    padding: 10px 20px !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
}

.stTabs [aria-selected="true"] {
    background-color: var(--sfa-primary) !important;
    color: #ffffff !important;
}

/* ===== Buttons ===== */
.stButton > button {
    background: linear-gradient(135deg, var(--sfa-primary) 0%, #4f46e5 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: var(--sfa-radius) !important;
    padding: 10px 20px !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    transition: all 0.2s ease !important;
}

.stButton > button:hover {
    background: linear-gradient(135deg, var(--sfa-primary-light) 0%, var(--sfa-primary) 100%) !important;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4) !important;
}

/* ===== Progress bar ===== */
.stProgress > div > div {
    background-color: var(--sfa-border) !important;
}

.stProgress > div > div > div {
    background: linear-gradient(90deg, var(--sfa-primary) 0%, var(--sfa-primary-light) 100%) !important;
}

/* ===== Charts ===== */
.stChart {
    background-color: var(--sfa-bg-card) !important;
    border: 1px solid var(--sfa-border) !important;
    border-radius: var(--sfa-radius-lg) !important;
    padding: 16px !important;
}

/* ===== Input ===== */
.stTextInput > div > div > input {
    background-color: var(--sfa-bg-card) !important;
    border: 1px solid var(--sfa-border) !important;
    border-radius: var(--sfa-radius) !important;
    color: var(--sfa-text-body) !important;
    font-size: 0.95rem !important;
    padding: 0.75rem 1rem !important;
}

.stTextInput > div > div > input:focus {
    border-color: var(--sfa-primary) !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
}

.stTextArea > div > div > textarea {
    background-color: var(--sfa-bg-card) !important;
    border: 1px solid var(--sfa-border) !important;
    border-radius: var(--sfa-radius) !important;
    color: var(--sfa-text-body) !important;
}

/* ===== Selectbox ===== */
.stSelectbox > div > div {
    background-color: var(--sfa-bg-card) !important;
    border: 1px solid var(--sfa-border) !important;
    border-radius: var(--sfa-radius) !important;
}

/* ===== Divider ===== */
hr {
    border-color: var(--sfa-border) !important;
    margin: 1.5rem 0 !important;
}

/* ===== Alert boxes ===== */
.stAlert {
    background-color: var(--sfa-bg-card) !important;
    border-radius: var(--sfa-radius) !important;
    border: 1px solid var(--sfa-border) !important;
}

/* ===== DataFrame ===== */
[data-testid="stDataFrame"] {
    border: 1px solid var(--sfa-border) !important;
    border-radius: var(--sfa-radius-lg) !important;
    overflow: hidden !important;
}

/* ===== Scrollbar ===== */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--sfa-bg-sub); }
::-webkit-scrollbar-thumb { background: var(--sfa-border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #3a3a4e; }

/* ===== Main content area ===== */
.block-container {
    padding-top: 2rem !important;
    padding-bottom: 2rem !important;
    max-width: 1200px !important;
}

/* ================================================================
   Reusable Component Classes
   ================================================================ */

/* Section Header */
.sfa-section-header {
    border-bottom: 2px solid var(--sfa-primary);
    padding-bottom: 0.5rem;
    margin: 2rem 0 1.5rem 0;
}
.sfa-section-header h2 {
    color: var(--sfa-text) !important;
    font-size: 1.4rem !important;
    font-weight: 600 !important;
    margin: 0 !important;
    letter-spacing: -0.02em;
}

/* Card */
.sfa-card {
    background: var(--sfa-bg-card);
    border: 1px solid var(--sfa-border);
    border-radius: var(--sfa-radius-lg);
    padding: 1rem 1.25rem;
}

/* Timeline */
.sfa-timeline {
    position: relative;
    padding-left: 1.5rem;
}
.sfa-timeline-stage {
    position: relative;
    padding-left: 2rem;
    padding-bottom: 1.25rem;
}
.sfa-timeline-stage:last-child {
    padding-bottom: 0;
}
.sfa-timeline-dot {
    position: absolute;
    left: 0;
    top: 0;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    border: 3px solid;
    box-sizing: content-box;
}
.sfa-timeline-connector {
    position: absolute;
    left: 6px;
    top: 20px;
    bottom: 0;
    width: 2px;
}

/* Stage Card */
.sfa-stage-card {
    border-radius: var(--sfa-radius);
    padding: 0.85rem 1.15rem;
    border: 1px solid;
}
.sfa-stage-head {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.25rem;
}
.sfa-stage-icon {
    font-size: 1rem;
    line-height: 1;
}
.sfa-stage-name {
    font-weight: 700;
    font-size: 0.9rem;
}
.sfa-stage-desc {
    color: var(--sfa-text-secondary);
    font-size: 0.82rem;
    margin-bottom: 0.2rem;
    line-height: 1.45;
}
.sfa-stage-detail {
    color: var(--sfa-text-tertiary);
    font-size: 0.82rem;
    font-weight: 500;
}

/* Badge */
.sfa-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    line-height: 1.5;
}

/* Insight Card */
.sfa-insight-card {
    display: flex;
    align-items: flex-start;
    gap: 0.65rem;
    margin-bottom: 0.5rem;
    padding: 0.55rem 0.9rem;
    background: var(--sfa-bg-sub);
    border-left: 3px solid var(--sfa-primary);
    border-radius: 0 var(--sfa-radius) var(--sfa-radius) 0;
}

/* Task Row */
.sfa-task-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.55rem 0.9rem;
    margin-bottom: 0.35rem;
    background: var(--sfa-bg-sub);
    border-radius: var(--sfa-radius);
    border-left: 3px solid;
}
.sfa-task-id {
    color: var(--sfa-primary-light);
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 0.8rem;
}
.sfa-task-tool {
    color: var(--sfa-text-secondary);
    font-size: 0.8rem;
    margin-left: 0.5rem;
}
.sfa-task-desc {
    color: var(--sfa-text-muted);
    font-size: 0.78rem;
    margin-left: 0.5rem;
}
.sfa-task-duration {
    color: var(--sfa-text-secondary);
    font-size: 0.78rem;
}
</style>
"""


def inject_theme():
    """Inject financial research theme CSS"""
    st.markdown(RESEARCH_THEME_CSS, unsafe_allow_html=True)


# ============================================================
# KPI Card
# ============================================================
def kpi_card(label: str, value: str, delta: str = None, delta_color: str = "normal"):
    st.metric(label=label, value=value, delta=delta, delta_color=delta_color)


def kpi_row(cards: list[dict], columns: int = 4):
    cols = st.columns(columns)
    for i, card in enumerate(cards):
        with cols[i % columns]:
            kpi_card(
                label=card.get("label", ""),
                value=card.get("value", ""),
                delta=card.get("delta"),
                delta_color=card.get("delta_color", "normal"),
            )


# ============================================================
# Status Badge
# ============================================================
def status_badge(status: str) -> str:
    colors = {
        "success": ("#10b981", "#065f46"),
        "failed": ("#ef4444", "#7f1d1d"),
        "running": ("#6366f1", "#312e81"),
        "pending": ("#f59e0b", "#78350f"),
        "skipped": ("#6b7280", "#1f2937"),
        "degraded": ("#f97316", "#7c2d12"),
    }
    text_color, bg_color = colors.get(status, ("#6b7280", "#1f2937"))
    return f'<span class="sfa-badge" style="background-color: {bg_color}; color: {text_color};">{status.upper()}</span>'


# ============================================================
# Section Header
# ============================================================
def section_header(title: str, right_text: str = None):
    if right_text:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### {title}")
        with col2:
            st.markdown(
                f"<p style='color: #8888a0; font-size: 0.8rem; text-align: right;'>{right_text}</p>",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(f"### {title}")


# ============================================================
# Empty State
# ============================================================
def empty_state(message: str, icon: str = ""):
    st.markdown(f"""
    <div style="text-align: center; padding: 3rem; color: #8888a0;">
        <div style="font-size: 2.5rem; margin-bottom: 0.75rem; opacity: 0.4;">{icon}</div>
        <div style="font-size: 0.95rem;">{message}</div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# Navigation
# ============================================================
PAGES = {
    "Research Report": "\U0001F4CA",
    "Research": "\U0001F50D",
    "System Overview": "\U0001F4C8",
    "DAG Execution": "\U0001F517",
    "Metrics Dashboard": "\U0001F4CB",
    "Trace Replay": "\U0001F504",
    "Latency Profiling": "\U0001F52C",
}


def render_sidebar_navigation():
    st.markdown("""
    <div style="padding: 1rem 0;">
        <div style="font-size: 1.2rem; font-weight: 700; color: #f0f0f5; letter-spacing: -0.02em;">
            Smart Finance
        </div>
        <div style="font-size: 0.75rem; color: #6366f1; font-weight: 500; margin-top: 2px;">
            RESEARCH PLATFORM
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='margin: 1rem 0; border-top: 1px solid #2a2a3e;'></div>", unsafe_allow_html=True)

    st.markdown(
        "<p style='color: #6b7280; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem;'>Navigation</p>",
        unsafe_allow_html=True,
    )

    page = st.radio(
        "Navigation",
        list(PAGES.keys()),
        format_func=lambda x: f"{PAGES[x]}  {x}",
        label_visibility="collapsed",
        key="page_selector",
    )

    return page
