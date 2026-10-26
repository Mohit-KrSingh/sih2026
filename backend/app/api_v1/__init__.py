from fastapi import APIRouter

from app.api_v1.dev import router as dev_router
from app.api_v1.health import router as health_router
from app.auth.router import router as auth_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(dev_router)
api_v1_router.include_router(auth_router)

