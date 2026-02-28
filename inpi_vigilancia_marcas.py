"""
╔══════════════════════════════════════════════════════════════════════════════╗
║     INPI ARGENTINA — SISTEMA DE VIGILANCIA DE MARCAS v2.0 (Producción)     ║
║     Con persistencia, deduplicación y notificaciones por email/WhatsApp     ║
╚══════════════════════════════════════════════════════════════════════════════╝

NOVEDADES v2.0:
  + Módulo 6: Persistencia y deduplicación (no alerta dos veces el mismo expediente)
  + Módulo 7: Notificaciones por email (SendGrid) y WhatsApp (Twilio)
  + Credenciales leídas desde variables de entorno → compatible con GitHub Secrets
  + Compatible con GitHub Actions (ejecución headless en Ubuntu)

DEPENDENCIAS:
    pip install -r requirements.txt
    python -m playwright install chromium

EJECUCIÓN:
    python inpi_vigilancia_marcas.py           # Modo real
    python inpi_vigilancia_marcas.py --demo    # Modo demo
"""

import json
import csv
import os
import re
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from fuzzywuzzy import fuzz

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN GLOBAL
# ─────────────────────────────────────────────────────────────────────────────

UMBRAL_SIMILITUD = 75

ARCHIVO_CLIENTES = "marcas_clientes.json"
ARCHIVO_BOLETIN  = "boletin_cache.json"
ARCHIVO_LOG_PROC = "procesados_historico.json"     # Log de deduplicación (se commitea a GitHub)
ARCHIVO_REPORTE  = f"reporte_alertas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
ARCHIVO_LOG      = "inpi_monitor.log"

INPI_BUSQUEDA_URL = "https://portaltramites.inpi.gob.ar/marcas/busqueda"

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(ARCHIVO_LOG),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# MÓDULO 1: BASE DE DATOS DE CLIENTES
# ═════════════════════════════════════════════════════════════════════════════

def inicializar_base_clientes():
    if Path(ARCHIVO_CLIENTES).exists():
        log.info(f"Base de clientes existente: {ARCHIVO_CLIENTES}")
        return
    datos_ejemplo = [
        {"nombre": "MERCADOLIBRE",      "clase": 35, "titular": "MercadoLibre SRL",   "contacto": "legal@example.com",  "notas": "Variantes fonéticas"},
        {"nombre": "NARANJA X",         "clase": 36, "titular": "Naranja X SA",        "contacto": "marcas@example.com", "notas": "Fintech, alta prioridad"},
        {"nombre": "LA PATAGONIA",      "clase": 43, "titular": "Gastronomía del Sur", "contacto": "info@example.com",   "notas": "Zona Córdoba"},
        {"nombre": "INFLUENCER EJEMPLO","clase": 41, "titular": "Persona Física",      "contacto": "agente@example.com", "notas": "Marca personal"},
    ]
    with open(ARCHIVO_CLIENTES, "w", encoding="utf-8") as f:
        json.dump(datos_ejemplo, f, ensure_ascii=False, indent=2)
    log.info(f"✅ Base de clientes creada. Editá {ARCHIVO_CLIENTES} con tus clientes reales.")


def cargar_clientes() -> list[dict]:
    inicializar_base_clientes()
    with open(ARCHIVO_CLIENTES, "r", encoding="utf-8") as f:
        clientes = json.load(f)
    log.info(f"📋 {len(clientes)} marcas de clientes cargadas.")
    return clientes


# ═════════════════════════════════════════════════════════════════════════════
# MÓDULO 2: SCRAPING DEL BOLETÍN INPI
# ═════════════════════════════════════════════════════════════════════════════

