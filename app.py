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

st.title("🛡️ Alpina: Dashboard de Alerta Temprana & Viralidad")
st.markdown("Monitoreo automatizado de métricas e impacto reputacional en tiempo real.")

# Sidebar - Configuración
st.sidebar.header("⚙️ Configuración del Feed")
sheet_url = st.sidebar.text_input(
    "URL pública de Google Sheets",
    help="Ingresa el link público de tu Google Sheet"
)

plataforma = st.sidebar.selectbox(
    "Vista o Red Social a Monitorear",
    ["📊 Seguimiento Total (Consolidado)", "TikTok", "Instagram", "Facebook", "X"]
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

platform_mappings = {
    'TikTok': [
        ('views', 'Vistas'), ('likes', 'Likes'), ('comments', 'Comentarios'),
        ('shares', 'Compartidos'), ('saves', 'Guardados'), ('reposts', 'Reposts'),
        ('scrapedAt', 'Fecha'), ('postUrl', 'URL'), ('inputUrl', 'URL'),
        ('profileHandle', 'Autor'), ('profileName', 'Autor')
    ],
    'Instagram': [
        ('videoViewCount', 'Vistas'), ('videoPlayCount', 'Vistas'), ('likesCount', 'Likes'),
        ('commentsCount', 'Comentarios'), ('timestamp', 'Fecha'), ('url', 'URL'),
        ('inputUrl', 'URL'), ('ownerUsername', 'Autor')
    ],
    'X': [
        ('viewCount', 'Vistas'), ('likeCount', 'Likes'), ('replyCount', 'Comentarios'),
        ('retweetCount', 'Compartidos'), ('quoteCount', 'Compartidos'), ('bookmarkCount', 'Guardados'),
        ('createdAt', 'Fecha'), ('twitterUrl', 'URL'), ('url', 'URL'),
        ('author/userName', 'Autor'), ('author/name', 'Autor')
    ],
    'Facebook': [
        ('views', 'Vistas'), ('plays', 'Vistas'), ('likes', 'Likes'),
        ('comments', 'Comentarios'), ('shares', 'Compartidos'), ('scrapedAt', 'Fecha'),
        ('contentUrl', 'URL'), ('inputUrl', 'URL'), ('profileUsername', 'Autor'),
        ('profileName', 'Autor')
    ]
}

def process_single_sheet(df_raw, p_name):
    if df_raw is None or df_raw.empty:
        return None
    
    mapping = platform_mappings.get(p_name, [])
    df_cols_lower = {str(c).lower(): c for c in df_raw.columns}
    rename_dict = {}
    already_mapped = set()
    
    for src_key, target in mapping:
        src_lower = src_key.lower()
        if src_lower in df_cols_lower and target not in already_mapped:
            actual_col = df_cols_lower[src_lower]
            rename_dict[actual_col] = target
            already_mapped.add(target)
            
    df = df_raw.rename(columns=rename_dict)
    
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
    
    metric_cols = ["Vistas", "Likes", "Comentarios", "Compartidos", "Guardados"]
    for col in metric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0.0

    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors='coerce')
        df = df.dropna(subset=["Fecha"]).sort_values("Fecha").reset_index(drop=True)
    else:
        df["Fecha"] = pd.date_range(end=pd.Timestamp.now(), periods=len(df), freq="30min")

    df["Plataforma"] = p_name
    return df

