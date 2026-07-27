import pytest

from app.core.startup_check import (
    check_jwt_secret,
    check_production_settings,
    run_startup_checks,
)


def test_jwt_secret_rejects_missing(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY not set"):
        check_jwt_secret()


def test_jwt_secret_rejects_short_value(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "short")

    with pytest.raises(RuntimeError, match="too weak"):
        check_jwt_secret()


def test_jwt_secret_rejects_placeholder(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "your-secret-key-at-least-32-chars-long")

    with pytest.raises(RuntimeError, match="placeholder"):
        check_jwt_secret()


def test_production_rejects_mock_data(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOW_MOCK_DATA", "true")
    monkeypatch.delenv("DEMO_MODE", raising=False)
    monkeypatch.setenv("CORS_ORIGINS", "https://finance.example.com")

    with pytest.raises(RuntimeError, match="ALLOW_MOCK_DATA"):
        check_production_settings()


def test_production_demo_allows_labelled_mock_data(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("ALLOW_MOCK_DATA", "true")
    monkeypatch.setenv("CORS_ORIGINS", "https://finance.example.com")
    monkeypatch.setenv("DEFAULT_ADMIN_PASSWORD", "safe-admin-password-123")

    assert check_production_settings() is True


def test_production_demo_requires_mock_data(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("ALLOW_MOCK_DATA", "false")

    with pytest.raises(RuntimeError, match="DEMO_MODE=true requires"):
        check_production_settings()


def test_production_rejects_unsafe_cors(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOW_MOCK_DATA", "false")
    monkeypatch.setenv(
        "CORS_ORIGINS", "https://finance.example.com,http://localhost:3000"
    )

    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        check_production_settings()


def test_production_rejects_missing_default_admin_password(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOW_MOCK_DATA", "false")
    monkeypatch.setenv("CORS_ORIGINS", "https://finance.example.com")
    monkeypatch.delenv("DEFAULT_ADMIN_PASSWORD", raising=False)

    with pytest.raises(RuntimeError, match="DEFAULT_ADMIN_PASSWORD"):
        check_production_settings()


def test_production_rejects_placeholder_default_admin_password(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOW_MOCK_DATA", "false")
    monkeypatch.setenv("CORS_ORIGINS", "https://finance.example.com")
    monkeypatch.setenv("DEFAULT_ADMIN_PASSWORD", "replace-with-a-strong-admin-password")

    with pytest.raises(RuntimeError, match="DEFAULT_ADMIN_PASSWORD"):
        check_production_settings()


def test_development_allows_mock_and_local_cors(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("ALLOW_MOCK_DATA", "true")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")

    assert check_production_settings() is True


def test_run_startup_checks_accepts_safe_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("DEMO_MODE", raising=False)
    monkeypatch.setenv("JWT_SECRET_KEY", "safe-production-secret-value-1234567890")
    monkeypatch.setenv("ALLOW_MOCK_DATA", "false")
    monkeypatch.setenv("CORS_ORIGINS", "https://finance.example.com")
    monkeypatch.setenv("DEFAULT_ADMIN_PASSWORD", "safe-admin-password-123")

    assert run_startup_checks() is True
