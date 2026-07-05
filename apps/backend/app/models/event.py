import uuid
import enum

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Text,
    DateTime,
    Enum,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class EventDirection(str, enum.Enum):
    entry = "entry"
    exit = "exit"


class EventStatus(str, enum.Enum):
    automatic = "automatic"
    corrected = "corrected"
    removed = "removed"


class VehicleEvent(Base, TimestampMixin):
    __tablename__ = "vehicle_events"

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
    event_time = Column(DateTime(timezone=True), nullable=False, index=True)
    vehicle_type = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    direction = Column(
        Enum(EventDirection, name="eventdirection"),
        nullable=True,
    )
    tracker_id = Column(Integer, nullable=True)
    bbox_x1 = Column(Float, nullable=True)
    bbox_y1 = Column(Float, nullable=True)
    bbox_x2 = Column(Float, nullable=True)
    bbox_y2 = Column(Float, nullable=True)
    snapshot_path = Column(String, nullable=True)
    status = Column(
        Enum(EventStatus, name="eventstatus"),
        nullable=False,
        default=EventStatus.automatic,
        server_default=EventStatus.automatic.value,
    )
    observation = Column(Text, nullable=True)

    # Relationships
    camera = relationship("Camera", back_populates="vehicle_events")
    manual_adjustments = relationship(
        "ManualAdjustment", back_populates="event", lazy="select"
    )

    __table_args__ = (
        Index("ix_vehicle_events_camera_event_time", "camera_id", "event_time"),
    )


class ManualAdjustment(Base):
    __tablename__ = "manual_adjustments"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    action = Column(String, nullable=False)  # added / removed / corrected
    previous_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        # populated via server_default in migration; set explicitly in app
        server_default="now()",
    )

    # Relationships
    event = relationship("VehicleEvent", back_populates="manual_adjustments")
    user = relationship("User", back_populates="manual_adjustments")
