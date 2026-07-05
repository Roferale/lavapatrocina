from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.models.user import Role


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    role: Role = Role.admin


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    role: Role | None = None
    is_active: bool | None = None
    password: str | None = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    role: Role
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
