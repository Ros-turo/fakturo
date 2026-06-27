import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from logging_config import logger


class TimingLoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        logger.info(f"Start timer for endpoint {request.url.path}")

        response = await call_next(request)

        timing = time.perf_counter() - start
        logger.info(f"Request {request.method}, {request.url.path}, {response.status_code} is {timing}")

        response.headers.update({"X-Process-Time": str(timing)})

        return response

class SecondMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request,  call_next: RequestResponseEndpoint) -> Response:

        logger.info("Inner Middleware start")
        response = await call_next(request)
        logger.info("Inner Middleware finish")

        return response