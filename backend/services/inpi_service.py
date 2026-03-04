"""
Motor de vigilancia INPI — versión producción para el backend SaaS.

Cambios respecto a la versión anterior:
  - Reemplaza Playwright por httpx directo a la JSON API del portal INPI.
  - Fix deadlock asyncio.run() en FastAPI: punto de entrada async + wrapper sync.
  - Retry con tenacity (3 intentos, backoff exponencial 2→4→16s).
  - Cache TTL 24h compartido entre usuarios (cachetools).
  - Parser de fechas .NET (/Date(ms)/).
  - Demo mode explícito: NUNCA fallback silencioso desde modo real.

API descubierta por ingeniería inversa del portal:
  POST https://portaltramites.inpi.gob.ar/MarcasConsultas/GrillaMarcasAvanzada
  Payload JSON → Response JSON {total, rows: [{Acta, Titulares, Fecha_Ingreso,
                                               Clase, Denominacion, ...}]}

Puntos de entrada públicos:
    await ejecutar_para_usuario_async(user_id, modo, notificar, db)  → FastAPI
          ejecutar_para_usuario(user_id, modo, notificar, db)        → APScheduler
"""

from __future__ import annotations

import asyncio
import logging
import re
import threading
import unicodedata
from datetime import datetime, timezone
from typing import Optional

import httpx
from cachetools import TTLCache
from sqlalchemy.orm import Session
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from models import Alerta, ExpedienteProcesado, Marca, NivelAlerta, PlanEnum, User

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────────────────────

INPI_BASE_URL   = "https://portaltramites.inpi.gob.ar"
INPI_SESION_URL = f"{INPI_BASE_URL}/marcasconsultas/busqueda/?Cod_Funcion=NQA0ADE"
INPI_API_URL    = f"{INPI_BASE_URL}/MarcasConsultas/GrillaMarcasAvanzada"

PAGE_SIZE  = 100   # registros por página
MAX_PAGES  = 20    # límite de seguridad: 20 × 100 = 2 000 registros máx. por búsqueda

