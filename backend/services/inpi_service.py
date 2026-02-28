"""
Motor de vigilancia INPI — versión multi-tenant para el backend SaaS.

Adapta la lógica de inpi_vigilancia_marcas.py a:
  - Operar sobre las marcas de UN usuario en la base de datos PostgreSQL
  - Guardar alertas y deduplicar con ExpedienteProcesado
  - Devolver un dict de resultados para el EjecucionMonitor

Punto de entrada:
    ejecutar_para_usuario(user_id, modo, notificar, db) -> dict
"""

import re
import asyncio
import logging
import unicodedata
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from models import Marca, Alerta, ExpedienteProcesado, NivelAlerta, User

log = logging.getLogger(__name__)

UMBRAL_SIMILITUD = 75  # Sobreescrito por settings si se importa


# ─────────────────────────────────────────────────────────────────────────────
# NORMALIZACIÓN Y SIMILITUD
# ─────────────────────────────────────────────────────────────────────────────

def _normalizar(nombre: str) -> str:
    """Uppercase, sin tildes, sin espacios dobles."""
    nombre = nombre.upper().strip()
    nombre = unicodedata.normalize("NFD", nombre)
    nombre = "".join(c for c in nombre if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", nombre)


def _calcular_similitud(m1: str, m2: str) -> dict:
    from fuzzywuzzy import fuzz
    a, b = _normalizar(m1), _normalizar(m2)
    scores = {
        "ratio":            fuzz.ratio(a, b),
        "partial_ratio":    fuzz.partial_ratio(a, b),
        "token_sort_ratio": fuzz.token_sort_ratio(a, b),
        "token_set_ratio":  fuzz.token_set_ratio(a, b),
    }
    scores["max_score"]      = max(scores.values())
    scores["metodo_ganador"] = max(
        (k for k in scores if k != "max_score"),
        key=lambda k: scores[k]
    )
    return scores


def _nivel_desde_score(score: float) -> NivelAlerta:
    if score >= 90:
        return NivelAlerta.critica
    elif score >= 80:
        return NivelAlerta.alta
    return NivelAlerta.media


# ─────────────────────────────────────────────────────────────────────────────
# SCRAPING / DEMO DATA
# ─────────────────────────────────────────────────────────────────────────────

def _datos_demo(clases: list[int]) -> list[dict]:
    """
    Solicitudes simuladas para modo demo (sin Playwright).
    Cubre los casos representativos del INPI real.
    """
    pool = [
        {"denominacion": "MERCADO LIBRE",        "expediente": "Nº 4.123.456", "fecha": datetime.now().strftime("%d/%m/%Y"), "titular": "Empresa Demo SA",        "clase": 35},
        {"denominacion": "MERCADOLIBRE SHOP",    "expediente": "Nº 4.123.457", "fecha": datetime.now().strftime("%d/%m/%Y"), "titular": "Competidor Demo SRL",     "clase": 35},
        {"denominacion": "NARANJAX",             "expediente": "Nº 4.123.458", "fecha": datetime.now().strftime("%d/%m/%Y"), "titular": "Fintech Paralela SA",     "clase": 36},
        {"denominacion": "LA PATAGONICA",        "expediente": "Nº 4.123.459", "fecha": datetime.now().strftime("%d/%m/%Y"), "titular": "Resto del Sur SRL",       "clase": 43},
        {"denominacion": "INFLUENCER EJMPLO",    "expediente": "Nº 4.123.461", "fecha": datetime.now().strftime("%d/%m/%Y"), "titular": "Squatter Digital",        "clase": 41},
        {"denominacion": "NARANJA DIGITAL",      "expediente": "Nº 4.123.470", "fecha": datetime.now().strftime("%d/%m/%Y"), "titular": "Fintech Clon SA",         "clase": 36},
        {"denominacion": "MARCA SIN CONFLICTO",  "expediente": "Nº 4.123.499", "fecha": datetime.now().strftime("%d/%m/%Y"), "titular": "Empresa Legítima SA",     "clase": 35},
    ]
    return [d for d in pool if d["clase"] in clases]


async def _scrape_inpi(clases: list[int]) -> list[dict]:
    """Scraping real del portal INPI con Playwright."""
    from playwright.async_api import async_playwright
    from core.config import get_settings

    settings = get_settings()
    solicitudes = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page    = await browser.new_page()
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        })

        for clase in clases:
            log.info(f"Scrapeando clase {clase}...")
            try:
                await page.goto(settings.INPI_URL, wait_until="networkidle", timeout=30000)
                await page.select_option('select[name="clase"]',  str(clase))
                await page.select_option('select[name="estado"]', "EN_TRAMITE")
                await page.select_option('select[name="orden"]',  "FECHA_DESC")
                await page.click('button[type="submit"]')
                await page.wait_for_selector(".resultado-marca", timeout=15000)
                items = await page.query_selector_all(".resultado-marca")

                for item in items[:50]:
                    try:
                        denom    = await item.query_selector(".denominacion")
                        exp      = await item.query_selector(".expediente")
                        fecha_el = await item.query_selector(".fecha")
                        tit_el   = await item.query_selector(".titular")
                        solicitudes.append({
                            "denominacion": (await denom.inner_text()).strip().upper()  if denom    else "N/D",
                            "expediente":   (await exp.inner_text()).strip()            if exp      else "N/D",
                            "fecha":        (await fecha_el.inner_text()).strip()       if fecha_el else "N/D",
                            "titular":      (await tit_el.inner_text()).strip()         if tit_el   else "N/D",
                            "clase":        clase,
                        })
                    except Exception as e:
                        log.warning(f"Error parseando ítem INPI: {e}")

                log.info(f"Clase {clase}: {len([s for s in solicitudes if s['clase'] == clase])} solicitudes.")

            except Exception as e:
                log.error(f"Error scrapin clase {clase}: {e}. Usando datos demo.")
                solicitudes.extend(_datos_demo([clase]))

        await browser.close()

    return solicitudes


