"""
Dashboard — estadísticas agregadas del usuario autenticado.

GET /dashboard/stats → KPIs: total marcas, alertas por nivel, próxima ejecución
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime

from database import get_db
from models import User, Marca, Alerta, NivelAlerta, EjecucionMonitor
from schemas import DashboardStats
from routers.deps import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retorna métricas clave del usuario:
    - Cantidad de marcas (total y activas)
    - Alertas sin resolver, por nivel
    - Timestamp de última y próxima ejecución del monitor
    """
    uid = current_user.id

    # ── Marcas ────────────────────────────────────────────────────────────────
    total_marcas   = db.query(func.count(Marca.id)).filter(Marca.user_id == uid).scalar()
    marcas_activas = db.query(func.count(Marca.id)).filter(
        Marca.user_id == uid, Marca.activa == True
    ).scalar()

    # ── Alertas sin resolver, por nivel ───────────────────────────────────────
    def _count_nivel(nivel: NivelAlerta) -> int:
        return db.query(func.count(Alerta.id)).filter(
            Alerta.user_id == uid,
            Alerta.nivel   == nivel,
            Alerta.resuelta == False,
        ).scalar()

    alertas_criticas = _count_nivel(NivelAlerta.critica)
    alertas_altas    = _count_nivel(NivelAlerta.alta)
    alertas_medias   = _count_nivel(NivelAlerta.media)

    alertas_sin_resolver = (
        db.query(func.count(Alerta.id))
        .filter(Alerta.user_id == uid, Alerta.resuelta == False)
        .scalar()
    )

    # ── Última/próxima ejecución (global, no por usuario) ─────────────────────
    ultima_ejecucion: Optional[datetime] = (
        db.query(EjecucionMonitor.finalizada_el)
        .filter(EjecucionMonitor.estado == "completado")
        .order_by(EjecucionMonitor.finalizada_el.desc())
        .scalar()
    )

    proxima_ejecucion: Optional[datetime] = None  # APScheduler lo proveerá en v2

    return DashboardStats(
        total_marcas          = total_marcas   or 0,
        marcas_activas        = marcas_activas or 0,
        alertas_criticas      = alertas_criticas,
        alertas_altas         = alertas_altas,
        alertas_medias        = alertas_medias,
        alertas_sin_resolver  = alertas_sin_resolver,
        ultima_ejecucion      = ultima_ejecucion,
        proxima_ejecucion     = proxima_ejecucion,
    )
