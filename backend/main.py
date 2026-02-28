"""
Argonut API — FastAPI entrypoint.

Rutas base:
  /auth      → registro, login, refresh, perfil
  /marcas    → CRUD de marcas del usuario
  /alertas   → gestión de alertas (resolver, ignorar)
  /dashboard → métricas agregadas
  /monitor   → ejecuciones del motor INPI

Documentación interactiva:
  GET /docs     → Swagger UI
  GET /redoc    → ReDoc
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from database   import create_tables

# Routers
from routers.auth      import router as auth_router
from routers.marcas    import router as marcas_router
from routers.alertas   import router as alertas_router
from routers.dashboard import router as dashboard_router
from routers.monitor   import router as monitor_router

settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# LIFESPAN (startup / shutdown)
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Eventos de ciclo de vida de la aplicación."""
    # ── Startup ────────────────────────────────────────────────────────────
    create_tables()  # Crea tablas si no existen (idempotente)

    from services.scheduler import iniciar_scheduler
    iniciar_scheduler()

    yield

    # ── Shutdown ───────────────────────────────────────────────────────────
    from services.scheduler import detener_scheduler
    detener_scheduler()


# ─────────────────────────────────────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title       = settings.APP_NAME,
    version     = "1.0.0",
    description = (
        "API de vigilancia de marcas INPI Argentina — SaaS multi-tenant.\n\n"
        "Autentica con Bearer JWT en /auth/login y luego usá el token en el botón 'Authorize'."
    ),
    docs_url    = "/docs",
    redoc_url   = "/redoc",
    lifespan    = lifespan,
)


# ─────────────────────────────────────────────────────────────────────────────
# CORS
# ─────────────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins     = [settings.FRONTEND_URL, "http://localhost:3000", "http://localhost:5173"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# ROUTERS
# ─────────────────────────────────────────────────────────────────────────────

app.include_router(auth_router)
app.include_router(marcas_router)
app.include_router(alertas_router)
app.include_router(dashboard_router)
app.include_router(monitor_router)


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
def health():
    """Railway lo usa para verificar que el servicio está vivo."""
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/", tags=["system"])
def root():
    return {
        "message": f"Bienvenido a {settings.APP_NAME} API",
        "docs":    "/docs",
        "version": "1.0.0",
    }
