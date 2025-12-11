# app.py
import streamlit as st
import pandas as pd
from modules.config import CONFIG_HOJAS
from modules.data import cargar_todo_aura
from modules.logic import evaluar_cumplimiento_dinamico

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="AURA - Dashboard Integral", page_icon="🧬", layout="wide")
st.title("🧬 AURA: Análisis Unificado del Ciclo de Vida")

# --- CSS PERSONALIZADO (MODO COMPACTO) ---
st.markdown("""
    <style>
        /* Reducir espacios verticales generales */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        /* Hacer las tarjetas (alertas) más delgadas */
        div[data-baseweb="alert"] {
            padding-top: 0.5rem;
            padding-bottom: 0.5rem;
            margin-bottom: 0.5rem;
        }
        /* Reducir tamaño de letra de las métricas dentro de las tarjetas */
        .stMarkdown p {
            font-size: 0.9rem;
            margin-bottom: 0px;
        }
        /* Reducir espacio de los divisores */
        hr {
            margin-top: 0.5rem;
            margin-bottom: 0.5rem;
        }
    </style>
""", unsafe_allow_html=True)


# --- BOTÓN DE CARGA ---
if st.button('🔄 Cargar Dashboard AURA Completo'):
    with st.spinner('Conectando con la nube y procesando datos...'):
        hist, resumen, logs = cargar_todo_aura()
        if hist is not None:
            st.session_state['hist'] = hist
            st.session_state['resumen'] = resumen
            st.success("¡Datos actualizados!")

