"""
Worker configuration loaded from environment variables.

Required env vars
-----------------
DATABASE_URL      Async DSN, e.g. postgresql+asyncpg://user:pass@host:5432/lava
ENCRYPTION_KEY    Exactly 32 ASCII characters used to build the Fernet key

Optional env vars (defaults shown)
-----------------------------------
YOLO_MODEL              yolo11n.pt
SNAPSHOTS_DIR           /app/snapshots
WORKER_STATUS_FILE      /tmp/worker_status.json
RECONNECT_INTERVAL      30   (seconds between RTSP reconnect attempts)
DEFAULT_FPS             5    (fallback processing FPS when camera row has no value)
DEFAULT_MIN_CONFIDENCE  0.5
SAVE_SNAPSHOTS          true
MAX_SNAPSHOT_AGE_DAYS   7
LOG_LEVEL               INFO
"""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()  # load .env file when running locally


def _env_str(key: str, default: str | None = None) -> str:
    val = os.environ.get(key, default)
    if val is None:
        raise RuntimeError(f"Required environment variable {key!r} is not set")
    return val


def _env_int(key: str, default: int) -> int:
    return int(os.environ.get(key, default))


def _env_float(key: str, default: float) -> float:
    return float(os.environ.get(key, default))


def _env_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key, str(default)).strip().lower()
    return raw in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    # ------------------------------------------------------------------ #
    # Required
    # ------------------------------------------------------------------ #
    DATABASE_URL: str = field(
        default_factory=lambda: _env_str("DATABASE_URL")
    )
    ENCRYPTION_KEY: str = field(
        default_factory=lambda: _env_str("ENCRYPTION_KEY")
    )

    # ------------------------------------------------------------------ #
    # Optional
    # ------------------------------------------------------------------ #
    YOLO_MODEL: str = field(
        default_factory=lambda: os.environ.get("YOLO_MODEL", "yolo11n.pt")
    )
    SNAPSHOTS_DIR: str = field(
        default_factory=lambda: os.environ.get("SNAPSHOTS_DIR", "/app/snapshots")
    )
    WORKER_STATUS_FILE: str = field(
        default_factory=lambda: os.environ.get("WORKER_STATUS_FILE", "/tmp/worker_status.json")
    )
    RECONNECT_INTERVAL: int = field(
        default_factory=lambda: _env_int("RECONNECT_INTERVAL", 30)
    )
    DEFAULT_FPS: int = field(
        default_factory=lambda: _env_int("DEFAULT_FPS", 5)
    )
    DEFAULT_MIN_CONFIDENCE: float = field(
        default_factory=lambda: _env_float("DEFAULT_MIN_CONFIDENCE", 0.5)
    )
    SAVE_SNAPSHOTS: bool = field(
        default_factory=lambda: _env_bool("SAVE_SNAPSHOTS", True)
    )
    MAX_SNAPSHOT_AGE_DAYS: int = field(
        default_factory=lambda: _env_int("MAX_SNAPSHOT_AGE_DAYS", 7)
    )
    LOG_LEVEL: str = field(
        default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO").upper()
    )


# Singleton — imported everywhere as `from worker.config import settings`
settings = Settings()
