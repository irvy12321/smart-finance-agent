"""Data trust layer.

Provides a uniform envelope for every data point that flows through the system
so that the provenance (real vs. simulated) of each value is explicit, and a
report-level aggregation of how trustworthy a report is.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

MOCK_WARNING = "SIMULATED DATA - NOT FOR INVESTMENT"

# Relative reliability of each known data source.
SOURCE_RELIABILITY: dict[str, str] = {
    "alpha_vantage": "high",
    "yahoo_finance": "high",
    "fmp": "high",
    "newsapi": "medium",
    "rag": "medium",
    "mock": "low",
    "unknown": "low",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DataEnvelope:
    """Wraps a single data point with its provenance."""

    value: Any
    source: str
    is_mock: bool = False
    fetched_at: str = field(default_factory=_utc_now)

    @property
    def warning(self) -> str:
        return MOCK_WARNING if self.is_mock else ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "source": self.source,
            "is_mock": self.is_mock,
            "warning": self.warning,
            "fetched_at": self.fetched_at,
        }


def aggregate_confidence(envelopes: list[DataEnvelope]) -> dict[str, Any]:
    """Aggregate report-level trust metrics from individual data points."""
    if not envelopes:
        return {
            "data_confidence": 0.0,
            "source_reliability": "low",
            "mock_ratio": 1.0,
            "sources": [],
        }

    mock_ratio = sum(1 for e in envelopes if e.is_mock) / len(envelopes)
    data_confidence = round(1.0 - mock_ratio, 2)
    if data_confidence >= 0.8:
        reliability = "high"
    elif data_confidence >= 0.4:
        reliability = "medium"
    else:
        reliability = "low"

    sources = sorted({e.source for e in envelopes})
    return {
        "data_confidence": data_confidence,
        "source_reliability": reliability,
        "mock_ratio": round(mock_ratio, 2),
        "sources": sources,
    }
