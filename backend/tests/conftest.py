import os

# Safe defaults so the test suite is self-contained (these must be set before
# `app` is imported, since auth config validates them at import time).
os.environ.setdefault(
    "JWT_SECRET_KEY", "test-jwt-secret-key-at-least-32-chars-long-aaaa"
)
os.environ.setdefault("DEFAULT_ADMIN_PASSWORD", "test-admin-password-123")
os.environ.setdefault("ALLOW_MOCK_DATA", "false")

import asyncio
from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_app() -> FastAPI:
    """Get the FastAPI application for testing."""
    return app


@pytest.fixture(autouse=True)
def _clear_tool_cache():
    """Clear the global MemoryTTLCache before every test.

    Tools share a process-wide ``MemoryTTLCache`` singleton. Without clearing,
    a real API response cached by an earlier test (e.g. one that constructs an
    Orchestrator with real keys) leaks into later tests that expect mock data,
    making ``is_mock`` come back as ``False``. The cache is a pure perf layer,
    so clearing it is always safe.
    """
    try:
        from app.tools.cache import get_cache

        get_cache().clear()
    except Exception:
        # Cache module not importable in some test contexts — ignore.
        pass
    yield


@pytest.fixture(autouse=True)
def _override_auth():
    """Authenticate every request as an admin user by default.

    Most endpoints now require `require_role(ADMIN/ANALYST)` (which depends on
    `get_current_user`). These behaviour tests predate RBAC, so we override the
    auth dependency with an admin user instead of minting real JWTs. Individual
    tests can still override `get_current_user` themselves (e.g. to test other
    roles); the teardown below restores a clean state.
    """
    from app.auth.dependencies import get_current_user
    from app.auth.models import UserResponse

    admin = UserResponse(
        id=1,
        username="admin",
        email="admin@test.local",
        role="admin",
        is_active=True,
        created_at="2026-01-01T00:00:00",
    )
    app.dependency_overrides[get_current_user] = lambda: admin
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Get an async HTTP client for testing."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_storage(monkeypatch):
    """Mock the storage module for isolated tests."""
    from unittest.mock import MagicMock, patch

    mock = MagicMock()
    mock.get_conversation.return_value = None
    mock.create_conversation.return_value = True
    mock.add_message.return_value = True
    mock.list_conversations.return_value = []
    mock.delete_conversation.return_value = True

    with patch("app.storage", mock):
        yield mock


@pytest.fixture
def mock_llm_client(monkeypatch):
    """Mock the LLM client for isolated tests."""
    from unittest.mock import AsyncMock, MagicMock, patch

    mock = MagicMock()
    mock.chat = AsyncMock(return_value=MagicMock(content="Test response"))
    mock.get_instance = MagicMock(return_value=mock)

    with patch(
        "app.infrastructure.llm_client.LLMClient.get_instance", return_value=mock
    ):
        yield mock


@pytest.fixture
def sample_task_data():
    """Sample task data for testing."""
    return {
        "task_id": "test-task-123",
        "query": "Analyze AAPL stock price",
        "status": "pending",
        "priority": 1,
    }


@pytest.fixture
def sample_conversation_data():
    """Sample conversation data for testing."""
    return {
        "conversation_id": "test-conv-123",
        "messages": [
            {"role": "user", "content": "What is the stock price of AAPL?"},
            {"role": "assistant", "content": "The current price of AAPL is $150."},
        ],
    }
