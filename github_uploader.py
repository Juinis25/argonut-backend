"""
╔══════════════════════════════════════════════════════════════════════════════╗
║       INPI ARGENTINA — MÓDULO DE SINCRONIZACIÓN CON GITHUB                 ║
║       Sube reportes y alertas automáticamente a un repositorio privado     ║
╚══════════════════════════════════════════════════════════════════════════════╝

DEPENDENCIAS:
    pip install PyGithub python-dotenv

CONFIGURACIÓN:
    1. Crear archivo .env en la misma carpeta (ver instrucciones en README)
    2. Definir las variables GITHUB_PAT y GITHUB_REPO

EJECUCIÓN:
    python github_uploader.py                        # Sube el reporte más reciente
    python github_uploader.py --archivo mi_reporte.txt  # Sube un archivo específico
    python github_uploader.py --todos                # Sube todos los reportes pendientes
"""

import os
import sys
import glob
import json
import logging
from datetime import datetime
from pathlib import Path

# Lee variables de entorno desde .env si existe
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Si no está python-dotenv, lee directamente desde el entorno del sistema

from github import Github, GithubException, Auth

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN — Todo se lee desde variables de entorno o .env
# ─────────────────────────────────────────────────────────────────────────────

# Tu Personal Access Token (PAT) de GitHub
# Nunca hardcodearlo aquí. Siempre desde variable de entorno.
GITHUB_PAT  = os.getenv("GITHUB_PAT")

# Formato: "tu_usuario/nombre-del-repositorio"
# Ejemplo: "juanperez/inpi-vigilancia-privado"
GITHUB_REPO = os.getenv("GITHUB_REPO")

