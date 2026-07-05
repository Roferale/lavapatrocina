"""
Alembic async env.py
--------------------
• Imports all SQLAlchemy models so that Base.metadata is fully populated.
• Reads DATABASE_URL from the environment (falls back to alembic.ini).
• Supports both --sql (offline) and online async migrations.
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# ---------------------------------------------------------------------------
# Alembic Config object (gives access to values in alembic.ini)
# ---------------------------------------------------------------------------
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Import models — MUST happen before we reference Base.metadata
# ---------------------------------------------------------------------------
from app.models.base import Base          # noqa: E402
import app.models.user                    # noqa: E402, F401
import app.models.camera                  # noqa: E402, F401
import app.models.event                   # noqa: E402, F401
import app.models.system                  # noqa: E402, F401

target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Resolve the DSN — environment variable takes precedence over alembic.ini
# ---------------------------------------------------------------------------
def _get_url() -> str:
    url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set and "
            "sqlalchemy.url is empty in alembic.ini"
        )
    return url


# ---------------------------------------------------------------------------
# Offline migrations  (alembic upgrade --sql)
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migrations  (alembic upgrade head)
# ---------------------------------------------------------------------------
def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(
        _get_url(),
        poolclass=pool.NullPool,
    )
    async with engine.connect() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
