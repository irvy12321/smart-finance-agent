"""
Prometheus metrics endpoint

Exposes /metrics for Prometheus scraping.
"""
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.requests import Request
from starlette.responses import Response


async def metrics_endpoint(request: Request) -> Response:
    """
    Prometheus metrics endpoint.

    Returns all registered metrics in Prometheus text format.
    This endpoint should be scraped by Prometheus.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
