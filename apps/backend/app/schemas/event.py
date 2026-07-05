from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.models.event import EventDirection, EventStatus


class VehicleEventResponse(BaseModel):
    id: UUID
    camera_id: UUID
    event_time: datetime
    vehicle_type: str | None
    confidence: float | None
    direction: EventDirection | None
    tracker_id: int | None
    bbox_x1: float | None
    bbox_y1: float | None
    bbox_x2: float | None
    bbox_y2: float | None
    snapshot_path: str | None
    status: EventStatus
    observation: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class VehicleEventCreate(BaseModel):
    camera_id: UUID
    event_time: datetime | None = None
    vehicle_type: str
    confidence: float = 1.0
    direction: EventDirection
    observation: str | None = None


class VehicleEventUpdate(BaseModel):
    status: EventStatus | None = None
    observation: str | None = None
    vehicle_type: str | None = None
    direction: EventDirection | None = None


class ManualAdjustmentResponse(BaseModel):
    id: UUID
    event_id: UUID | None
    user_id: UUID
    action: str
    previous_value: Any | None
    new_value: Any | None
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EventFilter(BaseModel):
    camera_id: UUID | None = None
    vehicle_type: str | None = None
    direction: EventDirection | None = None
    status: EventStatus | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    page: int = 1
    page_size: int = 50


class PaginatedEvents(BaseModel):
    """Formato paginado esperado pelo frontend (PaginatedResponse)."""
    items: list[VehicleEventResponse]
    total: int
    page: int
    page_size: int


class DashboardMetrics(BaseModel):
    today_count: int
    week_count: int
    month_count: int
    hourly_counts: list[dict]
    daily_counts: list[dict]
    recent_events: list[VehicleEventResponse]
    camera_online: bool
    worker_running: bool
