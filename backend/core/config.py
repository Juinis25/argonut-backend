"""
Configuración centralizada via variables de entorno.
Railway inyecta DATABASE_URL automáticamente al provisionar PostgreSQL.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── App
    APP_NAME: str = "Argonut API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    FRONTEND_URL: str = "https://argonut.ar"

    # ── Base de datos (Railway inyecta DATABASE_URL)
    DATABASE_URL: str = "postgresql://user:pass@localhost:5432/argonut"

    # ── JWT
    SECRET_KEY: str = "cambia-esto-en-produccion-por-una-clave-de-64-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24       # 24 horas
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── Email (Gmail SMTP o SendGrid)
    # Para SMTP: setear SMTP_HOST, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
    # Para SendGrid: setear SENDGRID_API_KEY, SENDGRID_FROM_EMAIL
    EMAIL_BACKEND: str = "smtp"          # "smtp" | "sendgrid" (informativo; selección es automática)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""              # Contraseña de aplicación Google

    # SendGrid (prioridad si SENDGRID_API_KEY está seteado)
    SENDGRID_API_KEY: str = ""

    # ── WhatsApp (Twilio)
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_FROM: str = "whatsapp:+14155238886"

    # ── Monitor INPI
    UMBRAL_SIMILITUD: int = 75
    # URL de sesión (GET para obtener cookies del portal)
    INPI_SESION_URL: str = "https://portaltramites.inpi.gob.ar/marcasconsultas/busqueda/?Cod_Funcion=NQA0ADE"
    # Endpoint JSON real (descubierto por ingeniería inversa del portal)
    INPI_API_URL: str = "https://portaltramites.inpi.gob.ar/MarcasConsultas/GrillaMarcasAvanzada"
    # Alias legacy (deprecado — no usar en código nuevo)
    INPI_URL: str = "https://portaltramites.inpi.gob.ar/MarcasConsultas/GrillaMarcasAvanzada"

    # ── Email from (usados por email_service.py)
    SMTP_FROM: str = "alertas@argonut.ar"
    SENDGRID_FROM_EMAIL: str = "alertas@argonut.ar"

    # ── Scheduler (APScheduler)
    SCHEDULER_TIMEZONE: str = "America/Argentina/Cordoba"
    MONITOR_CRON_DAY: str = "mon"        # Día de ejecución semanal
    MONITOR_CRON_HOUR: int = 8           # Hora (local)
    MONITOR_CRON_MINUTE: int = 0

    # Aliases alineados con scheduler.py
    SCHEDULER_CRON_DAY_OF_WEEK: str = "mon"
    SCHEDULER_CRON_HOUR: int = 8
    SCHEDULER_CRON_MINUTE: int = 0

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
