# Load testing

A small, reproducible [Locust](https://locust.io/) harness for the **lightweight
synchronous read path** of the backend.

> **Scope on purpose.** This measures the cheap, no-LLM read endpoints
> (`/ping`, `/api/system/health`, `/api/system/status`). It does **not** measure
> the multi-agent research pipeline (`/api/research/*`, `/api/chat/*`), which is
> LLM-bound and is reported separately as *end-to-end latency*, not throughput.
> Mixing the two would conflate "API throughput" with "agent latency".

## Install

```bash
pip install -r loadtest/requirements.txt
```

## Run

1. Start the backend (multi-worker, so it can use all cores):

   ```bash
   cd backend
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
   ```

2. In another shell, run the load test headless (200 virtual users, 60s):

   ```bash
   locust -f loadtest/locustfile.py --headless \
       -u 200 -r 50 -t 60s --host http://127.0.0.1:8000 \
       --csv loadtest/results/run
   ```

   Drop the `wait_time` in `locustfile.py` to `0` for a pure saturation run.

## Reference results

Captured with this harness so the throughput/latency claims are reproducible.

| | |
|---|---|
| Host | 2 vCPU / ~8 GB, Linux |
| Server | `uvicorn app.main:app --workers 4` |
| Client | locust, 200 users, 60s, ramp 50/s (same box as server) |

| Endpoint | Requests | Failures | RPS | p50 | p95 | p99 | max |
|---|---|---|---|---|---|---|---|
| `GET /ping` | 50,118 | 0 | 849 | 68 ms | 130 ms | 250 ms | 350 ms |
| `GET /api/system/health` | 30,117 | 0 | 510 | 68 ms | 130 ms | 240 ms | 341 ms |
| `GET /api/system/status` | 20,050 | 0 | 339 | 68 ms | 130 ms | 250 ms | 344 ms |
| **Aggregated** | **100,285** | **0 (0.00%)** | **~1,699** | **68 ms** | **130 ms** | **~245 ms** | **350 ms** |

Notes / honesty caveats:

- The load generator ran on the **same 2-vCPU box** as the server, so client and
  server competed for CPU — real server-only capacity is higher than the
  ~1.7k RPS shown here. For a clean number, run locust from a separate machine.
- Numbers scale with worker count and hardware; treat the table as a
  *reproducible lower bound on this box*, not a universal figure.
- `0` failures over 100k requests demonstrates the no-5xx behaviour of the
  lightweight path under sustained concurrency.

## Live production run (ECS, full nginx path)

Captured on the live ECS deployment (`docker-compose.prod.yml`), with locust run
**on the ECS box** against `http://localhost:80` — i.e. the real production path
through nginx → backend. This is intentionally different from the dedicated
benchmark above (which hits the backend directly with 4 workers on an 8 GB box).

| | |
|---|---|
| Host | 2 vCPU / 1.6 GB, Alibaba Cloud ECS |
| Backend | `uvicorn --workers 2 --limit-concurrency 100 --access-log` (behind nginx) |
| Client | locust, 200 users, 60s, ramp 50/s (co-located on the ECS box) |

| Endpoint | Requests | Failures | RPS | p50 | p99 | max |
|---|---|---|---|---|---|---|
| `GET /ping` (nginx static) | 6,456 | 0 | 109 | 72 ms | 700 ms | 1,364 ms |
| `GET /api/system/health` | 3,762 | 0 | 64 | 1,600 ms | 2,000 ms | 2,798 ms |
| `GET /api/system/status` | 2,570 | 0 | 43 | 1,600 ms | 2,000 ms | 2,807 ms |
| **Aggregated** | **12,788** | **0 (0.00%)** | **~216** | **490 ms** | **1,900 ms** | **2,807 ms** |

Why this sits far below the ~1.7k RPS benchmark — all environmental, not a regression:

- **Conservative prod tuning**: only 2 uvicorn workers (benchmark used 4),
  `--limit-concurrency 100` (so at 200 VUs roughly half the requests queue,
  ~doubling latency), and `--access-log` enabled.
- **Smaller box**: 1.6 GB RAM (benchmark box had ~8 GB), and the API path runs
  through the nginx reverse proxy rather than hitting uvicorn directly.
- **Client contention**: locust ran on the same 2 vCPU as the server and hit
  >90% CPU, so the load generator itself was a bottleneck — for a clean number,
  drive load from a separate machine.
- `0` failures over ~13k requests still holds under this constrained setup.

> The ~1.7k RPS / p99 < 250 ms figures in the section above are a **reproducible
> benchmark** (4 workers, dedicated run), not the throttled live-prod
> configuration. To approach them on ECS, raise the worker count, relax
> `--limit-concurrency`, disable `--access-log`, and give the box more RAM.
