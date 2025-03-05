import json

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from fastapi import Response, Request
from core.logger import get_logger
from core.config import settings
import time
from services.aws.cloudwatch_logs import get_cloudwatch_logs_client

logger = get_logger(__name__)


class CloudWatchLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Middleware to catch exceptions and log them to AWS CloudWatch."""
        try:
            return await call_next(request)
        except Exception as e:
            cloudwatch_logs = get_cloudwatch_logs_client()
            # Ensure log group and stream exist
            try:
                cloudwatch_logs.create_log_group(logGroupName=settings.AWS_LOG_GROUP)
            except cloudwatch_logs.get_exceptions().ResourceAlreadyExistsException:
                pass

            try:
                cloudwatch_logs.create_log_stream(logGroupName=settings.AWS_LOG_GROUP, logStreamName=settings.AWS_LOG_STREAM)
            except cloudwatch_logs.get_exceptions().ResourceAlreadyExistsException:
                pass
            error_message = {
                "error": str(e),
                "method": request.method,
                "path": request.url.path,
                "headers": dict(request.headers),
            }
            log_event = {
                "logGroupName": settings.AWS_LOG_GROUP,
                "logStreamName": settings.AWS_LOG_STREAM,
                "logEvents": [
                    {
                        "timestamp": int(request.state.timestamp),
                        "message": json.dumps(error_message),
                    }
                ],
            }
            cloudwatch_logs.put_log_events(**log_event)
            logger.error(f"Error: {str(e)}")
            raise e
