from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    # Must be exactly 32 ASCII characters for AES-256 via Fernet (base64-padded)
    ENCRYPTION_KEY: str = "12345678901234567890123456789012"
    SNAPSHOTS_DIR: str = "/app/snapshots"
    WORKER_STATUS_FILE: str = "/tmp/worker_status.json"
    LOG_RETENTION_DAYS: int = 30
    SNAPSHOT_RETENTION_DAYS: int = 7

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
