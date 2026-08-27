import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(
    page_title="Alpina - Monitor de Riesgo Reputacional",
    page_icon="🛡️",
    layout="wide"
)

# Título y encabezado
st.title("🛡️ Alpina: Dashboard de Alerta Temprana & Viralidad")
st.markdown("Monitoreo automatizado de métricas y velocidad de crecimiento en TikTok.")

# Sidebar - Configuración
st.sidebar.header("⚙️ Configuración del Feed")
sheet_url = st.sidebar.text_input(
    "URL pública de Google Sheets",
    help="Ingresa el link público de tu Google Sheet con permisos de 'Cualquier persona con el enlace puede ver'"
)

st.sidebar.markdown("---")
st.sidebar.header("🎚️ Umbrales de Alerta")
st.sidebar.markdown("Define el incremento de interacciones por ciclo que activa cada nivel de alerta.")
umbral_amarillo = st.sidebar.number_input("🟡 Umbral Amarillo (Precaución)", min_value=1, value=50)
umbral_rojo = st.sidebar.number_input("🔴 Umbral Rojo (Alerta Alta)", min_value=1, value=200)

@st.cache_data(ttl=60)
def load_data(url):
    try:
        if "/edit" in url:
            csv_url = url.split("/edit")[0] + "/gviz/tq?tqx=out:csv"
        else:
            csv_url = url
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        return None

if sheet_url:
    df = load_data(sheet_url)
    
    if df is not None and not df.empty:
        # Mapeo adaptado a las columnas exactas exportadas por Apify
        column_mapping = {
            'views': 'Vistas',
            'likes': 'Likes',
            'comments': 'Comentarios',
            'shares': 'Compartidos',
            'saves': 'Guardados',
            'reposts': 'Reposts',
            'scrapedAt': 'Fecha',
            'postUrl': 'URL',
            'profileHandle': 'Autor'
        }
        
        # Mapear columnas ignorando mayúsculas/minúsculas
        df_cols_lower = {str(c).lower(): c for c in df.columns}
        rename_dict = {}
        for key, target in column_mapping.items():
            if key.lower() in df_cols_lower:
                rename_dict[df_cols_lower[key.lower()]] = target

        df = df.rename(columns=rename_dict)
        
        # Asegurar columnas numéricas básicas
        metric_cols = ["Vistas", "Likes", "Comentarios", "Compartidos", "Guardados", "Reposts"]
        for col in metric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            else:
                df[col] = 0

        # Procesamiento de la columna Fecha (scrapedAt)
        if "Fecha" in df.columns:
            df["Fecha"] = pd.to_datetime(df["Fecha"], errors='coerce')
            df = df.dropna(subset=["Fecha"]).sort_values("Fecha").reset_index(drop=True)
        else:
            df["Fecha"] = pd.date_range(end=pd.Timestamp.now(), periods=len(df), freq="30min")

        if len(df) > 0:
            # Cálculo de Velocidad / Deltas (Nuevas interacciones por ciclo)
            df["Delta_Vistas"] = df["Vistas"].diff().fillna(df["Vistas"].iloc[0])
            df["Delta_Comentarios"] = df["Comentarios"].diff().fillna(df["Comentarios"].iloc[0])
            df["Delta_Compartidos"] = df["Compartidos"].diff().fillna(df["Compartidos"].iloc[0])
            df["Delta_Guardados"] = df["Guardados"].diff().fillna(df["Guardados"].iloc[0])

            # Índice de Velocidad de Riesgo = Comentarios (x1.5) + Compartidos (x2.0)
            df["Velocidad_Riesgo"] = (df["Delta_Comentarios"] * 1.5) + (df["Delta_Compartidos"] * 2.0)

            ultima_velocidad = df["Velocidad_Riesgo"].iloc[-1]
            
            # Encabezado del Post Monitoreado
            if "Autor" in df.columns and "URL" in df.columns:
                st.caption(f"📌 **Monitoreando post de:** `@{df['Autor'].iloc[-1]}` | **Link:** {df['URL'].iloc[-1]}")
            
            # --- KPI & ESTADO DE ALERTA ---
            st.subheader("🚦 Estado del Riesgo en Tiempo Real")
            
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
                st.metric("Comentarios", f"{int(df['Comentarios'].iloc[-1]):,}", delta=f"+{int(df['Delta_Comentarios'].iloc[-1])}")
            with col_kpi4:
                st.metric("Compartidos", f"{int(df['Compartidos'].iloc[-1]):,}", delta=f"+{int(df['Delta_Compartidos'].iloc[-1])}")
            with col_kpi5:
                st.metric("Guardados", f"{int(df['Guardados'].iloc[-1]):,}", delta=f"+{int(df['Delta_Guardados'].iloc[-1])}")

            st.divider()

            # --- PESTAÑAS DE VISUALIZACIÓN ---
            tab1, tab2, tab3 = st.tabs(["📈 Crecimiento Acumulado", "⚡ Velocidad e Índice de Riesgo", "📋 Registros en Vivo"])

            with tab1:
                st.subheader("Evolución Temporal Acumulada")
                fig1 = go.Figure()
                fig1.add_trace(go.Scatter(x=df['Fecha'], y=df['Vistas'], name='Vistas', line=dict(color='#1f77b4', width=2)))
                fig1.add_trace(go.Scatter(x=df['Fecha'], y=df['Likes'], name='Likes', line=dict(color='#2ca02c', width=2)))
                fig1.add_trace(go.Scatter(x=df['Fecha'], y=df['Comentarios'], name='Comentarios', line=dict(color='#ff7f0e', width=2)))
                fig1.add_trace(go.Scatter(x=df['Fecha'], y=df['Compartidos'], name='Compartidos', line=dict(color='#d62728', width=2)))
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
                st.subheader("Tabla de Capturas de Apify")
                st.dataframe(df.sort_values("Fecha", ascending=False), use_container_width=True)

        else:
            st.warning("⚠️ No se encontraron registros válidos en la hoja de cálculo.")
    else:
        st.error("No se pudo leer el Google Sheet. Verifica que la URL sea pública.")
else:
    st.info("👈 Ingresa la URL pública de tu Google Sheet en el panel de la izquierda para desplegar el dashboard.")
