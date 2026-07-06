"""Tests for the evaluation CLI threshold gate (--min-* flags)."""

import argparse

from app.core.evaluation import EvalResult, check_thresholds


def _result(**overrides) -> EvalResult:
    base = {
        "task_success_rate": 0.9,
        "tool_accuracy": 0.8,
        "retrieval_recall_at_k": 1.0,
        "answer_groundedness": 0.7,
        "avg_confidence": 0.8,
        "avg_duration_ms": 1000.0,
        "per_case": [{}],
    }
    base.update(overrides)
    return EvalResult(**base)


def _args(**overrides) -> argparse.Namespace:
    base = {
        "min_task_success": None,
        "min_tool_accuracy": None,
        "min_retrieval_recall": None,
        "min_groundedness": None,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def test_no_thresholds_always_passes():
    assert check_thresholds(_result(task_success_rate=0.0), _args()) == 0


def test_passing_thresholds_returns_zero(capsys):
    args = _args(min_task_success=0.8, min_tool_accuracy=0.5, min_groundedness=0.6)
    assert check_thresholds(_result(), args) == 0
    out = capsys.readouterr().out
    assert out.count("[PASS]") == 3
    assert "[FAIL]" not in out


def test_failing_threshold_returns_one(capsys):
    args = _args(min_task_success=0.95)
    assert check_thresholds(_result(task_success_rate=0.9), args) == 1
    assert "[FAIL] task_success_rate" in capsys.readouterr().out


def test_each_metric_is_gated_independently():
    assert (
        check_thresholds(_result(tool_accuracy=0.1), _args(min_tool_accuracy=0.5)) == 1
    )
    assert (
        check_thresholds(
            _result(retrieval_recall_at_k=0.2), _args(min_retrieval_recall=0.5)
        )
        == 1
    )
    assert (
        check_thresholds(_result(answer_groundedness=0.2), _args(min_groundedness=0.5))
        == 1
    )
