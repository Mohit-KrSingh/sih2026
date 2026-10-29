from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api_v1 import api_v1_router
from app.config import get_settings
from app.logging_config import setup_logging
from app.middleware import RequestBodySizeLimiterMiddleware, SecurityHeadersMiddleware

# Initialize log masking filter on application startup
setup_logging()

settings = get_settings()

app = FastAPI(
    title="APAAR Student Data Management & Verification API",
    description="Backend API for AICTE APAAR Student Data Management and Verification System",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Explicit allowed origins for strict CORS
origins = [
    settings.FRONTEND_URL,
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

# Strict CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "Idempotency-Key",
        "X-Idempotency-Key",
        "X-API-Key",
    ],
    expose_headers=["Content-Disposition", "X-Idempotent-Replayed", "Retry-After"],
)

# Standard security headers and request body size limiter
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestBodySizeLimiterMiddleware)

app.include_router(api_v1_router)


@app.get("/")
def read_root():
    return {
        "message": "APAAR Student Data Management and Verification API",
        "docs": "/docs",
        "health": "/api/v1/health",
        "version": "0.1.0",
        "demo_mode": settings.DEMO_MODE,
    }
