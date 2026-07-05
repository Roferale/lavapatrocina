from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.camera import CameraStatus, LineDirection


class CameraCreate(BaseModel):
    name: str
    rtsp_url: str
    username: str | None = None
    password: str | None = None
    status: CameraStatus = CameraStatus.active
    processing_fps: int = 5
    processing_width: int = 640
    processing_height: int = 480
    min_confidence: float = 0.5


class CameraUpdate(BaseModel):
    name: str | None = None
    rtsp_url: str | None = None
    username: str | None = None
    password: str | None = None
    status: CameraStatus | None = None
    processing_fps: int | None = None
    processing_width: int | None = None
    processing_height: int | None = None
    min_confidence: float | None = None


class CameraResponse(BaseModel):
    id: UUID
    name: str
    status: CameraStatus
    processing_fps: int
    processing_width: int
    processing_height: int
    min_confidence: float
    is_online: bool
    last_seen_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CountingLineCreate(BaseModel):
    x1_relative: float
    y1_relative: float
    x2_relative: float
    y2_relative: float
    direction: LineDirection = LineDirection.both
    active_classes: list[str] = ["car", "truck", "bus", "motorcycle"]


class CountingLineResponse(BaseModel):
    id: UUID
    camera_id: UUID
    x1_relative: float
    y1_relative: float
    x2_relative: float
    y2_relative: float
    direction: LineDirection
    active_classes: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class CameraTestRequest(BaseModel):
    rtsp_url: str
    username: str | None = None
    password: str | None = None


class RTSPTestResult(BaseModel):
    success: bool
    message: str
    frame_available: bool
