"""
Seed script — run once at startup or manually.

Creates the default admin user and default application settings when
the database is empty.

Usage (from apps/backend/):
    python -m app.db.init_db
"""

import asyncio
import uuid
import os

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal, engine
from app.models.base import Base
from app.models.user import User, Role
from app.models.system import AppSetting

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@lava.local")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

DEFAULT_SETTINGS: list[dict] = [
    {
        "key": "system.timezone",
        "value": "America/Sao_Paulo",
        "description": "Timezone used for event timestamps and reports",
    },
    {
        "key": "counting.default_fps",
        "value": 5,
        "description": "Default frames-per-second for new cameras",
    },
    {
        "key": "counting.default_min_confidence",
        "value": 0.5,
        "description": "Minimum YOLO confidence to register a vehicle event",
    },
    {
        "key": "retention.vehicle_events_days",
        "value": 365,
        "description": "How many days to keep vehicle_events rows",
    },
    {
        "key": "retention.system_logs_days",
        "value": 90,
        "description": "How many days to keep system_logs rows",
    },
    {
        "key": "snapshot.enabled",
        "value": True,
        "description": "Whether to save vehicle snapshot images on events",
    },
    {
        "key": "snapshot.storage_path",
        "value": "/data/snapshots",
        "description": "Filesystem path for snapshot storage",
    },
]


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------

async def _seed_admin(session: AsyncSession) -> None:
    result = await session.execute(select(User).limit(1))
    existing = result.scalar_one_or_none()
    if existing is not None:
        print("[init_db] Admin user already exists — skipping.")
        return

    admin = User(
        id=uuid.uuid4(),
        email=ADMIN_EMAIL,
        hashed_password=_hash_password(ADMIN_PASSWORD),
        full_name="System Administrator",
        role=Role.admin,
        is_active=True,
    )
    session.add(admin)
    print(f"[init_db] Created admin user: {ADMIN_EMAIL}")


async def _seed_settings(session: AsyncSession) -> None:
    for cfg in DEFAULT_SETTINGS:
        result = await session.execute(
            select(AppSetting).where(AppSetting.key == cfg["key"])
        )
        if result.scalar_one_or_none() is not None:
            continue

        setting = AppSetting(
            id=uuid.uuid4(),
            key=cfg["key"],
            value=cfg["value"],
            description=cfg.get("description"),
        )
        session.add(setting)
        print(f"[init_db] Seeded setting: {cfg['key']}")


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

async def init_db() -> None:
    # Ensure tables exist (idempotent; Alembic should manage this in prod)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            await _seed_admin(session)
            await _seed_settings(session)

    print("[init_db] Done.")


if __name__ == "__main__":
    asyncio.run(init_db())