# Carpeta dentro del repositorio donde se guardarán los reportes
CARPETA_DESTINO = "reportes"

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("github_uploader.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# MÓDULO 1: VALIDACIÓN DE CREDENCIALES
# ═════════════════════════════════════════════════════════════════════════════

def validar_configuracion() -> bool:
    """
    Verifica que las credenciales y configuración estén presentes
    antes de intentar cualquier conexión con GitHub.
    Falla rápido con mensajes claros en lugar de errores crípticos de la API.
    """
    errores = []

    if not GITHUB_PAT:
        errores.append(
            "❌ GITHUB_PAT no definido.\n"
            "   Creá el archivo .env con: GITHUB_PAT=ghp_xxxxxxxxxxxx\n"
            "   (Ver instrucciones de generación del PAT más abajo)"
        )

    if not GITHUB_REPO:
        errores.append(
            "❌ GITHUB_REPO no definido.\n"
            "   Creá el archivo .env con: GITHUB_REPO=tu_usuario/nombre-repo"
        )
    elif "/" not in GITHUB_REPO:
        errores.append(
            f"❌ GITHUB_REPO tiene formato inválido: '{GITHUB_REPO}'\n"
            "   Formato correcto: 'usuario/repositorio' (ej: 'juanperez/inpi-monitor')"
        )

    if not GITHUB_PAT or len(GITHUB_PAT) < 20:
        pass  # Ya fue capturado arriba
    elif not (GITHUB_PAT.startswith("ghp_") or
              GITHUB_PAT.startswith("github_pat_") or
              GITHUB_PAT.startswith("ghs_")):
        errores.append(
            f"⚠️  El PAT tiene un prefijo inusual: '{GITHUB_PAT[:8]}...'\n"
            "   Los tokens modernos de GitHub empiezan con 'ghp_' o 'github_pat_'"
        )

    if errores:
        log.error("\n" + "\n".join(errores))
        return False

    log.info(f"✅ Credenciales validadas. Repositorio destino: {GITHUB_REPO}")
    return True


# ═════════════════════════════════════════════════════════════════════════════
# MÓDULO 2: CONEXIÓN Y VERIFICACIÓN DEL REPOSITORIO
# ═════════════════════════════════════════════════════════════════════════════

def conectar_github() -> tuple:
    """
    Establece conexión con la API de GitHub y verifica acceso al repositorio.

    Retorna: (objeto_github, objeto_repo) o (None, None) si falla.

    Separamos la conexión de la operación de subida para poder reutilizar
    la conexión en operaciones múltiples sin re-autenticar cada vez.
    """
    try:
        # Método de autenticación moderno (PyGithub >= 1.58)
        auth = Auth.Token(GITHUB_PAT)
        g = Github(auth=auth)

        # Verificar identidad del token
        usuario = g.get_user()
        log.info(f"🔐 Autenticado como: @{usuario.login}")

        # Acceder al repositorio
        repo = g.get_repo(GITHUB_REPO)
        log.info(f"📁 Repositorio encontrado: {repo.full_name} ({'privado' if repo.private else 'público'})")

        return g, repo

    except GithubException as e:
        if e.status == 401:
            log.error(
                "❌ Token inválido o expirado (401 Unauthorized).\n"
                "   Verificá que el PAT sea correcto y no haya expirado.\n"
                "   Si tiene fecha de expiración, generá uno nuevo."
            )
        elif e.status == 404:
            log.error(
                f"❌ Repositorio no encontrado: '{GITHUB_REPO}' (404 Not Found).\n"
                "   Verificá:\n"
                "   1. El nombre exacto del repo (mayúsculas/minúsculas importan)\n"
                "   2. Que el PAT tenga permiso 'repo' (acceso a repos privados)\n"
                "   3. Que el repositorio exista y vos seas el dueño o colaborador"
            )
        elif e.status == 403:
            log.error(
                "❌ Sin permisos suficientes (403 Forbidden).\n"
                "   El PAT no tiene el scope 'repo'. Regeneralo con ese permiso."
            )
        else:
            log.error(f"❌ Error de GitHub API ({e.status}): {e.data}")
        return None, None

    except Exception as e:
        log.error(f"❌ Error de conexión inesperado: {e}")
        return None, None


# ═════════════════════════════════════════════════════════════════════════════
# MÓDULO 3: OPERACIONES DE SUBIDA
# ═════════════════════════════════════════════════════════════════════════════

def subir_archivo(repo, ruta_local: str, mensaje_commit: str = None) -> dict:
    """
    Sube un archivo al repositorio GitHub.

    Lógica:
    - Si el archivo NO existe en GitHub → lo crea (create_file)
    - Si el archivo YA existe en GitHub → lo actualiza (update_file)
    
    Esto permite que el script sea idempotente: podés correrlo múltiples
    veces sin errores. GitHub guarda el historial de versiones automáticamente.

    Retorna dict con resultado: {'exito': bool, 'url': str, 'sha': str}
    """
    ruta_local = Path(ruta_local)

    if not ruta_local.exists():
        log.error(f"❌ Archivo no encontrado localmente: {ruta_local}")
        return {"exito": False, "url": None, "sha": None}

    # Construir ruta de destino dentro del repo
    nombre_archivo = ruta_local.name
    ruta_en_repo   = f"{CARPETA_DESTINO}/{nombre_archivo}"

    # Leer contenido del archivo
    with open(ruta_local, "r", encoding="utf-8") as f:
        contenido = f.read()

    # Mensaje de commit por defecto con timestamp
    if not mensaje_commit:
        ts = datetime.now().strftime("%d/%m/%Y %H:%M")
        mensaje_commit = f"feat: reporte INPI vigilancia marcas — {ts}"

    try:
        # Intentar obtener el archivo actual (para update)
        archivo_existente = None
        try:
            archivo_existente = repo.get_contents(ruta_en_repo)
        except GithubException as e:
            if e.status != 404:
                raise  # Error real, no "no encontrado"
            # 404 = archivo nuevo, se creará en el siguiente paso

        if archivo_existente:
            # Actualizar archivo existente (requiere el SHA actual)
            resultado = repo.update_file(
                path=ruta_en_repo,
                message=mensaje_commit,
                content=contenido,
                sha=archivo_existente.sha
            )
            operacion = "actualizado"
        else:
            # Crear archivo nuevo
            resultado = repo.create_file(
                path=ruta_en_repo,
                message=mensaje_commit,
                content=contenido
            )
            operacion = "creado"

        url_github = resultado["content"].html_url
        sha_commit = resultado["commit"].sha[:7]

        log.info(f"✅ Archivo {operacion}: {ruta_en_repo}")
        log.info(f"   URL: {url_github}")
        log.info(f"   Commit: {sha_commit}")

        return {
            "exito":      True,
            "url":        url_github,
            "sha_commit": sha_commit,
            "operacion":  operacion,
            "ruta_repo":  ruta_en_repo
        }

    except GithubException as e:
        log.error(f"❌ Error subiendo '{nombre_archivo}': {e.status} — {e.data}")
        return {"exito": False, "url": None, "sha": None}


def subir_reporte_con_metadata(repo, ruta_reporte: str) -> bool:
    """
    Sube el reporte de texto Y un archivo JSON de metadata asociado.
    
    El JSON permite a futuros scripts (o un dashboard web) consumir
    la información sin parsear el texto libre del reporte.
    
    Patrón recomendado para cuando escales a SaaS: el .txt es para
    humanos, el .json es para máquinas.
    """
    ruta = Path(ruta_reporte)

    # ── Subir el reporte .txt principal
    resultado_txt = subir_archivo(
        repo=repo,
        ruta_local=ruta_reporte,
        mensaje_commit=f"report: vigilancia INPI — {ruta.stem}"
    )

    if not resultado_txt["exito"]:
        return False

    # ── Generar y subir metadata JSON
    nombre_json = ruta.stem + "_metadata.json"
    metadata = {
        "generado_el":      datetime.now().isoformat(),
        "archivo_reporte":  ruta.name,
        "url_github":       resultado_txt["url"],
        "sha_commit":       resultado_txt.get("sha_commit"),
        "sistema":          "INPI Vigilancia Marcas v1.0",
        "repositorio":      GITHUB_REPO,
    }

    ruta_metadata = Path(nombre_json)
    with open(ruta_metadata, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    subir_archivo(
        repo=repo,
        ruta_local=str(ruta_metadata),
        mensaje_commit=f"chore: metadata para {ruta.name}"
    )

    # Limpiar archivo temporal
    ruta_metadata.unlink(missing_ok=True)

    return True


def subir_todos_los_reportes_pendientes(repo) -> dict:
    """
    Busca todos los reportes locales que NO están en GitHub y los sube.
    
    Útil si el script de monitoreo corrió varias veces sin conexión
    y hay reportes acumulados localmente.
    
    Retorna resumen con contadores de éxitos y fallos.
    """
    # Buscar todos los reportes locales
    reportes_locales = sorted(glob.glob("reporte_alertas_*.txt"))

    if not reportes_locales:
        log.info("📭 No hay reportes locales para subir.")
        return {"total": 0, "subidos": 0, "fallidos": 0}

    log.info(f"📦 Encontrados {len(reportes_locales)} reportes locales.")

    # Obtener lista de archivos ya en GitHub para evitar duplicados innecesarios
    try:
        archivos_en_repo = {
            c.name
            for c in repo.get_contents(CARPETA_DESTINO)
        }
        log.info(f"   GitHub ya tiene {len(archivos_en_repo)} archivos en /{CARPETA_DESTINO}/")
    except GithubException:
        archivos_en_repo = set()  # La carpeta no existe aún, se creará al primer upload

    resultados = {"total": len(reportes_locales), "subidos": 0, "fallidos": 0, "detalle": []}

    for ruta_reporte in reportes_locales:
        nombre = Path(ruta_reporte).name

        # Subir siempre (update_file maneja duplicados), pero loguear si ya existía
        if nombre in archivos_en_repo:
            log.info(f"   ♻️  Actualizando versión existente: {nombre}")
        else:
            log.info(f"   ⬆️  Subiendo nuevo reporte: {nombre}")

        exito = subir_reporte_con_metadata(repo, ruta_reporte)

        if exito:
            resultados["subidos"] += 1
            resultados["detalle"].append({"archivo": nombre, "estado": "✅ subido"})
        else:
            resultados["fallidos"] += 1
            resultados["detalle"].append({"archivo": nombre, "estado": "❌ fallido"})

    return resultados


# ═════════════════════════════════════════════════════════════════════════════
# MÓDULO 4: ORQUESTADOR PRINCIPAL
# ═════════════════════════════════════════════════════════════════════════════

def main():
    """
    Punto de entrada con tres modos de operación:
    
    1. Sin argumentos:   sube el reporte más reciente
    2. --archivo X.txt:  sube un archivo específico
    3. --todos:          sube todos los reportes pendientes
    """
    SEPARADOR = "═" * 72

    print(f"\n{SEPARADOR}")
    print("  INPI ARGENTINA — SINCRONIZACIÓN CON GITHUB")
    print(f"{SEPARADOR}\n")

    # ── Validar configuración antes de conectar
    if not validar_configuracion():
        print("\n  Ver instrucciones de configuración del PAT más abajo.")
        sys.exit(1)

    # ── Conectar con GitHub
    g, repo = conectar_github()
    if not repo:
        sys.exit(1)

    # ── Determinar modo de operación por argumentos CLI
    args = sys.argv[1:]

    if "--todos" in args:
        # ── Modo: subir todos los reportes pendientes
        log.info("📤 Modo: subir TODOS los reportes pendientes")
        resultados = subir_todos_los_reportes_pendientes(repo)

        print(f"\n{SEPARADOR}")
        print(f"  RESUMEN DE SINCRONIZACIÓN")
        print(f"{SEPARADOR}")
        print(f"  Total encontrados: {resultados['total']}")
        print(f"  Subidos con éxito: {resultados['subidos']}")
        print(f"  Con errores:       {resultados['fallidos']}")
        if resultados.get("detalle"):
            print(f"\n  Detalle:")
            for item in resultados["detalle"]:
                print(f"    {item['estado']}  {item['archivo']}")
        print(f"{SEPARADOR}\n")

    elif "--archivo" in args:
        # ── Modo: subir archivo específico
        idx = args.index("--archivo")
        if idx + 1 >= len(args):
            log.error("❌ Especificá el nombre del archivo: --archivo mi_reporte.txt")
            sys.exit(1)

        ruta_archivo = args[idx + 1]
        log.info(f"📤 Modo: subir archivo específico → {ruta_archivo}")
        exito = subir_reporte_con_metadata(repo, ruta_archivo)

        if not exito:
            sys.exit(1)

    else:
        # ── Modo por defecto: subir el reporte más reciente
        reportes = sorted(glob.glob("reporte_alertas_*.txt"), reverse=True)

        if not reportes:
            log.error(
                "❌ No se encontró ningún reporte local.\n"
                "   Ejecutá primero: python inpi_vigilancia_marcas.py --demo\n"
                "   O especificá un archivo: python github_uploader.py --archivo mi_reporte.txt"
            )
            sys.exit(1)

        reporte_reciente = reportes[0]
        log.info(f"📤 Modo: subir reporte más reciente → {reporte_reciente}")
        exito = subir_reporte_con_metadata(repo, reporte_reciente)

        if not exito:
            sys.exit(1)

    # Cerrar conexión limpiamente
    g.close()
    log.info("🔒 Conexión con GitHub cerrada.")
    print(f"\n  ✅ Sincronización completada. Ver repositorio: https://github.com/{GITHUB_REPO}\n")


if __name__ == "__main__":
    main()
