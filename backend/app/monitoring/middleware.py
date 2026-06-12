"""
Prometheus HTTP middleware for FastAPI

Collects:
- http_requests_total: request count by endpoint/method/status
- http_request_duration_seconds: request duration histogram
- http_errors_total: error count (4xx + 5xx)
"""
import re
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.monitoring.prometheus import (
    http_errors_total,
    http_request_duration_seconds,
    http_requests_total,
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for Prometheus metrics collection"""

    # Paths to skip (avoid high cardinality or noise)
    SKIP_PATHS = {"/metrics", "/health", "/ping", "/favicon.ico"}

    # Path patterns to normalize (replace IDs with placeholders)
    ID_PATTERNS = [
        (re.compile(r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"), "/{uuid}"),
        (re.compile(r"/\d+"), "/{id}"),
    ]

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip non-metrics paths
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        # Extract normalized endpoint
        endpoint = self._normalize_path(request.url.path)
        method = request.method

        # Skip /api prefix for cleaner labels
        if endpoint.startswith("/api/"):
            endpoint = endpoint[4:]  # Remove /api prefix

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            duration = time.perf_counter() - start_time

            # Record metrics
            status_code = str(response.status_code)

            http_requests_total.labels(
                endpoint=endpoint,
                method=method,
                status_code=status_code,
            ).inc()

            http_request_duration_seconds.labels(
                endpoint=endpoint,
                method=method,
            ).observe(duration)

            # Record errors (4xx + 5xx)
            if response.status_code >= 400:
                http_errors_total.labels(
                    endpoint=endpoint,
                    method=method,
                    status_code=status_code,
                ).inc()

            return response

        except Exception as exc:
            duration = time.perf_counter() - start_time

            # Record error metrics
            http_requests_total.labels(
                endpoint=endpoint,
                method=method,
                status_code="500",
            ).inc()

            http_request_duration_seconds.labels(
                endpoint=endpoint,
                method=method,
            ).observe(duration)

            http_errors_total.labels(
                endpoint=endpoint,
                method=method,
                status_code="500",
            ).inc()

            raise exc

    def _normalize_path(self, path: str) -> str:
        """Normalize path by replacing dynamic segments with placeholders"""
        for pattern, replacement in self.ID_PATTERNS:
            path = pattern.sub(replacement, path)
        return path
