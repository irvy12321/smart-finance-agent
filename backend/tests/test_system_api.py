import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport


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