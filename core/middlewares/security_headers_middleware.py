from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        print(f"settings.ENVIRONMENT: {settings.ENVIRONMENT}")

        # Set Content Security Policy based on environment
        if settings.ENVIRONMENT == "production":
            csp = (
                "default-src 'self'; "
                "script-src 'self' https://frontend.example.com https://js.stripe.com; "
                "style-src 'self' https://fonts.googleapis.com; "
                "img-src 'self' data: https://cdn.example.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "connect-src 'self' https://api.example.com; "
                "frame-src https://js.stripe.com; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self'; "
            )
            response.headers["Content-Security-Policy"] = csp
        # else:
        #     csp = "default-src 'self';"

        # response.headers["Content-Security-Policy"] = csp
        return response
