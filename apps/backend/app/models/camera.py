import uuid
import enum

from sqlalchemy import (
    Column,
    String,
    Boolean,
    Integer,
    Float,
    DateTime,
    Enum,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class CameraStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class LineDirection(str, enum.Enum):
    entry = "entry"
    exit = "exit"
    both = "both"


class Camera(Base, TimestampMixin):
    __tablename__ = "cameras"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    name = Column(String, nullable=False)
    rtsp_url_encrypted = Column(String, nullable=False)
    username_encrypted = Column(String, nullable=True)
    password_encrypted = Column(String, nullable=True)
    status = Column(
        Enum(CameraStatus, name="camerastatus"),
        nullable=False,
        default=CameraStatus.active,
        server_default=CameraStatus.active.value,
    )
    processing_fps = Column(Integer, nullable=False, default=5, server_default="5")
    processing_width = Column(Integer, nullable=False, default=640, server_default="640")
    processing_height = Column(Integer, nullable=False, default=480, server_default="480")
    min_confidence = Column(Float, nullable=False, default=0.5, server_default="0.5")
    is_online = Column(Boolean, nullable=False, default=False, server_default="false")
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    counting_lines = relationship(
        "CameraCountingLine", back_populates="camera", lazy="select", cascade="all, delete-orphan"
    )
    vehicle_events = relationship(
        "VehicleEvent", back_populates="camera", lazy="select"
    )


class CameraCountingLine(Base, TimestampMixin):
    __tablename__ = "camera_counting_lines"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    camera_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    x1_relative = Column(Float, nullable=False)
    y1_relative = Column(Float, nullable=False)
    x2_relative = Column(Float, nullable=False)
    y2_relative = Column(Float, nullable=False)
    direction = Column(
        Enum(LineDirection, name="linedirection"),
        nullable=False,
        default=LineDirection.both,
        server_default=LineDirection.both.value,
    )
    active_classes = Column(
        JSONB,
        nullable=False,
        default=lambda: ["car", "truck", "bus", "motorcycle"],
        server_default='["car","truck","bus","motorcycle"]',
    )

    # Relationships
    camera = relationship("Camera", back_populates="counting_lines")
