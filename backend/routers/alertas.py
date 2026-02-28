"""
Gestión de alertas — solo lectura + acciones (resolver, descartar).

GET  /alertas                → Lista alertas del usuario (filtros opcionales)
GET  /alertas/{id}           → Detalle de alerta
POST /alertas/{id}/resolver  → Marcar como resuelta
POST /alertas/{id}/ignorar   → Marcar notificada sin resolver (ignorar)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import User, Alerta, NivelAlerta
from schemas import AlertaOut, AlertaResolverInput
from routers.deps import get_current_user

router = APIRouter(prefix="/alertas", tags=["alertas"])


def get_alerta_or_404(alerta_id: int, user: User, db: Session) -> Alerta:
    alerta = db.query(Alerta).filter(
        Alerta.id      == alerta_id,
        Alerta.user_id == user.id,
    ).first()
    if not alerta:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    return alerta


def _enrich(alerta: Alerta) -> dict:
    """Agrega marca_nombre al dict de salida."""
    d = {c.name: getattr(alerta, c.name) for c in alerta.__table__.columns}
    d["marca_nombre"] = alerta.marca.nombre if alerta.marca else None
    return d


# ── GET /alertas ──────────────────────────────────────────────────────────────

@router.get("/", response_model=List[AlertaOut])
def list_alertas(
    nivel:      Optional[str]  = Query(default=None, description="critica | alta | media"),
    resuelta:   Optional[bool] = Query(default=None),
    marca_id:   Optional[int]  = Query(default=None),
    score_min:  int            = Query(default=75, ge=0, le=100),
    page:       int            = Query(default=1, ge=1),
    size:       int            = Query(default=20, ge=1, le=100),
    current_user: User         = Depends(get_current_user),
    db: Session                = Depends(get_db),
):
    q = db.query(Alerta).filter(Alerta.user_id == current_user.id)

    if nivel:
        try:
            q = q.filter(Alerta.nivel == NivelAlerta(nivel))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Nivel inválido: {nivel}")
    if resuelta is not None:
        q = q.filter(Alerta.resuelta == resuelta)
    if marca_id:
        q = q.filter(Alerta.marca_id == marca_id)
    if score_min:
        q = q.filter(Alerta.score >= score_min)

    total   = q.count()
    alertas = q.order_by(Alerta.detectado_el.desc()).offset((page - 1) * size).limit(size).all()

    return [_enrich(a) for a in alertas]


# ── GET /alertas/{id} ─────────────────────────────────────────────────────────

@router.get("/{alerta_id}", response_model=AlertaOut)
def get_alerta(
    alerta_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    alerta = get_alerta_or_404(alerta_id, current_user, db)
    return _enrich(alerta)


# ── POST /alertas/{id}/resolver ───────────────────────────────────────────────

@router.post("/{alerta_id}/resolver", response_model=AlertaOut)
def resolver_alerta(
    alerta_id: int,
    payload: AlertaResolverInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Marca la alerta como resuelta (se analizó y se tomó acción)."""
    alerta = get_alerta_or_404(alerta_id, current_user, db)
    alerta.resuelta          = True
    alerta.notas_resolucion  = payload.notas_resolucion
    db.commit()
    db.refresh(alerta)
    return _enrich(alerta)


# ── POST /alertas/{id}/ignorar ────────────────────────────────────────────────

@router.post("/{alerta_id}/ignorar", response_model=AlertaOut)
def ignorar_alerta(
    alerta_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Descarta la alerta sin acción (falso positivo, ya analizado)."""
    alerta = get_alerta_or_404(alerta_id, current_user, db)
    alerta.resuelta         = True
    alerta.notas_resolucion = "Descartada — falso positivo"
    db.commit()
    db.refresh(alerta)
    return _enrich(alerta)
