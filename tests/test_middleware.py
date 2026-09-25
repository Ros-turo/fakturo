import asyncio
import pytest
from _pytest.logging import LogCaptureFixture
from typing import Any, Callable
import logging
from middleware import CORSMiddleware, SlowRequestMiddleware, MaxBodySizeMiddleware
from settings import settings
import json

ALLOWED_ORIGIN = settings.allowed_origins[0]
ALLOWED_ORIGIN_BYTES = ALLOWED_ORIGIN.encode()


@pytest.fixture(scope="function")
def messages_storage() -> list[dict[str, Any]]:
    return []


@pytest.fixture(scope="function")
def fake_send(messages_storage: list[Any]) -> Callable:
    async def send_wrapper(message):
        messages_storage.append(message)

    return send_wrapper


@pytest.fixture(scope="function")
def fake_scope() -> dict[str, Any]:
    return {
        "type": "http",
        "path": "/fake/path",
        "method": "GET",
        "headers": [],
    }


@pytest.fixture(scope="function")
async def fake_app() -> Callable:
    async def app_wrapper(scope: dict[str, Any], receive: Any, send: Callable) -> None:
        await asyncio.sleep(0.1)
        await send({"type": "http.response.start", "headers": [], "status": 200})
        await send({"type": "http.response.body", "body": b""})

    return app_wrapper


# SlowRequestMiddleware
async def test_slow_request_middleware_fast_request_no_warning(
    caplog: LogCaptureFixture,
    fake_app: Callable,
    fake_scope: dict[str, Any],
    fake_send: Callable,
    messages_storage: list,
) -> None:

    middleware = SlowRequestMiddleware(fake_app, threshold=5)

    with caplog.at_level(logging.WARNING):
        await middleware(fake_scope, receive=None, send=fake_send)
        assert caplog.messages == []
    headers = messages_storage[0].get("headers")

    assert headers[0][0] == b"X-Response-Time"


async def test_slow_request_middleware_catch(
    caplog: LogCaptureFixture,
    messages_storage: list[Any],
    fake_app: Callable,
    fake_scope: dict[str, Any],
    fake_send: Callable,
) -> None:

    middleware = SlowRequestMiddleware(fake_app, threshold=0)

    with caplog.at_level(logging.WARNING):
        await middleware(fake_scope, receive=None, send=fake_send)
        assert "/fake/path" in caplog.text
    headers = messages_storage[0].get("headers")

    assert headers[0][0] == b"X-Response-Time"


# CORSMiddleware
async def test_cors_middleware_allowed_origin_success(
    fake_app: Callable,
    fake_scope: dict[str, Any],
    fake_send: Callable,
    messages_storage: list[Any],
) -> None:

    middleware = CORSMiddleware(fake_app, allowed_origins=[ALLOWED_ORIGIN])

    fake_scope["headers"] = [(b"origin", ALLOWED_ORIGIN_BYTES)]
    await middleware(fake_scope, receive=None, send=fake_send)
    headers = messages_storage[0].get("headers")
    status_code = messages_storage[0].get("status")
    allow_origin_headers = [
        h for h in headers if h[0] == b"Access-Control-Allow-Origin"
    ]

    assert len(allow_origin_headers) == 1
    assert allow_origin_headers[0][1] == ALLOWED_ORIGIN_BYTES
    assert status_code == 200


async def test_cors_middleware_without_origin(
    fake_app: Callable,
    fake_scope: dict[str, Any],
    fake_send: Callable,
    messages_storage: list[Any],
) -> None:

    middleware = CORSMiddleware(fake_app, allowed_origins=[ALLOWED_ORIGIN])
    await middleware(fake_scope, receive=None, send=fake_send)
    status_code = messages_storage[0].get("status")
    headers = messages_storage[0].get("headers")
    allow_origin_headers = [
        h for h in headers if h[0] == b"Access-Control-Allow-Origin"
    ]

    assert status_code == 200
    assert len(allow_origin_headers) == 0


async def test_cors_middleware_wrong_origin(
    fake_app: Callable,
    fake_scope: dict[str, Any],
    fake_send: Callable,
    messages_storage: list[Any],
) -> None:

    middleware = CORSMiddleware(fake_app, allowed_origins=[ALLOWED_ORIGIN])

    fake_scope["headers"] = [(b"origin", b"http://csrf_attack")]
    await middleware(fake_scope, receive=None, send=fake_send)
    status_code = messages_storage[0].get("status")

    assert status_code == 403


async def test_cors_middleware_method_options(
    fake_app: Callable,
    fake_scope: dict[str, Any],
    fake_send: Callable,
    messages_storage: list[Any],
) -> None:

    middleware = CORSMiddleware(fake_app, allowed_origins=[ALLOWED_ORIGIN])

    fake_scope["method"] = "OPTIONS"
    fake_scope["headers"] = [(b"origin", ALLOWED_ORIGIN_BYTES)]
    await middleware(fake_scope, receive=None, send=fake_send)
    headers = messages_storage[0].get("headers")
    status_code = messages_storage[0].get("status")
    allow_origin_headers = [
        h for h in headers if h[0] == b"Access-Control-Allow-Origin"
    ]

    assert status_code == 200
    assert len(allow_origin_headers) == 1
    assert allow_origin_headers[0][1] == ALLOWED_ORIGIN_BYTES


#MaxBodySizeMiddleware
async def test_max_body_size_middleware_blocked_by_limit(
        fake_app: Callable,
        fake_scope: dict[str, Any],
        fake_send: Callable,
        messages_storage: list[Any],
) -> None:

    middleware = MaxBodySizeMiddleware(fake_app, max_body_size=1024)

    fake_scope["headers"].append((b"content-length", b"1025"))
    await middleware(fake_scope, receive=None, send=fake_send)

    status_code = messages_storage[0].get("status")
    json_body = messages_storage[1].get("body").decode()
    body = json.loads(json_body)
    detail = body["detail"]

    assert status_code == 413
    assert "too large" in detail.lower()

async def test_max_body_size_middleware_under_limit(
        fake_app: Callable,
        fake_scope: dict[str, Any],
        fake_send: Callable,
        messages_storage: list[Any],
) -> None:

    middleware = MaxBodySizeMiddleware(fake_app, max_body_size=1024)

    fake_scope["headers"].append((b"content-length", b"1022"))
    await middleware(fake_scope, receive=None, send=fake_send)
    status_code = messages_storage[0].get("status")

    assert status_code == 200
