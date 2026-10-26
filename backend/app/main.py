from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api_v1 import api_v1_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="APAAR Student Data Management & Verification API",
    description="Backend API for AICTE APAAR Student Data Management and Verification System",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

origins = [
    settings.FRONTEND_URL,
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
