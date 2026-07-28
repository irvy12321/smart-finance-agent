"""Production Uvicorn launcher with a boot id shared by all workers."""

import os
import uuid

import uvicorn


def main() -> None:
    os.environ["SFA_BOOT_ID"] = uuid.uuid4().hex
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        workers=int(os.getenv("WEB_CONCURRENCY", "2")),
        limit_concurrency=100,
        timeout_keep_alive=65,
        timeout_worker_healthcheck=int(
            os.getenv("UVICORN_WORKER_HEALTHCHECK_TIMEOUT", "120")
        ),
        access_log=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
