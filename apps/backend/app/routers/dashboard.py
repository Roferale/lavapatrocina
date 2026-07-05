from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.camera import Camera
from app.models.event import EventStatus, VehicleEvent
from app.models.user import User
from app.schemas.event import DashboardMetrics, VehicleEventResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/metrics", response_model=DashboardMetrics, summary="Métricas do dashboard")
async def get_metrics(
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardMetrics:
    """Retorna as métricas consolidadas para o dashboard principal."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)

    active_statuses = [EventStatus.automatic, EventStatus.corrected]

    # ---- Scalar counts ----
    def _count_query(since: datetime):
        return (
            select(func.count())
            .select_from(VehicleEvent)
            .where(
                VehicleEvent.event_time >= since,
                VehicleEvent.status.in_(active_statuses),
            )
        )

    today_count = (await db.execute(_count_query(today_start))).scalar_one()
    week_count = (await db.execute(_count_query(week_start))).scalar_one()
    month_count = (await db.execute(_count_query(month_start))).scalar_one()

    # ---- Hourly counts for today (hours 0–23) ----
    hourly_result = await db.execute(
        select(
            func.extract("hour", VehicleEvent.event_time).label("hour"),
            func.count().label("count"),
        )
        .where(
            VehicleEvent.event_time >= today_start,
            VehicleEvent.status.in_(active_statuses),
        )
        .group_by(func.extract("hour", VehicleEvent.event_time))
        .order_by(func.extract("hour", VehicleEvent.event_time))
    )
    hourly_map: dict[int, int] = {int(row.hour): row.count for row in hourly_result}
    hourly_counts = [{"hour": h, "count": hourly_map.get(h, 0)} for h in range(24)]

    # ---- Daily counts for the last 7 days ----
    seven_days_ago = today_start - timedelta(days=6)
    # 'day' como literal (text) para não virar parâmetro — assim o SELECT e o
    # GROUP BY geram a mesma expressão e o PostgreSQL aceita o agrupamento.
    day_expr = func.date_trunc(text("'day'"), VehicleEvent.event_time)
    daily_result = await db.execute(
        select(
            day_expr.label("day"),
            func.count().label("count"),
        )
        .where(
            VehicleEvent.event_time >= seven_days_ago,
            VehicleEvent.status.in_(active_statuses),
        )
        .group_by(day_expr)
        .order_by(day_expr)
    )
    daily_map: dict[str, int] = {}
    for row in daily_result:
        day_key = row.day.strftime("%Y-%m-%d") if hasattr(row.day, "strftime") else str(row.day)[:10]
        daily_map[day_key] = row.count
    daily_counts = []
    for i in range(7):
        day = (seven_days_ago + timedelta(days=i)).strftime("%Y-%m-%d")
        daily_counts.append({"date": day, "count": daily_map.get(day, 0)})

    # ---- Recent events ----
    recent_result = await db.execute(
        select(VehicleEvent)
        .where(VehicleEvent.status.in_(active_statuses))
        .order_by(VehicleEvent.event_time.desc())
        .limit(10)
    )
    recent_events = [
        VehicleEventResponse.model_validate(e) for e in recent_result.scalars().all()
    ]

    # ---- Camera online status ----
    online_result = await db.execute(
        select(func.count()).select_from(Camera).where(Camera.is_online.is_(True))
    )
    camera_online = (online_result.scalar_one() or 0) > 0

    # ---- Worker running status ----
    worker_running = False
    try:
        if os.path.isfile(settings.WORKER_STATUS_FILE):
            with open(settings.WORKER_STATUS_FILE, "r") as fh:
                data = json.load(fh)
                # Worker writes {"status": "running"} or {"status": "stopped"}
                worker_running = data.get("status") == "running"
    except Exception:
        worker_running = False

    return DashboardMetrics(
        today_count=today_count,
        week_count=week_count,
        month_count=month_count,
        hourly_counts=hourly_counts,
        daily_counts=daily_counts,
        recent_events=recent_events,
        camera_online=camera_online,
        worker_running=worker_running,
    )
