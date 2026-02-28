# Cómo Generar tu Personal Access Token (PAT) en GitHub
## Guía Paso a Paso — Sin Ambigüedades

---

## ¿Qué es un PAT y por qué lo necesitás?

GitHub eliminó la autenticación por usuario y contraseña para operaciones de API en agosto de 2021. El PAT es el reemplazo: una cadena de texto cifrada que actúa como credencial de acceso programático. Tiene tres ventajas sobre la contraseña: podés limitarlo a permisos específicos, podés revocarlo sin cambiar tu contraseña, y podés tener varios (uno por proyecto o sistema).

---

## Tipo de Token a Generar

GitHub ofrece dos tipos. Para este sistema usamos **Fine-grained Personal Access Token** (el moderno, más seguro): permite definir exactamente a qué repositorio tiene acceso y qué operaciones puede hacer. Nunca genera un token con acceso a todos tus repositorios cuando solo necesitás uno.

---

## Pasos para Generar el Token

### 1. Acceder a la configuración de tokens

Ve a: **https://github.com/settings/tokens?type=beta**

O manualmente:
```
GitHub → Tu avatar (arriba a la derecha) → Settings →
Developer settings (última opción del menú izquierdo) →
Personal access tokens → Fine-grained tokens
```

---

### 2. Crear nuevo token

Clic en **"Generate new token"** (botón verde, arriba a la derecha).

---

### 3. Completar el formulario

**Token name:**
```
inpi-vigilancia-marcas
```
Nombre descriptivo. En 6 meses vas a agradecer saber para qué sirve cada token.

---

**Expiration:**
Opciones recomendadas según tu caso de uso:

| Opción | Cuándo usarla |
|--------|---------------|
| 90 days | Si querés renovarlo frecuentemente por seguridad |
| 1 year | Uso general recomendado para sistemas automatizados |
| No expiration | Solo si es un repositorio completamente privado y de bajo riesgo |

Elegí **"1 year"** para empezar. Creá un recordatorio en el calendario para renovarlo antes del vencimiento.

---

**Resource owner:**
Seleccioná tu usuario personal (no una organización, a menos que el repo esté bajo una org).

---

**Repository access:**
Seleccioná **"Only select repositories"** → elegí el repositorio privado que creaste para los reportes.

⚠️ No selecciones "All repositories". El principio de mínimo privilegio aplica aunque el repositorio sea tuyo.

---

**Permissions → Repository permissions:**

Expandí la sección y configurá estos permisos. Todos los demás deben quedar en "No access":

| Permiso | Valor requerido | Por qué |
|---------|----------------|---------|
| **Contents** | **Read and write** | Crear y actualizar archivos en el repo |
| **Metadata** | **Read-only** | Se activa automáticamente, es obligatorio |

Solo esos dos. No necesitás Actions, Issues, Pull Requests, ni ningún otro.

---

### 4. Generar y copiar el token

Clic en **"Generate token"** al final de la página.

**GitHub muestra el token UNA SOLA VEZ.** Después de cerrar la página, no hay forma de volver a verlo. Solo podés revocarlo y generar uno nuevo.

El token tiene este formato:
```
github_pat_11XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

Copialo inmediatamente y guardalo en el archivo `.env`:
```
GITHUB_PAT=github_pat_11XXXXXXXX...
```

---

## Configuración del Archivo .env

En la misma carpeta donde está `github_uploader.py`:

```bash
# Crear el archivo .env desde el template
cp .env.example .env

# Editar con tu editor preferido
nano .env          # Linux/Mac
notepad .env       # Windows
```

Completar los dos valores:
```
GITHUB_PAT=github_pat_11TU_TOKEN_AQUI
GITHUB_REPO=tu_usuario/nombre-del-repositorio
```

---

## Configurar .gitignore (obligatorio)

El archivo `.env` **nunca debe subirse a GitHub**. Si lo subís, cualquiera que acceda al repo (incluso en el historial de commits) puede usar ese token para operar en tu nombre.

Creá o editá el archivo `.gitignore` en la raíz del proyecto:

```bash
# Agregar .env al gitignore
echo ".env" >> .gitignore
echo "*.log" >> .gitignore
echo "boletin_cache.json" >> .gitignore
```

O crear el archivo completo:

```
# Credenciales — NUNCA subir a GitHub
.env
.env.local
.env.production

# Archivos generados por el sistema
*.log
boletin_cache.json
alertas_*.json
*_metadata.json

# Python
__pycache__/
*.pyc
*.pyo
.venv/
```

---

## Verificar que Todo Funciona

```bash
# Instalar dependencias
pip install PyGithub python-dotenv

# Probar conexión
python github_uploader.py --archivo CUALQUIER_ARCHIVO_DE_PRUEBA.txt
```

Si la configuración es correcta, verás:
```
✅ Credenciales validadas. Repositorio destino: tu_usuario/tu-repo
🔐 Autenticado como: @tu_usuario
📁 Repositorio encontrado: tu_usuario/tu-repo (privado)
✅ Archivo creado: reportes/CUALQUIER_ARCHIVO_DE_PRUEBA.txt
```

---

## Errores Comunes y Soluciones

| Error | Causa más probable | Solución |
|-------|-------------------|----------|
| `401 Unauthorized` | Token inválido o copiado con espacios | Verificar que el token en .env no tenga espacios ni saltos de línea |
| `404 Not Found` | Nombre del repo incorrecto | Verificar mayúsculas/minúsculas exactas del nombre del repo |
| `403 Forbidden` | El token no tiene permiso "Contents: write" | Regenerar el token con el permiso correcto |
| `GITHUB_PAT no definido` | El .env no está en la misma carpeta que el script | Verificar que el .env esté en el directorio correcto |
| Token expirado | El PAT venció | Generar uno nuevo en github.com/settings/tokens |

---

## Revocar un Token Comprometido

Si por error subiste el `.env` a GitHub o compartiste el token:

1. Ir inmediatamente a: **https://github.com/settings/tokens**
2. Encontrar el token por nombre
3. Clic en **"Delete"**

El token queda invalidado instantáneamente. Generar uno nuevo y actualizar el `.env`.

---

## Flujo Completo de Integración

```bash
# 1. Generar reporte de vigilancia
python inpi_vigilancia_marcas.py --demo

# 2. Subir automáticamente a GitHub
python github_uploader.py

# 3. (Opcional) Subir todos los reportes acumulados
python github_uploader.py --todos

# 4. (Opcional) Subir un archivo específico
python github_uploader.py --archivo reporte_alertas_20250223_143022.txt
```

Los reportes quedan disponibles en:
```
https://github.com/TU_USUARIO/TU_REPO/tree/main/reportes/
```

Con historial de versiones completo, diff entre ejecuciones, y acceso desde cualquier dispositivo con tu sesión de GitHub.
