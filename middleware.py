import time
from logging_config import logger


class TimingLoggingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]
        method = scope["method"]
        status_code = 0
        start = time.perf_counter()
        logger.info(f"Start timer for endpoint {path}")

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        await self.app(scope, receive, send_wrapper)
        timing = time.perf_counter() - start
        logger.info(f"Request {method}, {path}, {status_code} is {timing}")


class SlowRequestMiddleware:
    def __init__(self, app, threshold: float) -> None:
        self.app = app
        self.threshold = threshold

    async def __call__(self, scope: dict, receive, send) -> None:

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]
        method = scope["method"]

        start = time.perf_counter()
        finish = None

        async def send_wrapper(message):
            nonlocal finish
            if message["type"] == "http.response.start":
                finish = time.perf_counter()

                message["headers"].append((b"X-Response-Time", str(finish - start).encode()))

            await send(message)

        await self.app(scope, receive, send_wrapper)

        if not finish is None:
            request_duration = finish - start

            if request_duration > self.threshold:
                logger.warning(f"{method}, {path}, takes {request_duration} seconds")


class CORSMiddleware:
    def __init__(self, app, allowed_origins: list[str]) -> None:
        self.app = app
        self.allowed_origins = allowed_origins

    async def __call__(self, scope: dict, receive, send):

        request_type = scope["type"]
        if request_type != "http":
            await self.app(scope, receive, send)
            return

        headers = scope["headers"]
        method = scope["method"]

        site_origin = self.get_site_origin(headers)
        if site_origin is None:
            await self.app(scope, receive, send)
            return
        elif site_origin not in self.allowed_origins:
            await self.block_request(send)
            return

        site_origin_bytes = site_origin.encode()

        if method == "OPTIONS":
            await self.method_options(site_origin_bytes, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                message["headers"].append(
                        (b"Access-Control-Allow-Origin", site_origin_bytes))
                await send(message)
            elif message["type"] == "http.response.body":
                await send(message)

        await self.app(scope, receive, send_wrapper)

    @staticmethod
    async def method_options(site_origin_bytes, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    (b"Access-Control-Allow-Origin", site_origin_bytes),
                    (b"Access-Control-Allow-Headers", b"*"),
                    (
                        b"Access-Control-Allow-Methods",
                        b"GET,POST,PUT,DELETE,OPTIONS",
                    ),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b"",
            }
        )

    @staticmethod
    def get_site_origin(headers: list[tuple]) -> str | None:
        site_origin = None
        for header in headers:
            if header[0] == b"origin":
                site_origin = header[1].decode()
        return site_origin

    @staticmethod
    async def block_request(send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 403,
            }
        )
        await send({"type": "http.response.body", "body": b""})


class MaxBodySizeMiddleware:
    def __init__(self, app, max_body_size: int = 1_000_000) -> None:
        self.app = app
        self.max_body_size = max_body_size

    async def __call__(self, scope: dict, receive, send) -> None:

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        body_size = 0
        headers: list[bytes] = scope["headers"]
        for header in headers:
            if header[0] == b"content-length":
                body_size = int(header[1])

        if body_size > self.max_body_size:
            await send(
                {
                    "type": "http.response.start",
                    "status": 413,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b'{"detail": "Payload too large"}',
                }
            )
            return

        await self.app(scope, receive, send)
