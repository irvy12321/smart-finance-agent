from unittest.mock import patch

import pytest
from httpx import AsyncClient

PASSWORD = "Str0ngPass-123"


@pytest.fixture
def mock_storage():
    with patch("app.api.system.storage") as mock:
        mock.list_tasks.return_value = [
            {"task_id": "task1", "status": "completed"},
            {"task_id": "task2", "status": "pending"},
            {"task_id": "task3", "status": "running"},
            {"task_id": "task4", "status": "failed"},
        ]
        yield mock


@pytest.mark.asyncio
async def test_get_system_status(client: AsyncClient):
    response = await client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "uptime" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_get_system_metrics(client: AsyncClient, mock_storage):
    response = await client.get("/api/system/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_tasks"] == 4
    assert data["completed_tasks"] == 1
    assert data["pending_tasks"] == 1
    assert data["running_tasks"] == 1
    assert data["failed_tasks"] == 1


@pytest.mark.asyncio
async def test_system_admin_endpoints_require_auth(real_client: AsyncClient):
    response = await real_client.get("/api/system/metrics")
    assert response.status_code == 401

    response = await real_client.post("/api/system/cache/clear")
    assert response.status_code == 401


async def _make_analyst(client: AsyncClient, storage, username: str) -> dict:
    response = await client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": PASSWORD,
        },
    )
    assert response.status_code == 201, response.text
    conn = storage._get_connection()
    try:
        conn.execute(
            "UPDATE users SET role = 'analyst' WHERE username = ?", (username,)
        )
        conn.commit()
    finally:
        conn.close()
    return response.json()


def _auth(data: dict) -> dict:
    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest.mark.asyncio
async def test_system_admin_endpoints_reject_analyst(real_client: AsyncClient, temp_db):
    analyst = await _make_analyst(real_client, temp_db, "system_analyst")
    headers = _auth(analyst)

    for method, path in [
        ("GET", "/api/system/metrics"),
        ("GET", "/api/system/agents"),
        ("GET", "/api/system/config"),
        ("GET", "/api/system/cache"),
        ("POST", "/api/system/cache/clear"),
        ("GET", "/api/system/auth-health"),
    ]:
        response = await real_client.request(method, path, headers=headers)
        assert response.status_code == 403, f"{method} {path}: {response.text}"


@pytest.mark.asyncio
async def test_get_agent_status(client: AsyncClient):
    response = await client.get("/api/system/agents")
    assert response.status_code == 200
    data = response.json()
    assert "planner" in data
    assert "executor" in data
    assert "reasoner" in data
    assert "report_agent" in data
    assert "orchestrator" in data


@pytest.mark.asyncio
async def test_get_system_config(client: AsyncClient):
    response = await client.get("/api/system/config")
    assert response.status_code == 200
    data = response.json()
    assert "model" in data
    assert "features" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/api/system/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "uptime" in data


@pytest.mark.asyncio
async def test_get_version(client: AsyncClient):
    response = await client.get("/api/system/version")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "1.0.0"
    assert "build" in data
    assert "api_version" in data


@pytest.mark.asyncio
async def test_auth_health_does_not_expose_secret_material(client: AsyncClient):
    response = await client.get("/api/system/auth-health")
    assert response.status_code == 200
    data = response.json()
    assert "jwt_secret_hash" not in data
    assert "jwt_secret_length" not in data
    assert data["jwt_secret_configured"] is True
    assert data["jwt_secret_min_length_ok"] is True
