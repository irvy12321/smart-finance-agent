"""Utilities for keeping report cards grounded in the full report text."""

import copy
import re
from typing import Any

_LOW_VALUE_TEXT_RE = re.compile(
    "|".join(
        [
            r"completed data collection tools",
            r"data collection tools",
            r"no verifiable key findings",
            r"no reliable market trend",
            r"verify data sources",
            r"report-generation logs",
            r"deterministic fallback",
            r"model output lacked",
            r"已完成数据收集工具",
            r"数据完整性",
            r"后端兜底",
            r"模型输出缺少",
            r"市场趋势未",
            r"核对数据源",
            r"生成日志",
            r"没有从已完成工具",
        ]
    ),
    re.IGNORECASE,
)

_DISCLAIMER_RE = re.compile(
    r"不构成.*投资建议|仅用于.*演示|仅用于.*研究|not investment advice",
    re.IGNORECASE,
)

_BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)]|[一二三四五六七八九十]+[、.])\s+")
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
_MARKDOWN_TOKEN_RE = re.compile(r"[*_`>#]")


def enrich_report_result(result: dict[str, Any]) -> dict[str, Any]:
    """Replace low-value fallback cards with grounded excerpts from answer text."""
    enriched = copy.deepcopy(result)
    answer = str(enriched.get("answer") or "")
    if not answer.strip():
        return enriched

    extracted = extract_report_cards_from_answer(answer)
    if not _has_useful_text(enriched.get("summary")) and extracted.get("summary"):
        enriched["summary"] = extracted["summary"]

    if not _has_useful_items(enriched.get("key_findings")) and extracted.get(
        "key_findings"
    ):
        enriched["key_findings"] = extracted["key_findings"]

    if not _has_useful_items(enriched.get("risk_factors")) and extracted.get(
        "risk_factors"
    ):
        enriched["risk_factors"] = extracted["risk_factors"]

    if not _has_useful_items(enriched.get("market_trends")) and extracted.get(
        "market_trends"
    ):
        enriched["market_trends"] = extracted["market_trends"]

    if not _has_useful_items(enriched.get("recommendations")) and extracted.get(
        "recommendations"
    ):
        enriched["recommendations"] = extracted["recommendations"]

    if not enriched.get("chart_specs") and extracted.get("chart_specs"):
        enriched["chart_specs"] = extracted["chart_specs"]

    return enriched


def extract_report_cards_from_answer(answer: str) -> dict[str, Any]:
    """Extract useful report card fields from already-generated report prose."""
    sections: dict[str, list[str]] = {
        "key_findings": [],
        "risk_factors": [],
        "market_trends": [],
        "recommendations": [],
    }
    summary = ""
    current_section: str | None = None

    for raw_line in answer.splitlines():
        line = raw_line.strip()
        if not line or line in {"---", "***"}:
            continue
        if _DISCLAIMER_RE.search(line):
            continue

        heading = _extract_heading(line)
        if heading:
            current_section = _classify_heading(heading)
            continue

        cleaned = _clean_report_line(line)
        if not _is_useful_text(cleaned):
            continue

        if _looks_like_inline_core_view(line):
            summary = summary or _extract_after_colon(cleaned)
            _append_unique(sections["key_findings"], _extract_after_colon(cleaned))
            continue

        inline_section = _classify_inline_section(cleaned)
        if inline_section:
            current_section = inline_section
            continue

        if _BULLET_RE.match(line):
            if current_section:
                _append_unique(sections[current_section], cleaned)
            elif _contains_data_signal(cleaned):
                _append_unique(sections["key_findings"], cleaned)
            continue

        if current_section in sections and _paragraph_belongs_on_card(cleaned):
            _append_unique(sections[current_section], cleaned)

    key_findings = _limit_items(sections["key_findings"], 4)
    market_trends = _limit_items(sections["market_trends"], 3)
    recommendations = _limit_recommendations(sections["recommendations"], 3)
    risk_factors = [
        _to_risk_factor(item) for item in _limit_items(sections["risk_factors"], 4)
    ]

    if not summary:
        summary = _first_useful_paragraph(answer)

    return {
        "summary": summary,
        "key_findings": key_findings,
        "risk_factors": risk_factors,
        "market_trends": market_trends,
        "recommendations": recommendations,
        "chart_specs": _extract_chart_specs(answer),
    }


