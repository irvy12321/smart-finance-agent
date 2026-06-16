from app.core import indicators


def test_pct_change():
    assert indicators.pct_change(110, 100) == 10.0
    assert indicators.pct_change(90, 100) == -10.0


def test_pct_change_guards_zero_and_none():
    assert indicators.pct_change(100, 0) is None
    assert indicators.pct_change(None, 100) is None


def test_sma():
    assert indicators.sma([1, 2, 3, 4], 2) == 3.5
    assert indicators.sma([1, 2], 5) is None


def test_ema_returns_value():
    val = indicators.ema([1, 2, 3, 4, 5], 3)
    assert val is not None
    assert isinstance(val, float)


def test_rsi_all_gains_is_100():
    assert indicators.rsi([1, 2, 3, 4, 5, 6], period=3) == 100.0


def test_rsi_insufficient_data():
    assert indicators.rsi([1, 2], period=14) is None


def test_pe_ratio():
    assert indicators.pe_ratio(200, 10) == 20.0
    assert indicators.pe_ratio(200, 0) is None
