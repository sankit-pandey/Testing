"""Shared pytest fixtures.

Requires a real PostgreSQL + Redis for integration tests (the schema uses
Postgres-only types — UUID, JSONB, INET — so SQLite is not a viable
substitute); see `knewron-localization/.github/workflows/ci.yml`, which runs
both as service containers. Point `DATABASE_URL_SYNC`/`DATABASE_URL` at a
disposable test database before running (defaults below assume the
docker-compose `db`/`redis` services running locally).
"""
import os

os.environ.setdefault(
    "DATABASE_URL_SYNC", "postgresql+psycopg2://localization:password@localhost:5432/knewron_test"
)
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://localization:password@localhost:5432/knewron_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("STORAGE_BACKEND", "local")
os.environ.setdefault("STORAGE_LOCAL_ROOT", "./data/test-storage")
os.environ.setdefault("AI_EMBEDDING_BACKEND", "phash")

import uuid
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base
from app.models import *  # noqa: F401,F403 — register all models


@pytest.fixture(scope="session")
def db_engine():
    settings = get_settings()
    engine = create_engine(settings.database_url_sync)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine) -> Generator[Session, None, None]:
    """Yields a session bound directly to the engine (not a rollback
    savepoint) because pipeline/service code under test calls `db.commit()`
    itself, same as it would in a real Celery task. Isolation between tests
    is via truncation, not rollback.
    """
    session_factory = sessionmaker(bind=db_engine)
    session = session_factory()
    yield session
    session.close()
    with db_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture()
def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


@pytest_asyncio.fixture()
async def async_db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Async session against the same physical test database as `db_session`
    (tables are created once via the sync engine in `db_engine`).
    """
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()
    with db_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
