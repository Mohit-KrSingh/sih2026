"""Public allowlist for endpoints exempt from RBAC role requirements.

All routes not on this explicit allowlist MUST enforce authentication
and role permissions via dependencies.
"""

# Explicit tuples of (path, HTTP_method) that do not require authentication
PUBLIC_ALLOWLIST: set[tuple[str, str]] = {
    # System and API documentation
    ("/", "GET"),
    ("/docs", "GET"),
    ("/docs/oauth2-redirect", "GET"),
    ("/redoc", "GET"),
    ("/openapi.json", "GET"),
    # Public health check
    ("/api/v1/health", "GET"),
    # Public authentication endpoints
    ("/api/v1/auth/login", "POST"),
    ("/api/v1/auth/refresh", "POST"),
    # Developer simulation endpoints (guarded by DEMO_MODE check)
    ("/api/v1/dev/outbox", "GET"),
    ("/api/v1/dev/outbox", "DELETE"),
    ("/api/v1/dev/otp/send", "POST"),
}
