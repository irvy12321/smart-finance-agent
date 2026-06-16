"""Computation layer.

Pure, deterministic financial indicator functions. All numeric analysis must
be produced here (not by the LLM). Every function returns ``None`` when there
is insufficient input data rather than fabricating a value.
"""

from __future__ import annotations


def pct_change(current: float, previous: float) -> float | None:
    """Percentage change from ``previous`` to ``current`` (rounded to 2 dp)."""
    if previous in (0, None) or current is None:
        return None
    return round((current - previous) / previous * 100, 2)


def sma(closes: list[float], window: int) -> float | None:
    """Simple moving average of the last ``window`` closes."""
    if window <= 0 or len(closes) < window:
        return None
    return round(sum(closes[-window:]) / window, 2)


def ema(closes: list[float], window: int) -> float | None:
    """Exponential moving average of the last ``window`` closes."""
    if window <= 0 or len(closes) < window:
        return None
    k = 2 / (window + 1)
    value = closes[0]
    for price in closes[1:]:
        value = price * k + value * (1 - k)
    return round(value, 2)


def rsi(closes: list[float], period: int = 14) -> float | None:
    """Relative Strength Index over ``period`` closes."""
    if len(closes) <= period:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(-period, 0):
        delta = closes[i] - closes[i - 1]
        gains += max(delta, 0.0)
        losses += max(-delta, 0.0)
    if losses == 0:
        return 100.0
    rs = (gains / period) / (losses / period)
    return round(100 - 100 / (1 + rs), 2)


def pe_ratio(price: float, eps: float) -> float | None:
    """Price-to-earnings ratio."""
    if eps in (0, None) or price is None:
        return None
    return round(price / eps, 2)
