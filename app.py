import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Configuración de página
st.set_page_config(
    page_title="Alpina - Monitor M.I.A. (YouScan)",
    page_icon="🚨",
    layout="wide"
)

# Título Principal
st.title("🚨 Alpina: Monitor de Crisis M.I.A. V3")
st.caption("Conexión Directa a la API de YouScan | Modelo de Incidentes Alpina")

# ==========================================
# 1. BARRA LATERAL (CONFIGURACIÓN)
# ==========================================
st.sidebar.header("⚙️ Configuración YouScan & Crisis")

api_key = st.sidebar.text_input(
    "YouScan API Key",
    value="5ec7c022ffd040ed",
    type="password",
    help="Clave de acceso para la API externa de YouScan"
)

base_url = "https://api.youscan.io/api/external/"
headers = {
    'X-API-KEY': api_key,
    'Accept': 'application/json'
}

# Obtener lista de tópicos dinámicamente desde YouScan
@st.cache_data(ttl=300)
def fetch_topics(key):
    try:
        res = requests.get(base_url + 'topics', headers={'X-API-KEY': key, 'Accept': 'application/json'}, timeout=10)
        if res.status_code == 200:
            topics_data = res.json().get('topics', res.json())
            return {t['name']: t['id'] for t in topics_data if 'name' in t and 'id' in t}
    except Exception:
        pass
    return {}

topics_dict = fetch_topics(api_key)

if topics_dict:
    topico_seleccionado = st.sidebar.selectbox("Seleccionar Tópico de Crisis", list(topics_dict.keys()))
    topic_id = topics_dict[topico_seleccionado]
else:
    topico_input = st.sidebar.text_input("Nombre del Tópico", value="Crisis Prueba")
    topic_id = None

cobertura_actual = st.sidebar.radio(
    "Cobertura Mediática",
    ["Local", "Nacional / Internacional"],
    help="Añade +6 puntos si la crisis tiene cobertura mediática Local según la fórmula M.I.A."
)

prom_vistas_hora_input = st.sidebar.number_input(
    "Velocidad Estimada (Vistas/Hora)",
    min_value=0,
    value=0,
    step=1000,
    help="Ingresa el promedio de crecimiento de vistas/hora para calcular la velocidad M.I.A."
)

# ==========================================
# 2. CALCULADORA M.I.A. (V3)
# ==========================================
def calcular_semaforo(menciones, vistas, engagement, prom_vistas_hora, cobertura):
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

    # Alcance Redes
    alcance_redes = (pts_vistas * 0.5) + (pts_eng * 0.3) + (pts_men * 0.2)

    # 4. Cobertura Mediática
    pts_cob = 6 if "local" in cobertura.lower() else 0

    # 5. Velocidad (Vistas/Hora)
    if prom_vistas_hora <= 0: pts_vel = 0
    elif prom_vistas_hora < 5000: pts_vel = 2
    elif prom_vistas_hora <= 40000: pts_vel = 8
    elif prom_vistas_hora <= 150000: pts_vel = 11
    else: pts_vel = 15

    indice = alcance_redes + pts_cob + pts_vel

    if indice < 15:
        color_texto = "🟢 RIESGO BAJO"
        nivel = "low"
    elif indice < 30:
        color_texto = "🟡 RIESGO MEDIO"
        nivel = "medium"
    else:
        color_texto = "🔴 RIESGO ALTO (CRÍTICO)"
        nivel = "high"

    return round(indice, 1), color_texto, nivel, round(alcance_redes, 1), pts_cob, pts_vel

# ==========================================
# 3. EXTRACCIÓN DE DATOS DE YOUSCAN
# ==========================================
if st.sidebar.button("🔄 Actualizar Datos Ahora", type="primary"):
    st.cache_data.clear()

