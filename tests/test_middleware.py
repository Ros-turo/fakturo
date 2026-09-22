import asyncio
import pytest
from _pytest.logging import LogCaptureFixture
from typing import Any, Callable
import logging
from middleware import SlowRequestMiddleware


@pytest.fixture(scope="function")
def messages_storage() -> list:
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
    }


@pytest.fixture(scope="function")
async def fake_app() -> Callable:
    async def app_wrapper(scope: dict[str, Any], receive: Any, send: Callable) -> None:
        await asyncio.sleep(0.1)
        await send(
            {
                "type": "http.response.start",
                "headers": [],
            }
        )

    return app_wrapper


#SlowRequestMiddleware
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
