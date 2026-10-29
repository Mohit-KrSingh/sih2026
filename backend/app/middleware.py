"""Security middlewares for HTTP headers, strict CORS, and request body limits."""

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send

DEFAULT_MAX_REQUEST_BODY_BYTES = 15 * 1024 * 1024  # 15 MB


class SecurityHeadersMiddleware:
    """Pure ASGI middleware enforcing standard web security headers on all responses."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["x-content-type-options"] = "nosniff"
                headers["x-frame-options"] = "DENY"
                headers["x-xss-protection"] = "1; mode=block"
                headers["strict-transport-security"] = "max-age=31536000; includeSubDomains"
                headers["referrer-policy"] = "strict-origin-when-cross-origin"
                headers["permissions-policy"] = (
                    "geolocation=(), camera=(), microphone=(), payment=()"
                )
                headers["content-security-policy"] = (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                    "img-src 'self' data: https:; "
                    "font-src 'self' https: data:; "
                    "connect-src 'self' http: https: ws: wss:; "
                    "frame-ancestors 'none';"
                )
            await send(message)

        await self.app(scope, receive, send_wrapper)


class RequestBodySizeLimiterMiddleware:
    """Pure ASGI middleware enforcing maximum allowed request body size (HTTP 413)."""

    def __init__(self, app: ASGIApp, max_bytes: int = DEFAULT_MAX_REQUEST_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length_raw = None
        for name, value in scope.get("headers", []):
            if name.lower() == b"content-length":
                content_length_raw = value
                break

        if content_length_raw is not None:
            try:
                content_length = int(content_length_raw.decode("latin1"))
                if content_length > self.max_bytes:
                    max_mb = self.max_bytes // (1024 * 1024)
                    response = JSONResponse(
                        status_code=413,
                        content={
                            "detail": (
                                f"Request entity too large. Maximum allowed size is {max_mb}MB."
                            )
                        },
                    )
                    await response(scope, receive, send)
                    return
            except ValueError:
                pass

        bytes_received = 0

        async def receive_with_limit() -> dict:
            nonlocal bytes_received
            message = await receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                bytes_received += len(body)
                if bytes_received > self.max_bytes:
                    max_mb = self.max_bytes // (1024 * 1024)
                    raise HTTPException(
                        status_code=413,
                        detail=f"Request entity too large. Maximum allowed size is {max_mb}MB.",
                    )
            return message

        try:
            await self.app(scope, receive_with_limit, send)
        except HTTPException as exc:
            if exc.status_code == 413:
                response = JSONResponse(status_code=413, content={"detail": exc.detail})
                await response(scope, receive, send)
                return
            raise
