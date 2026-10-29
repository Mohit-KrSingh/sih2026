from collections.abc import Generator

import redis
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args={"connect_timeout": 2},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def get_redis_client() -> redis.Redis:
    return redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=2.0,
        socket_timeout=2.0,
    )


def get_redis() -> Generator[redis.Redis, None, None]:
    """FastAPI dependency for obtaining a Redis client connection."""
    client = get_redis_client()
    try:
        yield client
    finally:
        try:
            client.close()
        except Exception:
            pass


def check_redis_connection() -> bool:
    try:
        r = get_redis_client()
        return bool(r.ping())
    except Exception:
        return False
