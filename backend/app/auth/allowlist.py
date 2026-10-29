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
    # Public privacy & DPDP compliance endpoint (Spec 16, TASKS.md T38)
    ("/api/v1/privacy", "GET"),
    # Public authentication endpoints
    ("/api/v1/auth/login", "POST"),
    ("/api/v1/auth/refresh", "POST"),
    ("/api/v1/auth/mfa/verify", "POST"),
    ("/api/v1/auth/otp/send", "POST"),
    ("/api/v1/auth/otp/verify", "POST"),
    ("/api/v1/auth/password-reset/request", "POST"),
    ("/api/v1/auth/password-reset/verify", "POST"),
    ("/api/v1/auth/password-reset/confirm", "POST"),
    # Public verification lookup endpoints
    ("/api/v1/verification/verify", "GET"),
    ("/api/v1/verification/records/{verification_id}", "GET"),
    ("/api/v1/verification/records/{verification_id}/qr", "GET"),
    ("/api/v1/verification/public-key", "GET"),
    # Public verifier onboarding & student consent portal endpoints (Spec 14, TASKS.md T33)
    ("/api/v1/verification/verifiers/register", "POST"),
    ("/api/v1/verification/student/otp/send", "POST"),
    ("/api/v1/verification/student/otp/verify", "POST"),
    # Public college activation endpoints (Spec 11, TASKS.md T08)
    ("/api/v1/institutions/activation/initiate", "POST"),
    ("/api/v1/institutions/activation/verify-otp", "POST"),
    ("/api/v1/institutions/activation/submit", "POST"),
    ("/api/v1/institutions/activation/submit-form", "POST"),
    ("/api/v1/institutions/activation/status/{aicte_id}", "GET"),
    # Developer simulation endpoints (guarded by DEMO_MODE check)
    ("/api/v1/dev/outbox", "GET"),
    ("/api/v1/dev/outbox", "DELETE"),
    ("/api/v1/dev/otp/send", "POST"),
}