_HEADERS = {
    "User-Agent":   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Referer":      INPI_SESION_URL,
    "Accept":       "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

# ─────────────────────────────────────────────────────────────────────────────
# CACHE COMPARTIDO (TTL 24 h)
# ─────────────────────────────────────────────────────────────────────────────
# Clave: (clase: int, denominacion: str)
# Valor: list[dict]  — filas de la API ya normalizadas

_cache: TTLCache = TTLCache(maxsize=1_000, ttl=86_400)   # 24 h
_cache_lock = threading.Lock()


# ─────────────────────────────────────────────────────────────────────────────
# UTILITARIOS
# ─────────────────────────────────────────────────────────────────────────────

_DOTNET_DATE_RE = re.compile(r"/Date\((-?\d+)(?:[+-]\d{4})?\)/")


def _parse_dotnet_date(val: Optional[str]) -> Optional[str]:
    """Convierte /Date(milliseconds)/ → 'DD/MM/YYYY'. None si inválido o None."""
    if not val:
        return None
    m = _DOTNET_DATE_RE.match(str(val))
    if not m:
        return str(val)[:10] if val else None
    ms = int(m.group(1))
    try:
        dt = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
        return dt.strftime("%d/%m/%Y")
    except (OSError, OverflowError, ValueError):
        return None


def _normalizar(nombre: str) -> str:
    """Uppercase, sin tildes, sin espacios dobles."""
    nombre = nombre.upper().strip()
    nombre = unicodedata.normalize("NFD", nombre)
    nombre = "".join(c for c in nombre if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", nombre)


def _calcular_similitud(m1: str, m2: str) -> dict:
    from fuzzywuzzy import fuzz  # import lazy para evitar peso en arranque

    a, b = _normalizar(m1), _normalizar(m2)
    scores = {
        "ratio":            fuzz.ratio(a, b),
        "partial_ratio":    fuzz.partial_ratio(a, b),
        "token_sort_ratio": fuzz.token_sort_ratio(a, b),
        "token_set_ratio":  fuzz.token_set_ratio(a, b),
    }
    ganador = max(scores, key=lambda k: scores[k])
    return {
        **scores,
        "max_score":      scores[ganador],
        "metodo_ganador": ganador,
    }


def _nivel_desde_score(score: float) -> NivelAlerta:
    if score >= 90:
        return NivelAlerta.critica
    if score >= 80:
        return NivelAlerta.alta
    return NivelAlerta.media


# ─────────────────────────────────────────────────────────────────────────────
# DATOS DEMO (sólo para modo == "demo")
# ─────────────────────────────────────────────────────────────────────────────

def _datos_demo(clases: list[int]) -> list[dict]:
    """
    Solicitudes simuladas.  Se usan ÚNICA Y EXCLUSIVAMENTE cuando modo='demo'.
    NUNCA se llaman como fallback silencioso desde modo real.
    """
    pool = [
        {"acta": "4123456", "denominacion": "MERCADO LIBRE",       "fecha": "01/03/2026", "titular": "Empresa Demo SA",      "clase": 35},
        {"acta": "4123457", "denominacion": "MERCADOLIBRE SHOP",   "fecha": "01/03/2026", "titular": "Competidor Demo SRL",  "clase": 35},
        {"acta": "4123458", "denominacion": "NARANJAX",            "fecha": "01/03/2026", "titular": "Fintech Paralela SA",  "clase": 36},
        {"acta": "4123459", "denominacion": "LA PATAGONICA",       "fecha": "01/03/2026", "titular": "Resto del Sur SRL",    "clase": 43},
        {"acta": "4123461", "denominacion": "INFLUENCER EJMPLO",   "fecha": "01/03/2026", "titular": "Squatter Digital",     "clase": 41},
        {"acta": "4123470", "denominacion": "NARANJA DIGITAL",     "fecha": "01/03/2026", "titular": "Fintech Clon SA",      "clase": 36},
        {"acta": "4123499", "denominacion": "MARCA SIN CONFLICTO", "fecha": "01/03/2026", "titular": "Empresa Legitima SA",  "clase": 35},
    ]
    return [d for d in pool if d["clase"] in clases]


# ─────────────────────────────────────────────────────────────────────────────
# CAPA HTTP — con retry tenacity
# ─────────────────────────────────────────────────────────────────────────────

@retry(
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=16),
    before_sleep=before_sleep_log(log, logging.WARNING),
    reraise=True,
)
async def _fetch_pagina_raw(
    client: httpx.AsyncClient,
    clase: int,
    denominacion: str,
    offset: int,
) -> dict:
    """
    Una sola llamada paginada a la JSON API del INPI.
    Lanza httpx.HTTPError si el servidor responde con status >= 400.
    Tenacity reintenta hasta 3 veces con backoff.
    """
    payload = {
        "Tipo_Resolucion":       "",
        "Clase":                 str(clase),
        "TipoBusquedaDenominacion": "1",   # CONTIENE
        "Denominacion":          denominacion,
        "Titular":               "",
        "TipoBusquedaTitular":   "0",
        "Fecha_IngresoDesde":    "",
        "Fecha_IngresoHasta":    "",
        "Fecha_ResolucionDesde": "",
        "Fecha_ResolucionHasta": "",
        "vigentes":              False,
        "limit":                 PAGE_SIZE,
        "offset":                offset,
    }
    resp = await client.post(INPI_API_URL, json=payload, timeout=30.0)
    resp.raise_for_status()
    return resp.json()


async def _fetch_todas_paginas(
    client: httpx.AsyncClient,
    clase: int,
    denominacion: str,
) -> list[dict]:
    """
    Descarga todas las páginas de resultados para (clase, denominacion).
    Mapea las filas de la API al formato interno normalizado.
    """
    filas: list[dict] = []
    total_conocido: Optional[int] = None

    for page in range(MAX_PAGES):
        offset = page * PAGE_SIZE
        if total_conocido is not None and offset >= total_conocido:
            break

        data = await _fetch_pagina_raw(client, clase, denominacion, offset)
        total_conocido = data.get("total", 0)
        rows = data.get("rows") or []

        for row in rows:
            acta = str(row.get("Acta", "")).strip()
            filas.append({
                "acta":        acta,
                "denominacion": str(row.get("Denominacion", "")).strip().upper(),
                "fecha":        _parse_dotnet_date(row.get("Fecha_Ingreso")),
                "titular":      str(row.get("Titulares", "")).strip(),
                "clase":        int(row.get("Clase", clase)),
                "estado":       str(row.get("Estado", "")).strip(),
                "resolucion":   str(row.get("Numero_Resolucion", "")).strip(),
            })

        if len(rows) < PAGE_SIZE:
            break   # última página

    return filas


async def _fetch_con_cache(
    client: httpx.AsyncClient,
    clase: int,
    denominacion: str,
) -> list[dict]:
    """
    Wrapper de cache sobre _fetch_todas_paginas.
    TTL 24 h — evita scraping redundante entre usuarios que vigilan marcas similares.
    """
    clave = (clase, _normalizar(denominacion))

    with _cache_lock:
        if clave in _cache:
            log.debug(f"Cache hit: clase={clase} denom='{denominacion}'")
            return _cache[clave]

    # Fuera del lock para no bloquear otros threads durante la I/O
    log.info(f"[INPI] Fetching clase={clase} denom='{denominacion}'...")
    filas = await _fetch_todas_paginas(client, clase, denominacion)

    with _cache_lock:
        _cache[clave] = filas

    log.info(f"[INPI] clase={clase} denom='{denominacion}' → {len(filas)} filas")
    return filas


# ─────────────────────────────────────────────────────────────────────────────
# DEDUPLICACIÓN Y PERSISTENCIA
# ─────────────────────────────────────────────────────────────────────────────

def _expediente_ya_alertado(
    expediente_id: str,
    marca_id: int,
    user_id: int,
    db: Session,
) -> bool:
    """True si ya existe una Alerta no resuelta para ese expediente + marca."""
    return db.query(Alerta).filter(
        Alerta.user_id    == user_id,
        Alerta.marca_id   == marca_id,
        Alerta.expediente == expediente_id,
        Alerta.resuelta   == False,
    ).first() is not None


def _upsert_expediente(
    acta: str,
    denominacion: str,
    fecha: Optional[str],
    titular: str,
    db: Session,
) -> None:
    """Upsert en la tabla global de expedientes procesados."""
    exp = db.query(ExpedienteProcesado).filter(
        ExpedienteProcesado.expediente_id == acta
    ).first()
    now = datetime.utcnow()
    if exp:
        exp.ultima_deteccion = now
    else:
        db.add(ExpedienteProcesado(
            expediente_id       = acta,
            solicitud_nombre    = denominacion,
            fecha_solicitud     = fecha,
            titular_solicitante = titular,
            primera_deteccion   = now,
            ultima_deteccion    = now,
        ))


# ─────────────────────────────────────────────────────────────────────────────
# LÓGICA PRINCIPAL — ASYNC
# ─────────────────────────────────────────────────────────────────────────────

async def ejecutar_para_usuario_async(
    user_id:   int,
    modo:      str,      # "demo" | "real"
    notificar: bool,
    db:        Session,
) -> dict:
    """
    Ciclo completo de vigilancia para un usuario.

    Flujo:
      1. Cargar marcas activas del usuario desde la DB.
      2. Obtener solicitudes INPI (demo → datos estáticos | real → JSON API).
      3. Fuzzy matching por marca × solicitud (misma clase).
      4. Persistir alertas nuevas (deduplicadas por expediente_id).
      5. Enviar email si notificar=True y hay alertas nuevas.
      6. Retornar métricas para EjecucionMonitor.

    Raises:
        RuntimeError — si modo='real' y el portal INPI falla después de retries.
                       NO cae silenciosamente a demo.
    """
    from core.config import get_settings
    settings   = get_settings()
    umbral     = settings.UMBRAL_SIMILITUD
    log_lines: list[str] = []

    def _log(msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        log.info(msg)
        log_lines.append(f"[{ts}] {msg}")

    # ── 1. Marcas activas del usuario ──────────────────────────────────────
    marcas: list[Marca] = db.query(Marca).filter(
        Marca.user_id == user_id,
        Marca.activa  == True,
    ).all()

    if not marcas:
        return {
            "marcas_vigiladas": 0,
            "alertas_nuevas":   0,
            "expedientes_proc": 0,
            "log":              "Sin marcas activas para este usuario.",
        }

    _log(f"Marcas a vigilar: {len(marcas)}")

    # ── 2. Obtener solicitudes INPI ────────────────────────────────────────
    # solicitudes_por_marca: {marca_id → [filas de la API]}
    solicitudes_por_marca: dict[int, list[dict]] = {}

    if modo == "demo":
        _log("⚠️  Modo DEMO — datos simulados, NO refleja el INPI real.")
        clases_all = list({m.clase for m in marcas})
        pool_demo  = _datos_demo(clases_all)
        for marca in marcas:
            solicitudes_por_marca[marca.id] = [
                s for s in pool_demo if s["clase"] == marca.clase
            ]

    else:
        _log("Modo REAL — consultando JSON API del portal INPI...")
        # Establece sesión con cookies (necesario para la API del portal)
        async with httpx.AsyncClient(
            headers=_HEADERS,
            follow_redirects=True,
            timeout=45.0,
        ) as client:
            # Obtener cookies de sesión
            try:
                _log(f"Estableciendo sesión en {INPI_SESION_URL}...")
                resp = await client.get(INPI_SESION_URL)
                resp.raise_for_status()
                _log("Sesión establecida OK.")
            except httpx.HTTPError as exc:
                raise RuntimeError(
                    f"No se pudo establecer sesión con el portal INPI: {exc}"
                ) from exc

            # Una búsqueda por marca (CONTIENE el nombre de la marca, en su clase)
            for marca in marcas:
                denominacion_busqueda = _normalizar(marca.nombre)
                _log(f"Buscando: clase={marca.clase} CONTIENE='{denominacion_busqueda}'")
                try:
                    filas = await _fetch_con_cache(
                        client,
                        clase        = marca.clase,
                        denominacion = denominacion_busqueda,
                    )
                    solicitudes_por_marca[marca.id] = filas
                    _log(f"  → {len(filas)} solicitudes para '{marca.nombre}'")
                except Exception as exc:
                    # Error después de todos los retries → fallo hard, no demo silencioso
                    raise RuntimeError(
                        f"Error al consultar INPI para marca '{marca.nombre}' "
                        f"(clase {marca.clase}): {exc}"
                    ) from exc

    # ── 3 & 4. Fuzzy matching + persistencia ──────────────────────────────
    alertas_nuevas  = 0
    expedientes_set: set[str] = set()

    for marca in marcas:
        solicitudes = solicitudes_por_marca.get(marca.id, [])
        _log(f"Procesando '{marca.nombre}' (clase {marca.clase}): "
             f"{len(solicitudes)} candidatos")

        for sol in solicitudes:
            if int(marca.clase) != int(sol["clase"]):
                continue

            sim = _calcular_similitud(marca.nombre, sol["denominacion"])
            if sim["max_score"] < umbral:
                continue

            acta = sol.get("acta", "").strip()

            # Deduplicación: skip si ya existe alerta no resuelta
            if acta and _expediente_ya_alertado(acta, marca.id, user_id, db):
                continue

            nivel  = _nivel_desde_score(sim["max_score"])
            alerta = Alerta(
                user_id             = user_id,
                marca_id            = marca.id,
                solicitud_nombre    = sol["denominacion"],
                expediente          = acta or None,
                fecha_solicitud     = sol.get("fecha"),
                titular_solicitante = sol.get("titular"),
                score               = float(sim["max_score"]),
                nivel               = nivel,
                metodo              = sim["metodo_ganador"],
                scores_detalle      = {
                    k: v for k, v in sim.items()
                    if k not in ("max_score", "metodo_ganador")
                },
                notificada          = False,
                resuelta            = False,
                detectado_el        = datetime.utcnow(),
            )
            db.add(alerta)
            alertas_nuevas += 1

            if acta:
                _upsert_expediente(
                    acta,
                    sol["denominacion"],
                    sol.get("fecha"),
                    sol.get("titular", ""),
                    db,
                )
                expedientes_set.add(acta)

            _log(
                f"  [{sim['max_score']}%/{nivel.value}] "
                f"'{marca.nombre}' ↔ '{sol['denominacion']}' "
                f"(Acta {acta or 'N/A'}, Titular: {sol.get('titular', 'N/A')})"
            )

    db.flush()

    # ── 5. Notificaciones ─────────────────────────────────────────────────
    if notificar and alertas_nuevas > 0:
        try:
            from services.email_service import enviar_resumen_alertas
            user: Optional[User] = db.query(User).filter(User.id == user_id).first()
            if (user
                    and getattr(user, "email_notif", False)
                    and user.email
                    and user.plan != PlanEnum.free):
                pendientes = db.query(Alerta).filter(
                    Alerta.user_id    == user_id,
                    Alerta.notificada == False,
                    Alerta.resuelta   == False,
                ).all()
                enviar_resumen_alertas(user, pendientes)
                now = datetime.utcnow()
                for a in pendientes:
                    a.notificada    = True
                    a.notificada_el = now
                _log(f"Email enviado a {user.email} ({len(pendientes)} alertas).")
        except Exception as exc:
            _log(f"⚠️  Error al enviar email: {exc}")

    _log(
        f"Finalizado — {alertas_nuevas} alertas nuevas, "
        f"{len(expedientes_set)} expedientes nuevos procesados."
    )

    return {
        "marcas_vigiladas": len(marcas),
        "alertas_nuevas":   alertas_nuevas,
        "expedientes_proc": len(expedientes_set),
        "log":              "\n".join(log_lines),
    }


# ─────────────────────────────────────────────────────────────────────────────
# WRAPPER SÍNCRONO — para APScheduler (corre en thread separado)
# ─────────────────────────────────────────────────────────────────────────────

def ejecutar_para_usuario(
    user_id:   int,
    modo:      str,
    notificar: bool,
    db:        Session,
) -> dict:
    """
    Wrapper síncrono de ejecutar_para_usuario_async.

    APScheduler llama a este wrapper desde un thread de background.
    Crear un event loop propio evita el RuntimeError que surge al llamar
    asyncio.run() cuando ya hay un loop activo (FastAPI / uvicorn).
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            ejecutar_para_usuario_async(user_id, modo, notificar, db)
        )
    finally:
        loop.close()
        asyncio.set_event_loop(None)
