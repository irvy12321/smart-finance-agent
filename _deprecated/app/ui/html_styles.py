"""
HTML Styles & Templates — 自包含 CSS + HTML 模板
所有组件通过 st.components.v1.html() 嵌入，绕过 Streamlit HTML 过滤。
"""
from string import Template

# ================================================================
# Design Tokens + Component CSS  (完整，iframe 内自包含)
# ================================================================
SHARED_CSS = Template("""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --bg:       #0a0a0f;  --bg-card:   #1a1a2e;  --bg-sub:    #12121a;
    --bg-alt:   #16162a;  --border:    #2a2a3e;  --border-lt: #1e1e2e;
    --primary:  #6366f1;  --primary-l: #818cf8;
    --text:     #f0f0f5;  --text-body: #e0e0e0;  --text-sec:  #8888a0;
    --text-ter: #a0a0b0;  --text-mut:  #6b7280;
    --success:  #10b981;  --success-bg:#065f46;
    --error:    #ef4444;  --error-bg:  #7f1d1d;
    --warning:  #f59e0b;  --warning-bg:#78350f;
    --running:  #6366f1;  --running-bg:#312e81;
    --degraded: #f97316;  --degraded-bg:#7c2d12;
    --radius:   8px;  --radius-lg: 12px;  --radius-xl: 16px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
    background: var(--bg); color: var(--text-body);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 14px; line-height: 1.5;
    -webkit-font-smoothing: antialiased;
}

/* Section Header */
.sfa-sec-hd { border-bottom: 2px solid var(--primary); padding-bottom: 0.5rem; margin-bottom: 1.25rem; }
.sfa-sec-hd h2 { color: var(--text); font-size: 1.35rem; font-weight: 600; letter-spacing: -0.02em; }

/* Card */
.sfa-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 1rem 1.25rem; }

/* Timeline */
.sfa-tl { position: relative; padding-left: 1.5rem; }
.sfa-tl-stage { position: relative; padding-left: 2rem; padding-bottom: 1.15rem; }
.sfa-tl-stage:last-child { padding-bottom: 0; }
.sfa-tl-dot {
    position: absolute; left: 0; top: 0;
    width: 14px; height: 14px; border-radius: 50%;
    border: 3px solid; box-sizing: content-box;
}
.sfa-tl-line {
    position: absolute; left: 6px; top: 20px; bottom: 0; width: 2px;
}
/* Stage Card */
.sfa-stg { border-radius: var(--radius); padding: 0.8rem 1.1rem; border: 1px solid; }
.sfa-stg-hd { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.2rem; }
.sfa-stg-icon { font-size: 1rem; line-height: 1; }
.sfa-stg-name { font-weight: 700; font-size: 0.88rem; }
.sfa-stg-desc { color: var(--text-sec); font-size: 0.8rem; margin-bottom: 0.15rem; line-height: 1.4; }
.sfa-stg-detail { color: var(--text-ter); font-size: 0.8rem; font-weight: 500; }

/* Badge */
.sfa-badge {
    display: inline-block; padding: 2px 8px; border-radius: 3px;
    font-size: 0.63rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.05em; line-height: 1.5;
}

/* Insight Card */
.sfa-insight {
    display: flex; align-items: flex-start; gap: 0.6rem;
    margin-bottom: 0.45rem; padding: 0.5rem 0.85rem;
    background: var(--bg-sub); border-left: 3px solid var(--primary);
    border-radius: 0 var(--radius) var(--radius) 0;
}

/* Task Row */
.sfa-task {
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.5rem 0.85rem; margin-bottom: 0.3rem;
    background: var(--bg-sub); border-radius: var(--radius); border-left: 3px solid;
}
.sfa-task-id { color: var(--primary-l); font-family: 'SF Mono','Fira Code',monospace; font-size: 0.78rem; }
.sfa-task-tool { color: var(--text-sec); font-size: 0.78rem; margin-left: 0.5rem; }
.sfa-task-desc { color: var(--text-mut); font-size: 0.75rem; margin-left: 0.5rem; }
.sfa-task-dur { color: var(--text-sec); font-size: 0.75rem; }

/* Findings Card Grid */
.sfa-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px,1fr)); gap: 0.85rem; }
.sfa-fcard {
    background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-lg);
    padding: 1.25rem; display: flex; flex-direction: column; justify-content: space-between; min-height: 150px;
}
.sfa-fcard-title { color: var(--text-mut); font-size: 0.68rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.4rem; }
.sfa-fcard-value { color: var(--text); font-size: 1.7rem; font-weight: 700; letter-spacing: -0.02em; }
.sfa-fcard-desc { color: var(--text-sec); font-size: 0.78rem; line-height: 1.4; border-top: 1px solid var(--border); padding-top: 0.45rem; margin-top: 0.45rem; }
.sfa-fcard-ind { width: 4px; height: 4px; border-radius: 50%; display: inline-block; margin-right: 6px; vertical-align: middle; }

/* Source Row */
.sfa-src {
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.45rem 0.75rem; margin-bottom: 0.25rem;
    background: var(--bg-sub); border-radius: 6px;
}
.sfa-src-id { color: var(--primary-l); font-family: 'SF Mono','Fira Code',monospace; font-size: 0.78rem; }
.sfa-src-desc { color: var(--text-sec); font-size: 0.78rem; margin-left: 0.5rem; }
.sfa-src-status { font-size: 0.68rem; font-weight: 600; text-transform: uppercase; }

/* Appendix Event Row */
.sfa-event {
    font-family: 'SF Mono','Fira Code',monospace; font-size: 0.78rem; color: var(--text-sec);
    padding: 0.2rem 0; border-bottom: 1px solid var(--border-lt);
}
.sfa-event-stage { color: var(--primary-l); }

/* Summary Finding */
.sfa-sum-finding {
    display: flex; align-items: flex-start; gap: 0.7rem;
    margin-bottom: 0.65rem; padding: 0.65rem 0.95rem;
    background: var(--bg-sub); border-left: 3px solid var(--primary);
    border-radius: 0 var(--radius) var(--radius) 0;
}
.sfa-sum-bullet { color: var(--primary); font-weight: 700; flex-shrink: 0; margin-top: 1px; }
.sfa-sum-text { color: #c0c0d0; font-size: 0.92rem; line-height: 1.6; }

/* Details/Summary (替代 Streamlit expander) */
details { margin-bottom: 0.5rem; }
details summary {
    background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-lg);
    padding: 0.7rem 1rem; color: var(--text-body); font-weight: 500; cursor: pointer;
    list-style: none; display: flex; align-items: center; gap: 0.5rem;
}
details summary::-webkit-details-marker { display: none; }
details summary::before { content: '\\25B6'; font-size: 0.65rem; color: var(--text-sec); transition: transform 0.2s; }
details[open] summary::before { transform: rotate(90deg); }
details[open] summary { border-radius: var(--radius-lg) var(--radius-lg) 0 0; border-bottom: none; }
details .details-body {
    background: var(--bg-sub); border: 1px solid var(--border); border-top: none;
    border-radius: 0 0 var(--radius-lg) var(--radius-lg); padding: 0.75rem 1rem;
}

/* Metric grid (替代 st.metric) */
.sfa-metrics { display: grid; grid-template-columns: repeat(4,1fr); gap: 0.75rem; margin-bottom: 1rem; }
.sfa-metric {
    background: linear-gradient(135deg, var(--bg-card), var(--bg-alt));
    border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 1rem 1.25rem;
}
.sfa-metric-label { color: var(--text-sec); font-size: 0.72rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }
.sfa-metric-value { color: var(--text); font-size: 1.6rem; font-weight: 700; margin-top: 0.2rem; }

/* Hero */
.sfa-hero {
    background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg) 50%, var(--bg-card) 100%);
    border: 1px solid var(--border); border-radius: var(--radius-xl);
    padding: 2.25rem 2.75rem; margin-bottom: 1.75rem; position: relative; overflow: hidden;
}
.sfa-hero-glow {
    position: absolute; top: 0; right: 0; width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(99,102,241,0.08) 0%, transparent 70%);
    pointer-events: none;
}
.sfa-hero-badge {
    display: inline-block; background: rgba(99,102,241,0.15); color: var(--primary-l);
    padding: 4px 12px; border-radius: 4px; font-size: 0.68rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.85rem;
}
.sfa-hero-title { color: var(--text); font-size: 1.9rem; font-weight: 700; letter-spacing: -0.03em; line-height: 1.2; margin: 0.4rem 0 0.25rem; }
.sfa-hero-sub { color: var(--text-sec); font-size: 0.95rem; margin: 0 0 1.25rem; line-height: 1.55; max-width: 700px; }
.sfa-hero-info { padding-top: 0.85rem; border-top: 1px solid rgba(255,255,255,0.06); }
.sfa-hero-info table { width: 100%; border-collapse: collapse; }
.sfa-hero-info td { padding: 3px 20px 3px 0; white-space: nowrap; }
.sfa-hero-label { color: var(--text-mut); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; }
.sfa-hero-val { color: var(--text-ter); font-size: 0.82rem; font-weight: 500; }

/* Chart card */
.sfa-chart-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-lg); overflow: hidden; margin-bottom: 1.25rem; }
.sfa-chart-card img { width: 100%; display: block; }
.sfa-chart-cap { padding: 0.85rem 1.25rem; }
.sfa-chart-cap-title { color: var(--text); font-weight: 600; font-size: 0.88rem; margin-bottom: 0.2rem; }
.sfa-chart-cap-desc { color: var(--text-sec); font-size: 0.82rem; line-height: 1.45; }
""")


