"""Database engines and session factories.

Two engines are provided:
- **Async** (`asyncpg`) — used by the FastAPI request path.
- **Sync** (`psycopg2`) — used by Celery tasks/workers, which run outside an
  asyncio event loop.

Design ref: `LOCKED_Design_v1.0.md` §9 (PostgreSQL + SQLAlchemy + Alembic). Story 0.2.
"""
from collections.abc import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

async_engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, autoflush=False, expire_on_commit=False, class_=AsyncSession
)

sync_engine = create_engine(settings.database_url_sync, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=sync_engine, autoflush=False, expire_on_commit=False, class_=Session)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async DB session."""
    async with AsyncSessionLocal() as session:
        yield session


def get_sync_db() -> Generator[Session, None, None]:
    """Context-managed sync DB session for Celery tasks."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
