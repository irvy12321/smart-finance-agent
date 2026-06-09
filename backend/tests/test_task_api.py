import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def mock_storage():
    with patch("app.api.task.storage") as mock:
        mock.get_task.return_value = None
        mock.create_task.return_value = None
        mock.update_task.return_value = None
        mock.list_tasks.return_value = []
        yield mock


@pytest.mark.asyncio
async def test_create_task(client: AsyncClient, mock_storage):
    response = await client.post(
        "/api/task/create",
        json={"query": "Analyze AAPL stock price and trends", "priority": 1}
    )
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_get_task_status(client: AsyncClient, mock_storage):
    mock_storage.get_task.return_value = {
        "task_id": "test-123",
        "status": "running",
        "progress": 50.0,
        "current_stage": "executing",
        "message": "Task is running"
    }

    response = await client.get("/api/task/test-123/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["progress"] == 50.0


@pytest.mark.asyncio
async def test_get_task_status_not_found(client: AsyncClient, mock_storage):
    mock_storage.get_task.return_value = None

    response = await client.get("/api/task/nonexistent/status")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_task_result(client: AsyncClient, mock_storage):
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

    response = await client.get("/api/task/test-123/result")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["confidence"] == 0.9


@pytest.mark.asyncio
async def test_get_task_result_not_completed(client: AsyncClient, mock_storage):
    mock_storage.get_task.return_value = {
        "task_id": "test-123",
        "status": "running",
        "progress": 50.0,
        "current_stage": "executing"
    }

    response = await client.get("/api/task/test-123/result")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_tasks(client: AsyncClient, mock_storage):
    mock_storage.list_tasks.return_value = [
        {"task_id": "task1", "query": "Query 1", "status": "completed"},
        {"task_id": "task2", "query": "Query 2", "status": "pending"},
    ]

    response = await client.get("/api/task/list")
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