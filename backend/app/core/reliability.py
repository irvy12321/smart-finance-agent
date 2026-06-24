"""Chaos / fault-injection harness for the orchestration layer.

This module exercises the *real* reliability primitives used in production —
the circuit breaker (``app.utils.circuit_breaker``), the fallback chains
(``app.core.fallback_manager``), and deadlock recovery
(``ExecutorAgent._try_resolve_deadlock``) — under deterministically injected
faults, and computes quantitative reliability metrics:

- ``hard_failure_rate``      : fraction of requests that return no result at all
- ``real_recovery_rate``     : fraction served by a genuine alternative tool
- ``static_fallback_rate``   : fraction served by the terminal static fallback
- ``cb_protection_rate``     : fraction of doomed calls short-circuited by the breaker
- ``deadlock_recovery_rate`` : fraction of stalled task graphs that still progress

All randomness is seeded; there are no network or LLM calls, so results are
reproducible and safe to assert on in CI.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from app.core.fallback_manager import FallbackManager
from app.tools.base_tool import BaseTool, ToolResult
from app.utils.circuit_breaker import CircuitBreaker
from app.utils.exceptions import CircuitBreakerOpenError


class FaultInjectingTool(BaseTool):
    """A tool whose ``execute`` fails with a seeded probability.

    Used to inject deterministic faults into the fallback chains without
    touching the network. ``failure_rate`` is the probability a call fails;
    ``fail_mode`` controls whether a failure surfaces as ``success=False``
    (``"error"``) or a raised exception (``"raise"``).
    """

    def __init__(
        self,
        name: str,
        failure_rate: float = 0.0,
        rng: random.Random | None = None,
        payload: object = None,
        fail_mode: str = "error",
    ):
        self.name = name
        self.failure_rate = failure_rate
        self._rng = rng or random.Random(0)
        self._payload = payload if payload is not None else {"tool": name}
        self._fail_mode = fail_mode
        self.calls = 0

    async def execute(self, **kwargs) -> ToolResult:
        self.calls += 1
        if self._rng.random() < self.failure_rate:
            if self._fail_mode == "raise":
                raise RuntimeError(f"injected failure in {self.name}")
            return ToolResult(
                success=False,
                error=f"injected failure in {self.name}",
                tool_name=self.name,
            )
        return ToolResult(
            success=True, data=self._payload, tool_name=self.name, source="real"
        )


class _DictRegistry:
    """Minimal registry exposing ``.get`` for FallbackManager."""

    def __init__(self, tools: dict[str, BaseTool]):
        self._tools = tools

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)


@dataclass
class DegradationStats:
    """Outcome distribution of a fallback-chain trial."""

    failure_rate: float
    trials: int
    primary_ok: int = 0
    real_recovery: int = 0
    static_fallback: int = 0
    hard_failure: int = 0

    @property
    def served_rate(self) -> float:
        return (self.trials - self.hard_failure) / self.trials if self.trials else 0.0

    @property
    def hard_failure_rate(self) -> float:
        return self.hard_failure / self.trials if self.trials else 0.0

    @property
    def real_recovery_rate(self) -> float:
        return self.real_recovery / self.trials if self.trials else 0.0

    @property
    def static_fallback_rate(self) -> float:
        return self.static_fallback / self.trials if self.trials else 0.0

    def to_dict(self) -> dict:
        return {
            "failure_rate": self.failure_rate,
            "trials": self.trials,
            "served_rate": round(self.served_rate, 4),
            "hard_failure_rate": round(self.hard_failure_rate, 4),
            "real_recovery_rate": round(self.real_recovery_rate, 4),
            "static_fallback_rate": round(self.static_fallback_rate, 4),
        }


async def run_degradation_trial(
    failure_rate: float,
    trials: int = 200,
    seed: int = 0,
    alt_failure_rate: float | None = None,
) -> DegradationStats:
    """Drive a fallback chain with the primary tool failing at ``failure_rate``.

    With ``alt_failure_rate=None`` the real alternative tools stay healthy, so
    every primary failure is absorbed by a genuine alternative (single-point
    fault). With ``alt_failure_rate`` set, the alternatives fail at that rate
    too (correlated/cascade outage), so trials cascade down to the terminal
    static fallback. In both modes the chain is designed never to hard-fail.
    """
    primary = "crawler"
    alt_rate = failure_rate if alt_failure_rate is None else alt_failure_rate
    rng = random.Random(seed)
    stats = DegradationStats(failure_rate=failure_rate, trials=trials)

    for _ in range(trials):
        healthy_alt = alt_failure_rate is None
        tools: dict[str, BaseTool] = {
            "crawler": FaultInjectingTool("crawler", failure_rate, rng),
            "news_search": FaultInjectingTool(
                "news_search", 0.0 if healthy_alt else alt_rate, rng
            ),
            "rag_retrieve": FaultInjectingTool(
                "rag_retrieve", 0.0 if healthy_alt else alt_rate, rng
            ),
        }

        mgr = FallbackManager(tool_registry=_DictRegistry(tools))
        result, used = await mgr.execute_with_fallback(
            primary, {"query": "q", "url": "u"}
        )
        if not result.success:
            stats.hard_failure += 1
        elif used == primary:
            stats.primary_ok += 1
        elif used == "static":
            stats.static_fallback += 1
        else:
            stats.real_recovery += 1
    return stats


def run_circuit_breaker_trial(
    failure_threshold: int = 5,
    total_calls: int = 100,
) -> dict:
    """Quantify how many doomed calls the breaker short-circuits.

    Models a tool that is fully down: the breaker opens after
    ``failure_threshold`` failures and short-circuits the remaining calls
    instead of invoking the dead tool, eliminating wasted work.
    """
    breaker = CircuitBreaker(
        name="down_tool",
        failure_threshold=failure_threshold,
        recovery_timeout=1e9,
    )
    invoked = 0
    short_circuited = 0
    for _ in range(total_calls):
        try:
            breaker.check_or_raise()
        except CircuitBreakerOpenError:
            short_circuited += 1
            continue
        invoked += 1
        breaker.record_failure()
    return {
        "total_calls": total_calls,
        "failure_threshold": failure_threshold,
        "invoked": invoked,
        "short_circuited": short_circuited,
        "cb_protection_rate": round(short_circuited / total_calls, 4),
    }


def run_deadlock_recovery_trial(scenarios: int = 50, seed: int = 0) -> dict:
    """Measure the fraction of stalled graphs that recover.

    Each scenario builds a graph where one upstream task has failed; a healthy
    orchestrator should unlock the downstream tasks whose only blocker is the
    failed dependency rather than skipping the whole graph.
    """
    from app.core.executor import ExecutorAgent, TaskResult

    rng = random.Random(seed)
    recovered = 0
    for _ in range(scenarios):
        n_downstream = rng.randint(1, 4)
        task_graph: dict[str, list[str]] = {
            f"d{i}": ["upstream"] for i in range(n_downstream)
        }
        completed = {
            "upstream": TaskResult(
                task_id="upstream",
                tool_name="x",
                success=False,
                error="injected upstream failure",
            )
        }
        unlocked = ExecutorAgent._try_resolve_deadlock(task_graph, completed)
        if unlocked and len(unlocked) == n_downstream:
            recovered += 1
    return {
        "scenarios": scenarios,
        "recovered": recovered,
        "deadlock_recovery_rate": round(recovered / scenarios, 4),
    }


@dataclass
class ReliabilityReport:
    degradation: list[DegradationStats] = field(default_factory=list)
    cascade: list[DegradationStats] = field(default_factory=list)
    circuit_breaker: dict = field(default_factory=dict)
    deadlock: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "single_point_curve": [s.to_dict() for s in self.degradation],
            "cascade_curve": [s.to_dict() for s in self.cascade],
            "circuit_breaker": self.circuit_breaker,
            "deadlock": self.deadlock,
        }
