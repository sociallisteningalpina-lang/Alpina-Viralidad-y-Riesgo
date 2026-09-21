import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ==========================================
# 1. CONFIGURACIÓN INTERNA DE LA CRISIS
# ==========================================
API_KEY = '5ec7c022ffd040ed'
BASE_URL = 'https://api.youscan.io/api/external/'
TOPICO_CRISIS = "Crisis Prueba"

headers = {
    'X-API-KEY': API_KEY,
    'Accept': 'application/json'
}

# Configuración de página en Streamlit
st.set_page_config(
    page_title="Alpina - Monitor de Incidentes (M.I.A.)",
    page_icon="🚨",
    layout="wide"
)

# Título e Introducción M.I.A.
st.title("🚨 Alpina: Reporte de Crisis M.I.A. V3")
st.markdown("""
> ℹ️ **M.I.A.** es el **Modelo de Incidentes Alpina** que nos permite determinar el riesgo de viralidad en redes sociales de cualquier tema en tiempo real.
""")
st.caption(f"Monitoreo automatizado vía YouScan | Tópico activo: **{TOPICO_CRISIS}**")

# ==========================================
# 2. BARRA LATERAL (AJUSTES)
# ==========================================
st.sidebar.header("⚙️ Ajustes de Crisis")

cobertura_actual = st.sidebar.radio(
    "Cobertura Mediática",
    ["Sin Cobertura", "Local", "Regional", "Nacional"],
    help="Puntaje M.I.A.: Nacional (+15 pts), Regional (+10 pts), Local (+6 pts), Sin Cobertura (0 pts)."
)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Capturar Nuevo Corte", type="primary"):
    st.cache_data.clear()

# ==========================================
# 3. CALCULADORA M.I.A. V3
# ==========================================
def calcular_semaforo(menciones, vistas, engagement, prom_vistas_hora, cobertura="Sin Cobertura"):
    # 1. Puntos Vistas (50%)
    if vistas < 100000: pts_vistas = 2
    elif vistas <= 1000000: pts_vistas = 6
    elif vistas <= 4000000: pts_vistas = 8
    else: pts_vistas = 15

    # 2. Puntos Engagement (30%)
    if engagement < 20000: pts_eng = 2
    elif engagement <= 75000: pts_eng = 8
    elif engagement <= 150000: pts_eng = 11
    else: pts_eng = 15

    # 3. Puntos Menciones (20%)
    if menciones == 0: pts_men = 0
    elif menciones <= 100: pts_men = 2
    elif menciones <= 800: pts_men = 8
    else: pts_men = 15

    alcance_redes = (pts_vistas * 0.5) + (pts_eng * 0.3) + (pts_men * 0.2)

    # 4. Cobertura Mediática (Lectura automatizada V3)
    cob_str = cobertura.lower().strip()
    if "nacional" in cob_str:
        pts_cob = 15
    elif "regional" in cob_str:
        pts_cob = 10
    elif "local" in cob_str:
        pts_cob = 6
    else:
        pts_cob = 0

    # 5. Velocidad (Vistas/Hora)
    if prom_vistas_hora <= 0: pts_vel = 0
    elif prom_vistas_hora < 5000: pts_vel = 2
    elif prom_vistas_hora <= 40000: pts_vel = 8
    elif prom_vistas_hora <= 150000: pts_vel = 11
    else: pts_vel = 15

    indice = alcance_redes + pts_cob + pts_vel

    if indice < 15:
        color = "🟢 RIESGO BAJO"
        nivel = "low"
    elif indice < 30:
        color = "🟡 RIESGO MEDIO"
        nivel = "medium"
    else:
        color = "🔴 RIESGO ALTO (CRÍTICO)"
        nivel = "high"

    return round(indice, 1), color, nivel, round(alcance_redes, 1), pts_cob, pts_vel

def detectar_plataforma(url):
    u = str(url).lower()
    if 'tiktok' in u: return 'TikTok'
    elif 'instagram' in u: return 'Instagram'
    elif 'twitter' in u or 'x.com' in u: return 'X (Twitter)'
    elif 'facebook' in u: return 'Facebook'
    elif 'youtube' in u: return 'YouTube'
    else: return 'Prensa / Web'