# ================================================================
# Helpers
# ================================================================
def _wrap(body_html: str, css: str = "") -> str:
    """将 HTML 片段包装成完整自包含文档。"""
    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        f'<style>{SHARED_CSS.safe_substitute()}{css}</style>'
        f'</head><body>{body_html}</body></html>'
    )


# ================================================================
# Hero Section
# ================================================================
def hero_html(
    title="Smart Finance Research Platform",
    subtitle="AI-Powered Financial Intelligence",
    updated_at="2026-01-01 00:00",
    sources_count=0,
    confidence=0.0,
    status="ready",
):
    status_map = {
        "ready":    ("#6b7280", "rgba(107,114,128,0.15)", "STANDBY"),
        "running":  ("#818cf8", "rgba(129,140,248,0.15)", "RESEARCHING"),
        "complete": ("#10b981", "rgba(16,185,129,0.15)", "COMPLETE"),
        "error":    ("#ef4444", "rgba(239,68,68,0.15)",  "ERROR"),
    }
    accent, bg, label = status_map.get(status, status_map["ready"])

    return _wrap(f"""
<div class="sfa-hero">
  <div class="sfa-hero-glow"></div>
  <div style="position:relative;z-index:1;">
    <div class="sfa-hero-badge">Research Report</div>
    <div class="sfa-hero-title">{title}</div>
    <div class="sfa-hero-sub">{subtitle}</div>
    <div class="sfa-hero-info">
      <table><tr>
        <td><span class="sfa-hero-label">Updated </span><span class="sfa-hero-val">{updated_at}</span></td>
        <td><span class="sfa-hero-label">Sources </span><span class="sfa-hero-val">{sources_count}</span></td>
        <td><span class="sfa-hero-label">Confidence </span><span class="sfa-hero-val">{confidence:.0%}</span></td>
        <td><span class="sfa-badge" style="background:{bg};color:{accent};">{label}</span></td>
      </tr></table>
    </div>
  </div>
</div>
""")


