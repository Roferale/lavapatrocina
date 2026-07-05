from __future__ import annotations

import csv
import io
import os
import uuid
from datetime import datetime, timezone
from typing import Annotated

import openpyxl
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user, require_operator
from app.db.database import get_db
from app.models.event import EventDirection, EventStatus, ManualAdjustment, VehicleEvent
from app.models.user import User
from app.schemas.event import (
    EventFilter,
    ManualAdjustmentResponse,
    VehicleEventCreate,
    VehicleEventResponse,
    VehicleEventUpdate,
)

router = APIRouter(prefix="/events", tags=["Eventos"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _apply_filters(query, f: EventFilter):
    """Apply EventFilter predicates to a SQLAlchemy select() statement."""
    if f.camera_id is not None:
        query = query.where(VehicleEvent.camera_id == str(f.camera_id))
    if f.vehicle_type is not None:
        query = query.where(VehicleEvent.vehicle_type == f.vehicle_type)
    if f.direction is not None:
        query = query.where(VehicleEvent.direction == f.direction)
    if f.status is not None:
        query = query.where(VehicleEvent.status == f.status)
    if f.date_from is not None:
        query = query.where(VehicleEvent.event_time >= f.date_from)
    if f.date_to is not None:
        query = query.where(VehicleEvent.event_time <= f.date_to)
    return query


def _event_to_row(e: VehicleEvent) -> list:
    """Convert a VehicleEvent ORM instance to a flat list for CSV/Excel export."""
    return [
        str(e.id),
        str(e.camera_id),
        e.event_time.isoformat() if e.event_time else "",
        e.vehicle_type or "",
        e.confidence or "",
        e.direction.value if e.direction else "",
        e.tracker_id or "",
        e.bbox_x1 or "",
        e.bbox_y1 or "",
        e.bbox_x2 or "",
        e.bbox_y2 or "",
        e.status.value if e.status else "",
        e.observation or "",
        e.created_at.isoformat() if e.created_at else "",
    ]


_EXPORT_HEADERS = [
    "ID", "Câmera ID", "Data/Hora", "Tipo de Veículo", "Confiança",
    "Direção", "Tracker ID", "BBox X1", "BBox Y1", "BBox X2", "BBox Y2",
    "Status", "Observação", "Criado em",
]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[VehicleEventResponse], summary="Listar eventos")
async def list_events(
    camera_id: str | None = Query(default=None),
    vehicle_type: str | None = Query(default=None),
    direction: EventDirection | None = Query(default=None),
    event_status: EventStatus | None = Query(default=None, alias="status"),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> list[VehicleEventResponse]:
    """Retorna eventos com filtros opcionais, paginado."""
    f = EventFilter(
        camera_id=camera_id,
        vehicle_type=vehicle_type,
        direction=direction,
        status=event_status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    query = select(VehicleEvent).order_by(VehicleEvent.event_time.desc())
    query = _apply_filters(query, f)
    query = query.offset((f.page - 1) * f.page_size).limit(f.page_size)
    result = await db.execute(query)
    events = result.scalars().all()
    return [VehicleEventResponse.model_validate(e) for e in events]


@router.get("/{event_id}/snapshot", summary="Imagem do evento (autenticado)")
async def get_event_snapshot(
    event_id: str,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileResponse:
    """Serve a imagem do evento apenas para usuários autenticados."""
    result = await db.execute(select(VehicleEvent).where(VehicleEvent.id == event_id))
    event: VehicleEvent | None = result.scalar_one_or_none()
    if event is None or not event.snapshot_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot não encontrado.")

    # Resolve o caminho e garante que fica dentro de SNAPSHOTS_DIR (anti path-traversal)
    base = os.path.realpath(settings.SNAPSHOTS_DIR)
    raw = event.snapshot_path
    candidate = raw if os.path.isabs(raw) else os.path.join(base, raw)
    resolved = os.path.realpath(candidate)
    if not resolved.startswith(base + os.sep) or not os.path.isfile(resolved):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot não encontrado.")

    return FileResponse(resolved, media_type="image/jpeg")


@router.post(
    "/",
    response_model=VehicleEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar evento manual",
)
async def create_event(
    payload: VehicleEventCreate,
    current_user: Annotated[User, Depends(require_operator)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VehicleEventResponse:
    """Cria um evento de veículo manualmente (operador ou admin)."""
    event = VehicleEvent(
        id=uuid.uuid4(),
        camera_id=str(payload.camera_id),
        event_time=payload.event_time or datetime.now(timezone.utc),
        vehicle_type=payload.vehicle_type,
        confidence=payload.confidence,
        direction=payload.direction,
        status=EventStatus.automatic,
        observation=payload.observation,
    )
    db.add(event)

    adjustment = ManualAdjustment(
        id=uuid.uuid4(),
        event_id=event.id,
        user_id=current_user.id,
        action="added",
        previous_value=None,
        new_value={
            "vehicle_type": payload.vehicle_type,
            "direction": payload.direction.value,
        },
        reason="Evento criado manualmente via API.",
        created_at=datetime.now(timezone.utc),
    )
    db.add(adjustment)
    await db.flush()
    await db.refresh(event)
    return VehicleEventResponse.model_validate(event)


@router.get("/{event_id}", response_model=VehicleEventResponse, summary="Obter evento")
async def get_event(
    event_id: str,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VehicleEventResponse:
    """Retorna os detalhes de um evento pelo ID."""
    result = await db.execute(select(VehicleEvent).where(VehicleEvent.id == event_id))
    event: VehicleEvent | None = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado.")
    return VehicleEventResponse.model_validate(event)


@router.put("/{event_id}", response_model=VehicleEventResponse, summary="Atualizar evento")
async def update_event(
    event_id: str,
    payload: VehicleEventUpdate,
    current_user: Annotated[User, Depends(require_operator)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VehicleEventResponse:
    """Atualiza um evento e registra a alteração no log de auditoria."""
    result = await db.execute(select(VehicleEvent).where(VehicleEvent.id == event_id))
    event: VehicleEvent | None = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado.")

    previous = {
        "status": event.status.value if event.status else None,
        "observation": event.observation,
        "vehicle_type": event.vehicle_type,
        "direction": event.direction.value if event.direction else None,
    }

    if payload.status is not None:
        event.status = payload.status
    if payload.observation is not None:
        event.observation = payload.observation
    if payload.vehicle_type is not None:
        event.vehicle_type = payload.vehicle_type
    if payload.direction is not None:
        event.direction = payload.direction

    new_val = {
        "status": event.status.value if event.status else None,
        "observation": event.observation,
        "vehicle_type": event.vehicle_type,
        "direction": event.direction.value if event.direction else None,
    }

    adjustment = ManualAdjustment(
        id=uuid.uuid4(),
        event_id=event.id,
        user_id=current_user.id,
        action="corrected",
        previous_value=previous,
        new_value=new_val,
        reason="Evento corrigido manualmente via API.",
        created_at=datetime.now(timezone.utc),
    )
    db.add(adjustment)
    await db.flush()
    await db.refresh(event)
    return VehicleEventResponse.model_validate(event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remover evento")
async def delete_event(
    event_id: str,
    current_user: Annotated[User, Depends(require_operator)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Marca um evento como removido (soft delete) e registra auditoria."""
    result = await db.execute(select(VehicleEvent).where(VehicleEvent.id == event_id))
    event: VehicleEvent | None = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado.")

    previous = {
        "status": event.status.value if event.status else None,
    }
    event.status = EventStatus.removed

    adjustment = ManualAdjustment(
        id=uuid.uuid4(),
        event_id=event.id,
        user_id=current_user.id,
        action="removed",
        previous_value=previous,
        new_value={"status": EventStatus.removed.value},
        reason="Evento removido manualmente via API.",
        created_at=datetime.now(timezone.utc),
    )
    db.add(adjustment)
    await db.flush()


@router.get("/{event_id}/snapshot", summary="Servir snapshot do evento")
async def get_snapshot(
    event_id: str,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    """Retorna a imagem snapshot do evento como arquivo JPEG."""
    import os
    import aiofiles

    result = await db.execute(select(VehicleEvent).where(VehicleEvent.id == event_id))
    event: VehicleEvent | None = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado.")
    if not event.snapshot_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Snapshot não disponível para este evento.",
        )
    if not os.path.isfile(event.snapshot_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo de snapshot não encontrado no servidor.",
        )

    async def _iter():
        async with aiofiles.open(event.snapshot_path, "rb") as f:
            while chunk := await f.read(65536):
                yield chunk

    return StreamingResponse(
        _iter(),
        media_type="image/jpeg",
        headers={"Content-Disposition": f"inline; filename={event_id}.jpg"},
    )


# ---------------------------------------------------------------------------
# Export helpers (run in thread executor because openpyxl is synchronous)
# ---------------------------------------------------------------------------

async def _fetch_events_for_export(
    f: EventFilter, db: AsyncSession
) -> list[VehicleEvent]:
    query = select(VehicleEvent).order_by(VehicleEvent.event_time.desc())
    query = _apply_filters(query, f)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/export/csv", summary="Exportar eventos em CSV")
async def export_csv(
    f: EventFilter,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    """Exporta os eventos filtrados como arquivo CSV."""
    events = await _fetch_events_for_export(f, db)

    def _generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(_EXPORT_HEADERS)
        for e in events:
            writer.writerow(_event_to_row(e))
        return buf.getvalue()

    import asyncio as _asyncio
    csv_content = await _asyncio.get_event_loop().run_in_executor(None, _generate)

    return StreamingResponse(
        iter([csv_content.encode("utf-8-sig")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=eventos.csv"},
    )


@router.post("/export/excel", summary="Exportar eventos em Excel")
async def export_excel(
    f: EventFilter,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    """Exporta os eventos filtrados como arquivo Excel (.xlsx)."""
    events = await _fetch_events_for_export(f, db)

    def _build_xlsx() -> bytes:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Eventos"
        ws.append(_EXPORT_HEADERS)
        for e in events:
            ws.append(_event_to_row(e))
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    import asyncio as _asyncio
    xlsx_bytes = await _asyncio.get_event_loop().run_in_executor(None, _build_xlsx)

    return StreamingResponse(
        iter([xlsx_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=eventos.xlsx"},
    )
