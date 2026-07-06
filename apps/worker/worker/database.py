"""
Async database layer for the worker process.

Deliberately standalone — does not import from apps/backend so the
worker container only needs its own requirements.txt.

Table / column names must stay in sync with the Alembic migration at
apps/backend/alembic/versions/001_initial.py.
"""

from __future__ import annotations

import base64
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from worker.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Engine & session factory
# ---------------------------------------------------------------------------

_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

_AsyncSessionLocal = async_sessionmaker(
    bind=_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager that yields a committed/rolled-back session."""
    async with _AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Fernet encryption helper
# ---------------------------------------------------------------------------

def _build_fernet() -> Fernet:
    """
    Build a Fernet cipher from ENCRYPTION_KEY.

    ENCRYPTION_KEY must be exactly 32 ASCII characters.  We base64url-encode
    those 32 bytes to get the 44-character key Fernet expects.
    """
    raw = settings.ENCRYPTION_KEY.encode("ascii")
    if len(raw) != 32:
        raise ValueError(
            f"ENCRYPTION_KEY must be exactly 32 ASCII chars, got {len(raw)}"
        )
    key = base64.urlsafe_b64encode(raw)  # 32 bytes → 44-char base64url token
    return Fernet(key)


_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = _build_fernet()
    return _fernet


def _decrypt(ciphertext: str | None) -> str | None:
    """Decrypt a Fernet-encrypted string.  Returns None for NULL/empty values."""
    if not ciphertext:
        return None
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        logger.error("Failed to decrypt value — wrong ENCRYPTION_KEY?")
        return None


# ---------------------------------------------------------------------------
# Public DB helpers
# ---------------------------------------------------------------------------

async def get_active_cameras() -> list[dict]:
    """
    Return all cameras with status='active', decrypting rtsp_url in the process.

    Each dict contains all columns from the `cameras` table plus a plain-text
    ``rtsp_url`` key (the decrypted form of ``rtsp_url_encrypted``).
    """
    sql = text(
        """
        SELECT
            id,
            name,
            rtsp_url_encrypted,
            username_encrypted,
            password_encrypted,
            status,
            processing_fps,
            processing_width,
            processing_height,
            min_confidence,
            is_online,
            last_seen_at
        FROM cameras
        WHERE status = 'active'
        """
    )
    async with get_session() as session:
        result = await session.execute(sql)
        rows = result.mappings().all()

    cameras: list[dict] = []
    for row in rows:
        cam = dict(row)
        # UUIDs come back as uuid.UUID objects; normalise to str for easy use.
        cam["id"] = str(cam["id"])
        decrypted = _decrypt(cam["rtsp_url_encrypted"])
        if not decrypted:
            logger.warning(
                "Camera %s (%s): rtsp_url_encrypted could not be decrypted — skipping",
                cam["id"],
                cam["name"],
            )
            continue
        cam["rtsp_url"] = decrypted
        cameras.append(cam)

    return cameras


async def get_counting_line(camera_id: str) -> dict | None:
    """
    Return the first counting-line row for this camera as a plain dict, or
    None if none has been configured.

    Coordinates are stored as relative (0.0–1.0) fractions of frame size.
    The caller (CameraProcessor) converts them to absolute pixel positions.
    """
    sql = text(
        """
        SELECT
            id,
            camera_id,
            x1_relative,
            y1_relative,
            x2_relative,
            y2_relative,
            direction,
            active_classes
        FROM camera_counting_lines
        WHERE camera_id = :camera_id
        ORDER BY created_at ASC
        LIMIT 1
        """
    )
    async with get_session() as session:
        result = await session.execute(sql, {"camera_id": camera_id})
        row = result.mappings().first()

    if row is None:
        return None

    d = dict(row)
    d["id"] = str(d["id"])
    d["camera_id"] = str(d["camera_id"])
    # active_classes comes back as a Python list from asyncpg's JSONB handling
    if d["active_classes"] is None:
        d["active_classes"] = ["car", "truck", "bus", "motorcycle"]
    return d


async def save_vehicle_event(event_data: dict) -> None:
    """
    Insert a new row into vehicle_events.

    Expected keys in event_data
    ---------------------------
    camera_id        str (UUID)
    event_time       datetime (timezone-aware)
    vehicle_type     str | None
    confidence       float | None
    direction        "entry" | "exit" | None
    tracker_id       int | None
    bbox_x1          float | None
    bbox_y1          float | None
    bbox_x2          float | None
    bbox_y2          float | None
    snapshot_path    str | None
    """
    sql = text(
        """
        INSERT INTO vehicle_events (
            id, camera_id, event_time, vehicle_type, confidence,
            direction, tracker_id,
            bbox_x1, bbox_y1, bbox_x2, bbox_y2,
            snapshot_path, status,
            created_at, updated_at
        ) VALUES (
            :id, :camera_id, :event_time, :vehicle_type, :confidence,
            CAST(:direction AS eventdirection), :tracker_id,
            :bbox_x1, :bbox_y1, :bbox_x2, :bbox_y2,
            :snapshot_path, 'automatic',
            now(), now()
        )
        """
    )
    params = {
        "id": str(uuid.uuid4()),
        "camera_id": event_data["camera_id"],
        "event_time": event_data.get("event_time", datetime.now(tz=timezone.utc)),
        "vehicle_type": event_data.get("vehicle_type"),
        "confidence": event_data.get("confidence"),
        "direction": event_data.get("direction"),
        "tracker_id": event_data.get("tracker_id"),
        "bbox_x1": event_data.get("bbox_x1"),
        "bbox_y1": event_data.get("bbox_y1"),
        "bbox_x2": event_data.get("bbox_x2"),
        "bbox_y2": event_data.get("bbox_y2"),
        "snapshot_path": event_data.get("snapshot_path"),
    }
    async with get_session() as session:
        await session.execute(sql, params)


async def update_camera_status(camera_id: str, is_online: bool) -> None:
    """Flip is_online and bump last_seen_at on the cameras row."""
    sql = text(
        """
        UPDATE cameras
        SET
            is_online    = :is_online,
            last_seen_at = CASE WHEN :is_online THEN now() ELSE last_seen_at END,
            updated_at   = now()
        WHERE id = :camera_id
        """
    )
    async with get_session() as session:
        await session.execute(sql, {"is_online": is_online, "camera_id": camera_id})


async def save_system_log(
    level: str,
    source: str,
    message: str,
    details: dict | None = None,
) -> None:
    """
    Append a row to system_logs.  Silently swallows its own errors to avoid
    infinite error loops.
    """
    sql = text(
        """
        INSERT INTO system_logs (id, level, source, message, details, created_at)
        VALUES (:id, :level, :source, :message, CAST(:details AS jsonb), now())
        """
    )
    import json

    params = {
        "id": str(uuid.uuid4()),
        "level": level.upper(),
        "source": source,
        "message": message,
        "details": json.dumps(details) if details is not None else None,
    }
    try:
        async with get_session() as session:
            await session.execute(sql, params)
    except Exception as exc:  # noqa: BLE001
        logger.error("save_system_log failed: %s", exc)


async def get_setting(key: str, default: Any = None) -> Any:
    """
    Fetch a value from app_settings by key.  Returns ``default`` when the key
    does not exist.  The stored JSONB value is returned as-is (Python type).
    """
    sql = text(
        "SELECT value FROM app_settings WHERE key = :key LIMIT 1"
    )
    async with get_session() as session:
        result = await session.execute(sql, {"key": key})
        row = result.first()
    if row is None:
        return default
    return row[0]