if topic_id or api_key:
    # Definir rango de fechas
    ahora = datetime.utcnow()
    from_iso = "2026-01-01T00:00:00Z"
    to_iso = ahora.strftime('%Y-%m-%dT%H:%M:%SZ')

    # Endpoints de YouScan
    url_metrics = f"{base_url}topics/{topic_id}/statistics/metrics"
    url_sents = f"{base_url}topics/{topic_id}/statistics/sentiments"
    url_mentions = f"{base_url}topics/{topic_id}/mentions"
    params_date = {'from': from_iso, 'to': to_iso}

    try:
        res_m = requests.get(url_metrics, headers=headers, params=params_date)
        res_s = requests.get(url_sents, headers=headers, params=params_date)
        
        if res_m.status_code == 200 and res_s.status_code == 200:
            data_m = res_m.json()
            data_s = res_s.json()

            menciones_totales = data_m.get('totalCount', 0)
            vistas_totales = data_m.get('viewsCount', 0)
            engagement_total = data_m.get('totalEngagement', 0)

            # Sentimientos
            pos, neg, neu = 0, 0, 0
            for s in data_s.get('sentiments', []):
                s_name = str(s.get('name', '')).lower()
                if 'pos' in s_name: pos = s.get('count', 0)
                elif 'neg' in s_name: neg = s.get('count', 0)
                elif 'neu' in s_name: neu = s.get('count', 0)

            # Calcular Alerta M.I.A.
            indice_mia, status_str, nivel_risk, pts_alc, pts_cob, pts_vel = calcular_semaforo(
                menciones_totales, vistas_totales, engagement_total, prom_vistas_hora_input, cobertura_actual
            )

            # --- DESPLIEGUE DEL SEMÁFORO ---
            st.subheader("🚦 Alerta Modelo de Incidentes Alpina (M.I.A.)")
            
            c_status, c_score, c_menc, c_views, c_eng = st.columns(5)
            
            with c_status:
                if nivel_risk == "high":
                    st.error(f"**ESTADO ACTUAL**\n### {status_str}")
                elif nivel_risk == "medium":
                    st.warning(f"**ESTADO ACTUAL**\n### {status_str}")
                else:
                    st.success(f"**ESTADO ACTUAL**\n### {status_str}")
                    
            with c_score:
                st.metric("Puntaje M.I.A.", f"{indice_mia} / 45.0 pts")
                st.caption(f"Alcance: {pts_alc} | Cob: {pts_cob} | Vel: {pts_vel}")
            with c_menc:
                st.metric("Menciones Totales", f"{menciones_totales:,}")
            with c_views:
                st.metric("Visualizaciones", f"{vistas_totales:,}")
            with c_eng:
                st.metric("Engagement Total", f"{engagement_total:,}")

            st.divider()

            # --- SECCIÓN GRÁFICAS DE SENTIMIENTO Y DESGLOSE ---
            col_chart1, col_chart2 = st.columns([1, 1])

            with col_chart1:
                st.subheader("📊 Distribución del Sentimiento")
                df_sent = pd.DataFrame({
                    "Sentimiento": ["Positivo", "Neutral", "Negativo"],
                    "Menciones": [pos, neu, neg]
                })
                fig_sent = px.pie(
                    df_sent, values="Menciones", names="Sentimiento",
                    color="Sentimiento",
                    color_discrete_map={"Positivo": "#2ca02c", "Neutral": "#7f7f7f", "Negativo": "#d62728"},
                    hole=0.4
                )
                fig_sent.update_layout(template="plotly_white")
                st.plotly_chart(fig_sent, width="stretch")

            with col_chart2:
                st.subheader("⚙️ Composición del Puntaje M.I.A.")
                df_pts = pd.DataFrame({
                    "Componente": ["Alcance Redes (50/30/20)", "Cobertura Mediática", "Velocidad (Vistas/Hora)"],
                    "Puntos": [pts_alc, pts_cob, pts_vel]
                })
                fig_pts = px.bar(
                    df_pts, x="Componente", y="Puntos", text="Puntos",
                    color="Componente",
                    color_discrete_sequence=["#1f77b4", "#ff7f0e", "#d62728"]
                )
                fig_pts.update_layout(template="plotly_white", showlegend=False)
                st.plotly_chart(fig_pts, width="stretch")

            # --- CONVERSATION STREAM (POSTS MÁS VIRALES) ---
            st.divider()
            st.subheader("🔥 Conversation Stream: Publicaciones Más Virales")

            res_mentions = requests.get(url_mentions, headers=headers, params={'from': from_iso, 'to': to_iso, 'size': 100})
            if res_mentions.status_code == 200:
                mentions_list = res_mentions.json().get('mentions', [])
                stream_data = []
                
                for m in mentions_list:
                    eng_data = m.get('engagement', {})
                    total_eng_post = (
                        int(eng_data.get('likes', 0) or 0) +
                        int(eng_data.get('comments', 0) or 0) +
                        int(eng_data.get('reposts', 0) or eng_data.get('shares', 0) or 0)
                    )
                    stream_data.append({
                        "Fecha": m.get('published'),
                        "Autor": m.get('author', {}).get('name', 'Desconocido'),
                        "Impacto Viral": total_eng_post,
                        "Sentimiento": m.get('sentiment', 'neutral'),
                        "Texto": m.get('text', ''),
                        "URL": m.get('url', '')
                    })

                if stream_data:
                    df_stream = pd.DataFrame(stream_data).drop_duplicates(subset=['URL']).sort_values(by="Impacto Viral", ascending=False)
                    st.dataframe(
                        df_stream,
                        column_config={
                            "URL": st.column_config.LinkColumn("Enlace Directo")
                        },
                        width="stretch"
                    )
                else:
                    st.info("No se encontraron menciones para el rango seleccionado.")
            else:
                st.warning("No se pudo obtener el Conversation Stream desde YouScan.")

        else:
            st.error(f"Error consultando la API de YouScan. Código HTTP: {res_m.status_code}")

    except Exception as e:
        st.error(f"Error de conexión con YouScan: {e}")
