"""
Scheduler automático — APScheduler para vigilancia periódica del INPI.

Corre semanalmente (por defecto: lunes 08:00 hora Argentina) para todos
los usuarios activos con marcas. Cada usuario es un job independiente.

Configurado en core/config.py:
  SCHEDULER_CRON_DAY_OF_WEEK = "mon"
  SCHEDULER_CRON_HOUR        = 8
  SCHEDULER_CRON_MINUTE      = 0
"""

import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory      import MemoryJobStore
from apscheduler.executors.pool        import ThreadPoolExecutor
from apscheduler.triggers.cron         import CronTrigger

log = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


# ─────────────────────────────────────────────────────────────────────────────
# JOB FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def _job_vigilancia_global():
    """
    Job maestro: itera sobre todos los usuarios activos con marcas
    y ejecuta el motor INPI para cada uno.
    """
    from database     import SessionLocal
    from models       import User, Marca, EjecucionMonitor
    from services.inpi_service import ejecutar_para_usuario

    db = SessionLocal()
    try:
        # Usuarios activos que tienen al menos una marca activa
        usuarios_con_marcas = (
            db.query(User)
            .join(Marca, Marca.user_id == User.id)
            .filter(User.is_active == True, Marca.activa == True)
            .distinct()
            .all()
        )

        log.info(f"[Scheduler] Iniciando run para {len(usuarios_con_marcas)} usuarios.")

        for user in usuarios_con_marcas:
            run = EjecucionMonitor(
                user_id          = user.id,
                modo             = "real",
                estado           = "corriendo",
                marcas_vigiladas = 0,
                alertas_nuevas   = 0,
                expedientes_proc = 0,
                iniciada_el      = datetime.utcnow(),
            )
            db.add(run)
            db.commit()
            db.refresh(run)

            try:
                result = ejecutar_para_usuario(
                    user_id   = user.id,
                    modo      = "real",
                    notificar = user.email_notif,
                    db        = db,
                )
                run.estado           = "completado"
                run.marcas_vigiladas = result.get("marcas_vigiladas", 0)
                run.alertas_nuevas   = result.get("alertas_nuevas", 0)
                run.expedientes_proc = result.get("expedientes_proc", 0)
                run.log_output       = result.get("log", "")
                run.finalizada_el    = datetime.utcnow()

                log.info(
                    f"[Scheduler] user_id={user.id} → "
                    f"{run.alertas_nuevas} alertas / {run.marcas_vigiladas} marcas"
                )

            except Exception as e:
                run.estado        = "error"
                run.error_msg     = str(e)[:2000]
                run.finalizada_el = datetime.utcnow()
                log.error(f"[Scheduler] Error en user_id={user.id}: {e}")

            db.commit()

    except Exception as e:
        log.error(f"[Scheduler] Error general en job maestro: {e}")
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# INIT / SHUTDOWN
# ─────────────────────────────────────────────────────────────────────────────

def iniciar_scheduler():
    """
    Crea e inicia el BackgroundScheduler.
    Llamado en el evento `startup` de FastAPI (main.py).
    """
    global _scheduler

    from core.config import get_settings
    settings = get_settings()

    jobstores  = {"default": MemoryJobStore()}
    executors  = {"default": ThreadPoolExecutor(max_workers=2)}
    job_defaults = {"coalesce": True, "max_instances": 1}

    _scheduler = BackgroundScheduler(
        jobstores    = jobstores,
        executors    = executors,
        job_defaults = job_defaults,
        timezone     = "America/Argentina/Cordoba",
    )

    trigger = CronTrigger(
        day_of_week = settings.SCHEDULER_CRON_DAY_OF_WEEK,
        hour        = settings.SCHEDULER_CRON_HOUR,
        minute      = settings.SCHEDULER_CRON_MINUTE,
        timezone    = "America/Argentina/Cordoba",
    )

    _scheduler.add_job(
        func     = _job_vigilancia_global,
        trigger  = trigger,
        id       = "vigilancia_inpi",
        name     = "Vigilancia INPI — todos los usuarios",
        replace_existing = True,
    )

    _scheduler.start()
    log.info(
        f"Scheduler iniciado: "
        f"cada {settings.SCHEDULER_CRON_DAY_OF_WEEK} "
        f"a las {settings.SCHEDULER_CRON_HOUR:02d}:{settings.SCHEDULER_CRON_MINUTE:02d} (ART)"
    )


def detener_scheduler():
    """Llamado en el evento `shutdown` de FastAPI."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("Scheduler detenido.")


def get_proxima_ejecucion() -> datetime | None:
    """Retorna el próximo datetime de ejecución (para el dashboard)."""
    global _scheduler
    if not _scheduler:
        return None
    jobs = _scheduler.get_jobs()
    if not jobs:
        return None
    return jobs[0].next_run_time
