from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import httpx


def load_server_module():
    server_path = Path(__file__).resolve().parents[1] / "server.py"
    spec = importlib.util.spec_from_file_location("canvas_mcp_server", server_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


server = load_server_module()


def build_http_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://canvas.example/api/v1/test")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError("request failed", request=request, response=response)


def test_headers_include_bearer_token(monkeypatch):
    monkeypatch.setattr(server, "CANVAS_API_TOKEN", "secret-token")

    assert server._headers() == {"Authorization": "Bearer secret-token"}


def test_check_config_reports_missing_values(monkeypatch):
    monkeypatch.setattr(server, "CANVAS_API_TOKEN", "")
    monkeypatch.setattr(server, "CANVAS_BASE_URL", "https://canvas.example")
    assert server._check_config() == "Error: CANVAS_API_TOKEN environment variable is not set."

    monkeypatch.setattr(server, "CANVAS_API_TOKEN", "secret-token")
    monkeypatch.setattr(server, "CANVAS_BASE_URL", "")
    assert server._check_config() == (
        "Error: CANVAS_BASE_URL environment variable is not set "
        "(e.g. https://yourschool.instructure.com)."
    )


def test_check_config_returns_none_when_complete(monkeypatch):
    monkeypatch.setattr(server, "CANVAS_API_TOKEN", "secret-token")
    monkeypatch.setattr(server, "CANVAS_BASE_URL", "https://canvas.example")

    assert server._check_config() is None


def test_fmt_date_formats_iso_timestamp():
    formatted = server._fmt_date("2026-04-03T15:30:00Z")

    assert formatted == "Fri Apr 3, 2026 at 3:30 PM UTC"


def test_fmt_date_normalizes_non_utc_offsets():
    formatted = server._fmt_date("2026-04-03T09:30:00-06:00")

    assert formatted == "Fri Apr 3, 2026 at 3:30 PM UTC"


def test_fmt_date_falls_back_for_invalid_input():
    assert server._fmt_date("not-a-date") == "not-a-date"
    assert server._fmt_date(None) == "No due date"


def test_urgency_label_variants():
    assert server._urgency_label(None) == ""
    assert server._urgency_label(-1) == " [OVERDUE]"
    assert server._urgency_label(0) == " [DUE TODAY]"
    assert server._urgency_label(1) == " [DUE TOMORROW]"
    assert server._urgency_label(3) == " [DUE IN 3 DAYS]"
    assert server._urgency_label(6) == ""


def test_handle_error_maps_status_codes():
    cases = {
        401: "Unauthorized",
        403: "Permission denied",
        404: "Not found",
        429: "Rate limit exceeded",
        500: "Canvas API returned HTTP 500",
    }

    for status_code, expected in cases.items():
        message = server._handle_error(build_http_error(status_code))
        assert expected in message


def test_handle_error_maps_non_http_exceptions():
    assert "Request timed out" in server._handle_error(httpx.TimeoutException("timeout"))
    assert server._handle_error(ValueError("bad config")) == "Error: bad config"
    assert server._handle_error(RuntimeError("boom")) == "Error: RuntimeError: boom"


class FakeResponse:
    def __init__(self, data, headers=None):
        self._data = data
        self.headers = headers or {}
        self.request = httpx.Request("GET", "https://canvas.example/api/v1/test")

    def json(self):
        return self._data

    def raise_for_status(self):
        return None


class FakeAsyncClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, headers=None, params=None):
        self.calls.append({"url": url, "headers": headers, "params": params})
        return self.responses.pop(0)


def test_get_combines_paginated_list_responses(monkeypatch):
    monkeypatch.setattr(server, "CANVAS_API_TOKEN", "secret-token")
    monkeypatch.setattr(server, "CANVAS_BASE_URL", "https://canvas.example")

    fake_client = FakeAsyncClient(
        [
            FakeResponse(
                [{"id": 1}],
                headers={
                    "Link": (
                        '<https://canvas.example/api/v1/courses?page=2>; rel="next", '
                        '<https://canvas.example/api/v1/courses?page=2>; rel="last"'
                    )
                },
            ),
            FakeResponse([{"id": 2}]),
        ]
    )

    monkeypatch.setattr(server.httpx, "AsyncClient", lambda timeout=30.0: fake_client)

    result = asyncio.run(server._get("courses", params={"per_page": 10}))

    assert result == [{"id": 1}, {"id": 2}]
    assert fake_client.calls[0]["url"] == "https://canvas.example/api/v1/courses"
    assert fake_client.calls[0]["params"] == {"per_page": 10}
    assert fake_client.calls[1]["url"] == "https://canvas.example/api/v1/courses?page=2"
    assert fake_client.calls[1]["params"] is None


def test_get_returns_single_object_response(monkeypatch):
    monkeypatch.setattr(server, "CANVAS_API_TOKEN", "secret-token")
    monkeypatch.setattr(server, "CANVAS_BASE_URL", "https://canvas.example")

    fake_client = FakeAsyncClient([FakeResponse({"id": 7, "name": "Course"})])
    monkeypatch.setattr(server.httpx, "AsyncClient", lambda timeout=30.0: fake_client)

    result = asyncio.run(server._get("courses/7"))

    assert result == {"id": 7, "name": "Course"}
    assert len(fake_client.calls) == 1