async def scrape_inpi_playwright(clases_a_buscar: list[int]) -> list[dict]:
    """
    Scraping real del portal INPI con Playwright (Chromium headless).
    Si el portal cambia su estructura, ajustar los selectores marcados con # ← SELECTOR.
    """
    from playwright.async_api import async_playwright
    solicitudes = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page    = await browser.new_page()
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        })

        for clase in clases_a_buscar:
            log.info(f"   🔍 Scrapeando Clase {clase}...")
            try:
                await page.goto(INPI_BUSQUEDA_URL, wait_until="networkidle", timeout=30000)
                await page.select_option('select[name="clase"]',  str(clase))    # ← SELECTOR
                await page.select_option('select[name="estado"]', "EN_TRAMITE")  # ← SELECTOR
                await page.select_option('select[name="orden"]',  "FECHA_DESC")  # ← SELECTOR
                await page.click('button[type="submit"]')                        # ← SELECTOR
                await page.wait_for_selector('.resultado-marca', timeout=15000)  # ← SELECTOR
                items = await page.query_selector_all('.resultado-marca')        # ← SELECTOR

                for item in items[:50]:
                    try:
                        denom    = await item.query_selector('.denominacion')    # ← SELECTOR
                        exp      = await item.query_selector('.expediente')      # ← SELECTOR
                        fecha_el = await item.query_selector('.fecha')           # ← SELECTOR
                        tit_el   = await item.query_selector('.titular')         # ← SELECTOR
                        solicitudes.append({
                            "denominacion": (await denom.inner_text()).strip().upper()   if denom    else "N/D",
                            "expediente":   (await exp.inner_text()).strip()             if exp      else "N/D",
                            "fecha":        (await fecha_el.inner_text()).strip()        if fecha_el else "N/D",
                            "titular":      (await tit_el.inner_text()).strip()          if tit_el   else "N/D",
                            "clase": clase,
                        })
                    except Exception as e:
                        log.warning(f"   ⚠️  Error parseando ítem: {e}")

                cnt = len([s for s in solicitudes if s['clase'] == clase])
                log.info(f"   ✅ Clase {clase}: {cnt} solicitudes.")

            except Exception as e:
                log.error(f"   ❌ Error en clase {clase}: {e}")
                solicitudes.extend(_generar_datos_demo(clase))

        await browser.close()
    return solicitudes


def _generar_datos_demo(clase: int) -> list[dict]:
    """Solicitudes simuladas para testing sin acceso real al INPI."""
    demo = [
        {"denominacion": "MERCADO LIBRE",       "expediente": "Nº 4.123.456", "fecha": datetime.now().strftime("%d/%m/%Y"), "titular": "Empresa Desconocida SA", "clase": 35},
        {"denominacion": "MERCADOLIBRE SHOP",   "expediente": "Nº 4.123.457", "fecha": datetime.now().strftime("%d/%m/%Y"), "titular": "Competidor SRL",         "clase": 35},
        {"denominacion": "NARANJAX",            "expediente": "Nº 4.123.458", "fecha": datetime.now().strftime("%d/%m/%Y"), "titular": "Fintech Paralela SA",     "clase": 36},
        {"denominacion": "LA PATAGÓNICA",       "expediente": "Nº 4.123.459", "fecha": datetime.now().strftime("%d/%m/%Y"), "titular": "Resto del Sur SRL",       "clase": 43},
        {"denominacion": "MARCA SIN CONFLICTO", "expediente": "Nº 4.123.460", "fecha": datetime.now().strftime("%d/%m/%Y"), "titular": "Empresa Legítima SA",     "clase": clase},
        {"denominacion": "INFLUENCER EJMPLO",   "expediente": "Nº 4.123.461", "fecha": datetime.now().strftime("%d/%m/%Y"), "titular": "Squatter Digital",        "clase": 41},
    ]
    return [d for d in demo if d["clase"] == clase]


