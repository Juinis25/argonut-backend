# Argonut — Deploy en Railway

Guía completa para llevar el backend a producción en Railway desde cero.

---

## Prerequisitos

- Cuenta en [railway.app](https://railway.app) (plan Hobby ≥ $5/mes — necesario para PostgreSQL)
- Repo en GitHub con el código del proyecto
- Python 3.11+ local (para generar el SECRET_KEY)

---

## Paso 1 — Preparar el repo en GitHub

Si aún no lo subiste:

```bash
cd Argonut/backend

# Inicializar git (si no existe)
git init
git add .
git commit -m "feat: argonut backend inicial"

# Crear repo en GitHub (via gh CLI o manualmente en github.com)
gh repo create argonut-backend --private --source=. --push
# o si ya lo tenés:
git remote add origin https://github.com/TU_USUARIO/argonut-backend.git
git push -u origin main
```

> **El `.gitignore` ya excluye `.env`** — verificá que el archivo `.env` NO aparezca en `git status` antes de hacer push.

---

## Paso 2 — Crear proyecto en Railway

1. Ir a [railway.app/new](https://railway.app/new)
2. **Deploy from GitHub repo** → seleccionar `argonut-backend`
3. En **Settings → Source**:
   - **Root Directory**: `backend` ← importante si el repo tiene la carpeta `backend/`
   - Si pushaste directamente la carpeta `backend/` como raíz del repo, dejalo vacío
4. Railway detecta Python automáticamente via `nixpacks.toml`

---

## Paso 3 — Agregar PostgreSQL

1. En el dashboard del proyecto → **+ New** → **Database** → **PostgreSQL**
2. Railway aprovisiona la DB y **inyecta `DATABASE_URL` automáticamente** en el servicio
3. No hay que configurar nada más — `database.py` ya maneja el formato `postgres://` → `postgresql://`

---

## Paso 4 — Configurar variables de entorno

En **Settings → Variables** del servicio, agregar:

| Variable | Valor |
|---|---|
| `SECRET_KEY` | Generá con `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DEBUG` | `False` |
| `FRONTEND_URL` | La URL que Railway asigne (o tu dominio, ej: `https://argonut.ar`) |
| `EMAIL_BACKEND` | `smtp` o `sendgrid` |
| `SMTP_USER` | Tu email de Gmail |
| `SMTP_PASSWORD` | App Password de Google (no tu contraseña normal) |
| `UMBRAL_SIMILITUD` | `75` |

Las variables INPI y Scheduler ya tienen defaults correctos en `config.py` — no hace falta agregarlas a menos que quieras cambiar algo.

`DATABASE_URL` la inyecta Railway automáticamente — **no la pongas a mano**.

---

## Paso 5 — Deploy

Railway deployea automáticamente al hacer push. Para forzar uno manual:

```bash
# Desde el dashboard: botón "Deploy" en la última build
# O via CLI:
railway up
```

El proceso de build hace:
1. `pip install -r requirements.txt` (nixpacks detecta `requirements.txt`)
2. Arranca `uvicorn main:app --host 0.0.0.0 --port $PORT` (single worker — requerido para APScheduler)
3. Railway verifica `GET /health` → espera `{"status": "ok"}`
4. Al startup: `create_tables()` crea las tablas en PostgreSQL + APScheduler arranca

---

## Paso 6 — Verificar

Una vez deployado, la URL pública de Railway (ej: `https://argonut-backend.up.railway.app`):

```bash
# Health check
curl https://argonut-backend.up.railway.app/health
# → {"status":"ok","app":"Argonut API"}

# Docs interactivos
# Abrir en browser: https://argonut-backend.up.railway.app/docs
```

---

## Paso 7 — Primer usuario admin

Desde Swagger (`/docs`) o curl:

```bash
# Registrar usuario
curl -X POST https://TU_URL.up.railway.app/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"vos@ejemplo.com","password":"clave-segura","nombre":"Admin"}'

# Login → obtenés el JWT
curl -X POST https://TU_URL.up.railway.app/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"vos@ejemplo.com","password":"clave-segura"}'
```

---

## Dominio personalizado (opcional)

1. Railway → **Settings → Networking → Custom Domain**
2. Agregar `api.argonut.ar` (o el que tengas)
3. En tu DNS: crear registro CNAME apuntando al dominio de Railway
4. Actualizar `FRONTEND_URL` en las variables de Railway si cambiaste el dominio

---

## Actualizaciones futuras

Cada `git push origin main` trigerea un nuevo deploy automático en Railway. Zero downtime por defecto.

```bash
# Flujo normal de trabajo
git add .
git commit -m "fix: descripción del cambio"
git push origin main
# Railway deploya solo
```

---

## Troubleshooting

**Build falla en `psycopg2`**
→ El `nixpacks.toml` ya incluye `postgresql_15` para las libs del sistema. Si sigue fallando, reemplazá `psycopg2-binary` en `requirements.txt` (ya está binary, no debería pasar).

**`DATABASE_URL` no encontrada**
→ Verificar que el servicio PostgreSQL esté en el mismo proyecto Railway y que las variables estén linkeadas. En **Variables**, buscá que `DATABASE_URL` aparezca como "reference" del plugin PostgreSQL.

**`RuntimeError: asyncio event loop`**
→ Ya corregido en `inpi_service.py` con el wrapper `asyncio.new_event_loop()`. Si reaparece, es que algo está llamando `asyncio.run()` desde un endpoint async.

**Scheduler no dispara**
→ Railway no tiene cron externo — el APScheduler corre dentro del mismo proceso uvicorn. El `railway.toml` ya usa single worker para evitar instancias duplicadas. Si querés escalar a múltiples workers en el futuro, la variable `SCHEDULER_ENABLED=false` en los workers secundarios es el mecanismo de control. Para escala real, migrar el scheduler a un servicio separado en Railway es la arquitectura correcta.

**Timeout en el health check**
→ Aumentar `healthcheckTimeout` en `railway.toml` (actualmente 30s). El primer startup puede tardar más si hay muchas tablas que crear.
