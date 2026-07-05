from __future__ import annotations

from pydantic import BaseModel, EmailStr

from app.models.user import Role


class LoginRequest(BaseModel):
    # Usamos str (não EmailStr) porque o login apenas busca o usuário no banco.
    # EmailStr rejeitaria domínios reservados como o padrão admin@lava.local.
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    role: str
    full_name: str | None


class UserInfo(BaseModel):
    id: str
    email: str
    role: str
    full_name: str | None
    is_active: bool