def _extract_chart_specs(answer: str) -> list[dict[str, Any]]:
    charts: list[dict[str, Any]] = []
    metric_chart = _extract_metric_chart(answer)
    if metric_chart:
        charts.append(metric_chart)

    series_chart = _extract_money_series_chart(answer)
    if series_chart:
        charts.append(series_chart)

    return charts[:2]


def _extract_metric_chart(answer: str) -> dict[str, Any] | None:
    metrics: dict[str, float] = {}
    for raw_line in answer.splitlines():
        line = _clean_report_line(raw_line)
        lowered = line.lower()
        numbers = _extract_numbers(line)
        if not numbers:
            continue

        if "p/e" in lowered or "pe ratio" in lowered:
            _set_metric(metrics, "P/E", _last_in_range(numbers, 0, 150))
        if "rsi" in lowered:
            _set_metric(metrics, "RSI", _last_in_range(numbers, 0, 100))
        if "roe" in lowered:
            _set_metric(metrics, "ROE %", _last_in_range(numbers, 0, 300))
        if "d/e" in lowered or "debt-to-equity" in lowered:
            _set_metric(metrics, "D/E", _last_in_range(numbers, 0, 20))
        if "eps" in lowered:
            _set_metric(metrics, "EPS", _last_in_range(numbers, 0, 200))

        if len(metrics) >= 5:
            break

    if len(metrics) < 2:
        return None

    return {
        "chart_type": "bar",
        "title": "Key financial metrics",
        "x_label": "Metric",
        "y_label": "Value",
        "data": [
            {"label": label, "value": round(value, 2)}
            for label, value in list(metrics.items())[:5]
        ],
        "description": "Extracted from grounded numbers in the generated report.",
    }


def _extract_money_series_chart(answer: str) -> dict[str, Any] | None:
    for raw_line in answer.splitlines():
        line = _clean_report_line(raw_line)
        money_values = _extract_money_values(line)
        if len(money_values) < 2:
            continue

        lowered = line.lower()
        years = re.findall(r"\b(20\d{2})\b", line)
        if years and len(years) >= len(money_values[:3]):
            labels = years[: len(money_values[:3])]
            title = "Financial trend"
        elif "price" in lowered or all(value < 1000 for value in money_values[:2]):
            labels = ["Start", "End"][: len(money_values[:2])]
            title = "Price movement"
            money_values = money_values[:2]
        else:
            labels = [f"Point {i + 1}" for i in range(len(money_values[:3]))]
            title = "Financial scale"

        values = money_values[: len(labels)]
        if len(values) < 2:
            continue

        return {
            "chart_type": "line",
            "title": title,
            "x_label": "Period",
            "y_label": "Value",
            "data": [
                {"label": label, "value": round(value, 2)}
                for label, value in zip(labels, values, strict=False)
            ],
            "description": "Extracted from monetary values in the generated report.",
        }

    return None


def _set_metric(metrics: dict[str, float], label: str, value: float | None) -> None:
    if value is not None and label not in metrics:
        metrics[label] = value


def _extract_numbers(text: str) -> list[float]:
    values = []
    for match in re.finditer(r"(?<![A-Za-z])[-+]?\d[\d,]*(?:\.\d+)?%?", text):
        token = match.group(0).replace(",", "").rstrip("%")
        try:
            values.append(float(token))
        except ValueError:
            continue
    return values


def _extract_money_values(text: str) -> list[float]:
    values = []
    for match in re.finditer(r"\$\s*([-+]?\d[\d,]*(?:\.\d+)?)", text):
        try:
            values.append(float(match.group(1).replace(",", "")))
        except ValueError:
            continue
    return values


def _last_in_range(
    numbers: list[float], minimum: float, maximum: float
) -> float | None:
    for value in reversed(numbers):
        if minimum <= value <= maximum:
            return value
    return None


