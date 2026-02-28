"""
CRUD de marcas vigiladas — scoped por usuario (multi-tenant).

GET    /marcas           → Lista marcas del usuario autenticado
POST   /marcas           → Agregar marca
GET    /marcas/{id}      → Detalle
PUT    /marcas/{id}      → Actualizar
DELETE /marcas/{id}      → Eliminar (soft-delete: activa=False)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import User, Marca
from schemas import MarcaCreate, MarcaUpdate, MarcaOut
from routers.deps import get_current_user
from core.config import get_settings

settings = get_settings()
router   = APIRouter(prefix="/marcas", tags=["marcas"])


# Límites por plan
PLAN_LIMITS = {
    "free":    3,
    "starter": 10,
    "pro":     9999,
}


def get_marca_or_404(marca_id: int, user: User, db: Session) -> Marca:
    marca = db.query(Marca).filter(
        Marca.id == marca_id,
        Marca.user_id == user.id,
    ).first()
    if not marca:
        raise HTTPException(status_code=404, detail="Marca no encontrada")
    return marca


# ── GET /marcas ───────────────────────────────────────────────────────────────

@router.get("/", response_model=List[MarcaOut])
def list_marcas(
    solo_activas: bool = Query(default=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Marca).filter(Marca.user_id == current_user.id)
    if solo_activas:
        q = q.filter(Marca.activa == True)
    return q.order_by(Marca.created_at.desc()).all()


# ── POST /marcas ──────────────────────────────────────────────────────────────

@router.post("/", response_model=MarcaOut, status_code=201)
def create_marca(
    payload: MarcaCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verificar límite de plan
    limite = PLAN_LIMITS.get(current_user.plan, 3)
    activas = db.query(Marca).filter(
        Marca.user_id == current_user.id,
        Marca.activa == True,
    ).count()

    if activas >= limite:
        raise HTTPException(
            status_code=403,
            detail=f"Tu plan {current_user.plan} permite máximo {limite} marcas activas. "
                   f"Actualizá tu plan para agregar más."
        )

    # Verificar duplicado (misma marca + clase para este usuario)
    existing = db.query(Marca).filter(
        Marca.user_id == current_user.id,
        Marca.nombre  == payload.nombre.upper().strip(),
        Marca.clase   == payload.clase,
        Marca.activa  == True,
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Ya tenés '{payload.nombre}' en Clase {payload.clase} en vigilancia"
        )

    marca = Marca(
        user_id  = current_user.id,
        nombre   = payload.nombre.upper().strip(),
        clase    = payload.clase,
        titular  = payload.titular.strip(),
        contacto = payload.contacto,
        notas    = payload.notas,
    )
    db.add(marca)
    db.commit()
    db.refresh(marca)
    return marca


# ── GET /marcas/{id} ──────────────────────────────────────────────────────────

@router.get("/{marca_id}", response_model=MarcaOut)
def get_marca(
    marca_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_marca_or_404(marca_id, current_user, db)


# ── PUT /marcas/{id} ──────────────────────────────────────────────────────────

@router.put("/{marca_id}", response_model=MarcaOut)
def update_marca(
    marca_id: int,
    payload: MarcaUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    marca = get_marca_or_404(marca_id, current_user, db)

    if payload.nombre  is not None: marca.nombre   = payload.nombre.upper().strip()
    if payload.clase   is not None: marca.clase    = payload.clase
    if payload.titular is not None: marca.titular  = payload.titular.strip()
    if payload.contacto is not None: marca.contacto = payload.contacto
    if payload.notas   is not None: marca.notas    = payload.notas
    if payload.activa  is not None: marca.activa   = payload.activa

    db.commit()
    db.refresh(marca)
    return marca


# ── DELETE /marcas/{id} ───────────────────────────────────────────────────────

@router.delete("/{marca_id}", status_code=204)
def delete_marca(
    marca_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    marca = get_marca_or_404(marca_id, current_user, db)
    marca.activa = False   # Soft-delete: conserva historial de alertas
    db.commit()
