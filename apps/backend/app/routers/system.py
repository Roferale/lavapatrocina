from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user, require_admin, require_operator
from app.db.database import get_db
from app.models.system import AppSetting, SystemLog
from app.models.user import User
from app.schemas.system import (
    AppSettingResponse,
    AppSettingUpdate,
    PaginatedLogs,
    SystemLogResponse,
)

router = APIRouter(prefix="/system", tags=["Sistema"])


# ---------------------------------------------------------------------------
# System Logs
# ---------------------------------------------------------------------------

@router.get("/logs", response_model=PaginatedLogs, summary="Listar logs do sistema")
async def list_logs(
    level: str | None = Query(default=None, description="Filtrar por nível (DEBUG, INFO, WARNING, ERROR, CRITICAL)"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000),
    _: Annotated[User, Depends(require_admin)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> PaginatedLogs:
    """Retorna os logs do sistema no formato paginado {items, total} (somente admins)."""
    total_query = select(func.count()).select_from(SystemLog)
    if level is not None:
        total_query = total_query.where(SystemLog.level == level.upper())
    total = (await db.execute(total_query)).scalar_one()

    query = select(SystemLog).order_by(SystemLog.created_at.desc())
    if level is not None:
        query = query.where(SystemLog.level == level.upper())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()
    return PaginatedLogs(
        items=[SystemLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# App Settings
# ---------------------------------------------------------------------------

@router.get(
    "/settings",
    response_model=list[AppSettingResponse],
    summary="Listar configurações",
)
async def list_settings(
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AppSettingResponse]:
    """Retorna todas as configurações da aplicação."""
    result = await db.execute(select(AppSetting).order_by(AppSetting.key))
    settings_list = result.scalars().all()
    return [AppSettingResponse.model_validate(s) for s in settings_list]


@router.put(
    "/settings/{key}",
    response_model=AppSettingResponse,
    summary="Atualizar configuração",
)
async def update_setting(
    key: str,
    payload: AppSettingUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AppSettingResponse:
    """Atualiza o valor de uma configuração pelo chave (somente administradores)."""
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    setting: AppSetting | None = result.scalar_one_or_none()

    if setting is None:
        # Auto-create if it doesn't exist
        setting = AppSetting(
            id=uuid.uuid4(),
            key=key,
            value=payload.value,
            description=payload.description,
            updated_by=current_user.id,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(setting)
    else:
        setting.value = payload.value
        setting.updated_by = current_user.id
        setting.updated_at = datetime.now(timezone.utc)
        if payload.description is not None:
            setting.description = payload.description

    await db.flush()
    await db.refresh(setting)
    return AppSettingResponse.model_validate(setting)


# ---------------------------------------------------------------------------
# Worker Status
# ---------------------------------------------------------------------------

@router.get("/worker-status", summary="Status do worker de detecção")
async def get_worker_status(
    _: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """Lê o status atual do processo worker a partir do arquivo de status."""
    if not os.path.isfile(settings.WORKER_STATUS_FILE):
        return {"running": False, "message": "Arquivo de status não encontrado."}
    try:
        with open(settings.WORKER_STATUS_FILE, "r") as fh:
            data = json.load(fh)
        return data
    except (json.JSONDecodeError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao ler arquivo de status do worker: {exc}",
        )


@router.post("/worker-status", summary="Atualizar status do worker")
async def set_worker_status(
    payload: dict[str, Any],
    _: Annotated[User, Depends(require_operator)],
) -> dict[str, Any]:
    """
    Atualiza o arquivo de status do worker.
    Usado pelo processo worker para reportar seu estado ao backend.
    """
    try:
        os.makedirs(os.path.dirname(settings.WORKER_STATUS_FILE) or ".", exist_ok=True)
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        with open(settings.WORKER_STATUS_FILE, "w") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        return {"message": "Status do worker atualizado.", "data": payload}
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao gravar arquivo de status do worker: {exc}",
        )