def _has_useful_items(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    return any(_item_is_useful(item) for item in value)


def _item_is_useful(item: Any) -> bool:
    if isinstance(item, dict):
        return _has_useful_text(
            " ".join(str(item.get(key, "")) for key in ("factor", "description"))
        )
    return _has_useful_text(str(item))


def _has_useful_text(value: Any) -> bool:
    return _is_useful_text(str(value or ""))


def _is_useful_text(text: str) -> bool:
    stripped = text.strip()
    return (
        bool(stripped)
        and len(stripped) >= 8
        and not _LOW_VALUE_TEXT_RE.search(stripped)
    )


def _extract_heading(line: str) -> str:
    match = _HEADING_RE.match(line)
    if match:
        return _clean_report_line(match.group(1))
    if line.startswith("**") and line.endswith("**") and len(line) < 80:
        return _clean_report_line(line)
    return ""


def _classify_heading(heading: str) -> str | None:
    text = heading.lower()
    if any(token in text for token in ("风险", "看跌", "risk", "bearish")):
        return "risk_factors"
    if any(
        token in text
        for token in ("趋势", "技术分析", "市场情绪", "technical", "trend", "sentiment")
    ):
        return "market_trends"
    if any(
        token in text
        for token in ("建议", "结论", "展望", "recommend", "outlook", "conclusion")
    ):
        return "recommendations"
    if any(
        token in text
        for token in (
            "核心观点",
            "关键发现",
            "估值",
            "财务",
            "综合评估",
            "financial",
            "valuation",
            "finding",
        )
    ):
        return "key_findings"
    return None


def _classify_inline_section(text: str) -> str | None:
    lowered = text.lower().rstrip("：:")
    if lowered in {"看跌/风险因素", "风险因素", "risks", "risk factors"}:
        return "risk_factors"
    if lowered in {"看涨因素", "综合评估", "bullish factors"}:
        return "key_findings"
    if lowered in {"未来展望", "建议", "结论", "recommendations", "outlook"}:
        return "recommendations"
    return None


def _looks_like_inline_core_view(line: str) -> bool:
    cleaned = _clean_report_line(line)
    return bool(re.match(r"^(核心观点|investment thesis)\s*[:：]", cleaned, re.I))


def _extract_after_colon(text: str) -> str:
    parts = re.split(r"[:：]\s*", text, maxsplit=1)
    return parts[-1].strip() if parts else text.strip()


def _clean_report_line(line: str) -> str:
    cleaned = _BULLET_RE.sub("", line).strip()
    cleaned = _MARKDOWN_TOKEN_RE.sub("", cleaned).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" -")


def _contains_data_signal(text: str) -> bool:
    return bool(re.search(r"\d|\$|%|P/E|EPS|RSI|ROE|D/E|营收|净利润|股价", text))


def _paragraph_belongs_on_card(text: str) -> bool:
    if len(text) < 18:
        return False
    return not text.startswith(("根据提供", "本次提供", "在真实场景中"))


def _append_unique(items: list[str], value: str) -> None:
    cleaned = _clean_report_line(value)
    if not _is_useful_text(cleaned):
        return
    if cleaned not in items:
        items.append(cleaned)


def _limit_items(items: list[str], limit: int) -> list[str]:
    return [_truncate(item, 260) for item in items if _is_useful_text(item)][:limit]


def _limit_recommendations(items: list[str], limit: int) -> list[str]:
    useful = [item for item in items if _is_useful_text(item)]
    action_items = [
        item
        for item in useful
        if re.search(r"需要|建议|等待|适合|关注|取决|should|consider|wait", item, re.I)
    ]
    ordered = action_items + [item for item in useful if item not in action_items]
    return [_truncate(item, 260) for item in ordered[:limit]]


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _to_risk_factor(item: str) -> dict[str, str]:
    factor, description = _split_factor_description(item)
    severity = (
        "high"
        if re.search(r"高|重大|显著|放缓|紧张|overvalu|slowdown", item, re.I)
        else "medium"
    )
    return {
        "factor": _truncate(factor, 80),
        "severity": severity,
        "description": _truncate(description or item, 220),
    }


def _split_factor_description(item: str) -> tuple[str, str]:
    parts = re.split(r"[:：]\s*", item, maxsplit=1)
    if len(parts) == 2 and parts[0].strip():
        return parts[0].strip(), parts[1].strip()
    return item[:40].strip(), item.strip()


def _first_useful_paragraph(answer: str) -> str:
    for raw_line in answer.splitlines():
        cleaned = _clean_report_line(raw_line)
        if _paragraph_belongs_on_card(cleaned) and not _DISCLAIMER_RE.search(cleaned):
            return _truncate(cleaned, 220)
    return ""
