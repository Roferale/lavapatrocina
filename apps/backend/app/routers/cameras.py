from __future__ import annotations

import asyncio
import base64
import uuid
from typing import Annotated
from urllib.parse import quote

import cv2
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_admin, require_operator
from app.core.security import decrypt_text, encrypt_text
from app.db.database import get_db
from app.models.camera import Camera, CameraCountingLine
from app.models.user import User
from app.schemas.camera import (
    CameraCreate,
    CameraResponse,
    CameraTestRequest,
    CameraUpdate,
    CountingLineCreate,
    CountingLineResponse,
    RTSPTestResult,
)

router = APIRouter(prefix="/cameras", tags=["Câmeras"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_rtsp_url(rtsp_url: str, username: str | None, password: str | None) -> str:
    """Inject credentials into an RTSP URL if provided."""
    if username and password:
        user_enc = quote(username, safe="")
        pass_enc = quote(password, safe="")
        if rtsp_url.startswith("rtsp://"):
            return f"rtsp://{user_enc}:{pass_enc}@{rtsp_url[7:]}"
    return rtsp_url


def _test_rtsp_sync(url: str) -> tuple[bool, str, bool]:
    """Synchronous RTSP probe — intended to run in a thread pool executor."""
    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        return False, "Não foi possível abrir a URL RTSP.", False
    ret, _ = cap.read()
    cap.release()
    if not ret:
        return True, "Conexão aberta, mas não foi possível ler um quadro.", False
    return True, "Conexão bem-sucedida e quadro lido com êxito.", True


def _capture_frame_sync(url: str) -> bytes | None:
    """Capture a single frame and return it as a JPEG byte string (or None)."""
    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        return None
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return None
    _, buf = cv2.imencode(".jpg", frame)
    return buf.tobytes()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[CameraResponse], summary="Listar câmeras")
async def list_cameras(
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CameraResponse]:
    """Retorna todas as câmeras cadastradas (sem credenciais)."""
    result = await db.execute(select(Camera).order_by(Camera.created_at))
    cameras = result.scalars().all()
    return [CameraResponse.model_validate(c) for c in cameras]


@router.post(
    "/",
    response_model=CameraResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar câmera",
)
async def create_camera(
    payload: CameraCreate,
    _: Annotated[User, Depends(require_operator)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CameraResponse:
    """Cadastra uma nova câmera (credenciais são criptografadas antes de salvar)."""
    camera = Camera(
        id=uuid.uuid4(),
        name=payload.name,
        rtsp_url_encrypted=encrypt_text(payload.rtsp_url),
        username_encrypted=encrypt_text(payload.username) if payload.username else None,
        password_encrypted=encrypt_text(payload.password) if payload.password else None,
        status=payload.status,
        processing_fps=payload.processing_fps,
        processing_width=payload.processing_width,
        processing_height=payload.processing_height,
        min_confidence=payload.min_confidence,
        is_online=False,
    )
    db.add(camera)
    await db.flush()
    await db.refresh(camera)
    return CameraResponse.model_validate(camera)


@router.post(
    "/test-connection",
    response_model=RTSPTestResult,
    summary="Testar conexão RTSP",
)
async def test_connection(
    payload: CameraTestRequest,
    _: Annotated[User, Depends(require_operator)],
) -> RTSPTestResult:
    """Testa uma URL RTSP antes de salvar a câmera."""
    url = _build_rtsp_url(payload.rtsp_url, payload.username, payload.password)
    loop = asyncio.get_event_loop()
    success, message, frame_available = await loop.run_in_executor(
        None, _test_rtsp_sync, url
    )
    return RTSPTestResult(success=success, message=message, frame_available=frame_available)


@router.get("/{camera_id}", response_model=CameraResponse, summary="Obter câmera")
async def get_camera(
    camera_id: str,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CameraResponse:
    """Retorna os dados de uma câmera pelo ID (sem credenciais)."""
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera: Camera | None = result.scalar_one_or_none()
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Câmera não encontrada.")
    return CameraResponse.model_validate(camera)


@router.put("/{camera_id}", response_model=CameraResponse, summary="Atualizar câmera")
async def update_camera(
    camera_id: str,
    payload: CameraUpdate,
    _: Annotated[User, Depends(require_operator)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CameraResponse:
    """Atualiza os dados de uma câmera existente."""
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera: Camera | None = result.scalar_one_or_none()
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Câmera não encontrada.")

    if payload.name is not None:
        camera.name = payload.name
    if payload.rtsp_url is not None:
        camera.rtsp_url_encrypted = encrypt_text(payload.rtsp_url)
    if payload.username is not None:
        camera.username_encrypted = encrypt_text(payload.username)
    if payload.password is not None:
        camera.password_encrypted = encrypt_text(payload.password)
    if payload.status is not None:
        camera.status = payload.status
    if payload.processing_fps is not None:
        camera.processing_fps = payload.processing_fps
    if payload.processing_width is not None:
        camera.processing_width = payload.processing_width
    if payload.processing_height is not None:
        camera.processing_height = payload.processing_height
    if payload.min_confidence is not None:
        camera.min_confidence = payload.min_confidence

    await db.flush()
    await db.refresh(camera)
    return CameraResponse.model_validate(camera)


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remover câmera")
async def delete_camera(
    camera_id: str,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Remove uma câmera e seus dados associados (somente administradores)."""
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera: Camera | None = result.scalar_one_or_none()
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Câmera não encontrada.")
    await db.delete(camera)
    await db.flush()


@router.get("/{camera_id}/frame", summary="Capturar quadro atual da câmera")
async def get_camera_frame(
    camera_id: str,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Captura um quadro atual da câmera e retorna como JPEG em base64."""
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera: Camera | None = result.scalar_one_or_none()
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Câmera não encontrada.")

    try:
        rtsp_url = decrypt_text(camera.rtsp_url_encrypted)
        username = decrypt_text(camera.username_encrypted) if camera.username_encrypted else None
        password = decrypt_text(camera.password_encrypted) if camera.password_encrypted else None
        url = _build_rtsp_url(rtsp_url, username, password)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao descriptografar credenciais da câmera.",
        )

    loop = asyncio.get_event_loop()
    frame_bytes = await loop.run_in_executor(None, _capture_frame_sync, url)

    if frame_bytes is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível capturar quadro da câmera.",
        )

    encoded = base64.b64encode(frame_bytes).decode("utf-8")
    return {"camera_id": camera_id, "frame_base64": encoded, "content_type": "image/jpeg"}


@router.get(
    "/{camera_id}/counting-line",
    response_model=CountingLineResponse | None,
    summary="Obter linha de contagem",
)
async def get_counting_line(
    camera_id: str,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CountingLineResponse | None:
    """Retorna a linha de contagem ativa da câmera (ou null se não configurada)."""
    result = await db.execute(
        select(CameraCountingLine)
        .where(CameraCountingLine.camera_id == camera_id)
        .order_by(CameraCountingLine.created_at.desc())
        .limit(1)
    )
    line: CameraCountingLine | None = result.scalar_one_or_none()
    if line is None:
        return None
    return CountingLineResponse.model_validate(line)


@router.post(
    "/{camera_id}/counting-line",
    response_model=CountingLineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Salvar linha de contagem",
)
async def save_counting_line(
    camera_id: str,
    payload: CountingLineCreate,
    _: Annotated[User, Depends(require_operator)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CountingLineResponse:
    """Salva (ou substitui) a linha de contagem da câmera."""
    cam_result = await db.execute(select(Camera).where(Camera.id == camera_id))
    if cam_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Câmera não encontrada.")

    # Remove existing lines for this camera
    existing = await db.execute(
        select(CameraCountingLine).where(CameraCountingLine.camera_id == camera_id)
    )
    for old_line in existing.scalars().all():
        await db.delete(old_line)

    line = CameraCountingLine(
        id=uuid.uuid4(),
        camera_id=camera_id,
        x1_relative=payload.x1_relative,
        y1_relative=payload.y1_relative,
        x2_relative=payload.x2_relative,
        y2_relative=payload.y2_relative,
        direction=payload.direction,
        active_classes=payload.active_classes,
    )
    db.add(line)
    await db.flush()
    await db.refresh(line)
    return CountingLineResponse.model_validate(line)


@router.get("/{camera_id}/status", summary="Status da câmera")
async def camera_status(
    camera_id: str,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Retorna o status online e o último contato da câmera."""
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera: Camera | None = result.scalar_one_or_none()
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Câmera não encontrada.")
    return {
        "camera_id": camera_id,
        "is_online": camera.is_online,
        "last_seen_at": camera.last_seen_at,
    }
