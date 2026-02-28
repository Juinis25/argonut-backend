"""
Monitor — ejecuta el motor de vigilancia INPI bajo demanda.

POST /monitor/run      → Dispara una ejecución (demo o real)
GET  /monitor/runs     → Historial de ejecuciones
GET  /monitor/runs/{id} → Detalle de una ejecución
"""

import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from database import get_db
from models import User, EjecucionMonitor, Marca
from schemas import MonitorRunRequest, MonitorRunOut
from routers.deps import get_current_user

router = APIRouter(prefix="/monitor", tags=["monitor"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_run_or_404(run_id: int, db: Session) -> EjecucionMonitor:
    run = db.query(EjecucionMonitor).filter(EjecucionMonitor.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Ejecución no encontrada")
    return run


# ── Background task ──────────────────────────────────────────────────────────

def _ejecutar_monitor_bg(run_id: int, user_id: int, modo: str, notificar: bool):
    """
    Tarea en background: importa y corre el servicio INPI para el usuario.
    Actualiza EjecucionMonitor con resultados o error.
    """
    # Importamos aquí para evitar circular imports y cargar Playwright solo cuando
    # sea necesario (no en cada startup de la API).
    from database import SessionLocal
    from services.inpi_service import ejecutar_para_usuario

    db = SessionLocal()
    try:
        run = db.query(EjecucionMonitor).filter(EjecucionMonitor.id == run_id).first()
        if not run:
            return

        result = ejecutar_para_usuario(
            user_id   = user_id,
            modo      = modo,
            notificar = notificar,
            db        = db,
        )

        run.estado           = "completado"
        run.marcas_vigiladas = result.get("marcas_vigiladas", 0)
        run.alertas_nuevas   = result.get("alertas_nuevas", 0)
        run.expedientes_proc = result.get("expedientes_proc", 0)
        run.log_output       = result.get("log", "")
        run.finalizada_el    = datetime.utcnow()

    except Exception as exc:
        run = db.query(EjecucionMonitor).filter(EjecucionMonitor.id == run_id).first()
        if run:
            run.estado        = "error"
            run.error_msg     = str(exc)[:2000]
            run.finalizada_el = datetime.utcnow()
    finally:
        db.commit()
        db.close()


# ── POST /monitor/run ─────────────────────────────────────────────────────────

@router.post("/run", response_model=MonitorRunOut, status_code=202)
def run_monitor(
    payload:          MonitorRunRequest,
    background_tasks: BackgroundTasks,
    current_user:     User    = Depends(get_current_user),
    db:               Session = Depends(get_db),
):
    """
    Dispara el motor de vigilancia INPI en background.
    Devuelve 202 inmediatamente con el ID de la ejecución para polling.

    - modo='demo'  → usa datos cacheados/simulados (no scraping real)
    - modo='real'  → scraping en vivo del INPI
    """
    # Bloquear si ya hay una ejecución corriendo para este usuario
    corriendo = db.query(EjecucionMonitor).filter(
        EjecucionMonitor.user_id == current_user.id,
        EjecucionMonitor.estado  == "corriendo",
    ).first()
    if corriendo:
        raise HTTPException(
            status_code=409,
            detail=f"Ya hay una ejecución en curso (id={corriendo.id}). Esperá a que termine."
        )

    # Contar marcas activas del usuario
    marcas_count = db.query(Marca).filter(
        Marca.user_id == current_user.id,
        Marca.activa  == True,
    ).count()

    if marcas_count == 0:
        raise HTTPException(
            status_code=400,
            detail="El usuario no tiene marcas activas para vigilar."
        )

    # Crear registro de ejecución
    run = EjecucionMonitor(
        user_id          = current_user.id,
        modo             = payload.modo,
        estado           = "corriendo",
        marcas_vigiladas = marcas_count,
        alertas_nuevas   = 0,
        expedientes_proc = 0,
        iniciada_el      = datetime.utcnow(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # Despachar en background
    background_tasks.add_task(
        _ejecutar_monitor_bg,
        run_id    = run.id,
        user_id   = current_user.id,
        modo      = payload.modo,
        notificar = payload.notificar,
    )

    return run


# ── GET /monitor/runs ─────────────────────────────────────────────────────────

@router.get("/runs", response_model=List[MonitorRunOut])
def list_runs(
    page:         int     = Query(default=1, ge=1),
    size:         int     = Query(default=10, ge=1, le=50),
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    """Historial de ejecuciones del usuario, más recientes primero."""
    runs = (
        db.query(EjecucionMonitor)
        .filter(EjecucionMonitor.user_id == current_user.id)
        .order_by(EjecucionMonitor.iniciada_el.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return runs


# ── GET /monitor/runs/{id} ────────────────────────────────────────────────────

@router.get("/runs/{run_id}", response_model=MonitorRunOut)
def get_run(
    run_id:       int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    """Detalle de una ejecución específica (útil para polling del frontend)."""
    run = db.query(EjecucionMonitor).filter(
        EjecucionMonitor.id      == run_id,
        EjecucionMonitor.user_id == current_user.id,
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Ejecución no encontrada")
    return run
