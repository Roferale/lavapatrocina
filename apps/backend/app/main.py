from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.init_db import init_db
from app.routers import auth, cameras, dashboard, events, system, users


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Run startup tasks (seed DB) then yield to serve requests."""
    await init_db()
    yield


app = FastAPI(
    title="Lava — Sistema de Contagem de Veículos",
    description="API backend para gestão de câmeras, contagem de veículos e relatórios.",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow all origins for local / intranet use
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(cameras.router, prefix=API_PREFIX)
app.include_router(events.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(system.router, prefix=API_PREFIX)

# ---------------------------------------------------------------------------
# Static files — snapshots
# ---------------------------------------------------------------------------
os.makedirs(settings.SNAPSHOTS_DIR, exist_ok=True)
app.mount(
    "/snapshots",
    StaticFiles(directory=settings.SNAPSHOTS_DIR),
    name="snapshots",
)

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"], summary="Verificação de saúde da API")
async def health_check() -> dict:
    """Retorna o status de operação da API."""
    return {"status": "ok", "service": "lava-backend"}
