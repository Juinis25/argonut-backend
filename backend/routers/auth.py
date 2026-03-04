"""
Auth endpoints:
  POST /auth/register  → Registro de nuevo usuario
  POST /auth/login     → Login → access + refresh token
  POST /auth/refresh   → Renovar access token
  GET  /auth/me        → Perfil del usuario autenticado
  PUT  /auth/me        → Actualizar perfil
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import User, PlanEnum
from schemas import UserRegister, UserLogin, TokenResponse, RefreshRequest, UserOut, UserUpdate
from core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from core.config import get_settings
from routers.deps import get_current_user
from services.email_service import enviar_email_bienvenida

settings = get_settings()
router   = APIRouter(prefix="/auth", tags=["auth"])


# ── Registro ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    user = User(
        email           = payload.email.lower(),
        hashed_password = hash_password(payload.password),
        nombre          = payload.nombre,
        plan            = PlanEnum.free,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Bienvenida por email — no bloquea el registro si falla
    try:
        enviar_email_bienvenida(user)
    except Exception:
        pass

    return user


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Cuenta desactivada")

    # Actualizar último login
    user.last_login = datetime.utcnow()
    db.commit()

    access_token  = create_access_token({"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token  = access_token,
        refresh_token = refresh_token,
        expires_in    = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ── Refresh ───────────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    token_data = decode_token(payload.refresh_token)

    if token_data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token de refresh inválido")

    user_id = int(token_data["sub"])
    user    = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    access_token  = create_access_token({"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token  = access_token,
        refresh_token = refresh_token,
        expires_in    = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ── Perfil ────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserOut)
def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.nombre is not None:
        current_user.nombre = payload.nombre
    if payload.email_notif is not None:
        current_user.email_notif = payload.email_notif
    if payload.whatsapp_notif is not None:
        current_user.whatsapp_notif = payload.whatsapp_notif
    if payload.whatsapp_numero is not None:
        current_user.whatsapp_numero = payload.whatsapp_numero

    db.commit()
    db.refresh(current_user)
    return current_user
