import uuid
import enum

from sqlalchemy import Column, String, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class Role(str, enum.Enum):
    admin = "admin"
    operator = "operator"
    readonly = "readonly"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(
        Enum(Role, name="userrole"),
        nullable=False,
        default=Role.admin,
        server_default=Role.admin.value,
    )
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")

    # Relationships
    manual_adjustments = relationship(
        "ManualAdjustment", back_populates="user", lazy="select"
    )
    settings_updated = relationship(
        "AppSetting", back_populates="updated_by_user", lazy="select"
    )
