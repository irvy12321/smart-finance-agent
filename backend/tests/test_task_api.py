from unittest.mock import patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.auth.dependencies import get_current_user
from app.auth.models import UserResponse


@pytest.fixture
def mock_storage():
    with patch("app.api.task.storage") as mock:
        mock.get_task.return_value = None
        mock.get_task_owner.return_value = 1
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
        role="admin",
        is_active=True,
        created_at="2026-01-01T00:00:00",
    )


@pytest.fixture(autouse=True)
def clear_stream_token_state():
    from app.api import task as task_api

    task_api._stream_tokens.clear()
    yield
    task_api._stream_tokens.clear()


def test_fail_interrupted_running_tasks(temp_db):
    pending = temp_db.create_task("pending-task", "Analyze MSFT", user_id=1)
    running = temp_db.create_task("running-task", "Analyze AAPL", user_id=1)
    temp_db.update_task(running["task_id"], status="running", current_stage="executing")

    count = temp_db.fail_interrupted_running_tasks()

    assert count == 1
    assert temp_db.get_task(pending["task_id"])["status"] == "pending"

    recovered = temp_db.get_task(running["task_id"])
    assert recovered["status"] == "failed"
    assert recovered["current_stage"] == "interrupted"
    assert "backend restart" in recovered["message"]


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
        json={"query": "Analyze AAPL stock price and trends", "priority": 1},
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
        "message": "Task is running",
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
            "confidence": 0.9,
        },
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
        "current_stage": "executing",
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


@pytest.mark.asyncio
async def test_stream_token_is_one_time(auth_client: AsyncClient, mock_storage):
    from app.api.task import get_user_for_stream

    mock_storage.get_task.return_value = {
        "task_id": "test-123",
        "status": "running",
    }

    response = await auth_client.post("/api/task/test-123/stream-token")
    assert response.status_code == 200
    stream_token = response.json()["stream_token"]

    user = await get_user_for_stream(
        task_id="test-123", stream_token=stream_token, credentials=None
    )
    assert user.id == 1

    with pytest.raises(HTTPException):
        await get_user_for_stream(
            task_id="test-123", stream_token=stream_token, credentials=None
        )


def test_stream_token_issue_prunes_expired_entries(monkeypatch, mock_current_user):
    from app.api import task as task_api

    monkeypatch.setattr(task_api.time, "monotonic", lambda: 1000.0)
    task_api._stream_tokens["expired"] = (mock_current_user, "old-task", 999.0)

    token = task_api._issue_stream_token(mock_current_user, "task-123")

    assert "expired" not in task_api._stream_tokens
    assert token in task_api._stream_tokens


def test_stream_token_issue_caps_oldest_entries(monkeypatch, mock_current_user):
    from app.api import task as task_api

    monkeypatch.setattr(task_api, "_STREAM_TOKEN_MAX_ENTRIES", 2)
    monkeypatch.setattr(task_api.time, "monotonic", lambda: 1000.0)
    task_api._stream_tokens["old"] = (mock_current_user, "task", 1001.0)
    task_api._stream_tokens["middle"] = (mock_current_user, "task", 1002.0)

    token = task_api._issue_stream_token(mock_current_user, "task")

    assert len(task_api._stream_tokens) == 2
    assert "old" not in task_api._stream_tokens
    assert "middle" in task_api._stream_tokens
    assert token in task_api._stream_tokens


def test_stream_token_consume_rejects_expired_token(monkeypatch, mock_current_user):
    from app.api import task as task_api

    clock = {"now": 1000.0}
    monkeypatch.setattr(task_api.time, "monotonic", lambda: clock["now"])
    token = task_api._issue_stream_token(mock_current_user, "task-123")

    clock["now"] = 1000.0 + task_api._STREAM_TOKEN_TTL_SECONDS + 1

    assert task_api._consume_stream_token(token, "task-123") is None
    assert token not in task_api._stream_tokens


def test_process_events():
    from app.api.task import process_events

    events = [
        {
            "stage": "plan_ready",
            "subtasks": [{"id": "t1", "tool": "stock_price"}],
            "reasoning": "Plan",
        },
        {
            "stage": "task_done",
            "task_id": "t1",
            "tool": "stock_price",
            "success": True,
            "duration_ms": 100,
        },
        {"stage": "reasoning_done", "confidence": 0.85, "insights": ["insight1"]},
        {
            "stage": "complete",
            "answer": "Final answer",
            "report_markdown": "# Report\n## 摘要\nTest summary",
        },
    ]

    result = process_events(events, "Test query")

    assert result["answer"] == "Final answer"
    assert result["confidence"] == 0.85
    assert result["total_tasks"] == 1
    assert result["success_tasks"] == 1
    assert result["failed_tasks"] == 0
    assert "Test summary" in result["summary"]


@pytest.mark.asyncio
async def test_execute_task_background_handles_startup_failure(mock_storage):
    from app.api import task as task_api

    mock_storage.get_task.return_value = {"query": "Analyze AAPL"}
    mock_storage.update_task.side_effect = RuntimeError("database unavailable")

    await task_api.execute_task_background("task-123", object(), language="en")

    mock_storage.update_task_failure.assert_called_once()
    args = mock_storage.update_task_failure.call_args.args
    assert args[:3] == ("task-123", "failed", "error")
    assert "RuntimeError" in args[3]
    assert "database unavailable" in args[3]


@pytest.mark.asyncio
async def test_cancel_progress_task_suppresses_updater_exception():
    import asyncio

    from app.api.task import _cancel_progress_task

    async def failing_updater():
        raise RuntimeError("progress write failed")

    progress_task = asyncio.create_task(failing_updater())
    await asyncio.sleep(0)

    await _cancel_progress_task("task-123", progress_task)