# ================================================================
# Executive Summary
# ================================================================
def executive_summary_html(summary="", findings=None):
    findings = findings or []

    empty = ""
    if not summary:
        empty = """
<div class="sfa-card" style="text-align:center;padding:2.5rem;">
  <div style="font-size:2.2rem;margin-bottom:0.6rem;opacity:0.4;">📊</div>
  <p style="color:var(--text-sec);font-size:0.92rem;margin:0;">Run a research query to generate an executive summary.</p>
</div>"""
        return _wrap(f"""
<div class="sfa-sec-hd"><h2>Executive Summary</h2></div>
{empty}
""")

    findings_html = ""
    if findings:
        items = "".join(f"""
<div class="sfa-sum-finding">
  <span class="sfa-sum-bullet">▶</span>
  <span class="sfa-sum-text">{f}</span>
</div>""" for f in findings)
        findings_html = f"""
<h3 style="color:var(--text);font-size:1.05rem;font-weight:600;margin:1.25rem 0 0.75rem;">Core Viewpoints</h3>
{items}"""

    return _wrap(f"""
<div class="sfa-sec-hd"><h2>Executive Summary</h2></div>
<div class="sfa-card" style="padding:1.75rem 2.25rem;margin-bottom:1.25rem;">
  <p style="color:var(--text-body);font-size:1.02rem;line-height:1.8;margin:0;">{summary}</p>
</div>
{findings_html}
""")


