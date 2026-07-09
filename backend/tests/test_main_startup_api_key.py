import pytest

from app.main import _handle_api_key_validation_error, _validate_api_key


def test_validate_api_key_rejects_missing_active_provider_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mimo")
    monkeypatch.delenv("MIMO_API_KEY", raising=False)

    with pytest.raises(ValueError, match="MIMO_API_KEY"):
        _validate_api_key()


def test_validate_api_key_rejects_placeholder(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mimo")
    monkeypatch.setenv("MIMO_API_KEY", "replace-with-mimo-api-key")

    with pytest.raises(ValueError, match="MIMO_API_KEY"):
        _validate_api_key()


def test_api_key_error_is_fatal_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")

    with pytest.raises(RuntimeError, match="LLM provider API key"):
        _handle_api_key_validation_error(ValueError("missing key"))


def test_api_key_error_is_non_fatal_in_development(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")

    assert _handle_api_key_validation_error(ValueError("missing key")) is None
