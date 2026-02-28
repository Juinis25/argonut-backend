"""
╔══════════════════════════════════════════════════════════════════════════════╗
║     ARGONUT — Modelos SQLAlchemy (PostgreSQL)                              ║
║     Multi-tenant: cada usuario gestiona sus propias marcas y alertas       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    Float, ForeignKey, Text, JSON, Enum as SAEnum
)
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


# ─────────────────────────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────────────────────────

class PlanEnum(str, enum.Enum):
    free       = "free"        # hasta 3 marcas, sin email
    starter    = "starter"     # hasta 10 marcas, email semanal
    pro        = "pro"         # ilimitado, WhatsApp, prioridad


class NivelAlerta(str, enum.Enum):
    critica = "critica"   # score >= 90
    alta    = "alta"      # 80 <= score < 90
    media   = "media"     # 75 <= score < 80


# ─────────────────────────────────────────────────────────────────────────────
# MODELO: USUARIO
# ─────────────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id               = Column(Integer, primary_key=True, index=True)
    email            = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password  = Column(String(255), nullable=False)
    nombre           = Column(String(100), nullable=True)
    plan             = Column(SAEnum(PlanEnum), default=PlanEnum.free, nullable=False)

    # Notificaciones
    email_notif      = Column(Boolean, default=True)
    whatsapp_notif   = Column(Boolean, default=False)
    whatsapp_numero  = Column(String(30), nullable=True)

    # Control
    is_active        = Column(Boolean, default=True)
    is_verified      = Column(Boolean, default=False)
    created_at       = Column(DateTime, default=datetime.utcnow)
    last_login       = Column(DateTime, nullable=True)

    # Relaciones
    marcas   = relationship("Marca",   back_populates="user", cascade="all, delete-orphan")
    alertas  = relationship("Alerta",  back_populates="user")

    def __repr__(self):
        return f"<User {self.email} [{self.plan}]>"


# ─────────────────────────────────────────────────────────────────────────────
# MODELO: MARCA (vigilada por un usuario)
# ─────────────────────────────────────────────────────────────────────────────

class Marca(Base):
    __tablename__ = "marcas"

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    nombre           = Column(String(200), nullable=False)
    clase            = Column(Integer, nullable=False)      # Clase INPI (1-45)
    titular          = Column(String(200), nullable=False)
    contacto         = Column(String(255), nullable=True)   # Email de contacto del cliente
    notas            = Column(Text, nullable=True)

    activa           = Column(Boolean, default=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    user     = relationship("User",   back_populates="marcas")
    alertas  = relationship("Alerta", back_populates="marca", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Marca {self.nombre} Cl.{self.clase} [user:{self.user_id}]>"


# ─────────────────────────────────────────────────────────────────────────────
# MODELO: ALERTA (colisión detectada)
# ─────────────────────────────────────────────────────────────────────────────

class Alerta(Base):
    __tablename__ = "alertas"

    id                   = Column(Integer, primary_key=True, index=True)
    user_id              = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    marca_id             = Column(Integer, ForeignKey("marcas.id"), nullable=False, index=True)

    # Datos de la solicitud conflictiva
    solicitud_nombre     = Column(String(200), nullable=False)
    expediente           = Column(String(50),  nullable=True, index=True)
    fecha_solicitud      = Column(String(30),  nullable=True)
    titular_solicitante  = Column(String(200), nullable=True)

    # Scoring
    score                = Column(Float, nullable=False)
    metodo               = Column(String(30), nullable=True)
    scores_detalle       = Column(JSON, nullable=True)   # {ratio, partial_ratio, token_sort, token_set}
    nivel                = Column(SAEnum(NivelAlerta), nullable=False)

    # Estado
    notificada           = Column(Boolean, default=False)
    resuelta             = Column(Boolean, default=False)   # El abogado la marcó como atendida
    notas_resolucion     = Column(Text, nullable=True)

    detectado_el         = Column(DateTime, default=datetime.utcnow)
    notificada_el        = Column(DateTime, nullable=True)

    # Relaciones
    user   = relationship("User",  back_populates="alertas")
    marca  = relationship("Marca", back_populates="alertas")

    def __repr__(self):
        return f"<Alerta {self.solicitud_nombre} vs {self.marca.nombre if self.marca else '?'} [{self.score}%]>"


# ─────────────────────────────────────────────────────────────────────────────
# MODELO: EXPEDIENTE PROCESADO (deduplicación global)
# ─────────────────────────────────────────────────────────────────────────────

class ExpedienteProcesado(Base):
    __tablename__ = "expedientes_procesados"

    id                  = Column(Integer, primary_key=True, index=True)
    expediente_id       = Column(String(50), unique=True, index=True, nullable=False)
    solicitud_nombre    = Column(String(200), nullable=True)
    fecha_solicitud     = Column(String(30),  nullable=True)
    titular_solicitante = Column(String(200), nullable=True)
    primera_deteccion   = Column(DateTime, default=datetime.utcnow)
    ultima_deteccion    = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Expediente {self.expediente_id}>"


# ─────────────────────────────────────────────────────────────────────────────
# MODELO: EJECUCIÓN DEL MONITOR (log de runs)
# ─────────────────────────────────────────────────────────────────────────────

class EjecucionMonitor(Base):
    __tablename__ = "ejecuciones_monitor"

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id"), nullable=True)  # None = run global/scheduled
    modo             = Column(String(10), default="real")    # "real" | "demo"
    estado           = Column(String(20), default="running") # running | ok | error
    marcas_vigiladas = Column(Integer, default=0)
    alertas_nuevas   = Column(Integer, default=0)
    expedientes_proc = Column(Integer, default=0)
    log_output       = Column(Text, nullable=True)
    error_msg        = Column(Text, nullable=True)
    iniciada_el      = Column(DateTime, default=datetime.utcnow)
    finalizada_el    = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Run #{self.id} [{self.estado}] alertas:{self.alertas_nuevas}>"
