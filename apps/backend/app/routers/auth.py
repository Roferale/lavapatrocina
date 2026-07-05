from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserInfo

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", response_model=TokenResponse, summary="Realizar login")
async def login(
    payload: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Autentica o usuário com e-mail e senha e retorna um token JWT."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user: User | None = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo. Entre em contato com o administrador.",
        )

    token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
        full_name=user.full_name,
    )


@router.post("/logout", summary="Realizar logout")
async def logout() -> dict:
    """
    Logout é stateless com JWT.
    O cliente deve descartar o token localmente.
    """
    return {"message": "Logout realizado com sucesso."}


@router.get("/me", response_model=UserInfo, summary="Dados do usuário atual")
async def me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserInfo:
    """Retorna as informações do usuário autenticado."""
    return UserInfo(
        id=str(current_user.id),
        email=current_user.email,
        role=current_user.role.value,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
    )
