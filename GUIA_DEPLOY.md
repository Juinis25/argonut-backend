# GUÍA DE DEPLOY EN GITHUB ACTIONS
## Para abogados y no-técnicos: del cero al sistema en producción en 30 minutos

---

## ÍNDICE
1. [Estructura del proyecto](#1-estructura-del-proyecto)
2. [Crear el repositorio privado en GitHub](#2-crear-el-repositorio-privado)
3. [Subir los archivos](#3-subir-los-archivos)
4. [Configurar los Secrets (credenciales seguras)](#4-configurar-secrets)
5. [Activar y verificar el workflow](#5-activar-el-workflow)
6. [Cómo ver los reportes](#6-ver-los-reportes)
7. [Referencia de todos los Secrets disponibles](#7-referencia-de-secrets)
8. [Resolución de problemas frecuentes](#8-resolución-de-problemas)

---

## 1. ESTRUCTURA DEL PROYECTO

Así deben estar organizados los archivos en tu computadora antes de subirlos:

```
inpi-monitor/                          ← carpeta raíz del proyecto
│
├── .github/
│   └── workflows/
│       └── inpi_monitor.yml           ← el workflow que ejecuta GitHub
│
├── inpi_vigilancia_marcas.py          ← script principal (v2.0)
├── marcas_clientes.json               ← TU base de datos de clientes
├── requirements.txt                   ← dependencias Python
├── procesados_historico.json          ← se crea automáticamente
└── README.md                          ← documentación
```

**IMPORTANTE:** La carpeta `.github` empieza con un punto. En Windows puede estar oculta.
Si usás el Explorador de Windows, activá "Mostrar archivos ocultos" en la pestaña Vista.

---

## 2. CREAR EL REPOSITORIO PRIVADO

### Paso 1: Crear cuenta en GitHub (si no tenés)
→ Ir a https://github.com/signup
→ Elegir el plan **Free** (es suficiente para este sistema)

### Paso 2: Crear el repositorio

1. Ir a https://github.com/new
2. Completar el formulario:

| Campo | Valor |
|-------|-------|
| **Repository name** | `inpi-monitor` |
| **Description** | Sistema de vigilancia de marcas INPI Argentina |
| **Visibility** | ✅ **Private** ← MUY IMPORTANTE: privado para confidencialidad |
| **Initialize this repository** | ✅ Marcar esta opción |
| **Add .gitignore** | Python |

3. Hacer clic en **"Create repository"** (botón verde)

✅ Tu repositorio privado está creado. Los nombres de tus clientes y credenciales
   solo los podrás ver vos.

---

## 3. SUBIR LOS ARCHIVOS

### Opción A: Desde la interfaz web de GitHub (más simple)

1. En tu repositorio recién creado, hacer clic en **"Add file"** → **"Upload files"**
2. Arrastrar todos los archivos del proyecto (EXCEPTO la carpeta `.github/`, que se sube por separado)
3. En el campo de commit escribir: `Versión inicial del sistema INPI Monitor`
4. Hacer clic en **"Commit changes"**

**Para subir la carpeta `.github/workflows/`:**

1. Hacer clic en **"Add file"** → **"Create new file"**
2. En el campo de nombre escribir exactamente: `.github/workflows/inpi_monitor.yml`
   (GitHub crea las carpetas automáticamente cuando ponés la barra `/`)
3. Pegar el contenido completo del archivo `inpi_monitor.yml`
4. Hacer clic en **"Commit new file"**

### Opción B: Con GitHub Desktop (más cómoda si subís cambios frecuentes)

1. Descargar GitHub Desktop desde https://desktop.github.com/
2. "Clone" tu repositorio a tu computadora
3. Copiar todos los archivos dentro de la carpeta clonada
4. En GitHub Desktop: escribir un mensaje de commit y hacer clic en "Push origin"

---

## 4. CONFIGURAR SECRETS

Los Secrets son credenciales encriptadas que GitHub guarda de forma segura.
**Nunca aparecen en el código ni en los logs.** Ni GitHub los puede leer una vez guardados.

### Cómo acceder a los Secrets

1. En tu repositorio, ir a: **Settings** (pestaña superior)
2. En el menú izquierdo: **Security** → **Secrets and variables** → **Actions**
3. Hacer clic en **"New repository secret"**

### Secrets OBLIGATORIOS para el email (Gmail)

Antes de crear estos secrets, necesitás configurar una "Contraseña de Aplicación" en Google:

**Paso previo — Crear contraseña de aplicación en Gmail:**
1. Ir a https://myaccount.google.com/security
2. Activar la "Verificación en 2 pasos" si no la tenés
3. Ir a https://myaccount.google.com/apppasswords
4. En "Seleccionar aplicación" elegir "Correo"
5. En "Seleccionar dispositivo" elegir "Otro" y escribir "INPI Monitor"
6. Copiar la contraseña de 16 caracteres que aparece (ej: `abcd efgh ijkl mnop`)

**Ahora crear los secrets en GitHub:**

| Nombre del Secret | Valor | Ejemplo |
|-------------------|-------|---------|
| `EMAIL_REMITENTE` | Tu dirección de Gmail | `tuemail@gmail.com` |
| `EMAIL_PASSWORD` | La contraseña de aplicación de Google | `abcdefghijklmnop` (sin espacios) |
| `EMAIL_SMTP_HOST` | Servidor SMTP de Gmail | `smtp.gmail.com` |
| `EMAIL_SMTP_PORT` | Puerto SMTP | `465` |
| `EMAIL_DESTINATARIOS` | Email(s) donde llegará el reporte | `abogado@estudio.com` o `email1@gmail.com,email2@gmail.com` |

### Secrets OPCIONALES para WhatsApp (Twilio)

Si querés recibir también el resumen por WhatsApp:

1. Crear cuenta gratuita en https://twilio.com
2. En el panel de Twilio, ir a: **Messaging** → **Try it out** → **Send a WhatsApp message**
3. Seguir las instrucciones para activar el Sandbox de WhatsApp
4. Obtener tus credenciales en https://console.twilio.com

| Nombre del Secret | Dónde encontrarlo en Twilio |
|-------------------|-----------------------------|
| `TWILIO_ACCOUNT_SID` | Panel principal de Twilio (empieza con AC...) |
| `TWILIO_AUTH_TOKEN` | Panel principal de Twilio (debajo del SID) |
| `TWILIO_WHATSAPP_FROM` | El número Sandbox: `whatsapp:+14155238886` |
| `TWILIO_WHATSAPP_TO` | Tu número: `whatsapp:+5491100000000` |

### Secret OPCIONAL de configuración

| Nombre del Secret | Valor | Descripción |
|-------------------|-------|-------------|
| `UMBRAL_SIMILITUD` | `75` | Sensibilidad del detector (70-90, default 75) |

---

## 5. ACTIVAR EL WORKFLOW

### Verificar que el workflow está activo

1. En tu repositorio, ir a la pestaña **"Actions"**
2. Debería aparecer el workflow **"🔍 INPI — Vigilancia Semanal de Marcas"**
3. Si aparece un mensaje "Workflows aren't being run on this repository" → hacer clic en **"I understand my workflows, go ahead and enable them"**

### Ejecutar manualmente por primera vez (para testear)

1. En la pestaña **Actions**, hacer clic en el workflow
2. Hacer clic en **"Run workflow"** (botón azul a la derecha)
3. Configurar:
   - **Modo de ejecución**: `demo` (para el primer test)
   - **Enviar notificaciones**: `false` (para el primer test)
4. Hacer clic en **"Run workflow"** (botón verde)

### Verificar que funcionó

1. Aparecerá una nueva ejecución con un círculo amarillo (en proceso)
2. Al terminar, el círculo se convierte en ✅ verde (éxito) o ❌ rojo (error)
3. Hacer clic en la ejecución para ver los logs detallados
4. Ir a la sección **"Artifacts"** al final de la página → descargar el reporte

---

## 6. VER LOS REPORTES

### Opción A: Descargar como artefacto

1. Ir a **Actions** en tu repositorio
2. Hacer clic en la ejecución que te interesa
3. Al final de la página, sección **"Artifacts"**:
   - `reporte-inpi-[número]` → contiene el .txt con todas las alertas
4. Descargar y abrir con cualquier editor de texto

### Opción B: Ver el log en tiempo real

1. Hacer clic en la ejecución
2. Hacer clic en el job **"Monitoreo INPI"**
3. Expandir el paso **"🔍 Ejecutar vigilancia INPI"**
4. El reporte completo aparece directamente en la consola

### Opción C: Recibirlo por email (producción)

Una vez configurados los secrets de email, el reporte llegará automáticamente
todos los lunes a las 8:00 AM hora Argentina.

---

## 7. REFERENCIA COMPLETA DE SECRETS

```
┌─────────────────────────────────────────────────────────────────┐
│                    SECRETS DISPONIBLES                          │
├──────────────────────────┬──────────────────────────────────────┤
│ SECRET                   │ DESCRIPCIÓN                          │
├──────────────────────────┼──────────────────────────────────────┤
│ EMAIL_REMITENTE          │ Cuenta Gmail desde la que se envía   │
│ EMAIL_PASSWORD           │ Contraseña de aplicación Google      │
│ EMAIL_SMTP_HOST          │ smtp.gmail.com                       │
│ EMAIL_SMTP_PORT          │ 465                                  │
│ EMAIL_DESTINATARIOS      │ Uno o más emails separados por coma  │
├──────────────────────────┼──────────────────────────────────────┤
│ TWILIO_ACCOUNT_SID       │ SID de cuenta Twilio (ACxxxxxx)      │
│ TWILIO_AUTH_TOKEN        │ Token de autenticación Twilio        │
│ TWILIO_WHATSAPP_FROM     │ whatsapp:+14155238886 (sandbox)      │
│ TWILIO_WHATSAPP_TO       │ whatsapp:+549XXXXXXXXX               │
├──────────────────────────┼──────────────────────────────────────┤
│ UMBRAL_SIMILITUD         │ Número del 60 al 95 (default: 75)    │
└──────────────────────────┴──────────────────────────────────────┘
```

**Regla de oro:** Si un secret no está configurado, esa funcionalidad
simplemente se omite sin romper el resto del sistema.

---

## 8. RESOLUCIÓN DE PROBLEMAS

### ❌ El workflow falla con "ModuleNotFoundError"
**Causa:** Una dependencia no está en `requirements.txt`
**Solución:** Verificar que `requirements.txt` esté en la raíz del repositorio (no en subcarpeta)

### ❌ El scraping falla pero el sistema continúa en modo demo
**Causa:** El portal del INPI cambió su estructura HTML
**Solución:** Actualizar los selectores CSS marcados como `# ← SELECTOR` en el script.
Para encontrar los nuevos selectores: abrir Chrome, ir al portal del INPI, hacer clic
derecho sobre el elemento → "Inspeccionar" → copiar el selector CSS.

### ❌ El email no llega
**Causa:** Contraseña de aplicación incorrecta o 2FA no activado
**Solución:**
1. Verificar que el 2FA está activo en tu cuenta Google
2. Generar una nueva contraseña de aplicación
3. Actualizar el secret `EMAIL_PASSWORD` en GitHub

### ❌ "Workflows aren't being run on this repository"
**Causa:** GitHub requiere confirmación explícita para repositorios nuevos
**Solución:** Ir a Actions → hacer clic en el botón de habilitación

### ❌ El commit automático falla con "Permission denied"
**Causa:** Los permisos del workflow no están configurados correctamente
**Solución:** En Settings → Actions → General → Workflow permissions →
seleccionar "Read and write permissions" → Guardar

### ⚠️ Los selectores del portal INPI no funcionan
**Esto es esperable** si el portal fue actualizado. Para solucionarlo:
1. Abrir https://portaltramites.inpi.gob.ar/marcas/busqueda en Chrome
2. Hacer F12 (DevTools) → pestaña Elements
3. Buscar los elementos HTML que corresponden a: clase, estado, botón de búsqueda,
   resultados, denominación, expediente, fecha, titular
4. Actualizar los valores en las líneas marcadas `# ← SELECTOR` del script

---

## CALENDARIO DE EJECUCIÓN

```
Configuración actual: todos los lunes a las 08:00 AM Argentina

ENERO 2026
Lun  5 → ejecución automática
Lun 12 → ejecución automática
Lun 19 → ejecución automática
Lun 26 → ejecución automática
...
```

Para cambiar el día u hora, editar la línea `cron` en el workflow:
```yaml
- cron: "0 11 * * 1"   # lunes 11:00 UTC = 08:00 Argentina
```

Ejemplos:
- Miércoles 09:00 Argentina: `"0 12 * * 3"`
- Dos veces por semana (lun y jue): `"0 11 * * 1,4"`
- Diario a las 08:00: `"0 11 * * *"`

---

*Sistema INPI Monitor — Documentación v2.0*
*Para soporte técnico: revisar los logs en GitHub Actions*
