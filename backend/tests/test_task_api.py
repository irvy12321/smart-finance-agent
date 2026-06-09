from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.auth.dependencies import get_current_user
from app.auth.models import UserResponse


@pytest.fixture
def mock_storage():
    with patch("app.api.task.storage") as mock:
        mock.get_task.return_value = None
        mock.create_task.return_value = None
        mock.update_task.return_value = None
        mock.list_tasks.return_value = []
        yield mock


@pytest.fixture
def mock_current_user():
    """Mock authenticated user for testing."""
    return UserResponse(
        id=1,
        username="testuser",
        email="test@example.com",
        is_active=True,
        created_at="2026-01-01T00:00:00",
    )


@pytest.fixture
def auth_app(test_app, mock_current_user):
    """Override auth dependency for testing."""
    test_app.dependency_overrides[get_current_user] = lambda: mock_current_user
    yield test_app
    test_app.dependency_overrides.clear()


@pytest.fixture
async def auth_client(auth_app) -> AsyncClient:
    """Get an async HTTP client with auth override."""
    from httpx import ASGITransport
    transport = ASGITransport(app=auth_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_create_task(auth_client: AsyncClient, mock_storage):
    response = await auth_client.post(
        "/api/task/create",
        json={"query": "Analyze AAPL stock price and trends", "priority": 1}
    )
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_get_task_status(auth_client: AsyncClient, mock_storage):
    mock_storage.get_task.return_value = {
        "task_id": "test-123",
        "status": "running",
        "progress": 50.0,
        "current_stage": "executing",
        "message": "Task is running"
    }

    response = await auth_client.get("/api/task/test-123/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["progress"] == 50.0


@pytest.mark.asyncio
async def test_get_task_status_not_found(auth_client: AsyncClient, mock_storage):
    mock_storage.get_task.return_value = None

    response = await auth_client.get("/api/task/nonexistent/status")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_task_result(auth_client: AsyncClient, mock_storage):
    mock_storage.get_task.return_value = {
        "task_id": "test-123",
        "status": "completed",
        "query": "Analyze AAPL",
        "result": {
            "answer": "AAPL analysis complete",
            "report_markdown": "# Report",
            "summary": "Summary",
            "key_findings": ["finding1"],
            "confidence": 0.9
        }
    }

    response = await auth_client.get("/api/task/test-123/result")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["confidence"] == 0.9


@pytest.mark.asyncio
async def test_get_task_result_not_completed(auth_client: AsyncClient, mock_storage):
    mock_storage.get_task.return_value = {
        "task_id": "test-123",
        "status": "running",
        "progress": 50.0,
        "current_stage": "executing"
    }

    response = await auth_client.get("/api/task/test-123/result")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_tasks(auth_client: AsyncClient, mock_storage):
    mock_storage.list_tasks.return_value = [
        {"task_id": "task1", "query": "Query 1", "status": "completed"},
        {"task_id": "task2", "query": "Query 2", "status": "pending"},
    ]

    response = await auth_client.get("/api/task/list")
    assert response.status_code == 200
    data = response.json()
    assert len(data["tasks"]) == 2


def test_process_events():
    from app.api.task import process_events

    events = [
        {"stage": "plan_ready", "subtasks": [{"id": "t1", "tool": "stock_price"}], "reasoning": "Plan"},
        {"stage": "task_done", "task_id": "t1", "tool": "stock_price", "success": True, "duration_ms": 100},
        {"stage": "reasoning_done", "confidence": 0.85, "insights": ["insight1"]},
        {"stage": "complete", "answer": "Final answer", "report_markdown": "# Report\n## 摘要\nTest summary"}
    ]

    result = process_events(events, "Test query")

    assert result["answer"] == "Final answer"
    assert result["confidence"] == 0.85
    assert result["total_tasks"] == 1
    assert result["success_tasks"] == 1
    assert result["failed_tasks"] == 0
    assert "Test summary" in result["summary"]
