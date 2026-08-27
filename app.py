import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(
    page_title="Alpina - Monitor de Riesgo Multi-Plataforma",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Alpina: Dashboard de Alerta Temprana & Viralidad")
st.markdown("Monitoreo automatizado de métricas reputacionales en tiempo real.")

# Sidebar - Configuración
st.sidebar.header("⚙️ Configuración del Feed")
sheet_url = st.sidebar.text_input(
    "URL pública de Google Sheets",
    help="Ingresa el link público de tu Google Sheet con acceso de lectura"
)

plataforma = st.sidebar.selectbox(
    "Red Social a Monitorear",
    ["TikTok", "Instagram", "Facebook", "X"]
)

st.sidebar.markdown("---")
st.sidebar.header("🎚️ Umbrales de Alerta")
umbral_amarillo = st.sidebar.number_input("🟡 Umbral Amarillo (Precaución)", min_value=1, value=50)
umbral_rojo = st.sidebar.number_input("🔴 Umbral Rojo (Alerta Alta)", min_value=1, value=200)

@st.cache_data(ttl=60)
def load_data(url, sheet_name):
    try:
        if "/edit" in url:
            base_url = url.split("/edit")[0]
            csv_url = f"{base_url}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
        else:
            csv_url = url
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        return None

# Mapeos prioritarios específicos por plataforma para evitar duplicados
platform_mappings = {
    'TikTok': [
        ('views', 'Vistas'),
        ('likes', 'Likes'),
        ('comments', 'Comentarios'),
        ('shares', 'Compartidos'),
        ('saves', 'Guardados'),
        ('reposts', 'Reposts'),
        ('scrapedAt', 'Fecha'),
        ('postUrl', 'URL'),
        ('inputUrl', 'URL'),
        ('profileHandle', 'Autor'),
        ('profileName', 'Autor')
    ],
    'Instagram': [
        ('videoViewCount', 'Vistas'),
        ('videoPlayCount', 'Vistas'),
        ('likesCount', 'Likes'),
        ('commentsCount', 'Comentarios'),
        ('timestamp', 'Fecha'),
        ('url', 'URL'),
        ('inputUrl', 'URL'),
        ('ownerUsername', 'Autor')
    ],
    'X': [
        ('viewCount', 'Vistas'),
        ('likeCount', 'Likes'),
        ('replyCount', 'Comentarios'),
        ('retweetCount', 'Compartidos'),
        ('quoteCount', 'Compartidos'),
        ('bookmarkCount', 'Guardados'),
        ('createdAt', 'Fecha'),
        ('twitterUrl', 'URL'),
        ('url', 'URL'),
        ('author/userName', 'Autor'),
        ('author/name', 'Autor')
    ],
    'Facebook': [
        ('views', 'Vistas'),
        ('plays', 'Vistas'),
        ('likes', 'Likes'),
        ('comments', 'Comentarios'),
        ('shares', 'Compartidos'),
        ('scrapedAt', 'Fecha'),
        ('contentUrl', 'URL'),
        ('inputUrl', 'URL'),
        ('profileUsername', 'Autor'),
        ('profileName', 'Autor')
    ]
}

if sheet_url:
    df_raw = load_data(sheet_url, plataforma)
    
    if df_raw is not None and not df_raw.empty:
        mapping = platform_mappings.get(plataforma, [])
        df_cols_lower = {str(c).lower(): c for c in df_raw.columns}
        rename_dict = {}
        already_mapped_targets = set()
        
        # Mapear garantizando 1 sola asignación por métrica
        for src_key, target in mapping:
            src_lower = src_key.lower()
            if src_lower in df_cols_lower and target not in already_mapped_targets:
                actual_col = df_cols_lower[src_lower]
                rename_dict[actual_col] = target
                already_mapped_targets.add(target)
                
        df = df_raw.rename(columns=rename_dict)
        
        # Garantizar que NO existan nombres de columnas duplicados en Pandas
        cols = list(df.columns)
        seen = {}
        new_cols = []
        for c in cols:
            if c in seen:
                seen[c] += 1
                new_cols.append(f"{c}_{seen[c]}")
            else:
                seen[c] = 0
                new_cols.append(c)
        df.columns = new_cols
        
        # Asegurar columnas numéricas básicas
        metric_cols = ["Vistas", "Likes", "Comentarios", "Compartidos", "Guardados"]
        for col in metric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            else:
                df[col] = 0.0

        # Procesar columna Fecha
        if "Fecha" in df.columns:
            df["Fecha"] = pd.to_datetime(df["Fecha"], errors='coerce')
            df = df.dropna(subset=["Fecha"]).sort_values("Fecha").reset_index(drop=True)
        else:
            df["Fecha"] = pd.date_range(end=pd.Timestamp.now(), periods=len(df), freq="30min")

        if len(df) > 0:
            df["Delta_Vistas"] = df["Vistas"].diff().fillna(df["Vistas"].iloc[0])
            df["Delta_Comentarios"] = df["Comentarios"].diff().fillna(df["Comentarios"].iloc[0])
            df["Delta_Compartidos"] = df["Compartidos"].diff().fillna(df["Compartidos"].iloc[0])

            # Índice de Velocidad de Riesgo
            df["Velocidad_Riesgo"] = (df["Delta_Comentarios"] * 1.5) + (df["Delta_Compartidos"] * 2.0)
            ultima_velocidad = df["Velocidad_Riesgo"].iloc[-1]
            
            # Información de la publicación
            info_text = []
            if "Autor" in df.columns and pd.notna(df['Autor'].iloc[-1]):
                info_text.append(f"📌 **Autor:** `@{df['Autor'].iloc[-1]}`")
            if "URL" in df.columns and pd.notna(df['URL'].iloc[-1]):
                info_text.append(f"🔗 **Link:** {df['URL'].iloc[-1]}")
            
            if info_text:
                st.caption(" | ".join(info_text))
            
            # KPI & Semáforo de Estado
            st.subheader(f"🚦 Estado del Riesgo en {plataforma}")
            
            col_status, col_kpi1, col_kpi2, col_kpi3, col_kpi4, col_kpi5 = st.columns(6)
            
            with col_status:
                if ultima_velocidad >= umbral_rojo:
                    st.error("🔴 **ALERTA ALTA**\nViralidad crítica")
                elif ultima_velocidad >= umbral_amarillo:
                    st.warning("🟡 **PRECAUCIÓN**\nCrecimiento acelerado")
                else:
                    st.success("🟢 **ESTABLE**\nBajo control")
                    
            with col_kpi1:
                st.metric("Vistas Totales", f"{int(df['Vistas'].iloc[-1]):,}", delta=f"+{int(df['Delta_Vistas'].iloc[-1])}")
            with col_kpi2:
                st.metric("Likes", f"{int(df['Likes'].iloc[-1]):,}")
            with col_kpi3:
                st.metric("Comentarios / Respuestas", f"{int(df['Comentarios'].iloc[-1]):,}", delta=f"+{int(df['Delta_Comentarios'].iloc[-1])}")
            with col_kpi4:
                st.metric("Compartidos / Retweets", f"{int(df['Compartidos'].iloc[-1]):,}", delta=f"+{int(df['Delta_Compartidos'].iloc[-1])}")
            with col_kpi5:
                st.metric("Guardados / Marcadores", f"{int(df['Guardados'].iloc[-1]):,}")

            st.divider()

            # Pestañas de Visualización
            tab1, tab2, tab3 = st.tabs(["📈 Crecimiento Acumulado", "⚡ Velocidad e Índice de Riesgo", "📋 Registros en Vivo"])

            with tab1:
                st.subheader("Evolución Temporal Acumulada")
                fig1 = go.Figure()
                fig1.add_trace(go.Scatter(x=df['Fecha'], y=df['Vistas'], name='Vistas', line=dict(color='#1f77b4', width=2)))
                fig1.add_trace(go.Scatter(x=df['Fecha'], y=df['Likes'], name='Likes', line=dict(color='#2ca02c', width=2)))
                fig1.add_trace(go.Scatter(x=df['Fecha'], y=df['Comentarios'], name='Comentarios / Respuestas', line=dict(color='#ff7f0e', width=2)))
                fig1.add_trace(go.Scatter(x=df['Fecha'], y=df['Compartidos'], name='Compartidos / Retweets', line=dict(color='#d62728', width=2)))
                fig1.update_layout(xaxis_title="Fecha / Hora", yaxis_title="Cantidad Acumulada", template="plotly_white", hovermode="x unified")
                st.plotly_chart(fig1, use_container_width=True)

            with tab2:
                st.subheader("Aceleración por Ejecución (Nuevas Interacciones)")
                fig2 = go.Figure()
                fig2.add_bar(x=df['Fecha'], y=df['Delta_Comentarios'], name='Nuevos Comentarios', marker_color='#ff7f0e')
                fig2.add_bar(x=df['Fecha'], y=df['Delta_Compartidos'], name='Nuevos Compartidos', marker_color='#d62728')
                fig2.add_trace(go.Scatter(x=df['Fecha'], y=df['Velocidad_Riesgo'], name='Índice de Riesgo Combinado', line=dict(color='black', width=3, dash='dash')))
                
                fig2.add_hline(y=umbral_rojo, line_dash="dot", line_color="red", annotation_text="Umbral Rojo")
                fig2.add_hline(y=umbral_amarillo, line_dash="dot", line_color="orange", annotation_text="Umbral Amarillo")
                
                fig2.update_layout(barmode='stack', xaxis_title="Fecha / Hora", yaxis_title="Nuevas Interacciones", template="plotly_white", hovermode="x unified")
                st.plotly_chart(fig2, use_container_width=True)

            with tab3:
                st.subheader(f"Tabla de Capturas ({plataforma})")
                st.dataframe(df.sort_values("Fecha", ascending=False), use_container_width=True)

        else:
            st.warning(f"⚠️ La pestaña '{plataforma}' no contiene registros válidos aún.")
    else:
        st.error(f"No se pudo leer la pestaña '{plataforma}'. Verifica el enlace público del archivo.")
else:
    st.info("👈 Ingresa la URL pública de tu Google Sheet y selecciona la red social a monitorear.")
