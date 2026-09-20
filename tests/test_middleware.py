import asyncio
import logging

from middleware import SlowRequestMiddleware


async def test_slow_request_middleware_fast_request_no_warning(caplog) -> None:

    async def fake_app(scope, recieve, send) -> None:
        await asyncio.sleep(1)
        await send(
            {
                "type": "http.response.start",
                "headers": [],
            }
        )

    middleware = SlowRequestMiddleware(fake_app, threshold=5)

    messages_storage = []
    fake_scope = {
        "type": "http",
        "path": "/fake/path",
        "method": "GET",
    }

    async def fake_send(message):
        messages_storage.append(message)

    with caplog.at_level(logging.WARNING):
        await middleware(fake_scope, receive=None, send=fake_send)
        assert caplog.messages == []

    headers = messages_storage[0].get("headers")
    assert headers[0][0] == b"X-Response-Time"


async def test_slow_request_middleware_catch(
    caplog,
) -> None:

    async def fake_app(scope, recieve, send) -> None:
        await asyncio.sleep(1)
        await send(
            {
                "type": "http.response.start",
                "headers": [],
            }
        )

    middleware = SlowRequestMiddleware(fake_app, threshold=0.5)

    messages_storage = []
    fake_scope = {
        "type": "http",
        "path": "/fake/path",
        "method": "GET",
    }

    async def fake_send(message):
        messages_storage.append(message)

    with caplog.at_level(logging.WARNING):
        await middleware(fake_scope, receive=None, send=fake_send)
        assert "/fake/path" in caplog.text

    headers = messages_storage[0].get("headers")
    assert headers[0][0] == b"X-Response-Time"
