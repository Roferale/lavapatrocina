"""
Async SQLAlchemy engine + session factory.

Environment variables
---------------------
DATABASE_URL   Async DSN, e.g.
               postgresql+asyncpg://user:pass@localhost:5432/lava
"""

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.models.base import Base  # noqa: F401 — re-exported for Alembic
# Import every model module so that Base.metadata is populated when this
# module is imported (needed by Alembic and create_all).
import app.models.user      # noqa: F401
import app.models.camera    # noqa: F401
import app.models.event     # noqa: F401
import app.models.system    # noqa: F401

DATABASE_URL: str = os.environ["DATABASE_URL"]

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
