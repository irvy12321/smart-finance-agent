"""Safe error helpers for API responses."""

from app.utils.redaction import redact_sensitive_text

GENERIC_INTERNAL_ERROR = "Internal server error"


def safe_bad_request_detail(error: object, fallback: str = "Request failed") -> str:
    detail = redact_sensitive_text(error).strip()
    return detail or fallback


def safe_internal_detail(fallback: str = GENERIC_INTERNAL_ERROR) -> str:
    return fallback
