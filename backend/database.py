"""
Conexión a PostgreSQL con SQLAlchemy.
Railway inyecta DATABASE_URL con el formato:
  postgresql://user:pass@host:port/dbname
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from core.config import get_settings

settings = get_settings()

# PostgreSQL driver: psycopg2 (sync)
# Reemplazamos el esquema para compatibilidad con Railway (postgres:// → postgresql://)
DATABASE_URL = settings.DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Detectamos si estamos usando SQLite (tests) o PostgreSQL (producción)
_is_sqlite = DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    # SQLite en memoria para tests — no soporta pool_size ni max_overflow
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # PostgreSQL en producción
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,      # Reconecta si la conexión se cayó
        pool_size=10,
        max_overflow=20,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency de FastAPI. Provee una sesión por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Crea todas las tablas si no existen. Llamado al startup."""
    from models import Base
    Base.metadata.create_all(bind=engine)
