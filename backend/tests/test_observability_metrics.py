import threading

from app.core.observability.metrics import MetricsCollector


def test_histogram_percentiles_do_not_index_past_end():
    metrics = MetricsCollector()
    metrics.clear()

    for value in [10, 20]:
        metrics.histogram("latency", value)

    stats = metrics.get_histogram_stats("latency")

    assert stats["count"] == 2
    assert stats["p50"] == 20
    assert stats["p99"] == 20


def test_get_all_uses_reentrant_snapshot_without_deadlock():
    metrics = MetricsCollector()
    metrics.clear()

    metrics.record("agent_call", 1, agent="planner")
    metrics.record("agent_tokens", 42, agent="planner")
    metrics.histogram("agent.planner.latency", 123)

    summary = metrics.get_all()

    assert summary["counters"]["agent_call"] == 1
    assert summary["agent_summary"]["planner"]["calls"] == 1
    assert summary["agent_summary"]["planner"]["tokens"] == 42
    assert summary["histograms"]["agent.planner.latency"]["count"] == 1


def test_metrics_snapshot_is_safe_during_concurrent_writes():
    metrics = MetricsCollector()
    metrics.clear()
    errors: list[BaseException] = []

    def writer():
        try:
            for idx in range(250):
                metrics.record("requests", 1, worker=str(idx % 4))
                metrics.histogram("latency", float(idx))
        except BaseException as exc:
            errors.append(exc)

    def reader():
        try:
            for _ in range(100):
                summary = metrics.get_all()
                assert "counters" in summary
                assert "histograms" in summary
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=writer) for _ in range(4)] + [
        threading.Thread(target=reader) for _ in range(4)
    ]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert metrics.get_counter("requests") == 1000
