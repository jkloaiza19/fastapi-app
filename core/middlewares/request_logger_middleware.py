from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from fastapi import Response, Request
from core.logger import get_logger
import time

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.time()
        logger.info(f"Request started at {start_time} | {request.method} | {request.url}")

        response = await call_next(request)

        process_time = time.time() - start_time

        logger.info(f"Request completed: {request.method} - {request.url} - Status: {response.status_code} - Process Time: {process_time:.2f}s")

        return response
