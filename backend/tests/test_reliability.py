"""Deterministic tests for the orchestration reliability harness.

All trials are seeded and free of network / LLM calls, so the asserted
metrics are reproducible and safe to run in CI.
"""

import time

import pytest

from app.core.reliability import (
    ReliabilityReport,
    run_circuit_breaker_trial,
    run_deadlock_recovery_trial,
    run_degradation_trial,
)
from app.utils.circuit_breaker import BreakerState, CircuitBreaker
from app.utils.exceptions import CircuitBreakerOpenError


@pytest.mark.asyncio
async def test_degradation_curve_is_deterministic():
    a = await run_degradation_trial(0.5, trials=300, seed=7)
    b = await run_degradation_trial(0.5, trials=300, seed=7)
    assert a.to_dict() == b.to_dict()


@pytest.mark.asyncio
async def test_single_point_fault_never_hard_fails():
    """A healthy alternative absorbs every primary failure: zero hard failures."""
    for rate in (0.0, 0.25, 0.5, 0.75, 1.0):
        stats = await run_degradation_trial(rate, trials=300, seed=1)
        assert stats.hard_failure == 0
        assert stats.served_rate == 1.0
    # At 100% primary failure, every served request is a real recovery.
    full = await run_degradation_trial(1.0, trials=300, seed=1)
    assert full.real_recovery == full.trials


@pytest.mark.asyncio
async def test_cascade_fault_falls_through_to_static_net():
    """When alternatives also fail, the static fallback keeps served_rate at 1.0."""
    stats = await run_degradation_trial(1.0, trials=300, seed=1, alt_failure_rate=1.0)
    assert stats.hard_failure == 0
    assert stats.static_fallback == stats.trials
    assert stats.real_recovery == 0


@pytest.mark.asyncio
async def test_real_recovery_increases_with_failure_rate():
    low = await run_degradation_trial(0.25, trials=400, seed=3)
    high = await run_degradation_trial(0.75, trials=400, seed=3)
    assert high.real_recovery_rate > low.real_recovery_rate


def test_circuit_breaker_state_transitions():
    cb = CircuitBreaker(name="t", failure_threshold=3, recovery_timeout=0.05)
    assert cb.state == BreakerState.CLOSED
    for _ in range(3):
        cb.record_failure()
    assert cb.state == BreakerState.OPEN
    assert cb.allow_request() is False
    time.sleep(0.06)
    assert cb.state == BreakerState.HALF_OPEN
    cb.record_success()
    assert cb.state == BreakerState.CLOSED


def test_circuit_breaker_short_circuits_doomed_calls():
    res = run_circuit_breaker_trial(failure_threshold=5, total_calls=100)
    # Only the calls up to the threshold reach the dead tool; the rest are
    # short-circuited by the open breaker.
    assert res["invoked"] == 5
    assert res["short_circuited"] == 95
    assert res["cb_protection_rate"] == 0.95


def test_circuit_breaker_short_circuit_raises():
    cb = CircuitBreaker(name="t", failure_threshold=1, recovery_timeout=1e9)
    cb.record_failure()
    with pytest.raises(CircuitBreakerOpenError):
        cb.check_or_raise()


def test_deadlock_recovery_unlocks_downstream():
    res = run_deadlock_recovery_trial(scenarios=50, seed=42)
    assert res["deadlock_recovery_rate"] == 1.0
    assert res["recovered"] == res["scenarios"]


def test_deadlock_recovery_is_deterministic():
    assert run_deadlock_recovery_trial(
        scenarios=30, seed=9
    ) == run_deadlock_recovery_trial(scenarios=30, seed=9)


def test_report_to_dict_shape():
    report = ReliabilityReport()
    report.circuit_breaker = run_circuit_breaker_trial()
    report.deadlock = run_deadlock_recovery_trial(scenarios=10)
    d = report.to_dict()
    assert {
        "single_point_curve",
        "cascade_curve",
        "circuit_breaker",
        "deadlock",
    } <= d.keys()