# ================================================================
# Key Findings
# ================================================================
def key_findings_html(cards=None):
    cards = cards or []
    if not cards:
        return _wrap("""
<div class="sfa-sec-hd"><h2>Key Findings</h2></div>
<div class="sfa-card" style="text-align:center;padding:2rem;">
  <p style="color:var(--text-sec);font-size:0.92rem;margin:0;">Key findings will appear after research completes.</p>
</div>
""")
    ind_colors = {"positive": "var(--success)", "negative": "var(--error)", "neutral": "var(--text-mut)"}
    items = ""
    for c in cards:
        ind = c.get("indicator", "neutral")
        items += f"""
<div class="sfa-fcard">
  <div>
    <div class="sfa-fcard-title"><span class="sfa-fcard-ind" style="background:{ind_colors.get(ind,'var(--text-mut)')}"></span>{c['title']}</div>
    <div class="sfa-fcard-value">{c['value']}</div>
  </div>
  <div class="sfa-fcard-desc">{c.get('description','')}</div>
</div>"""

    return _wrap(f"""
<div class="sfa-sec-hd"><h2>Key Findings</h2></div>
<div class="sfa-cards">{items}</div>
""")


# ================================================================
# Market Analysis
# ================================================================
def market_analysis_html(report_html="", charts=None, answer=""):
    charts = charts or []

    if not report_html and not charts and not answer:
        return _wrap("""
<div class="sfa-sec-hd"><h2>Market Analysis</h2></div>
<div class="sfa-card" style="text-align:center;padding:2.5rem;">
  <div style="font-size:2.2rem;margin-bottom:0.6rem;opacity:0.4;">📈</div>
  <p style="color:var(--text-sec);font-size:0.92rem;margin:0;">Charts and market analysis will appear after research completes.</p>
</div>
""")

    content = ""
    if report_html:
        content += f'<div class="sfa-card" style="padding:1.75rem 2.25rem;margin-bottom:1.5rem;">{report_html}</div>'
    elif answer:
        content += f'<div class="sfa-card" style="padding:1.75rem 2.25rem;margin-bottom:1.5rem;"><p style="color:var(--text-body);font-size:0.92rem;line-height:1.8;margin:0;">{answer}</p></div>'

    if charts:
        content += '<h3 style="color:var(--text);font-size:1.05rem;font-weight:600;margin:1.25rem 0 0.75rem;">Research Charts</h3>'
        for ch in charts:
            cap = ""
            if ch.get("title") or ch.get("description"):
                cap = '<div class="sfa-chart-cap">'
                if ch.get("title"):
                    cap += f'<div class="sfa-chart-cap-title">{ch["title"]}</div>'
                if ch.get("description"):
                    cap += f'<div class="sfa-chart-cap-desc">{ch["description"]}</div>'
                cap += '</div>'
            content += f"""
<div class="sfa-chart-card">
  <img src="{ch['src']}" alt="chart">
  {cap}
</div>"""

    return _wrap(f"""
<div class="sfa-sec-hd"><h2>Market Analysis</h2></div>
{content}
""")


# ================================================================
# Agent Process (Timeline)
# ================================================================
_STATUS = {
    "complete": ("#10b981", "rgba(16,185,129,0.08)",  "#065f46", "#10b981"),
    "running":  ("#818cf8", "rgba(129,140,248,0.08)",  "#312e81", "#818cf8"),
    "pending":  ("#6b7280", "rgba(107,114,128,0.04)",  "#2a2a3e", "#4a4a5e"),
}
_TASK_CLR = {
    "success": "#10b981", "failed": "#ef4444", "running": "#818cf8",
    "pending": "#6b7280", "skipped": "#f59e0b", "degraded": "#f97316",
}


