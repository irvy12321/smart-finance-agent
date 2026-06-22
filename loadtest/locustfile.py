"""Load test for Smart Finance Agent lightweight read endpoints.

Scope (intentional): this exercises the *lightweight* synchronous read path
(`/ping`, `/api/system/health`, `/api/system/status`) — NOT the multi-agent
research pipeline, which is LLM-bound and measured separately by end-to-end
latency. Keeping the two apart avoids conflating "API throughput" with
"agent latency".

Run (headless), example targeting a locally running backend:

    locust -f loadtest/locustfile.py --headless \
        -u 200 -r 50 -t 60s --host http://localhost:8000 \
        --csv loadtest/results/run

See loadtest/README.md for the full methodology and how the numbers in the
README/resume were produced.
"""

from locust import HttpUser, between, task


class LightweightReadUser(HttpUser):
    """Simulates clients polling the lightweight, no-auth read endpoints."""

    # Small think time so a single box can drive high concurrency without the
    # client itself becoming the bottleneck. Set to 0 for a pure saturation run.
    wait_time = between(0.0, 0.05)

    @task(5)
    def ping(self):
        self.client.get("/ping", name="GET /ping")

    @task(3)
    def health(self):
        self.client.get("/api/system/health", name="GET /api/system/health")

    @task(2)
    def status(self):
        self.client.get("/api/system/status", name="GET /api/system/status")