def cachear_boletin(solicitudes: list[dict]):
    cache = {"fecha_scraping": datetime.now().isoformat(), "total": len(solicitudes), "solicitudes": solicitudes}
    with open(ARCHIVO_BOLETIN, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    log.info(f"💾 Caché guardado: {len(solicitudes)} solicitudes.")


def cargar_cache_boletin() -> list[dict] | None:
    if not Path(ARCHIVO_BOLETIN).exists():
        return None
    with open(ARCHIVO_BOLETIN, "r", encoding="utf-8") as f:
        cache = json.load(f)
    if datetime.fromisoformat(cache["fecha_scraping"]).date() == datetime.now().date():
        log.info(f"✅ Usando caché del día: {cache['total']} solicitudes.")
        return cache["solicitudes"]
    return None


# ═════════════════════════════════════════════════════════════════════════════
# MÓDULO 3: LÓGICA DE COLISIONES
# ═════════════════════════════════════════════════════════════════════════════

def normalizar_nombre(nombre: str) -> str:
    import unicodedata
    nombre = nombre.upper().strip()
    nombre = unicodedata.normalize("NFD", nombre)
    nombre = "".join(c for c in nombre if unicodedata.category(c) != "Mn")
    return re.sub(r'\s+', ' ', nombre)


def calcular_similitud(m1: str, m2: str) -> dict:
    a, b = normalizar_nombre(m1), normalizar_nombre(m2)
    scores = {
        "ratio":            fuzz.ratio(a, b),
        "partial_ratio":    fuzz.partial_ratio(a, b),
        "token_sort_ratio": fuzz.token_sort_ratio(a, b),
        "token_set_ratio":  fuzz.token_set_ratio(a, b),
    }
    scores["max_score"]      = max(scores.values())
    scores["metodo_ganador"] = max((k for k in scores if k != "max_score"), key=lambda k: scores[k])
    return scores


def detectar_colisiones(clientes: list[dict], solicitudes: list[dict]) -> list[dict]:
    alertas = []
    log.info(f"🔬 Analizando {len(clientes)} marcas × {len(solicitudes)} solicitudes...")
    for cliente in clientes:
        for solicitud in solicitudes:
            if int(cliente["clase"]) != int(solicitud["clase"]):
                continue
            sim = calcular_similitud(cliente["nombre"], solicitud["denominacion"])
            if sim["max_score"] >= UMBRAL_SIMILITUD:
                alertas.append({
                    "marca_cliente":       cliente["nombre"],
                    "clase":               cliente["clase"],
                    "titular_cliente":     cliente.get("titular", "N/D"),
                    "contacto":            cliente.get("contacto", "N/D"),
                    "solicitud_nombre":    solicitud["denominacion"],
                    "expediente":          solicitud["expediente"],
                    "fecha_solicitud":     solicitud["fecha"],
                    "titular_solicitante": solicitud.get("titular", "N/D"),
                    "score":               sim["max_score"],
                    "metodo":              sim["metodo_ganador"],
                    "scores_detalle":      sim,
                    "detectado_el":        datetime.now().strftime("%d/%m/%Y %H:%M"),
                })
                log.info(f"   🚨 [{sim['max_score']}%] '{cliente['nombre']}' ↔ '{solicitud['denominacion']}'")

    alertas.sort(key=lambda x: x["score"], reverse=True)
    log.info(f"✅ {len(alertas)} alertas detectadas.")
    return alertas


# ═════════════════════════════════════════════════════════════════════════════
# MÓDULO 4: REPORTE
# ═════════════════════════════════════════════════════════════════════════════

SEP = "═" * 72

def generar_reporte(alertas: list[dict], total_solicitudes: int) -> str:
    L = []
    now = datetime.now().strftime("%d/%m/%Y a las %H:%M hs")
    L += [SEP, "  SISTEMA DE VIGILANCIA DE MARCAS — INPI ARGENTINA",
          f"  Reporte generado el {now}", SEP, "",
          f"  Solicitudes analizadas: {total_solicitudes}",
          f"  Umbral de similitud:    {UMBRAL_SIMILITUD}%",
          f"  Alertas detectadas:     {len(alertas)}", ""]

    if not alertas:
        L += ["  ✅ Sin alertas. Ninguna solicitud supera el umbral.", "", SEP]
        return "\n".join(L)

    criticas = [a for a in alertas if a["score"] >= 90]
    if criticas:
        L += [f"  ⚠️  ALERTAS CRÍTICAS (≥ 90%): {len(criticas)} caso(s)",
              "  Requieren acción inmediata. Plazo: 30 días hábiles desde publicación.", ""]

    for i, a in enumerate(alertas, 1):
        prioridad = "🔴 CRÍTICA" if a["score"] >= 90 else ("🟡 ALTA" if a["score"] >= 80 else "🟠 MEDIA")
        L += [
            f"  {'─'*68}",
            f"  ALERTA #{i}  |  {prioridad}  |  Similitud: {a['score']}%",
            f"  {'─'*68}", "",
            f"  ALERTA: Posible conflicto entre [{a['marca_cliente']}] y [{a['solicitud_nombre']}]", "",
            f"  ▸ MARCA PROTEGIDA:   {a['marca_cliente']} (Clase {a['clase']}) — {a['titular_cliente']}",
            f"    Contacto:          {a['contacto']}",
            f"  ▸ NUEVA SOLICITUD:   {a['solicitud_nombre']}",
            f"    Expediente:        {a['expediente']} | Fecha: {a['fecha_solicitud']}",
            f"    Solicitante:       {a['titular_solicitante']}",
            f"  ▸ Scores:  ratio={a['scores_detalle']['ratio']}% | "
            f"partial={a['scores_detalle']['partial_ratio']}% | "
            f"token_sort={a['scores_detalle']['token_sort_ratio']}%", "",
        ]

    L += [SEP, "  PRÓXIMOS PASOS: portaltramites.inpi.gob.ar | Ley 22.362 Art. 12", SEP]
    return "\n".join(L)


def guardar_reporte(contenido: str):
    with open(ARCHIVO_REPORTE, "w", encoding="utf-8") as f:
        f.write(contenido)
    log.info(f"📄 Reporte: {ARCHIVO_REPORTE}")


def exportar_alertas_json(alertas: list[dict]) -> str:
    nombre = f"alertas_{datetime.now().strftime('%Y%m%d')}.json"
    with open(nombre, "w", encoding="utf-8") as f:
        json.dump(alertas, f, ensure_ascii=False, indent=2)
    return nombre


# ═════════════════════════════════════════════════════════════════════════════
# MÓDULO 6 (NUEVO): PERSISTENCIA Y DEDUPLICACIÓN
# ═════════════════════════════════════════════════════════════════════════════

def cargar_log_procesados() -> dict:
    """
    Carga el historial de expedientes ya alertados.

    Estructura canónica (v2.0):
    {
      "ultima_actualizacion": "2024-06-10T11:00:00",
      "expedientes_procesados": {
        "Nº 4.123.456": {
          "primera_deteccion": "2024-06-10",
          "alerta_enviada":    true,
          "score_maximo":      92,
          "marca_colisionada": "MERCADOLIBRE"
        }
      }
    }

    Nota: si el archivo existe con un esquema legacy (versiones < 2.0),
    se migra automáticamente al formato canónico sin perder datos.

    Este archivo se commitea automáticamente al repositorio de GitHub en cada
    ejecución, garantizando que la segunda ejecución recuerde lo que ya alertó.
    """
    _default = {"ultima_actualizacion": None, "expedientes_procesados": {}}

    if not Path(ARCHIVO_LOG_PROC).exists():
        return _default

    with open(ARCHIVO_LOG_PROC, "r", encoding="utf-8") as f:
        data = json.load(f)

    # ── Migración automática de esquema legacy (v1 usaba lista "procesados": [])
    if "expedientes_procesados" not in data:
        log.info("⚙️  Migrando log de procesados a esquema v2.0...")
        lista_legacy = data.get("procesados", [])
        expedientes_migrados = {}
        for exp in lista_legacy:
            if isinstance(exp, str):
                expedientes_migrados[exp] = {
                    "primera_deteccion": data.get("ultima_actualizacion", "desconocida")[:10],
                    "alerta_enviada":    True,
                    "score_maximo":      0,
                    "marca_colisionada": "migrado_desde_v1",
                }
        data = {
            "ultima_actualizacion": data.get("ultima_actualizacion"),
            "expedientes_procesados": expedientes_migrados,
        }
        log.info(f"✅ Migración completada: {len(expedientes_migrados)} expedientes preservados.")

    return data


def guardar_log_procesados(log_data: dict):
    """Persiste el log actualizado. Este archivo es commiteado por GitHub Actions."""
    log_data["ultima_actualizacion"] = datetime.now().isoformat()
    with open(ARCHIVO_LOG_PROC, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)
    n = len(log_data["expedientes_procesados"])
    log.info(f"💾 Log de procesados actualizado: {n} expedientes en historial.")


def filtrar_alertas_nuevas(alertas: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Separa alertas en:
      - nuevas:    expedientes nunca vistos → se notifican
      - conocidas: ya alertados en ejecuciones previas → se omiten

    El log de expedientes conocidos vive en marcas_procesadas_log.json
    que se commitea automáticamente a GitHub tras cada ejecución.
    """
    log_data   = cargar_log_procesados()
    procesados = log_data["expedientes_procesados"]

    nuevas    = []
    conocidas = []

    for alerta in alertas:
        exp = alerta["expediente"]
        if exp not in procesados:
            nuevas.append(alerta)
            procesados[exp] = {
                "primera_deteccion": datetime.now().strftime("%Y-%m-%d"),
                "alerta_enviada":    True,
                "score_maximo":      alerta["score"],
                "marca_colisionada": alerta["marca_cliente"],
                "solicitud":         alerta["solicitud_nombre"],
            }
        else:
            conocidas.append(alerta)
            log.info(f"   ⏭️  Conocido, omitido: {exp}")

    guardar_log_procesados(log_data)
    log.info(f"📊 Deduplicación: {len(nuevas)} nuevas | {len(conocidas)} ya conocidas.")
    return nuevas, conocidas


# ═════════════════════════════════════════════════════════════════════════════
# MÓDULO 7 (NUEVO): NOTIFICACIONES
# Credenciales leídas de variables de entorno → configuradas como GitHub Secrets
# ═════════════════════════════════════════════════════════════════════════════

def enviar_email_sendgrid(reporte_texto: str, alertas_nuevas: list[dict]) -> bool:
    """
    Envía reporte por email via SendGrid.

    Variables de entorno requeridas (configurar como GitHub Secrets):
      SENDGRID_API_KEY    → API key de SendGrid (plan gratuito: 100 emails/día)
      EMAIL_DESTINATARIO  → Destinatario del reporte
      EMAIL_REMITENTE     → Email verificado como sender en SendGrid
    """
    api_key      = os.getenv("SENDGRID_API_KEY")
    destinatario = os.getenv("EMAIL_DESTINATARIO")
    remitente    = os.getenv("EMAIL_REMITENTE")

    if not all([api_key, destinatario, remitente]):
        log.warning("⚠️  Email omitido: faltan SENDGRID_API_KEY / EMAIL_DESTINATARIO / EMAIL_REMITENTE.")
        return False

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        if not alertas_nuevas:
            asunto = "✅ INPI Monitor — Sin nuevas alertas esta semana"
        else:
            criticas = sum(1 for a in alertas_nuevas if a["score"] >= 90)
            asunto   = f"🚨 INPI Monitor — {len(alertas_nuevas)} alerta(s) nueva(s) ({criticas} crítica(s))"

        # Tabla HTML de alertas
        filas_html = ""
        for a in alertas_nuevas[:10]:
            color = "#cc0000" if a["score"] >= 90 else ("#e6ac00" if a["score"] >= 80 else "#e67300")
            filas_html += (
                f"<tr>"
                f"<td style='padding:8px;border-bottom:1px solid #eee;'>"
                f"<strong style='color:{color};'>{a['score']}%</strong></td>"
                f"<td style='padding:8px;border-bottom:1px solid #eee;'>{a['marca_cliente']}</td>"
                f"<td style='padding:8px;border-bottom:1px solid #eee;'>{a['solicitud_nombre']}</td>"
                f"<td style='padding:8px;border-bottom:1px solid #eee;'>{a['expediente']}</td>"
                f"<td style='padding:8px;border-bottom:1px solid #eee;'>{a['fecha_solicitud']}</td>"
                f"</tr>"
            )

        tabla_html = (
            "<table style='width:100%;border-collapse:collapse;'>"
            "<thead><tr style='background:#1a1a2e;color:white;'>"
            "<th style='padding:10px;'>Score</th>"
            "<th style='padding:10px;'>Marca Protegida</th>"
            "<th style='padding:10px;'>Nueva Solicitud</th>"
            "<th style='padding:10px;'>Expediente</th>"
            "<th style='padding:10px;'>Fecha</th>"
            f"</tr></thead><tbody>{filas_html}</tbody></table>"
            if alertas_nuevas else
            "<p style='color:green;'>✅ Sin nuevas colisiones esta semana.</p>"
        )

        html = f"""
        <html><body style="font-family:Arial,sans-serif;max-width:800px;margin:0 auto;padding:20px;">
          <h2 style="color:#1a1a2e;border-bottom:3px solid #e63946;padding-bottom:10px;">
            🔍 INPI Argentina — Vigilancia de Marcas
          </h2>
          <p style="color:#666;">Reporte: {datetime.now().strftime('%d/%m/%Y %H:%M hs')}</p>
          <div style="background:#f8f9fa;border-left:4px solid #e63946;padding:15px;margin:20px 0;">
            <strong>{len(alertas_nuevas)} alerta(s) nueva(s) detectada(s) esta semana.</strong>
          </div>
          {tabla_html}
          <hr style="margin:30px 0;">
          <pre style="background:#f8f9fa;padding:15px;font-size:11px;">{reporte_texto[:2500]}</pre>
          <p style="color:#999;font-size:11px;margin-top:20px;">
            INPI Monitor v2.0 — Ley 22.362 — portaltramites.inpi.gob.ar
          </p>
        </body></html>
        """

        msg = Mail(from_email=remitente, to_emails=destinatario, subject=asunto, html_content=html)
        sg  = SendGridAPIClient(api_key)
        res = sg.send(msg)

        if res.status_code in [200, 202]:
            log.info(f"✅ Email enviado → {destinatario} (HTTP {res.status_code})")
            return True
        else:
            log.error(f"❌ SendGrid HTTP {res.status_code}")
            return False

    except ImportError:
        log.warning("sendgrid no instalado. pip install sendgrid")
        return False
    except Exception as e:
        log.error(f"❌ Error SendGrid: {e}")
        return False


def enviar_whatsapp_twilio(alertas_nuevas: list[dict]) -> bool:
    """
    Envía resumen de alertas por WhatsApp via Twilio.

    Variables de entorno (GitHub Secrets):
      TWILIO_ACCOUNT_SID    → Account SID de tu cuenta Twilio
      TWILIO_AUTH_TOKEN     → Auth Token de Twilio
      TWILIO_WHATSAPP_FROM  → ej: whatsapp:+14155238886 (Twilio sandbox)
      TWILIO_WHATSAPP_TO    → ej: whatsapp:+5491112345678 (tu número)

    Sandbox gratuito: console.twilio.com → Messaging → WhatsApp → Sandbox
    """
    sid       = os.getenv("TWILIO_ACCOUNT_SID")
    token     = os.getenv("TWILIO_AUTH_TOKEN")
    from_num  = os.getenv("TWILIO_WHATSAPP_FROM")
    to_num    = os.getenv("TWILIO_WHATSAPP_TO")

    if not all([sid, token, from_num, to_num]):
        log.warning("⚠️  WhatsApp omitido: faltan credenciales Twilio.")
        return False

    if not alertas_nuevas:
        log.info("Sin alertas nuevas → no se envía WhatsApp (evitar spam semanal).")
        return True

    try:
        from twilio.rest import Client

        lineas = []
        for a in alertas_nuevas[:5]:
            emoji = "🔴" if a["score"] >= 90 else ("🟡" if a["score"] >= 80 else "🟠")
            lineas.append(f"{emoji} *{a['marca_cliente']}* ({a['score']}%)\n   → {a['solicitud_nombre']} | {a['expediente']}")

        cuerpo = (
            f"🔍 *INPI Monitor — {datetime.now().strftime('%d/%m/%Y')}*\n\n"
            f"*{len(alertas_nuevas)} alerta(s) nueva(s):*\n\n"
            + "\n\n".join(lineas)
            + ("\n\n_(y más — ver reporte en GitHub Actions)_" if len(alertas_nuevas) > 5 else "")
        )

        c   = Client(sid, token)
        msg = c.messages.create(body=cuerpo, from_=from_num, to=to_num)
        log.info(f"✅ WhatsApp enviado. SID: {msg.sid}")
        return True

    except ImportError:
        log.warning("twilio no instalado. pip install twilio")
        return False
    except Exception as e:
        log.error(f"❌ Error Twilio: {e}")
        return False


# ═════════════════════════════════════════════════════════════════════════════
# MÓDULO 8: ORQUESTADOR PRINCIPAL v2.0
# ═════════════════════════════════════════════════════════════════════════════

async def main(modo_demo: bool = False):
    """
    Pipeline completo de producción:
      1 → Cargar clientes
      2 → Scraping INPI (o demo)
      3 → Detectar colisiones
      4 → Deduplicar (filtrar expedientes ya alertados)
      5 → Generar y guardar reporte
      6 → Notificar (email + WhatsApp) solo alertas nuevas
      7 → Persistir log (commiteado a GitHub por el workflow)
    """
    print(f"\n{SEP}")
    print("  INPI ARGENTINA — VIGILANCIA DE MARCAS v2.0")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M hs')}")
    print(f"{SEP}\n")

    # ── 1. Clientes
    clientes = cargar_clientes()
    if not clientes:
        log.error("Sin clientes cargados.")
        return

    clases = list(set(int(c["clase"]) for c in clientes))
    log.info(f"📌 Clases: {clases}")

    # ── 2. Solicitudes INPI
    solicitudes = cargar_cache_boletin()
    if not solicitudes:
        if modo_demo:
            log.info("🎭 MODO DEMO")
            solicitudes = []
            for clase in clases:
                solicitudes.extend(_generar_datos_demo(clase))
        else:
            try:
                solicitudes = await scrape_inpi_playwright(clases)
            except Exception as e:
                log.error(f"Scraping fallido ({e}). Activando demo.")
                solicitudes = []
                for clase in clases:
                    solicitudes.extend(_generar_datos_demo(clase))
        cachear_boletin(solicitudes)

    # ── 3. Colisiones
    alertas_totales = detectar_colisiones(clientes, solicitudes)

    # ── 4. Deduplicación
    alertas_nuevas, alertas_conocidas = filtrar_alertas_nuevas(alertas_totales)

    # ── 5. Reporte
    reporte = generar_reporte(alertas_totales, len(solicitudes))
    print("\n" + reporte)
    guardar_reporte(reporte)
    exportar_alertas_json(alertas_totales)

    # ── 6. Notificaciones (solo alertas nuevas)
    enviar = os.getenv("ENVIAR_EMAIL", "true").lower() == "true"
    if enviar:
        log.info("📧 Enviando notificaciones...")
        email_ok = enviar_email_sendgrid(reporte, alertas_nuevas)
        wa_ok    = enviar_whatsapp_twilio(alertas_nuevas)
        log.info(f"   Email: {'✅' if email_ok else '⚠️ no configurado'} | WA: {'✅' if wa_ok else '⚠️ no configurado'}")

    # ── Resumen
    print(f"\n{'─'*72}")
    print(f"  Solicitudes analizadas:  {len(solicitudes)}")
    print(f"  Alertas totales:         {len(alertas_totales)}")
    print(f"  Alertas NUEVAS:          {len(alertas_nuevas)}  ← solo estas disparan notificación")
    print(f"  Alertas ya conocidas:    {len(alertas_conocidas)}")
    print(f"  Reporte:                 {ARCHIVO_REPORTE}")
    print(f"{'─'*72}\n")


# ═════════════════════════════════════════════════════════════════════════════
# PUNTO DE ENTRADA
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="INPI Argentina — Vigilancia de Marcas v2.0",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--modo",
        choices=["real", "demo"],
        default="real",
        help="Modo de ejecución:\n  real → scraping real del portal INPI\n  demo → datos simulados (testing sin acceso)"
    )
    parser.add_argument(
        "--notificar",
        choices=["true", "false"],
        default="true",
        help="Enviar notificaciones por email/WhatsApp (default: true)"
    )
    # Compatibilidad retroactiva: --demo sigue funcionando para quienes lo usan localmente
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Alias de --modo demo (compatibilidad con versiones anteriores)"
    )

    args, _ = parser.parse_known_args()

    # --demo legacy tiene precedencia si se pasa explícitamente
    modo_demo = args.demo or (args.modo == "demo")

    # --notificar false sobreescribe la variable de entorno
    if args.notificar == "false":
        os.environ["ENVIAR_EMAIL"] = "false"

    if modo_demo:
        print("\n[MODO DEMO ACTIVADO]\n")

    asyncio.run(main(modo_demo=modo_demo))