def agent_process_html(stages=None, insights=None, dag_subtasks=None, task_states=None):
    stages = stages or []
    insights = insights or []
    dag_subtasks = dag_subtasks or []
    task_states = task_states or {}

    # Timeline
    tl_items = ""
    for i, stg in enumerate(stages):
        color, bg, border, dot = _STATUS.get(stg["status"], _STATUS["pending"])
        is_last = i == len(stages) - 1
        line = ""
        if not is_last:
            nc = _STATUS[stages[i + 1]["status"]][3]
            line = f'<div class="sfa-tl-line" style="background:{nc};"></div>'
        detail = f'<div class="sfa-stg-detail">{stg["detail"]}</div>' if stg.get("detail") else ""
        tl_items += f"""
<div class="sfa-tl-stage">
  <div class="sfa-tl-dot" style="background:{dot};border-color:{bg};box-shadow:0 0 0 2px {border};"></div>
  {line}
  <div class="sfa-stg" style="background:{bg};border-color:{border};">
    <div class="sfa-stg-hd">
      <span class="sfa-stg-icon">{stg['icon']}</span>
      <span class="sfa-stg-name" style="color:{color};">{stg['name']}</span>
      <span class="sfa-badge" style="background:{color};color:#fff;">{stg['status']}</span>
    </div>
    <div class="sfa-stg-desc">{stg['description']}</div>
    {detail}
  </div>
</div>"""

    timeline = f'<div class="sfa-tl">{tl_items}</div>' if tl_items else ""

    # Insights
    ins_html = ""
    if insights:
        ins_items = "".join(f"""
<div class="sfa-insight">
  <span style="color:var(--primary);flex-shrink:0;">●</span>
  <span style="color:#c0c0d0;font-size:0.86rem;line-height:1.5;">{ins}</span>
</div>""" for ins in insights)
        ins_html = f"""
<h3 style="color:var(--text);font-size:1rem;font-weight:600;margin:1.1rem 0 0.65rem;">Reasoning Insights</h3>
{ins_items}"""

    # Task Details
    task_html = ""
    if dag_subtasks and task_states:
        rows = ""
        for t in dag_subtasks:
            tid = t["id"]
            ts = task_states.get(tid, {})
            status = ts.get("status", "pending")
            dur = ts.get("duration_ms", 0)
            clr = _TASK_CLR.get(status, "#6b7280")
            dur_s = f'<span class="sfa-task-dur">{dur:.0f}ms</span>' if dur > 0 else ""
            rows += f"""
<div class="sfa-task" style="border-left-color:{clr};">
  <div>
    <code class="sfa-task-id">{tid}</code>
    <span class="sfa-task-tool">{t.get('tool','')}</span>
    <span class="sfa-task-desc">{t.get('desc','')[:60]}</span>
  </div>
  <div style="display:flex;align-items:center;gap:0.75rem;">
    {dur_s}
    <span class="sfa-badge" style="background:{clr};color:#fff;">{status}</span>
  </div>
</div>"""
        task_html = f"""
<details>
  <summary>Task Execution Details</summary>
  <div class="details-body">{rows}</div>
</details>"""

    return _wrap(f"""
<div class="sfa-sec-hd"><h2>Agent Research Process</h2></div>
{timeline}
{ins_html}
{task_html}
""")


