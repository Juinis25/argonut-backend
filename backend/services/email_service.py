"""
Servicio de email para notificaciones de alertas.

Soporte dual:
  - SendGrid (recomendado para producción)
  - SMTP estándar (Gmail, Zoho, etc.) como fallback

Configurado en core/config.py vía variables de entorno.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from typing import List

from core.config import get_settings

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATES
# ─────────────────────────────────────────────────────────────────────────────

def _html_resumen(user_nombre: str, alertas: list) -> str:
    """Genera el HTML del email de resumen de alertas."""
    nombre   = user_nombre or "Usuario"
    n_alertas = len(alertas)
    criticas  = [a for a in alertas if a.nivel.value == "critica"]
    altas     = [a for a in alertas if a.nivel.value == "alta"]
    medias    = [a for a in alertas if a.nivel.value == "media"]

    filas = ""
    for a in sorted(alertas, key=lambda x: x.score, reverse=True):
        color = "#dc3545" if a.nivel.value == "critica" else ("#fd7e14" if a.nivel.value == "alta" else "#ffc107")
        filas += f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #dee2e6">{a.solicitud_nombre}</td>
          <td style="padding:8px;border-bottom:1px solid #dee2e6">{a.expediente or '—'}</td>
          <td style="padding:8px;border-bottom:1px solid #dee2e6">{a.score:.0f}%</td>
          <td style="padding:8px;border-bottom:1px solid #dee2e6">
            <span style="background:{color};color:#fff;padding:2px 8px;border-radius:4px;font-size:12px">
              {a.nivel.value.upper()}
            </span>
          </td>
        </tr>"""

    return f"""
<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;max-width:640px;margin:auto;color:#333">
  <div style="background:#1a1a2e;padding:24px;text-align:center">
    <h1 style="color:#fff;margin:0;font-size:22px">🔍 Argonut · Vigilancia de Marcas</h1>
    <p style="color:#aaa;margin:4px 0 0">INPI Argentina</p>
  </div>

  <div style="padding:24px">
    <p>Hola <strong>{nombre}</strong>,</p>
    <p>Tu monitor de marcas detectó <strong>{n_alertas} alerta(s) nueva(s)</strong>
       en la última ejecución.</p>

    <div style="display:flex;gap:12px;margin:20px 0">
      <div style="flex:1;background:#fff5f5;border-left:4px solid #dc3545;padding:12px;border-radius:4px">
        <div style="font-size:24px;font-weight:bold;color:#dc3545">{len(criticas)}</div>
        <div style="font-size:12px;color:#666">CRÍTICAS</div>
      </div>
      <div style="flex:1;background:#fff8f0;border-left:4px solid #fd7e14;padding:12px;border-radius:4px">
        <div style="font-size:24px;font-weight:bold;color:#fd7e14">{len(altas)}</div>
        <div style="font-size:12px;color:#666">ALTAS</div>
      </div>
      <div style="flex:1;background:#fffdf0;border-left:4px solid #ffc107;padding:12px;border-radius:4px">
        <div style="font-size:24px;font-weight:bold;color:#ffc107">{len(medias)}</div>
        <div style="font-size:12px;color:#666">MEDIAS</div>
      </div>
    </div>

    <table style="width:100%;border-collapse:collapse;font-size:14px">
      <thead>
        <tr style="background:#f8f9fa">
          <th style="padding:10px;text-align:left;border-bottom:2px solid #dee2e6">Solicitud INPI</th>
          <th style="padding:10px;text-align:left;border-bottom:2px solid #dee2e6">Expediente</th>
          <th style="padding:10px;text-align:left;border-bottom:2px solid #dee2e6">Score</th>
          <th style="padding:10px;text-align:left;border-bottom:2px solid #dee2e6">Nivel</th>
        </tr>
      </thead>
      <tbody>{filas}</tbody>
    </table>

    <div style="margin-top:24px;text-align:center">
      <a href="https://argonut.ar/dashboard"
         style="background:#1a1a2e;color:#fff;padding:12px 24px;
                border-radius:6px;text-decoration:none;font-weight:bold">
        Ver alertas en el dashboard →
      </a>
    </div>

    <p style="margin-top:24px;font-size:12px;color:#999">
      Las alertas críticas (≥90%) requieren acción dentro de los 30 días hábiles
      desde la publicación en el Boletín de Marcas del INPI (Ley 22.362, Art. 12).<br><br>
      Este email fue enviado automáticamente por Argonut.
      <a href="https://argonut.ar/dashboard" style="color:#999">Gestionar notificaciones</a>
    </p>
  </div>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# BACKENDS DE ENVÍO
# ─────────────────────────────────────────────────────────────────────────────

def _enviar_smtp(to_email: str, subject: str, html_body: str):
    """Envía via SMTP estándar (Gmail con App Password, Zoho, etc.)."""
    settings = get_settings()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = settings.SMTP_FROM
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())


def _enviar_sendgrid(to_email: str, subject: str, html_body: str):
    """Envía via SendGrid API (recomendado para volumen y deliverability)."""
    import sendgrid
    from sendgrid.helpers.mail import Mail

    settings = get_settings()
    sg       = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
    mail     = Mail(
        from_email    = settings.SENDGRID_FROM_EMAIL,
        to_emails     = to_email,
        subject       = subject,
        html_content  = html_body,
    )
    response = sg.send(mail)
    if response.status_code not in (200, 201, 202):
        raise RuntimeError(f"SendGrid error: {response.status_code} — {response.body}")


def _enviar_email(to_email: str, subject: str, html_body: str):
    """
    Selecciona el backend de envío según la configuración disponible.
    Prioriza SendGrid si hay API key, cae a SMTP si no.
    """
    settings = get_settings()

    if settings.SENDGRID_API_KEY:
        _enviar_sendgrid(to_email, subject, html_body)
    elif settings.SMTP_HOST and settings.SMTP_USER:
        _enviar_smtp(to_email, subject, html_body)
    else:
        log.warning("Sin backend de email configurado (SENDGRID_API_KEY o SMTP_HOST). Email no enviado.")


# ─────────────────────────────────────────────────────────────────────────────
# API PÚBLICA
# ─────────────────────────────────────────────────────────────────────────────

def enviar_resumen_alertas(user, alertas: list):
    """
    Envía al usuario un resumen HTML con sus alertas sin notificar.

    Args:
        user: instancia del modelo User (necesita .email, .nombre)
        alertas: lista de instancias Alerta
    """
    if not alertas:
        return

    subject   = f"⚠️ Argonut: {len(alertas)} alerta(s) nueva(s) en tu vigilancia de marcas"
    html_body = _html_resumen(user.nombre, alertas)

    try:
        _enviar_email(user.email, subject, html_body)
        log.info(f"Email de alertas enviado a {user.email} ({len(alertas)} alertas)")
    except Exception as e:
        log.error(f"Error enviando email a {user.email}: {e}")
        raise


def enviar_email_bienvenida(user):
    """Bienvenida al registrarse. Simple, sin dependencia de alertas."""
    nombre = user.nombre or "nuevo usuario"
    html   = f"""
<!DOCTYPE html>
<html lang="es">
<body style="font-family:Arial,sans-serif;max-width:560px;margin:auto;color:#333;padding:24px">
  <h2>👋 Bienvenido/a a Argonut, {nombre}</h2>
  <p>Tu cuenta fue creada exitosamente. Ya podés empezar a vigilar tus marcas en el INPI Argentina.</p>
  <p>
    <a href="https://argonut.ar/dashboard"
       style="background:#1a1a2e;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none">
      Ir al dashboard →
    </a>
  </p>
  <p style="font-size:12px;color:#999;margin-top:24px">Argonut · argonut.ar</p>
</body>
</html>"""
    try:
        _enviar_email(user.email, "Bienvenido/a a Argonut 🔍", html)
    except Exception as e:
        log.warning(f"Email de bienvenida no enviado a {user.email}: {e}")
