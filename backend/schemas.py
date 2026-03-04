"""
Schemas Pydantic: validación de entrada/salida en todos los endpoints.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator
from models import PlanEnum, NivelAlerta


# ─────────────────────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email:    EmailStr
    password: str = Field(min_length=8, description="Mínimo 8 caracteres")
    nombre:   Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v


class UserLogin(BaseModel):
    email:    EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    expires_in:    int   # segundos


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id:              int
    email:           str
    nombre:          Optional[str]
    plan:            PlanEnum
    email_notif:     bool
    whatsapp_notif:  bool
    is_verified:     bool
    created_at:      datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    nombre:          Optional[str] = None
    email_notif:     Optional[bool] = None
    whatsapp_notif:  Optional[bool] = None
    whatsapp_numero: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# MARCAS
# ─────────────────────────────────────────────────────────────────────────────

class MarcaCreate(BaseModel):
    nombre:   str = Field(min_length=1, max_length=200)
    clase:    int = Field(ge=1, le=45, description="Clase INPI (1-45)")
    titular:  str = Field(min_length=1, max_length=200)
    contacto: Optional[str] = None
    notas:    Optional[str] = None

    @field_validator("nombre")
    @classmethod
    def uppercase_nombre(cls, v):
        return v.upper().strip()


class MarcaUpdate(BaseModel):
    nombre:   Optional[str] = None
    clase:    Optional[int] = Field(default=None, ge=1, le=45)
    titular:  Optional[str] = None
    contacto: Optional[str] = None
    notas:    Optional[str] = None
    activa:   Optional[bool] = None


class MarcaOut(BaseModel):
    id:         int
    nombre:     str
    clase:      int
    titular:    str
    contacto:   Optional[str]
    notas:      Optional[str]
    activa:     bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────────────
# ALERTAS
# ─────────────────────────────────────────────────────────────────────────────

class AlertaOut(BaseModel):
    id:                  int
    marca_id:            int
    marca_nombre:        Optional[str] = None   # populated from join
    clase:               Optional[int] = None   # populated from join (marca.clase)
    solicitud_nombre:    str
    expediente:          Optional[str]
    fecha_solicitud:     Optional[str]
    titular_solicitante: Optional[str]
    score:               float
    nivel:               NivelAlerta
    metodo:              Optional[str]
    scores_detalle:      Optional[dict]
    notificada:          bool
    resuelta:            bool
    notas_resolucion:    Optional[str]
    detectado_el:        datetime

    class Config:
        from_attributes = True


class AlertaResolverInput(BaseModel):
    notas_resolucion: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_marcas:          int
    marcas_activas:        int
    alertas_criticas:      int
    alertas_altas:         int
    alertas_medias:        int
    alertas_sin_resolver:  int
    ultima_ejecucion:      Optional[datetime]
    proxima_ejecucion:     Optional[datetime]


# ─────────────────────────────────────────────────────────────────────────────
# MONITOR
# ─────────────────────────────────────────────────────────────────────────────

class MonitorRunRequest(BaseModel):
    modo:      str = Field(default="demo", pattern="^(demo|real)$")
    notificar: bool = False


class MonitorRunOut(BaseModel):
    id:               int
    modo:             str
    estado:           str
    marcas_vigiladas: int
    alertas_nuevas:   int
    expedientes_proc: int
    iniciada_el:      datetime
    finalizada_el:    Optional[datetime]
    log_output:       Optional[str]
    error_msg:        Optional[str]

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────────────
# GENÉRICOS
# ─────────────────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str


class PaginatedResponse(BaseModel):
    items:   list
    total:   int
    page:    int
    size:    int
    pages:   int
