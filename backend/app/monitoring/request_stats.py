"""Small in-process HTTP summary used by the system overview API."""

import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class HttpStats:
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_latency_ms: float

    @property
    def success_rate(self) -> float:
        if not self.total_requests:
            return 100.0
        return self.successful_requests / self.total_requests * 100

    @property
    def avg_latency_ms(self) -> float:
        if not self.total_requests:
            return 0.0
        return self.total_latency_ms / self.total_requests


_lock = threading.Lock()
_total_requests = 0
_successful_requests = 0
_failed_requests = 0
_total_latency_ms = 0.0


def record_http_request(status_code: int, latency_ms: float) -> None:
    global _total_requests, _successful_requests, _failed_requests, _total_latency_ms
    with _lock:
        _total_requests += 1
        _total_latency_ms += max(latency_ms, 0.0)
        if status_code < 400:
            _successful_requests += 1
        else:
            _failed_requests += 1


def get_http_stats() -> HttpStats:
    with _lock:
        return HttpStats(
            total_requests=_total_requests,
            successful_requests=_successful_requests,
            failed_requests=_failed_requests,
            total_latency_ms=_total_latency_ms,
        )


def reset_http_stats() -> None:
    global _total_requests, _successful_requests, _failed_requests, _total_latency_ms
    with _lock:
        _total_requests = 0
        _successful_requests = 0
        _failed_requests = 0
        _total_latency_ms = 0.0
