import time

from logging_config import logger


class TimingLoggingMiddleware:

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):

        if scope["type"] != "http":
            await self.app(scope,receive, send)
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

class CORSMiddleware:

    def __init__(self,app):
        self.app = app

    async def __call__(self, scope:dict, receive, send):

        if scope["type"] != "http":
            await self.app(scope,receive, send)
            return

        if scope["method"] == "OPTIONS":
            await send({
                "type":"http.response.start",
                "status":200,
                "headers":[
                    (b"Access-Control-Allow-Origin",b"*"),
                    (b"Access-Control-Allow-Headers",b"*"),
                    (b"Access-Control-Allow-Methods",b"GET,POST,PUT,DELETE,OPTIONS"),
                ]
            })
            await send(
                {
                    "type":"http.response.body",
                    "body":b"",
                }
            )
            return

        start = None
        async def send_wrapper(message):
            nonlocal start
            if message["type"] == "http.response.start":
                start = message
                return
            elif message["type"] == "http.response.body":
                if start:
                    start["headers"].append((b"Access-Control-Allow-Origin", b"*"))
                    await send(start)
                    start = None
                await send(message)

        await self.app(scope, receive, send_wrapper)




