"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          ARGONUT — Dashboard de Vigilancia de Marcas INPI Argentina        ║
║          Streamlit App · Friends & Family v1.0                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import glob
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Argonut — Vigilancia de Marcas",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# ESTILOS CUSTOM
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
  /* Fuente y paleta */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  /* Header de la app */
  .app-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    color: white;
    padding: 1.5rem 2rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
  }
  .app-header h1 { font-size: 1.8rem; font-weight: 800; margin: 0; letter-spacing: -0.5px; }
  .app-header h1 span { color: #e63946; }
  .app-header p { color: #94a3b8; margin: 0.3rem 0 0; font-size: 0.9rem; }

  /* Tarjetas de alerta */
  .alert-card {
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
    border-left: 5px solid;
  }
  .alert-critica  { background: #fff1f2; border-color: #e63946; }
  .alert-alta     { background: #fffbeb; border-color: #f59e0b; }
  .alert-media    { background: #fff7ed; border-color: #f97316; }

  .alert-score {
    font-size: 1.4rem;
    font-weight: 800;
    line-height: 1;
  }
  .score-critica { color: #dc2626; }
  .score-alta    { color: #d97706; }
  .score-media   { color: #ea580c; }

  /* Metric overrides */
  [data-testid="metric-container"] {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 1rem;
  }

  /* Badge */
  .badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .badge-red    { background: #fef2f2; color: #dc2626; }
  .badge-yellow { background: #fffbeb; color: #d97706; }
  .badge-orange { background: #fff7ed; color: #ea580c; }
  .badge-green  { background: #f0fdf4; color: #16a34a; }
  .badge-blue   { background: #eff6ff; color: #2563eb; }

  /* Sidebar */
  section[data-testid="stSidebar"] { background: #0f172a; }
  section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
  section[data-testid="stSidebar"] .stSelectbox label { color: #94a3b8 !important; }

  /* Botón primario */
  .stButton > button {
    background: #e63946;
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    padding: 0.5rem 1.2rem;
    transition: opacity 0.15s;
  }
  .stButton > button:hover { opacity: 0.85; border: none; color: white; }

  /* Tabla */
  .dataframe thead tr th {
    background: #0f172a !important;
    color: white !important;
    font-weight: 600;
  }

  /* Quitar padding excesivo */
  .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS DE DATOS
# ─────────────────────────────────────────────────────────────────────────────

def cargar_alertas() -> list[dict]:
    """Carga el JSON de alertas más reciente disponible."""
    archivos = sorted(glob.glob("alertas_*.json"), reverse=True)
    if not archivos:
        return []
    with open(archivos[0], "r", encoding="utf-8") as f:
        return json.load(f)


def cargar_clientes() -> list[dict]:
    """Carga la base de clientes."""
    if not Path("marcas_clientes.json").exists():
        return []
    with open("marcas_clientes.json", "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_clientes(clientes: list[dict]):
    """Persiste la base de clientes."""
    with open("marcas_clientes.json", "w", encoding="utf-8") as f:
        json.dump(clientes, f, ensure_ascii=False, indent=2)


def cargar_procesados() -> dict:
    """Carga el log de expedientes procesados."""
    if not Path("procesados_historico.json").exists():
        return {"expedientes_procesados": {}}
    with open("procesados_historico.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    if "expedientes_procesados" not in data:
        data["expedientes_procesados"] = {}
    return data


def cargar_log_ejecucion() -> list[str]:
    """Últimas líneas del log de ejecución."""
    if not Path("inpi_monitor.log").exists():
        return []
    with open("inpi_monitor.log", "r", encoding="utf-8") as f:
        lineas = f.readlines()
    return [l.strip() for l in lineas[-50:] if l.strip()]


def score_to_nivel(score: int) -> tuple[str, str, str]:
    """Retorna (nivel_texto, clase_css, emoji) según el score."""
    if score >= 90:
        return "CRÍTICA", "critica", "🔴"
    elif score >= 80:
        return "ALTA", "alta", "🟡"
    else:
        return "MEDIA", "media", "🟠"


def ultimo_reporte() -> str | None:
    archivos = sorted(glob.glob("reporte_alertas_*.txt"), reverse=True)
    return archivos[0] if archivos else None


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🔍 Argonut")
    st.markdown("*Vigilancia de Marcas · INPI Argentina*")
    st.divider()

    pagina = st.radio(
        "Navegación",
        ["📊 Dashboard", "🚨 Alertas", "👥 Mis Marcas", "⚙️ Ejecutar", "📋 Logs"],
        label_visibility="collapsed",
    )

    st.divider()

    # Estado rápido
    alertas_data = cargar_alertas()
    criticas = sum(1 for a in alertas_data if a.get("score", 0) >= 90)
    clientes_data = cargar_clientes()

    st.markdown(f"**{len(clientes_data)}** marcas vigiladas")
    if criticas > 0:
        st.markdown(f"⚠️ **{criticas}** alertas críticas")
    else:
        st.markdown("✅ Sin alertas críticas")

    st.divider()
    st.markdown(
        "<small style='color:#475569;'>Ley 22.362 · INPI Argentina<br>"
        "portaltramites.inpi.gob.ar</small>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA: DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

if pagina == "📊 Dashboard":
    st.markdown("""
    <div class="app-header">
      <h1>Argo<span>nut</span> — Vigilancia de Marcas</h1>
      <p>Sistema de detección temprana de colisiones en el Boletín INPI Argentina · v2.0</p>
    </div>
    """, unsafe_allow_html=True)

    alertas = cargar_alertas()
    clientes = cargar_clientes()
    procesados = cargar_procesados()

    # ── KPIs
    col1, col2, col3, col4 = st.columns(4)

    criticas  = sum(1 for a in alertas if a.get("score", 0) >= 90)
    altas     = sum(1 for a in alertas if 80 <= a.get("score", 0) < 90)
    medias    = sum(1 for a in alertas if 75 <= a.get("score", 0) < 80)
    n_proc    = len(procesados.get("expedientes_procesados", {}))

    col1.metric("🚨 Alertas Críticas (≥90%)",  criticas,  delta="requieren acción" if criticas else None, delta_color="inverse")
    col2.metric("🟡 Alertas Altas (80-89%)",   altas)
    col3.metric("👥 Marcas Vigiladas",          len(clientes))
    col4.metric("📦 Expedientes en historial",  n_proc)

    st.divider()

    # ── Alertas recientes
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("🚨 Alertas más recientes")
        if not alertas:
            st.info("No hay alertas registradas. Ejecutá el sistema en modo demo para ver un ejemplo.")
        else:
            for a in alertas[:5]:
                score   = a.get("score", 0)
                nivel, clase, emoji = score_to_nivel(score)
                st.markdown(f"""
                <div class="alert-card alert-{clase}">
                  <div style="display:flex;align-items:center;gap:1rem;">
                    <div class="alert-score score-{clase}">{score}%</div>
                    <div>
                      <strong>{a['marca_cliente']}</strong>
                      <span class="badge badge-blue" style="margin-left:0.4rem;">Clase {a['clase']}</span>
                      <span class="badge badge-{'red' if clase=='critica' else 'yellow' if clase=='alta' else 'orange'}" style="margin-left:0.3rem;">{emoji} {nivel}</span>
                      <br/>
                      <span style="font-size:0.85rem;color:#475569;">
                        Solicitud: <strong>{a['solicitud_nombre']}</strong>
                        &nbsp;·&nbsp; {a.get('expediente','N/D')}
                        &nbsp;·&nbsp; {a.get('titular_solicitante','N/D')}
                      </span>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

    with col_right:
        st.subheader("📌 Marcas vigiladas")
        if not clientes:
            st.info("Sin marcas configuradas.")
        else:
            for c in clientes:
                st.markdown(f"""
                <div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:0.8rem 1rem;margin-bottom:0.6rem;">
                  <strong>{c['nombre']}</strong>
                  <span class="badge badge-blue" style="margin-left:0.4rem;">Cl. {c['clase']}</span>
                  <br/><small style="color:#64748b;">{c.get('titular','N/D')}</small>
                </div>
                """, unsafe_allow_html=True)

    # ── Última ejecución
    reporte = ultimo_reporte()
    if reporte:
        ts_str = Path(reporte).stem.replace("reporte_alertas_", "")
        try:
            ts = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
            st.caption(f"📅 Última ejecución: {ts.strftime('%d/%m/%Y a las %H:%M hs')}")
        except ValueError:
            st.caption(f"📅 Último reporte: {reporte}")


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA: ALERTAS
# ─────────────────────────────────────────────────────────────────────────────

elif pagina == "🚨 Alertas":
    st.title("🚨 Centro de Alertas")

    alertas = cargar_alertas()

    if not alertas:
        st.info("No hay alertas en el archivo más reciente. Ejecutá el sistema primero.")
        st.stop()

    # Filtros
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        marcas_disponibles = ["Todas"] + sorted(set(a["marca_cliente"] for a in alertas))
        filtro_marca = st.selectbox("Filtrar por marca", marcas_disponibles)
    with col_f2:
        niveles = ["Todos", "🔴 Crítica (≥90%)", "🟡 Alta (80-89%)", "🟠 Media (75-79%)"]
        filtro_nivel = st.selectbox("Filtrar por nivel", niveles)
    with col_f3:
        score_min = st.slider("Score mínimo", 70, 100, 75)

    # Aplicar filtros
    filtradas = alertas
    if filtro_marca != "Todas":
        filtradas = [a for a in filtradas if a["marca_cliente"] == filtro_marca]
    if filtro_nivel == "🔴 Crítica (≥90%)":
        filtradas = [a for a in filtradas if a.get("score", 0) >= 90]
    elif filtro_nivel == "🟡 Alta (80-89%)":
        filtradas = [a for a in filtradas if 80 <= a.get("score", 0) < 90]
    elif filtro_nivel == "🟠 Media (75-79%)":
        filtradas = [a for a in filtradas if 75 <= a.get("score", 0) < 80]
    filtradas = [a for a in filtradas if a.get("score", 0) >= score_min]

    st.markdown(f"**{len(filtradas)}** alerta(s) encontradas")
    st.divider()

    for i, a in enumerate(filtradas, 1):
        score  = a.get("score", 0)
        nivel, clase, emoji = score_to_nivel(score)

        with st.expander(f"{emoji} [{score}%] **{a['marca_cliente']}** ↔ **{a['solicitud_nombre']}** — {nivel}", expanded=(score >= 90)):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**🏷️ Marca protegida**")
                st.markdown(f"- Nombre: `{a['marca_cliente']}`")
                st.markdown(f"- Clase INPI: `{a['clase']}`")
                st.markdown(f"- Titular: `{a.get('titular_cliente', 'N/D')}`")
                st.markdown(f"- Contacto: `{a.get('contacto', 'N/D')}`")
            with col_b:
                st.markdown("**⚠️ Nueva solicitud conflictiva**")
                st.markdown(f"- Denominación: `{a['solicitud_nombre']}`")
                st.markdown(f"- Expediente: `{a.get('expediente', 'N/D')}`")
                st.markdown(f"- Fecha: `{a.get('fecha_solicitud', 'N/D')}`")
                st.markdown(f"- Solicitante: `{a.get('titular_solicitante', 'N/D')}`")

            scores_d = a.get("scores_detalle", {})
            if scores_d:
                st.markdown("**📊 Desglose de scores**")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Ratio",       f"{scores_d.get('ratio', 0)}%")
                c2.metric("Partial",     f"{scores_d.get('partial_ratio', 0)}%")
                c3.metric("Token Sort",  f"{scores_d.get('token_sort_ratio', 0)}%")
                c4.metric("Token Set",   f"{scores_d.get('token_set_ratio', 0)}%")

            if score >= 90:
                st.error("⏰ **Acción requerida:** Plazo de 30 días hábiles desde publicación (Ley 22.362 Art. 12). Verificar en portaltramites.inpi.gob.ar")
            elif score >= 80:
                st.warning("⚠️ Evaluar si amerita oposición. Consultar con el titular.")

            st.caption(f"Detectado el {a.get('detectado_el', 'N/D')} · Método: {a.get('metodo', 'N/D')}")


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA: MIS MARCAS
# ─────────────────────────────────────────────────────────────────────────────

elif pagina == "👥 Mis Marcas":
    st.title("👥 Gestión de Marcas")

    clientes = cargar_clientes()

    # Tabla de marcas actuales
    st.subheader(f"Marcas en vigilancia ({len(clientes)})")

    if clientes:
        import pandas as pd
        df = pd.DataFrame(clientes)
        df.columns = [c.capitalize().replace("_", " ") for c in df.columns]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No hay marcas configuradas aún.")

    st.divider()

    # Agregar nueva marca
    st.subheader("➕ Agregar nueva marca")

    CLASES_INPI = {
        35: "Clase 35 — Publicidad / E-commerce",
        36: "Clase 36 — Finanzas / Seguros",
        38: "Clase 38 — Telecomunicaciones",
        41: "Clase 41 — Educación / Contenido digital",
        42: "Clase 42 — Tecnología / Software / SaaS",
        43: "Clase 43 — Gastronomía / Alimentos",
        44: "Clase 44 — Salud / Medicina",
        45: "Clase 45 — Legal / Seguridad",
    }

    with st.form("form_nueva_marca", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nuevo_nombre  = st.text_input("Nombre de la marca *", placeholder="Ej: MI MARCA")
            nuevo_titular = st.text_input("Titular registral *",  placeholder="Ej: Mi Empresa SA")
        with col2:
            nueva_clase   = st.selectbox("Clase INPI *", options=list(CLASES_INPI.keys()),
                                          format_func=lambda x: CLASES_INPI[x])
            nuevo_contacto = st.text_input("Email de contacto", placeholder="legal@empresa.com")

        nuevas_notas = st.text_area("Notas (opcional)", placeholder="Ej: Vigilar variantes con SHOP, GO, PRO")

        submitted = st.form_submit_button("Agregar marca")
        if submitted:
            if not nuevo_nombre.strip() or not nuevo_titular.strip():
                st.error("Nombre y titular son obligatorios.")
            elif any(c["nombre"].upper() == nuevo_nombre.upper().strip() and c["clase"] == nueva_clase for c in clientes):
                st.warning(f"Ya existe '{nuevo_nombre.upper()}' en Clase {nueva_clase}.")
            else:
                clientes.append({
                    "nombre":   nuevo_nombre.upper().strip(),
                    "clase":    nueva_clase,
                    "titular":  nuevo_titular.strip(),
                    "contacto": nuevo_contacto.strip(),
                    "notas":    nuevas_notas.strip(),
                })
                guardar_clientes(clientes)
                st.success(f"✅ **{nuevo_nombre.upper()}** (Clase {nueva_clase}) agregada correctamente.")
                st.rerun()

    st.divider()

    # Eliminar marca
    if clientes:
        st.subheader("🗑️ Eliminar marca")
        opciones = [f"{c['nombre']} — Clase {c['clase']}" for c in clientes]
        a_eliminar = st.selectbox("Seleccionar marca a eliminar", opciones)
        if st.button("Eliminar marca seleccionada", type="secondary"):
            idx = opciones.index(a_eliminar)
            eliminada = clientes.pop(idx)
            guardar_clientes(clientes)
            st.success(f"✅ '{eliminada['nombre']}' eliminada.")
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA: EJECUTAR
# ─────────────────────────────────────────────────────────────────────────────

elif pagina == "⚙️ Ejecutar":
    st.title("⚙️ Ejecutar Vigilancia")

    st.markdown("""
    Lanzá una ejecución manual del sistema directamente desde el dashboard.
    En producción esto corre automáticamente **todos los lunes a las 8 AM** vía GitHub Actions.
    """)

    col1, col2 = st.columns(2)
    with col1:
        modo = st.radio("Modo de ejecución", ["demo (datos simulados)", "real (scraping INPI)"],
                        help="Demo: perfecto para testear. Real: accede al portal del INPI.")
    with col2:
        notificar = st.checkbox("Enviar notificaciones por email/WhatsApp",
                                value=False,
                                help="Requiere SendGrid y Twilio configurados.")

    st.divider()

    if st.button("▶️ Ejecutar ahora", type="primary"):
        modo_arg      = "demo" if "demo" in modo else "real"
        notif_arg     = "true" if notificar else "false"

        with st.spinner(f"Ejecutando en modo **{modo_arg}**..."):
            try:
                resultado = subprocess.run(
                    [sys.executable, "inpi_vigilancia_marcas.py",
                     "--modo", modo_arg, "--notificar", notif_arg],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=str(Path(__file__).parent),
                )

                if resultado.returncode == 0:
                    st.success("✅ Ejecución completada exitosamente.")
                else:
                    st.error(f"❌ La ejecución terminó con errores (código {resultado.returncode}).")

                with st.expander("Ver output completo", expanded=True):
                    output = resultado.stdout + resultado.stderr
                    st.code(output[-3000:] if len(output) > 3000 else output, language="text")

                st.rerun()

            except subprocess.TimeoutExpired:
                st.error("⏰ Timeout: la ejecución superó los 2 minutos. Verificá los logs.")
            except FileNotFoundError:
                st.error("❌ No se encontró `inpi_vigilancia_marcas.py`. Verificá que estés en la carpeta correcta.")
            except Exception as e:
                st.error(f"❌ Error inesperado: {e}")

    st.divider()

    # Último reporte
    reporte = ultimo_reporte()
    if reporte:
        st.subheader("📄 Último reporte generado")
        with open(reporte, "r", encoding="utf-8") as f:
            contenido = f.read()
        st.download_button(
            label=f"⬇️ Descargar {Path(reporte).name}",
            data=contenido,
            file_name=Path(reporte).name,
            mime="text/plain",
        )
        with st.expander("Ver reporte"):
            st.code(contenido, language="text")


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA: LOGS
# ─────────────────────────────────────────────────────────────────────────────

elif pagina == "📋 Logs":
    st.title("📋 Logs del Sistema")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🕐 Log de ejecución")
        lineas = cargar_log_ejecucion()
        if lineas:
            # Color coding de niveles
            log_coloreado = []
            for l in lineas:
                if "[ERROR]" in l:
                    log_coloreado.append(f"❌ {l}")
                elif "[WARNING]" in l:
                    log_coloreado.append(f"⚠️  {l}")
                elif "✅" in l or "INFO" in l:
                    log_coloreado.append(l)
                else:
                    log_coloreado.append(l)
            st.code("\n".join(log_coloreado[-30:]), language="text")
        else:
            st.info("No hay logs disponibles aún.")

    with col2:
        st.subheader("📦 Historial de expedientes procesados")
        procesados = cargar_procesados()
        exps = procesados.get("expedientes_procesados", {})

        if not exps:
            st.info("Sin expedientes procesados aún. El historial se construye con cada ejecución.")
        else:
            ultima = procesados.get("ultima_actualizacion", "N/D")
            if ultima and ultima != "N/D":
                try:
                    ts = datetime.fromisoformat(ultima)
                    st.caption(f"Última actualización: {ts.strftime('%d/%m/%Y %H:%M')}")
                except ValueError:
                    pass

            import pandas as pd
            rows = []
            for exp_id, datos in exps.items():
                rows.append({
                    "Expediente":   exp_id,
                    "Marca":        datos.get("marca_colisionada", "N/D"),
                    "Solicitud":    datos.get("solicitud", "N/D"),
                    "Score":        datos.get("score_maximo", 0),
                    "Detectado":    datos.get("primera_deteccion", "N/D"),
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"Total: {len(rows)} expediente(s) en historial")

    st.divider()

    # Archivos de reportes disponibles
    st.subheader("📁 Reportes disponibles")
    reportes = sorted(glob.glob("reporte_alertas_*.txt"), reverse=True)
    alertas_json = sorted(glob.glob("alertas_*.json"), reverse=True)

    if reportes:
        for r in reportes[:5]:
            with open(r, "r", encoding="utf-8") as f:
                contenido = f.read()
            st.download_button(
                label=f"⬇️ {Path(r).name}",
                data=contenido,
                file_name=Path(r).name,
                mime="text/plain",
                key=f"dl_{r}",
            )
    else:
        st.info("No hay reportes generados aún.")