# ─────────────────────────────────────────────────────────────────────────────
# DEDUPLICACIÓN Y PERSISTENCIA
# ─────────────────────────────────────────────────────────────────────────────

def _expediente_ya_alertado(expediente_id: str, marca_id: int, user_id: int, db: Session) -> bool:
    """
    Un expediente se considera ya alertado si existe una Alerta no resuelta
    para la misma combinación expediente + marca del usuario.
    """
    existe = db.query(Alerta).filter(
        Alerta.user_id    == user_id,
        Alerta.marca_id   == marca_id,
        Alerta.expediente == expediente_id,
        Alerta.resuelta   == False,
    ).first()
    return existe is not None


def _registrar_expediente(expediente_id: str, denominacion: str, fecha: str, titular: str, db: Session):
    """Upsert en la tabla global de expedientes procesados."""
    exp = db.query(ExpedienteProcesado).filter(
        ExpedienteProcesado.expediente_id == expediente_id
    ).first()

    if exp:
        exp.ultima_deteccion = datetime.utcnow()
    else:
        exp = ExpedienteProcesado(
            expediente_id        = expediente_id,
            solicitud_nombre     = denominacion,
            fecha_solicitud      = fecha,
            titular_solicitante  = titular,
            primera_deteccion    = datetime.utcnow(),
            ultima_deteccion     = datetime.utcnow(),
        )
        db.add(exp)


