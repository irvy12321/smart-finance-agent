from app.main import _before_send, _redact_headers, _redact_url


def test_redact_headers_is_case_insensitive():
    headers = {
        "Authorization": "Bearer secret-token",
        "Cookie": "session=secret",
        "X-Api-Key": "tool-key",
        "Accept": "application/json",
    }

    assert _redact_headers(headers) == {
        "Authorization": "[FILTERED]",
        "Cookie": "[FILTERED]",
        "X-Api-Key": "[FILTERED]",
        "Accept": "application/json",
    }


def test_redact_url_filters_sensitive_query_params():
    url = "https://api.example.com/api/task/abc/stream?stream_token=secret&symbol=AAPL"

    assert (
        _redact_url(url)
        == "https://api.example.com/api/task/abc/stream?stream_token=[FILTERED]&symbol=AAPL"
    )


def test_before_send_redacts_request_context_headers_urls_and_extra():
    event = {
        "request": {
            "url": "https://api.example.com/research?access_token=secret&q=AAPL",
            "query_string": "refresh_token=secret&page=1",
            "headers": {
                "Authorization": "Bearer secret",
                "User-Agent": "pytest",
            },
        },
        "contexts": {
            "request": {
                "url": "https://api.example.com/stream?apiKey=secret&x=1",
                "headers": {
                    "Cookie": "sid=secret",
                    "Accept": "text/event-stream",
                },
            }
        },
        "extra": {
            "password": "secret",
            "nested": {"api_key": "secret"},
            "safe": "keep",
        },
    }

    redacted = _before_send(event, hint={})

    assert redacted["request"]["headers"]["Authorization"] == "[FILTERED]"
    assert redacted["request"]["headers"]["User-Agent"] == "pytest"
    assert "access_token=[FILTERED]" in redacted["request"]["url"]
    assert redacted["request"]["query_string"] == "refresh_token=[FILTERED]&page=1"
    assert redacted["contexts"]["request"]["headers"]["Cookie"] == "[FILTERED]"
    assert "apiKey=[FILTERED]" in redacted["contexts"]["request"]["url"]
    assert redacted["extra"]["password"] == "[FILTERED]"
    assert redacted["extra"]["nested"]["api_key"] == "[FILTERED]"
    assert redacted["extra"]["safe"] == "keep"