# ================================================================
# Data Sources
# ================================================================
def data_sources_html(categories=None, simple_sources=None):
    categories = categories or []
    simple_sources = simple_sources or []

    if not categories and not simple_sources:
        return _wrap("""
<div class="sfa-sec-hd"><h2>Data Sources</h2></div>
<div class="sfa-card" style="text-align:center;padding:2rem;">
  <p style="color:var(--text-sec);font-size:0.92rem;margin:0;">Data sources will be listed after research completes.</p>
</div>
""")

    cats_html = ""
    for cat_name, cat_sources in categories:
        if not cat_sources:
            continue
        ok = sum(1 for s in cat_sources if s.get("success"))
        total = len(cat_sources)
        rows = ""
        for s in cat_sources:
            st = s.get("status", "pending")
            clr = _TASK_CLR.get(st, "#6b7280")
            dur = s.get("duration_ms", 0)
            dur_s = f'<span style="color:var(--text-sec);font-size:0.73rem;">{dur:.0f}ms</span>' if dur > 0 else ""
            rows += f"""
<div class="sfa-src">
  <div>
    <code class="sfa-src-id">{s['task_id']}</code>
    <span class="sfa-src-desc">{s.get('description','')[:80]}</span>
  </div>
  <div style="display:flex;align-items:center;gap:0.5rem;">
    {dur_s}
    <span class="sfa-src-status" style="color:{clr};">{st}</span>
  </div>
</div>"""
        cats_html += f"""
<details>
  <summary>{cat_name} ({ok}/{total} successful)</summary>
  <div class="details-body">{rows}</div>
</details>"""

    src_html = ""
    if simple_sources and not categories:
        rows = "".join(f"""
<div class="sfa-src">
  <span style="color:#c0c0d0;font-size:0.82rem;">{s.get('tool','N/A')} – {s.get('task_id','')}</span>
  <span style="color:var(--text-mut);font-size:0.78rem;">{s.get('duration_ms',0):.0f}ms</span>
</div>""" for s in simple_sources)
        src_html = f"""
<details>
  <summary>Sources ({len(simple_sources)})</summary>
  <div class="details-body">{rows}</div>
</details>"""

    return _wrap(f"""
<div class="sfa-sec-hd"><h2>Data Sources</h2></div>
{cats_html}
{src_html}
""")


# ================================================================
# Appendix
# ================================================================
def appendix_html(events=None, task_states=None, elapsed=0.0, total_tasks=0, success_tasks=0, failed_tasks=0):
    events = events or []
    task_states = task_states or {}

    metrics_html = ""
    if total_tasks > 0:
        items = [
            ("Total Tasks", str(total_tasks)),
            ("Successful", str(success_tasks)),
            ("Failed", str(failed_tasks)),
            ("Duration", f"{elapsed:.1f}s"),
        ]
        cells = "".join(
            f'<div class="sfa-metric"><div class="sfa-metric-label">{l}</div><div class="sfa-metric-value">{v}</div></div>'
            for l, v in items
        )
        metrics_html = f'<div class="sfa-metrics">{cells}</div>'

    # Event trace
    trace_html = ""
    if events:
        stage_counts = {}
        for e in events:
            st = e.get("stage", "unknown")
            stage_counts[st] = stage_counts.get(st, 0) + 1
        summary = " &middot; ".join(f'<code style="color:var(--primary-l);font-size:0.78rem;">{s}</code>: {c}' for s, c in stage_counts.items())
        rows = ""
        for e in events:
            stage = e.get("stage", "")
            msg = e.get("message", e.get("task_id", ""))
            ok = e.get("success", None)
            icon = "✅" if ok is True else "❌" if ok is False else "▶"
            rows += f'<div class="sfa-event">{icon} <span class="sfa-event-stage">[{stage}]</span> {msg}</div>'
        trace_html = f"""
<details>
  <summary>Trace Replay</summary>
  <div class="details-body">
    <div style="margin-bottom:0.5rem;font-size:0.82rem;color:var(--text-sec);">{summary}</div>
    {rows}
  </div>
</details>"""

    # Task states
    states_html = ""
    if task_states:
        rows = ""
        for tid, ts in task_states.items():
            status = ts.get("status", "unknown")
            dur = ts.get("duration_ms", 0)
            tool = ts.get("tool", "")
            clr = _TASK_CLR.get(status, "#6b7280")
            rows += f"""
<div class="sfa-task" style="border-left-color:{clr};">
  <div>
    <code class="sfa-task-id">{tid}</code>
    <span class="sfa-task-tool">{tool}</span>
  </div>
  <div style="display:flex;align-items:center;gap:0.75rem;">
    <span class="sfa-task-dur">{dur:.0f}ms</span>
    <span class="sfa-badge" style="background:{clr};color:#fff;">{status}</span>
  </div>
</div>"""
        states_html = f"""
<details>
  <summary>Task States</summary>
  <div class="details-body">{rows}</div>
</details>"""

    return _wrap(f"""
<div class="sfa-sec-hd"><h2>Appendix</h2></div>
{metrics_html}
{trace_html}
{states_html}
""")