# ─────────────────────────────────────────────────────────────────────────────
# PUNTO DE ENTRADA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def ejecutar_para_usuario(
    user_id:   int,
    modo:      str,       # "demo" | "real"
    notificar: bool,
    db:        Session,
) -> dict:
    """
    Ejecuta el ciclo completo de vigilancia para un usuario:
      1. Carga sus marcas activas de la DB
      2. Obtiene solicitudes INPI (demo o scraping real)
      3. Detecta colisiones con fuzzy matching
      4. Persiste alertas nuevas (deduplicadas)
      5. Envía notificaciones si se pidió
      6. Retorna métricas del run

    Retorna:
        {
            "marcas_vigiladas": int,
            "alertas_nuevas": int,
            "expedientes_proc": int,
            "log": str,
        }
    """
    log_lines = []

    def _log(msg: str):
        log.info(msg)
        log_lines.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    # 1. Cargar marcas del usuario
    marcas = db.query(Marca).filter(
        Marca.user_id == user_id,
        Marca.activa  == True,
    ).all()

    if not marcas:
        return {"marcas_vigiladas": 0, "alertas_nuevas": 0, "expedientes_proc": 0, "log": "Sin marcas activas."}

    _log(f"Marcas a vigilar: {len(marcas)}")
    clases = list(set(m.clase for m in marcas))

    # 2. Obtener solicitudes INPI
    if modo == "demo":
        _log("Modo DEMO — usando datos simulados")
        solicitudes = _datos_demo(clases)
    else:
        _log(f"Modo REAL — scraping INPI para clases {clases}")
        solicitudes = asyncio.run(_scrape_inpi(clases))

    _log(f"Solicitudes INPI obtenidas: {len(solicitudes)}")

    # 3. Detección de colisiones
    alertas_nuevas  = 0
    expedientes_set = set()

    for marca in marcas:
        for sol in solicitudes:
            if int(marca.clase) != int(sol["clase"]):
                continue

            sim = _calcular_similitud(marca.nombre, sol["denominacion"])
            from core.config import get_settings
            umbral = get_settings().UMBRAL_SIMILITUD

            if sim["max_score"] < umbral:
                continue

            exp_id = sol.get("expediente", "").strip()

            # 4. Deduplicación: no crear alerta si ya existe y no está resuelta
            if exp_id and _expediente_ya_alertado(exp_id, marca.id, user_id, db):
                _log(f"[DUP] '{marca.nombre}' ↔ '{sol['denominacion']}' — ya alertado")
                continue

            # Nueva alerta
            nivel = _nivel_desde_score(sim["max_score"])
            alerta = Alerta(
                user_id              = user_id,
                marca_id             = marca.id,
                solicitud_nombre     = sol["denominacion"],
                expediente           = exp_id or None,
                fecha_solicitud      = sol.get("fecha"),
                titular_solicitante  = sol.get("titular"),
                score                = float(sim["max_score"]),
                nivel                = nivel,
                metodo               = sim.get("metodo_ganador"),
                scores_detalle       = {k: v for k, v in sim.items() if k != "metodo_ganador"},
                notificada           = False,
                resuelta             = False,
                detectado_el         = datetime.utcnow(),
            )
            db.add(alerta)
            alertas_nuevas += 1

            # Registrar expediente en tabla global
            if exp_id:
                _registrar_expediente(
                    exp_id,
                    sol["denominacion"],
                    sol.get("fecha", ""),
                    sol.get("titular", ""),
                    db,
                )
                expedientes_set.add(exp_id)

            _log(f"[{sim['max_score']}%] '{marca.nombre}' ↔ '{sol['denominacion']}' ({nivel.value})")

    db.flush()  # Fuerza IDs antes del commit final (lo hace el router)

    # 5. Notificaciones
    if notificar and alertas_nuevas > 0:
        try:
            from services.email_service import enviar_resumen_alertas
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.email_notif and user.email:
                alertas_pendientes = db.query(Alerta).filter(
                    Alerta.user_id   == user_id,
                    Alerta.notificada == False,
                    Alerta.resuelta   == False,
                ).all()
                enviar_resumen_alertas(user, alertas_pendientes)
                for a in alertas_pendientes:
                    a.notificada    = True
                    a.notificada_el = datetime.utcnow()
                _log(f"Email enviado a {user.email} con {len(alertas_pendientes)} alertas.")
        except Exception as e:
            _log(f"Error enviando email: {e}")

    _log(f"Finalizado: {alertas_nuevas} alertas nuevas, {len(expedientes_set)} expedientes procesados.")

    return {
        "marcas_vigiladas": len(marcas),
        "alertas_nuevas":   alertas_nuevas,
        "expedientes_proc": len(solicitudes),
        "log":              "\n".join(log_lines),
    }
