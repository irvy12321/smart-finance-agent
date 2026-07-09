"""Shared helpers for removing credentials from logs and error payloads."""

import re

_REDACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"sk-[A-Za-z0-9_\-]{8,}"), "sk-***"),
    (re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]{8,}", re.IGNORECASE), r"\1***"),
    (
        re.compile(
            r"([?&](?:api[_-]?key|apikey|access[_-]?token|refresh[_-]?token|auth[_-]?token|stream[_-]?token|token|secret|password|key)=)"
            r"[^&\s\"']+",
            re.IGNORECASE,
        ),
        r"\1***",
    ),
    (
        re.compile(
            r"""(
                ["']?
                (?:[A-Z0-9_]*_?API_KEY|api[_-]?key|access[_-]?token|refresh[_-]?token|auth[_-]?token|stream[_-]?token|token|secret|password)
                ["']?
                \s*[=:]\s*
                ["']?
            )
            [^\s"',}&]{6,}
            (["']?)
            """,
            re.IGNORECASE | re.VERBOSE,
        ),
        r"\1***\2",
    ),
)


def redact_sensitive_text(value: object) -> str:
    """Best-effort text redaction for API keys, bearer tokens, and secrets."""
    if value is None:
        return ""

    text = str(value)
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text
