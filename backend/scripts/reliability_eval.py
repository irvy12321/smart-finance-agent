"""Standalone reliability A/B harness for the orchestration layer.

Runs fault injection against the real circuit breaker, fallback chains, and
deadlock recovery, then prints quantitative metrics. Deterministic; no network.

Usage:
    cd backend && PYTHONPATH=. python scripts/reliability_eval.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.reliability import (  # noqa: E402
    ReliabilityReport,
    run_circuit_breaker_trial,
    run_deadlock_recovery_trial,
    run_degradation_trial,
)

RATES = [0.0, 0.25, 0.5, 0.75, 1.0]
TRIALS = 400


async def _build_report() -> ReliabilityReport:
    report = ReliabilityReport()
    for rate in RATES:
        report.degradation.append(
            await run_degradation_trial(rate, trials=TRIALS, seed=42)
        )
    for rate in RATES:
        report.cascade.append(
            await run_degradation_trial(
                rate, trials=TRIALS, seed=42, alt_failure_rate=rate
            )
        )
    report.circuit_breaker = run_circuit_breaker_trial(
        failure_threshold=5, total_calls=100
    )
    report.deadlock = run_deadlock_recovery_trial(scenarios=50, seed=42)
    return report


def _print_curve(title: str, rows) -> None:
    print(f"\n=== {title} ===")
    print(
        f"{'p(fail)':>8} | {'served':>8} | {'hard_fail':>10} | "
        f"{'real_recov':>11} | {'static':>8}"
    )
    print("-" * 56)
    for s in rows:
        print(
            f"{s.failure_rate:>8.2f} | {s.served_rate:>8.3f} | "
            f"{s.hard_failure_rate:>10.3f} | {s.real_recovery_rate:>11.3f} | "
            f"{s.static_fallback_rate:>8.3f}"
        )


def _print_report(report: ReliabilityReport) -> None:
    _print_curve(
        "Single-point fault (primary down, alternatives healthy)", report.degradation
    )
    _print_curve(
        "Cascade fault (primary + alternatives degrade together)", report.cascade
    )

    cb = report.circuit_breaker
    print("\n=== Circuit-breaker protection (tool fully down) ===")
    print(
        f"threshold={cb['failure_threshold']} total_calls={cb['total_calls']} "
        f"-> invoked={cb['invoked']} short_circuited={cb['short_circuited']} "
        f"(protection={cb['cb_protection_rate']:.1%})"
    )

    dl = report.deadlock
    print("\n=== Deadlock recovery (failed upstream dependency) ===")
    print(
        f"scenarios={dl['scenarios']} recovered={dl['recovered']} "
        f"(recovery_rate={dl['deadlock_recovery_rate']:.1%})"
    )


def main() -> None:
    report = asyncio.run(_build_report())
    _print_report(report)

    out_dir = ROOT / "data" / "reliability_eval"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "results.json"
    out_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