if sheet_url:
    if plataforma == "📊 Seguimiento Total (Consolidado)":
        all_sheets = ["TikTok", "Instagram", "Facebook", "X"]
        processed_dfs = []
        
        for p in all_sheets:
            raw_data = load_data(sheet_url, p)
            p_df = process_single_sheet(raw_data, p)
            if p_df is not None and not p_df.empty:
                processed_dfs.append(p_df)
                
        if processed_dfs:
            combined_df = pd.concat(processed_dfs, ignore_index=True).sort_values("Fecha")
            latest_per_platform = combined_df.groupby("Plataforma").last().reset_index()
            
            total_vistas = latest_per_platform["Vistas"].sum()
            total_likes = latest_per_platform["Likes"].sum()
            total_comentarios = latest_per_platform["Comentarios"].sum()
            total_compartidos = latest_per_platform["Compartidos"].sum()
            total_guardados = latest_per_platform["Guardados"].sum()
            
            velocidad_global = (total_comentarios * 0.5) + (total_compartidos * 1.0)
            
            st.subheader("🌐 Visión Consolidada Multi-Plataforma")
            
            col_status, col_k1, col_k2, col_k3, col_k4, col_k5 = st.columns(6)
            
            with col_status:
                if velocidad_global >= umbral_rojo:
                    st.error("🔴 **ALERTA CRÍTICA**\nRiesgo extendido")
                elif velocidad_global >= umbral_amarillo:
                    st.warning("🟡 **PRECAUCIÓN**\nCrecimiento global")
                else:
                    st.success("🟢 **ESTABLE**\nBajo control")
                    
            with col_k1:
                st.metric("Vistas Consolidadas", f"{int(total_vistas):,}")
            with col_k2:
                st.metric("Likes Totales", f"{int(total_likes):,}")
            with col_k3:
                st.metric("Comentarios Totales", f"{int(total_comentarios):,}")
            with col_k4:
                st.metric("Compartidos Totales", f"{int(total_compartidos):,}")
            with col_k5:
                st.metric("Guardados Totales", f"{int(total_guardados):,}")

            st.divider()

            tab_summary, tab_growth, tab_charts, tab_raw = st.tabs([
                "📊 Resumen por Red", 
                "📉 Crecimiento por Métrica", 
                "🍩 Distribución por Red", 
                "📋 Todos los Registros"
            ])
            
            with tab_summary:
                st.subheader("Estado Actual por Plataforma")
                summary_table = latest_per_platform[["Plataforma", "Vistas", "Likes", "Comentarios", "Compartidos", "Guardados"]].copy()
                st.dataframe(summary_table, use_container_width=True)

            with tab_growth:
                st.subheader("📈 Crecimiento Temporal por Métrica")
                col_g1, col_g2 = st.columns(2)
                
                with col_g1:
                    fig_views = px.line(combined_df, x="Fecha", y="Vistas", color="Plataforma", markers=True, title="Evolución de Vistas")
                    fig_views.update_layout(template="plotly_white", hovermode="x unified")
                    st.plotly_chart(fig_views, use_container_width=True)
                    
                    fig_comments = px.line(combined_df, x="Fecha", y="Comentarios", color="Plataforma", markers=True, title="Evolución de Comentarios")
                    fig_comments.update_layout(template="plotly_white", hovermode="x unified")
                    st.plotly_chart(fig_comments, use_container_width=True)

                with col_g2:
                    fig_likes = px.line(combined_df, x="Fecha", y="Likes", color="Plataforma", markers=True, title="Evolución de Likes")
                    fig_likes.update_layout(template="plotly_white", hovermode="x unified")
                    st.plotly_chart(fig_likes, use_container_width=True)

                    fig_shares = px.line(combined_df, x="Fecha", y="Compartidos", color="Plataforma", markers=True, title="Evolución de Compartidos")
                    fig_shares.update_layout(template="plotly_white", hovermode="x unified")
                    st.plotly_chart(fig_shares, use_container_width=True)

            with tab_charts:
                col_chart1, col_chart2 = st.columns(2)
                
                with col_chart1:
                    st.subheader("Distribución de Comentarios por Red")
                    fig_comm = px.pie(latest_per_platform, values='Comentarios', names='Plataforma', color='Plataforma', hole=0.4)
                    st.plotly_chart(fig_comm, use_container_width=True)
                    
                with col_chart2:
                    st.subheader("Distribución de Compartidos por Red")
                    fig_share = px.pie(latest_per_platform, values='Compartidos', names='Plataforma', color='Plataforma', hole=0.4)
                    st.plotly_chart(fig_share, use_container_width=True)

            with tab_raw:
                st.subheader("Consolidado Histórico Completo")
                st.dataframe(combined_df.sort_values("Fecha", ascending=False), use_container_width=True)
        else:
            st.warning("⚠️ No se encontraron datos válidos en las pestañas de Google Sheets.")

    else:
        df_raw = load_data(sheet_url, plataforma)
        df = process_single_sheet(df_raw, plataforma)
        
        if df is not None and not df.empty:
            df["Delta_Vistas"] = df["Vistas"].diff().fillna(df["Vistas"].iloc[0])
            df["Delta_Comentarios"] = df["Comentarios"].diff().fillna(df["Comentarios"].iloc[0])
            df["Delta_Compartidos"] = df["Compartidos"].diff().fillna(df["Compartidos"].iloc[0])

            df["Velocidad_Riesgo"] = (df["Delta_Comentarios"] * 1.5) + (df["Delta_Compartidos"] * 2.0)
            ultima_velocidad = df["Velocidad_Riesgo"].iloc[-1]
            
            info_text = []
            if "Autor" in df.columns and pd.notna(df['Autor'].iloc[-1]):
                info_text.append(f"📌 **Autor:** `@{df['Autor'].iloc[-1]}`")
            if "URL" in df.columns and pd.notna(df['URL'].iloc[-1]):
                info_text.append(f"🔗 **Link:** {df['URL'].iloc[-1]}")
            
            if info_text:
                st.caption(" | ".join(info_text))
            
            st.subheader(f"🚦 Estado del Riesgo en {plataforma}")
            
            col_status, col_k1, col_k2, col_k3, col_k4, col_k5 = st.columns(6)
            
            with col_status:
                if ultima_velocidad >= umbral_rojo:
                    st.error("🔴 **ALERTA ALTA**\nViralidad crítica")
                elif ultima_velocidad >= umbral_amarillo:
                    st.warning("🟡 **PRECAUCIÓN**\nCrecimiento acelerado")
                else:
                    st.success("🟢 **ESTABLE**\nBajo control")
                    
            with col_k1:
                st.metric("Vistas Totales", f"{int(df['Vistas'].iloc[-1]):,}", delta=f"+{int(df['Delta_Vistas'].iloc[-1])}")
            with col_k2:
                st.metric("Likes", f"{int(df['Likes'].iloc[-1]):,}")
            with col_k3:
                st.metric("Comentarios / Respuestas", f"{int(df['Comentarios'].iloc[-1]):,}", delta=f"+{int(df['Delta_Comentarios'].iloc[-1])}")
            with col_k4:
                st.metric("Compartidos / Retweets", f"{int(df['Compartidos'].iloc[-1]):,}", delta=f"+{int(df['Delta_Compartidos'].iloc[-1])}")
            with col_k5:
                st.metric("Guardados / Marcadores", f"{int(df['Guardados'].iloc[-1]):,}")

            st.divider()

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
    st.info("👈 Ingresa la URL pública de tu Google Sheet y selecciona la vista deseada.")
