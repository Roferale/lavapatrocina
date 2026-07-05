from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class SystemLogResponse(BaseModel):
    id: UUID
    level: str
    source: str
    message: str
    details: Any | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedLogs(BaseModel):
    """Formato paginado esperado pelo frontend (PaginatedResponse)."""
    items: list[SystemLogResponse]
    total: int
    page: int
    page_size: int


class AppSettingResponse(BaseModel):
    id: UUID
    key: str
    value: Any
    description: str | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class AppSettingUpdate(BaseModel):
    value: Any
    description: str | None = None
