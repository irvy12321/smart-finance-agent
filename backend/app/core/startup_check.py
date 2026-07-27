import os

_PRODUCTION_ENVS = {"prod", "production"}
_TRUE_VALUES = {"1", "true", "yes", "on"}
_WEAK_SECRET_MARKERS = {
    "admin",
    "admin123",
    "change-me",
    "changeme",
    "default-password",
    "default-secret",
    "jwt-secret",
    "password",
    "secret",
    "test-secret",
    "your-secret",
    "your-secret-key",
}


def is_production() -> bool:
    return os.getenv("ENVIRONMENT", "development").strip().lower() in _PRODUCTION_ENVS


def is_demo_mode() -> bool:
    """Whether this public deployment is explicitly serving labelled demo data."""
    return _env_bool("DEMO_MODE", default=False)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE_VALUES


def _looks_like_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return (
        lowered in _WEAK_SECRET_MARKERS
        or lowered.startswith(("your-", "change-", "replace-"))
        or "placeholder" in lowered
    )


def check_jwt_secret():
    """Validate JWT_SECRET_KEY at startup. Fail fast if missing or weak."""
    secret = os.getenv("JWT_SECRET_KEY", "").strip()

    if not secret:
        raise RuntimeError(
            "FATAL: JWT_SECRET_KEY not set. "
            "Set it in .env or docker-compose environment."
        )

    if len(secret) < 32:
        raise RuntimeError(
            f"FATAL: JWT_SECRET_KEY too weak ({len(secret)} chars). "
            "Minimum 32 characters required."
        )

    if _looks_like_placeholder(secret):
        raise RuntimeError(
            "FATAL: JWT_SECRET_KEY looks like a default or placeholder value. "
            "Generate a unique production secret."
        )

    print("[STARTUP] JWT_SECRET_KEY configured and length check passed")
    return True


def check_production_settings():
    """Validate production-only safety switches."""
    if not is_production():
        return True

    allow_mock_data = _env_bool("ALLOW_MOCK_DATA", default=False)
    demo_mode = is_demo_mode()

    if allow_mock_data and not demo_mode:
        raise RuntimeError(
            "FATAL: ALLOW_MOCK_DATA must be false in production. "
            "Set DEMO_MODE=true only for a public portfolio/demo deployment."
        )

    if demo_mode and not allow_mock_data:
        raise RuntimeError(
            "FATAL: DEMO_MODE=true requires ALLOW_MOCK_DATA=true so the "
            "deployment mode and data policy cannot disagree."
        )

    cors_origins = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]
    unsafe_origins = {
        origin
        for origin in cors_origins
        if origin == "*"
        or origin.startswith("http://localhost")
        or origin.startswith("http://127.0.0.1")
    }
    if unsafe_origins:
        raise RuntimeError(
            "FATAL: CORS_ORIGINS contains unsafe production origins: "
            f"{', '.join(sorted(unsafe_origins))}"
        )

    admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "").strip()
    if not admin_password:
        raise RuntimeError(
            "FATAL: DEFAULT_ADMIN_PASSWORD must be set in production. "
            "Do not rely on a generated admin password in production logs."
        )

    if len(admin_password) < 12:
        raise RuntimeError(
            "FATAL: DEFAULT_ADMIN_PASSWORD is too weak. "
            "Use at least 12 characters for the initial admin password."
        )

    if _looks_like_placeholder(admin_password):
        raise RuntimeError(
            "FATAL: DEFAULT_ADMIN_PASSWORD looks like a default or placeholder value. "
            "Set a unique production admin password."
        )

    if demo_mode:
        print(
            "[STARTUP] DEMO MODE enabled: simulated financial data is allowed "
            "and must remain visibly labelled"
        )
    else:
        print("[STARTUP] production safety settings check passed")
    return True


def run_startup_checks():
    """Run all fail-fast startup checks."""
    check_jwt_secret()
    check_production_settings()
    return True
