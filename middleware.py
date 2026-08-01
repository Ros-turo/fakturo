import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

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

"""
Zadání: Napiš middleware RequestLoggingMiddleware, co:

Přečte celé tělo requestu (přes receive()) předtím, než ho appka dostane
Zaloguje velikost těla v bajtech (len(body))
Musí tělo znovu zpřístupnit appce beze změny — pokud tělo jednou přečteš přes receive(), 
appka by ho už neviděla (stream se dá přečíst jen jednou), takže musíš vymyslet, jak ho "vrátit zpátky"

Otázka na rozjezd, než začneš: receive() může vrátit víc zpráv za sebou 
(pokud je tělo velké, přijde po částech, s more_body: True/False flagem).
 Jak zjistíš, že jsi přečetl celé tělo (žádná další část nepřijde)?"""

class RequestLoggingMiddleware:

    def __init__(self,app):
        self.app = app

    async def __call__(self,scope, receive, send):

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return


        body = []
        while True:
            message:dict = await receive()
            body_flag = message.get("more_body")

            body.append(message)

            if body_flag is None or not body_flag:
                break

        index = 0
        async def receive_wrapper():

            nonlocal index

            if index < len(body):
                message = body[index]
                index += 1
                return message

            return await receive()

        logger.info(f"{sum([len(message["body"]) for message in body])}, body: {body}")

        await self.app(scope, receive_wrapper, send)



