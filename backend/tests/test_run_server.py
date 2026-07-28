import os
from unittest.mock import patch


def test_production_launcher_shares_boot_id_and_relaxes_worker_healthcheck(
    monkeypatch,
):
    from app.ops import run_server

    monkeypatch.delenv("SFA_BOOT_ID", raising=False)
    monkeypatch.delenv("UVICORN_WORKER_HEALTHCHECK_TIMEOUT", raising=False)

    with patch.object(run_server.uvicorn, "run") as uvicorn_run:
        run_server.main()

    assert os.environ["SFA_BOOT_ID"]
    uvicorn_run.assert_called_once_with(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        workers=2,
        limit_concurrency=100,
        timeout_keep_alive=65,
        timeout_worker_healthcheck=120,
        access_log=True,
        log_level="info",
    )
