from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

SECRET = "api-secret-value-123456"


@pytest.mark.asyncio
async def test_chat_create_conversation_error_does_not_expose_secret(
    client: AsyncClient,
):
    with patch(
        "app.api.chat.storage.create_conversation",
        side_effect=RuntimeError(f"db failed password={SECRET}"),
    ):
        response = await client.post("/api/chat/conversations")

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to create conversation"
    assert SECRET not in response.text


@pytest.mark.asyncio
async def test_tools_business_error_is_redacted(client: AsyncClient):
    result = MagicMock()
    result.success = False
    result.error = f"provider failed: https://example.com?api_key={SECRET}"

    tool = MagicMock()
    tool.execute = AsyncMock(return_value=result)

    with patch("app.api.tools.StockPriceTool", return_value=tool):
        response = await client.post(
            "/api/tools/stock/price",
            json={"symbol": "AAPL"},
        )

    assert response.status_code == 400
    data = response.json()
    assert SECRET not in str(data)
    assert "api_key=***" in data["detail"]


@pytest.mark.asyncio
async def test_system_metrics_error_does_not_expose_secret(client: AsyncClient):
    with patch(
        "app.api.system.storage.list_tasks",
        side_effect=RuntimeError(f"storage failed password={SECRET}"),
    ):
        response = await client.get("/api/system/metrics")

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to get system metrics"
    assert SECRET not in response.text


@pytest.mark.asyncio
async def test_research_error_does_not_expose_secret(client: AsyncClient):
    service = MagicMock()
    service.research = AsyncMock(
        side_effect=RuntimeError(f"provider failed api_key={SECRET}")
    )

    with patch("app.api.research.ResearchService", return_value=service):
        response = await client.post("/api/research/AAPL")

    assert response.status_code == 500
    assert response.json()["detail"] == "Research failed"
    assert SECRET not in response.text


@pytest.mark.asyncio
async def test_auth_register_error_does_not_expose_secret(real_client: AsyncClient):
    with (
        patch("app.api.auth.get_user_by_username", return_value=None),
        patch("app.api.auth.get_user_by_email", return_value=None),
        patch(
            "app.api.auth.create_user",
            side_effect=RuntimeError(f"insert failed password={SECRET}"),
        ),
    ):
        response = await real_client.post(
            "/api/auth/register",
            json={
                "username": "safe_error_user",
                "email": "safe_error_user@example.com",
                "password": "Str0ngPass-123",
            },
        )

    assert response.status_code == 500
    assert response.json()["detail"] == "Registration failed"
    assert SECRET not in response.text
