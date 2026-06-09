import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def mock_auth():
    with patch("app.api.auth.get_user_by_username") as mock_get_user, \
         patch("app.api.auth.get_user_by_email") as mock_get_email, \
         patch("app.api.auth.create_user") as mock_create, \
         patch("app.api.auth.authenticate_user") as mock_authenticate, \
         patch("app.api.auth.create_access_token") as mock_token, \
         patch("app.api.auth.get_password_hash") as mock_hash:

        mock_get_user.return_value = None
        mock_get_email.return_value = None
        mock_create.return_value = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "is_active": True,
            "created_at": "2026-01-01"
        }
        mock_authenticate.return_value = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "is_active": True,
            "created_at": "2026-01-01"
        }
        mock_token.return_value = "test-jwt-token"
        mock_hash.return_value = "hashed-password"

        yield {
            "get_user": mock_get_user,
            "get_email": mock_get_email,
            "create": mock_create,
            "authenticate": mock_authenticate,
            "token": mock_token,
            "hash": mock_hash
        }


@pytest.mark.asyncio
async def test_register(client: AsyncClient, mock_auth):
    response = await client.post(
        "/api/auth/register",
        json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["access_token"] == "test-jwt-token"
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "testuser"


@pytest.mark.asyncio
async def test_register_existing_username(client: AsyncClient, mock_auth):
    mock_auth["get_user"].return_value = {"id": 1, "username": "existing"}

    response = await client.post(
        "/api/auth/register",
        json={
            "username": "existing",
            "email": "new@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_existing_email(client: AsyncClient, mock_auth):
    mock_auth["get_email"].return_value = {"id": 1, "email": "existing@example.com"}

    response = await client.post(
        "/api/auth/register",
        json={
            "username": "newuser",
            "email": "existing@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login(client: AsyncClient, mock_auth):
    response = await client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "password123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "test-jwt-token"
    assert data["user"]["username"] == "testuser"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, mock_auth):
    mock_auth["authenticate"].return_value = None

    response = await client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_inactive_user(client: AsyncClient, mock_auth):
    mock_auth["authenticate"].return_value = {
        "id": 1,
        "username": "testuser",
        "is_active": False
    }

    response = await client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "password123"
        }
    )
    assert response.status_code == 403