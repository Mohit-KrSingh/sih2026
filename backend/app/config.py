import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENV: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    DEMO_MODE: bool = True

    # Database
    DATABASE_URL: str = "postgresql+psycopg://apaar:apaar_password@localhost:5432/apaar_db"
    TEST_DATABASE_URL: str = (
        "postgresql+psycopg://apaar:apaar_password@localhost:5432/apaar_test_db"
    )

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    JWT_SECRET: str = "super-secret-development-jwt-key-minimum-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    FERNET_KEY: str = "0123456789abcdef0123456789abcdef0123456789a="
    ED25519_PRIVATE_KEY: str = "development-ed25519-private-seed-32bytes-len!!"

    # Storage
    STORAGE_DIR: str = "./storage/uploads"

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 10
    RATE_LIMIT_OTP_PER_MINUTE: int = 5
    RATE_LIMIT_VERIFY_PER_MINUTE: int = 20

    # Integration Client Types ("mock" | "http")
    APAAR_CLIENT_TYPE: str = "mock"
    AICTE_MASTER_CLIENT_TYPE: str = "mock"
    OTP_SENDER_TYPE: str = "mock"
    IDENTITY_VERIFIER_TYPE: str = "mock"
    STORAGE_TYPE: str = "mock"  # "mock" | "local" | "http"

    # CORS
    FRONTEND_URL: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
