from app.monitoring.request_stats import (
    get_http_stats,
    record_http_request,
    reset_http_stats,
)


def test_request_stats_tracks_real_counts_and_latency():
    reset_http_stats()

    record_http_request(200, 20.0)
    record_http_request(404, 40.0)

    stats = get_http_stats()
    assert stats.total_requests == 2
    assert stats.successful_requests == 1
    assert stats.failed_requests == 1
    assert stats.success_rate == 50.0
    assert stats.avg_latency_ms == 30.0