# --- INTERFAZ ---
if 'resumen' in st.session_state:
    df_resumen = st.session_state['resumen']
    df_hist = st.session_state['hist']

    tab_auditoria, tab_ciclo, tab_diag, tab_maestro = st.tabs(["🎯 Auditoría (F2)", "🧬 Ciclo Vida (F1)", "🧠 Diagnóstico (F3)", "📂 Datos Maestros"])

    # ==============================================================================
    # TAB 1: AUDITORÍA (F2) - 4 COLUMNAS
    # ==============================================================================
    with tab_auditoria:
        clientes = sorted(df_resumen['Client'].unique())
        cliente_sel = st.selectbox("Auditar Cliente:", clientes)
        
        if cliente_sel:
            row = df_resumen[df_resumen['Client'] == cliente_sel].iloc[0]
            historia_cli = df_hist[df_hist['Client'] == cliente_sel]
            
            # Barra de estado superior
            st.info(f"Estado: **{row['Fase_Vida']}** | AURA Score: **{row['Estado_AURA']}**")
            
            # Layout Columnas: Izquierda (KPIs) | Derecha (Gráfica)
            col_kpis, col_graph = st.columns([3, 2], gap="medium")

            # === COLUMNA IZQUIERDA: TARJETAS ===
            with col_kpis:
                st.subheader("Resultados del Mes")
                
                with st.container(height=550, border=True):
                    
                    # --- CAMBIO AQUÍ: 4 COLUMNAS ---
                    cols_grid = st.columns(4) 
                    idx = 0
                    
                    for key, cfg in CONFIG_HOJAS.items():
                        st_msg, det_msg, color, _ = evaluar_cumplimiento_dinamico(row, historia_cli, cfg)
                        
                        # Distribuir en las 4 columnas (idx % 4)
                        with cols_grid[idx % 4]:
                            st.markdown(f"**{key}**")
                            
                            val = row[cfg['kpi']]
                            val_str = f"{val:.1%}" if cfg['is_pct'] else f"{val:.1f}"
                            
                            # Barra de progreso mini
                            if key == 'Transacciones' and 'del Goal' in det_msg:
                                try:
                                    pct = float(det_msg.split('%')[0]) / 100
                                    st.progress(min(pct, 1.0))
                                except: pass
                            
                            # Tarjeta de color
                            if color == 'success': st.success(f"{val_str}\n\n{st_msg}")
                            elif color == 'warning': st.warning(f"{val_str}\n\n{st_msg}")
                            elif color == 'error': st.error(f"{val_str}\n\n{st_msg}")
                            else: st.info(f"{val_str}\n\n{st_msg}")
                            
                            st.caption(det_msg)
                            st.divider()
                        idx += 1

            # === COLUMNA DERECHA: GRÁFICA ===
            with col_graph:
                 st.subheader("Tendencia Histórica")
                 kpi_grafico = st.selectbox("Selecciona KPI:", list(CONFIG_HOJAS.keys()))
                 
                 col_tecnica = CONFIG_HOJAS[kpi_grafico]['kpi']
                 df_plot = df_hist[df_hist['Client'] == cliente_sel][['Date_Obj', col_tecnica]].set_index('Date_Obj').sort_index()
                 
                 st.line_chart(df_plot, height=350)
                 st.caption(f"Visualizando: {CONFIG_HOJAS[kpi_grafico]['desc']}")
                 st.info("💡 Tip: Usa el scroll en la izquierda para ver más KPIs.")


    # TAB 2: CICLO VIDA (Sin cambios)
    with tab_ciclo:
        col1, col2 = st.columns([2, 1])
        conteo = df_resumen['Fase_Vida'].value_counts().reset_index()
        conteo.columns = ['Fase', 'Clientes']
        with col1: st.bar_chart(conteo.set_index('Fase'), color="#4A90E2")
        with col2: st.dataframe(conteo, hide_index=True, use_container_width=True)
        st.divider()
        fases_ordenadas = sorted(df_resumen['Fase_Vida'].unique())
        for fase in fases_ordenadas:
            clientes_en_fase = df_resumen[df_resumen['Fase_Vida'] == fase]['Client']
            with st.expander(f"{fase} ({len(clientes_en_fase)} clientes)"):
                st.write(", ".join(clientes_en_fase))

    # TAB 3: DIAGNÓSTICO (Sin cambios)
    with tab_diag:
        st.header("🧠 Diagnóstico Estratégico")
        fases_activas = ["On Going ✅", "Deployment 🚀", "Adopción 🌱"]
        df_activos = df_resumen[df_resumen['Fase_Vida'].str.contains('|'.join([x.split(' ')[0] for x in fases_activas]), case=False, na=False)]
        
        criticos = df_activos[df_activos['Estado_AURA'].str.contains("Crítico")]
        revision = df_activos[df_activos['Estado_AURA'].str.contains("Revisión")]
        atencion = df_activos[df_activos['Estado_AURA'].str.contains("Atención")]
        saludables = df_activos[df_activos['Estado_AURA'].str.contains("Saludable")]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🚨 Críticos", len(criticos))
        c2.metric("🟠 Revisión", len(revision))
        c3.metric("⚠️ Atención", len(atencion))
        c4.metric("🏆 Saludables", len(saludables))
        st.divider()
        
        if not criticos.empty:
            st.error("🚨 **RIESGO CRÍTICO**")
            for index, row in criticos.iterrows():
                with st.expander(f"🔴 {row['Client']} ({row['Fase_Vida']})"):
                    if row['Motivo_Critico']: st.markdown(f"**Causa:** {row['Motivo_Critico']}")
                    for alerta in row['Alertas_Detalle']: st.markdown(f"- {alerta}")
        
        col_rev, col_ok = st.columns(2)
        with col_rev:
            st.warning("⚠️ **Necesitan Revisión**")
            df_view = pd.concat([revision, atencion])
            if not df_view.empty:
                for index, row in df_view.iterrows():
                     with st.expander(f"🔸 {row['Client']}"):
                        for alerta in row['Alertas_Detalle']: st.markdown(f"- {alerta}")
        with col_ok:
            st.success("🏆 **Saludables**")
            if not saludables.empty:
                st.dataframe(saludables[['Client', 'Fase_Vida']], hide_index=True, use_container_width=True)

    # TAB 4: MAESTRO (Sin cambios)
    with tab_maestro:
        st.dataframe(df_hist.drop(columns=['Date_Obj']), use_container_width=True)