from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings
from app.db import check_db_connection, check_redis_connection

router = APIRouter(prefix="/health", tags=["Health"])


class ServiceStatus(BaseModel):
    database: str
    redis: str


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    services: ServiceStatus
    demo_mode: bool


@router.get("", response_model=HealthResponse)
def get_health() -> HealthResponse:
    settings = get_settings()
    db_ok = check_db_connection()
    redis_ok = check_redis_connection()

    overall_status = "healthy" if (db_ok and redis_ok) else "degraded"

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(UTC).isoformat(),
        version="0.1.0",
        services=ServiceStatus(
            database="connected" if db_ok else "disconnected",
            redis="connected" if redis_ok else "disconnected",
        ),
        demo_mode=settings.DEMO_MODE,
    )
