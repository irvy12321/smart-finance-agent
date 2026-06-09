import pytest
import asyncio
from typing import Generator, AsyncGenerator
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

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
    from unittest.mock import MagicMock, AsyncMock, patch

    mock = MagicMock()
    mock.chat = AsyncMock(return_value=MagicMock(content="Test response"))
    mock.get_instance = MagicMock(return_value=mock)

    with patch("app.infrastructure.llm_client.LLMClient.get_instance", return_value=mock):
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
