from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    # Sem default: obrigar definição via .env — um default conhecido permitiria
    # forjar tokens JWT caso o .env falte.
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    # Must be exactly 32 ASCII characters (Fernet). Sem default pelo mesmo motivo.
    ENCRYPTION_KEY: str
    # Origens permitidas para CORS, separadas por vírgula. Vazio = nenhuma
    # origem externa (o frontend é servido same-origin pelo Nginx).
    CORS_ORIGINS: str = ""
    SNAPSHOTS_DIR: str = "/app/snapshots"
    WORKER_STATUS_FILE: str = "/tmp/worker_status.json"
    LOG_RETENTION_DAYS: int = 30
    SNAPSHOT_RETENTION_DAYS: int = 7

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
