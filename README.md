# INPI Argentina — Sistema de Vigilancia de Marcas
## Guía de Instalación, Ejecución y Automatización

---

## 1. INSTALACIÓN (5 minutos)

### Requisitos
- Python 3.10 o superior
- Terminal (Linux/Mac) o CMD/PowerShell (Windows)

### Instalar dependencias

```bash
pip install playwright beautifulsoup4 requests fuzzywuzzy python-Levenshtein PyPDF2
python -m playwright install chromium
```

---

## 2. ESTRUCTURA DE ARCHIVOS

```
inpi_monitor/
├── inpi_vigilancia_marcas.py   ← Script principal
├── marcas_clientes.json        ← Tu base de clientes (se crea automáticamente)
├── boletin_cache.json          ← Caché del boletín (se genera al correr)
├── reporte_alertas_XXXXXX.txt  ← Reportes generados
├── alertas_YYYYMMDD.json       ← Alertas en JSON (para integraciones)
└── inpi_monitor.log            ← Log de ejecuciones
```

---

## 3. CONFIGURACIÓN DE CLIENTES

Al ejecutar por primera vez, se crea `marcas_clientes.json` con ejemplos.  
**Editarlo** con tus clientes reales:

```json
[
  {
    "nombre": "TU MARCA AQUÍ",
    "clase": 35,
    "titular": "Nombre del Titular SA",
    "contacto": "email@cliente.com",
    "notas": "Observaciones relevantes"
  },
  {
    "nombre": "OTRA MARCA",
    "clase": 43,
    "titular": "Otro Cliente SRL",
    "contacto": "otro@email.com",
    "notas": ""
  }
]
```

### Referencia de Clases (las más comunes)
| Clase | Descripción |
|-------|-------------|
| 35 | Publicidad, gestión comercial, e-commerce |
| 36 | Seguros, finanzas, servicios bancarios |
| 38 | Telecomunicaciones |
| 41 | Educación, entretenimiento, contenido digital |
| 42 | Tecnología, software, SaaS |
| 43 | Restaurantes, servicios de alimentos |
| 44 | Servicios médicos, salud |
| 45 | Servicios legales, seguridad |

---

## 4. EJECUCIÓN

### Modo Demo (testing sin acceso al INPI)
```bash
python inpi_vigilancia_marcas.py --demo
```
Genera alertas con datos simulados. Ideal para verificar que todo funciona.

### Modo Real (scraping del portal INPI)
```bash
python inpi_vigilancia_marcas.py
```
Accede al portal del INPI. Si falla la conexión, activa modo demo automáticamente.

---

## 5. EJECUCIÓN EN GOOGLE COLAB

```python
# Celda 1: Instalación
!pip install playwright beautifulsoup4 requests fuzzywuzzy python-Levenshtein -q
!playwright install chromium

# Celda 2: Subir tu archivo de clientes
from google.colab import files
uploaded = files.upload()  # Subir marcas_clientes.json

# Celda 3: Ejecutar
!python inpi_vigilancia_marcas.py --demo

# Celda 4: Descargar reportes
import glob
reportes = glob.glob('reporte_alertas_*.txt')
for r in reportes:
    files.download(r)
```

---

## 6. AUTOMATIZACIÓN SEMANAL

### Opción A: cron (Linux/Mac) — RECOMENDADO

Abre la configuración del cron:
```bash
crontab -e
```

Agrega esta línea (ejecuta todos los lunes a las 8:00 AM):
```bash
0 8 * * 1 /usr/bin/python3 /ruta/completa/al/script/inpi_vigilancia_marcas.py >> /ruta/logs/inpi_cron.log 2>&1
```

Verificar que el cron está activo:
```bash
crontab -l
```

---

### Opción B: Tarea Programada (Windows)

1. Abrir "Programador de Tareas" (Task Scheduler)
2. "Crear tarea básica"
3. Nombre: `INPI Vigilancia Marcas`
4. Disparador: Semanal, Lunes, 08:00
5. Acción: Iniciar programa
   - Programa: `python`
   - Argumentos: `C:\ruta\al\script\inpi_vigilancia_marcas.py`
   - Iniciar en: `C:\ruta\al\script\`

---

### Opción C: GitHub Actions (ejecución en la nube, GRATIS)

Crear archivo `.github/workflows/inpi_monitor.yml` en tu repositorio:

```yaml
name: INPI Vigilancia Semanal

on:
  schedule:
    # Ejecuta todos los lunes a las 11:00 UTC (08:00 Argentina)
    - cron: '0 11 * * 1'
  workflow_dispatch:  # Permite ejecución manual desde GitHub

jobs:
  monitorear:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Instalar dependencias
        run: |
          pip install playwright fuzzywuzzy python-Levenshtein
          playwright install chromium
      
      - name: Ejecutar monitoreo
        run: python inpi_vigilancia_marcas.py --demo
      
      - name: Subir reporte como artefacto
        uses: actions/upload-artifact@v3
        with:
          name: reporte-inpi-${{ github.run_id }}
          path: reporte_alertas_*.txt
          retention-days: 30
```

**El reporte queda disponible en la sección "Artifacts" de cada ejecución en GitHub.**

---

### Opción D: PythonAnywhere (hosting gratuito)

1. Crear cuenta en pythonanywhere.com (plan free)
2. Subir el script y `marcas_clientes.json`
3. En "Tasks" → "Scheduled Tasks":
   - Horario: `08:00` todos los lunes
   - Comando: `python /home/tu_usuario/inpi_vigilancia_marcas.py`

---

## 7. AJUSTE DEL UMBRAL DE SIMILITUD

En la línea 30 del script:
```python
UMBRAL_SIMILITUD = 75
```

| Valor | Comportamiento | Recomendado para |
|-------|----------------|------------------|
| 90+ | Muy conservador, solo marcas casi idénticas | Clientes con mucho volumen de marcas |
| 75-89 | Balanceado, detecta variantes obvias | **Uso general recomendado** |
| 60-74 | Agresivo, más falsos positivos | Clientes en sectores de alto riesgo |

---

## 8. ARQUITECTURA FUTURA (Camino al SaaS)

```
v1 (actual)  → Script local, reporte en .txt
v2           → API REST (FastAPI) + base de datos PostgreSQL
v3           → Dashboard web con Next.js, alertas por email (SendGrid)
v4           → Multi-tenant, facturación automática (Stripe), white-label para estudios jurídicos
```

**Stack sugerido para v2:**
- Backend: FastAPI + SQLAlchemy + PostgreSQL
- Scheduler: APScheduler o Celery + Redis
- Notificaciones: SendGrid (email) + Twilio (WhatsApp)
- Deploy: Railway.app o Render (plan gratuito disponible)

---

## 9. NOTAS LEGALES IMPORTANTES

- Este sistema es una herramienta de **detección temprana**, no un dictamen jurídico.
- Las decisiones de interponer oposición requieren análisis profesional.
- Verificar siempre los expedientes directamente en: https://portaltramites.inpi.gob.ar
- El plazo para oponerse es **30 días hábiles** desde la publicación en el Boletín.
- Ley aplicable: Ley de Marcas y Designaciones N° 22.362.

---

*Sistema desarrollado para vigilancia comercial de activos intangibles.*  
*Para consultas sobre implementación: adaptar contacto según el caso.*
