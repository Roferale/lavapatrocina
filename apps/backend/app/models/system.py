import uuid

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base


class SystemLog(Base):
    """Append-only log table — no updated_at."""

    __tablename__ = "system_logs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    level = Column(String, nullable=False)   # DEBUG / INFO / WARNING / ERROR / CRITICAL
    source = Column(String, nullable=False)  # module / service name
    message = Column(Text, nullable=False)
    details = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )


class AppSetting(Base):
    """Key-value application settings with audit trail."""

    __tablename__ = "app_settings"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(JSONB, nullable=False)
    description = Column(String, nullable=True)
    updated_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )

    # Relationships
    updated_by_user = relationship("User", back_populates="settings_updated")
