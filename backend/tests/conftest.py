"""Pytest configuration and database fixtures for PostgreSQL testing."""

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.config import get_settings
from app.db import Base

settings = get_settings()


@pytest.fixture(scope="session")
def test_engine():
    """Session-scoped database engine for test suite."""
    engine = create_engine(settings.TEST_DATABASE_URL, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine) -> Generator[Session, None, None]:
    """Function-scoped database session wrapped in an outer transaction for clean rollback."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session = session_factory()

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()