# Guardar historial en sesión de Streamlit
if 'historial_horas' not in st.session_state:
    st.session_state['historial_horas'] = []

# ==========================================
# 4. EXTRACCIÓN DE DATOS DE YOUSCAN
# ==========================================
@st.cache_data(ttl=60)
def obtener_topic_id():
    try:
        res = requests.get(BASE_URL + 'topics', headers=headers, timeout=10)
        if res.status_code == 200:
            topics = res.json().get('topics', res.json())
            for t in topics:
                if t.get('name') == TOPICO_CRISIS:
                    return t.get('id')
    except Exception:
        pass
    return None

topic_id = obtener_topic_id()

if not topic_id:
    st.error(f"❌ No se encontró el tópico '{TOPICO_CRISIS}' en YouScan. Verifica el nombre exacto.")
else:
    ahora = datetime.utcnow()
    from_iso = "2026-01-01T00:00:00Z"
    to_iso = ahora.strftime('%Y-%m-%dT%H:%M:%SZ')
    hora_colombia = (ahora - timedelta(hours=5)).strftime('%H:%M')

    url_metrics = f"{BASE_URL}topics/{topic_id}/statistics/metrics"
    url_sents = f"{BASE_URL}topics/{topic_id}/statistics/sentiments"
    url_mentions = f"{BASE_URL}topics/{topic_id}/mentions"

    try:
        res_m = requests.get(url_metrics, headers=headers, params={'from': from_iso, 'to': to_iso})
        res_s = requests.get(url_sents, headers=headers, params={'from': from_iso, 'to': to_iso})

        if res_m.status_code == 200 and res_s.status_code == 200:
            data_m = res_m.json()
            data_s = res_s.json()

            menciones_totales = data_m.get('totalCount', 0)
            vistas = data_m.get('viewsCount', 0)
            engagement = data_m.get('totalEngagement', 0)

            pos, neg, neu = 0, 0, 0
            for s in data_s.get('sentiments', []):
                s_name = str(s.get('name', '')).lower()
                if 'pos' in s_name: pos = s.get('count', 0)
                elif 'neg' in s_name: neg = s.get('count', 0)
                elif 'neu' in s_name: neu = s.get('count', 0)

            historial = st.session_state['historial_horas']
            if not historial or historial[-1]['Hora de Corte'] != hora_colombia or historial[-1]['Visualizaciones'] != vistas:
                historial.append({
                    "Hora de Corte": hora_colombia,
                    "Menciones Totales": menciones_totales,
                    "Visualizaciones": vistas,
                    "Engagement": engagement,
                    "Positivas": pos,
                    "Negativas": neg,
                    "Neutrales": neu
                })

            df_historial = pd.DataFrame(historial)

            # CÁLCULOS AUTOMÁTICOS DE VELOCIDAD
            prom_vistas_hora = 0.0
            crec_menciones_prom = 0.0
            crec_eng_prom = 0.0

            if len(df_historial) > 1:
                crecimiento_vistas = df_historial['Visualizaciones'].diff().dropna()
                crecimiento_menciones = df_historial['Menciones Totales'].diff().dropna()
                crecimiento_eng = df_historial['Engagement'].diff().dropna()

                prom_vistas_hora = float(crecimiento_vistas.mean())
                crec_menciones_prom = float(crecimiento_menciones.mean())
                crec_eng_prom = float(crecimiento_eng.mean())

            # CALCULADORA M.I.A.
            indice_mia, color_semaforo, nivel_risk, pts_alc, pts_cob, pts_vel = calcular_semaforo(
                menciones=menciones_totales,
                vistas=vistas,
                engagement=engagement,
                prom_vistas_hora=prom_vistas_hora,
                cobertura=cobertura_actual
            )

            # ==========================================
            # 5. DESPLIEGUE VISUAL
            # ==========================================
            st.subheader("🚨 Alerta del Modelo de Incidentes Alpina (M.I.A.)")

            c_status, c_score, c_menc, c_views, c_eng = st.columns([1.3, 1.1, 1, 1, 1])

            with c_status:
                if nivel_risk == "high":
                    st.error(f"**ESTADO ACTUAL**\n### {color_semaforo}")
                elif nivel_risk == "medium":
                    st.warning(f"**ESTADO ACTUAL**\n### {color_semaforo}")
                else:
                    st.success(f"**ESTADO ACTUAL**\n### {color_semaforo}")

            with c_score:
                st.metric("Puntaje Total", f"{indice_mia} pts")
                st.caption(f"Máx: 45.0 pts | Alc: {pts_alc} | Cob: {pts_cob} | Vel: {pts_vel}")
            with c_menc:
                st.metric("Menciones Totales", f"{menciones_totales:,}", delta=f"+{crec_menciones_prom:.1f}/hr" if len(df_historial) > 1 else None)
            with c_views:
                st.metric("Visualizaciones", f"{vistas:,}", delta=f"+{prom_vistas_hora:.1f}/hr" if len(df_historial) > 1 else None)
            with c_eng:
                st.metric("Engagement", f"{engagement:,}", delta=f"+{crec_eng_prom:.1f}/hr" if len(df_historial) > 1 else None)

            # Escala M.I.A. Clarificada
            st.markdown("""
            > **Escala M.I.A. de Evaluación de Riesgo:**  
            > 🟢 **BAJO (< 15 pts):** Impacto controlado y monitoreo estándar.  
            > 🟡 **MEDIO (15 a 29 pts):** Crecimiento acelerado; evaluar acciones de contención.  
            > 🔴 **ALTO (30 a 45 pts):** Viralidad crítica; activar protocolo de crisis inmediatamente.
            """)
            st.divider()

            # --- CONVERSATION STREAM ---
            res_mentions = requests.get(url_mentions, headers=headers, params={'from': from_iso, 'to': to_iso, 'size': 500})
            stream_menciones = []
            if res_mentions.status_code == 200:
                for m in res_mentions.json().get('mentions', []):
                    eng_data = m.get('engagement', {})
                    total_eng_post = (
                        int(eng_data.get('likes', 0) or 0) +
                        int(eng_data.get('comments', 0) or 0) +
                        int(eng_data.get('reposts', 0) or eng_data.get('shares', 0) or 0)
                    )
                    u_link = m.get('url', '')
                    plat = detectar_plataforma(u_link)
                    stream_menciones.append({
                        "Fecha de Publicación": m.get('published'),
                        "Plataforma": plat,
                        "Autor": m.get('author', {}).get('name', 'Desconocido'),
                        "Impacto Viral": total_eng_post,
                        "Sentimiento": m.get('sentiment', 'neutral'),
                        "Texto": m.get('text', ''),
                        "URL": u_link
                    })

            df_stream = pd.DataFrame(stream_menciones)
            if not df_stream.empty:
                df_stream = df_stream.drop_duplicates(subset=['URL']).sort_values(by="Impacto Viral", ascending=False)

            # ==========================================
            # 6. PESTAÑAS
            # ==========================================
            tab_evol, tab_redes, tab_sent, tab_stream = st.tabs([
                "📈 Evolución Temporal", 
                "📱 Desglose por Red Social", 
                "📊 Sentimiento & M.I.A.", 
                "🔥 Conversation Stream"
            ])

            # TAB 1: EVOLUCIÓN TEMPORAL
            with tab_evol:
                st.subheader("📈 Curvas de Acumulado de la Crisis")
                if len(df_historial) >= 1:
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        fig_m = px.line(df_historial, x="Hora de Corte", y="Menciones Totales", markers=True, title="Acumulado Menciones", color_discrete_sequence=['red'])
                        fig_m.update_layout(template="plotly_white")
                        st.plotly_chart(fig_m, width="stretch")

                    with col2:
                        fig_v = px.line(df_historial, x="Hora de Corte", y="Visualizaciones", markers=True, title="Acumulado Vistas", color_discrete_sequence=['orange'])
                        fig_v.update_layout(template="plotly_white")
                        st.plotly_chart(fig_v, width="stretch")

                    with col3:
                        fig_e = px.line(df_historial, x="Hora de Corte", y="Engagement", markers=True, title="Acumulado Engagement", color_discrete_sequence=['blue'])
                        fig_e.update_layout(template="plotly_white")
                        st.plotly_chart(fig_e, width="stretch")

                    st.markdown("#### 📑 Histórico de Capturas de Pantalla")
                    st.dataframe(df_historial.sort_values("Hora de Corte", ascending=False), width="stretch")

            # TAB 2: DESGLOSE POR RED SOCIAL
            with tab_redes:
                st.subheader("📱 Métricas e Impacto por Red Social / Canal")
                if not df_stream.empty:
                    col_r1, col_r2 = st.columns(2)

                    with col_r1:
                        fig_plat_count = px.pie(
                            df_stream, names="Plataforma", title="Distribución de Publicaciones por Plataforma",
                            hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel
                        )
                        st.plotly_chart(fig_plat_count, width="stretch")

                    with col_r2:
                        fig_plat_eng = px.bar(
                            df_stream.groupby("Plataforma")["Impacto Viral"].sum().reset_index(),
                            x="Plataforma", y="Impacto Viral", color="Plataforma",
                            title="Impacto Viral Acumulado por Red Social", text="Impacto Viral"
                        )
                        fig_plat_eng.update_layout(template="plotly_white")
                        st.plotly_chart(fig_plat_eng, width="stretch")

                    filtro_plat = st.multiselect("Filtrar publicaciones por Red Social:", df_stream["Plataforma"].unique(), default=df_stream["Plataforma"].unique())
                    df_filtered = df_stream[df_stream["Plataforma"].isin(filtro_plat)]
                    st.dataframe(df_filtered[['Plataforma', 'Autor', 'Impacto Viral', 'Sentimiento', 'Texto', 'URL']], width="stretch")

            # TAB 3: SENTIMIENTO & M.I.A.
            with tab_sent:
                col_s1, col_s2 = st.columns(2)

                with col_s1:
                    st.subheader("📊 Distribución del Sentimiento")
                    df_sent = pd.DataFrame({
                        "Sentimiento": ["Positivo", "Neutral", "Negativo"],
                        "Menciones": [pos, neu, neg]
                    })
                    fig_sent = px.pie(
                        df_sent, values="Menciones", names="Sentimiento", color="Sentimiento",
                        color_discrete_map={"Positivo": "#2ca02c", "Neutral": "#7f7f7f", "Negativo": "#d62728"},
                        hole=0.4
                    )
                    fig_sent.update_layout(template="plotly_white")
                    st.plotly_chart(fig_sent, width="stretch")

                with col_s2:
                    st.subheader("⚙️ Desglose de Puntos M.I.A.")
                    df_pts = pd.DataFrame({
                        "Componente": ["Alcance Redes (50/30/20)", "Cobertura Mediática", "Velocidad Vistas/Hr"],
                        "Puntos": [pts_alc, pts_cob, pts_vel]
                    })
                    fig_pts = px.bar(
                        df_pts, x="Componente", y="Puntos", text="Puntos", color="Componente",
                        color_discrete_sequence=["#1f77b4", "#ff7f0e", "#d62728"]
                    )
                    fig_pts.update_layout(template="plotly_white", showlegend=False)
                    st.plotly_chart(fig_pts, width="stretch")

            # TAB 4: CONVERSATION STREAM
            with tab_stream:
                st.subheader("🔥 Publicaciones Más Virales Absolutas (Conversation Stream)")
                if not df_stream.empty:
                    st.dataframe(
                        df_stream[['Fecha de Publicación', 'Plataforma', 'Autor', 'Impacto Viral', 'Sentimiento', 'Texto', 'URL']].head(30),
                        column_config={
                            "URL": st.column_config.LinkColumn("Enlace Directo")
                        },
                        width="stretch"
                    )

    except Exception as e:
        st.error(f"Error procesando los datos de YouScan: {e}")
