# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from modules.config import CONFIG_HOJAS
from modules.data import cargar_todo_aura
from modules.logic import evaluar_cumplimiento_dinamico

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="AURA - Dashboard Integral", page_icon="🧬", layout="wide")
st.title("🧬 AURA: Análisis Unificado del Ciclo de Vida")

# --- CSS PERSONALIZADO (DARK MODE + UI) ---
st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        
        div[data-baseweb="alert"] {
            min-height: 120px;
            height: 100%;
            padding: 1rem;
            margin-bottom: 0.5rem;
            display: flex;
            flex-direction: column;
            justify_content: center;
        }
        
        .gray-card {
            background-color: #262730;
            border: 1px solid #41444b;
            border-radius: 0.5rem;
            padding: 1rem;
            min-height: 120px;
            margin-bottom: 0.5rem;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        
        .stMarkdown p { font-size: 0.9rem; margin-bottom: 0px; }
        hr { margin-top: 0.5rem; margin-bottom: 0.5rem; }
        
        .diag-header {
            font-size: 1.2rem;
            font-weight: bold;
            padding-bottom: 10px;
            border-bottom: 1px solid #41444b;
            margin-bottom: 15px;
            text-align: center;
        }

        div[data-testid="stMetricValue"] { font-size: 2rem; }
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
        else:
            st.error(logs)

# --- INTERFAZ PRINCIPAL ---
if 'resumen' in st.session_state:
    df_resumen = st.session_state['resumen']
    df_hist = st.session_state['hist']

    tab_global, tab_diag, tab_auditoria, tab_ciclo, tab_maestro = st.tabs([
        "📈 Visión Global (F4)", 
        "🧠 Diagnóstico (F3)", 
        "🎯 Auditoría (F2)", 
        "🧬 Ciclo Vida (F1)", 
        "📂 Datos Maestros"
    ])

    # ==============================================================================
    # TAB 1: VISIÓN GLOBAL
    # ==============================================================================
    with tab_global:
        st.header("🌍 Estado Operativo de la Cartera")
        
        total_clientes = len(df_resumen)
        total_trx = df_resumen['Transacciones'].sum()
        
        df_criticos = df_resumen[df_resumen['Estado_AURA'].str.contains("Crítico")]
        n_criticos = len(df_criticos)
        pct_criticos = n_criticos / total_clientes if total_clientes > 0 else 0
        
        riesgo_volumen = df_criticos['Transacciones'].sum()
        pct_riesgo_vol = riesgo_volumen / total_trx if total_trx > 0 else 0
        
        df_activos_calc = df_resumen[df_resumen['Transacciones'] > 0]
        avg_ontime = df_activos_calc['Tasa_Ontime'].mean()

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        # Formatos en métricas globales
        kpi1.metric("📦 Volumen Total", f"{total_trx:,.0f}".replace(",", "."), "Transacciones procesadas")
        kpi2.metric("🚨 Volumen en Riesgo", f"{riesgo_volumen:,.0f}".replace(",", "."), f"-{pct_riesgo_vol:.0%} del total", delta_color="inverse")
        kpi3.metric("📉 Clientes Críticos", f"{n_criticos}", f"{pct_criticos:.0%} de la cartera", delta_color="inverse")
        kpi4.metric("⏱️ Ontime Global", f"{avg_ontime:.0%}", "Promedio Compañía")

        st.divider()

        g1, g2 = st.columns([1, 1])
        color_map = {
            'Saludable / Campeón 🏆': '#09AB3B',
            'Atención Operativa': '#FFD700',
            'Revisión Profunda': '#FFA500',
            'Crítico / Riesgo': '#FF4B4B'
        }

        with g1:
            st.subheader("Salud de la Cartera (Por Clientes)")
            conteo_salud = df_resumen['Estado_AURA'].value_counts().reset_index()
            conteo_salud.columns = ['Estado', 'Clientes']
            fig_pie = px.pie(conteo_salud, values='Clientes', names='Estado', hole=0.4, color='Estado', color_discrete_map=color_map)
            st.plotly_chart(fig_pie, use_container_width=True)

        with g2:
            st.subheader("Impacto en Operación (Por Volumen)")
            df_impacto = df_resumen.groupby('Estado_AURA')['Transacciones'].sum().reset_index()
            fig_bar = px.bar(df_impacto, x='Estado_AURA', y='Transacciones', color='Estado_AURA', text_auto='.2s', color_discrete_map=color_map)
            st.plotly_chart(fig_bar, use_container_width=True)

    # ==============================================================================
    # TAB 2: DIAGNÓSTICO
    # ==============================================================================
    with tab_diag:
        st.header("🧠 Diagnóstico Estratégico")
        
        fases_activas = ["On Going ✅", "Deployment 🚀", "Adopción 🌱"]
        df_activos = df_resumen[df_resumen['Fase_Vida'].str.contains('|'.join([x.split(' ')[0] for x in fases_activas]), case=False, na=False)]
        
        criticos = df_activos[df_activos['Estado_AURA'].str.contains("Crítico")]
        revision = df_activos[df_activos['Estado_AURA'].str.contains("Revisión")]
        atencion = df_activos[df_activos['Estado_AURA'].str.contains("Atención")]
        saludables = df_activos[df_activos['Estado_AURA'].str.contains("Saludable")]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🚨 Riesgo Crítico", len(criticos))
        c2.metric("🟠 Revisión Profunda", len(revision))
        c3.metric("⚠️ Atención Operativa", len(atencion))
        c4.metric("🏆 Saludables", len(saludables))
        st.divider()
        
        col_crit, col_rev, col_attn, col_ok = st.columns(4)

        with col_crit:
            st.markdown('<div class="diag-header" style="color:#FF4B4B;">🚨 Críticos</div>', unsafe_allow_html=True)
            if criticos.empty: st.caption("Ningún cliente en riesgo crítico.")
            else:
                for index, row in criticos.iterrows():
                    with st.expander(f"{row['Client']}"):
                        st.error(f"**Estado:** {row['Fase_Vida']}")
                        if row['Motivo_Critico']: st.markdown(f"**Causa:** {row['Motivo_Critico']}")
                        st.markdown("---")
                        for alerta in row['Alertas_Detalle']: st.markdown(f"- {alerta}")

        with col_rev:
            st.markdown('<div class="diag-header" style="color:#FFA500;">🟠 Revisión</div>', unsafe_allow_html=True)
            if revision.empty: st.caption("Limpio.")
            else:
                for index, row in revision.iterrows():
                    with st.expander(f"{row['Client']}"):
                        st.warning(f"**Alertas:** {len(row['Alertas_Detalle'])} detectadas")
                        for alerta in row['Alertas_Detalle']: st.markdown(f"- {alerta}")

        with col_attn:
            st.markdown('<div class="diag-header" style="color:#FFD700;">⚠️ Atención</div>', unsafe_allow_html=True)
            if atencion.empty: st.caption("Limpio.")
            else:
                for index, row in atencion.iterrows():
                    with st.expander(f"{row['Client']}"):
                        st.info("Detalles menores:")
                        for alerta in row['Alertas_Detalle']: st.markdown(f"- {alerta}")

        with col_ok:
            st.markdown('<div class="diag-header" style="color:#09AB3B;">🏆 Saludables</div>', unsafe_allow_html=True)
            if saludables.empty: st.caption("Sin clientes perfectos.")
            else:
                st.dataframe(saludables[['Client', 'Fase_Vida']], hide_index=True, use_container_width=True)

    # ==============================================================================
    # TAB 3: AUDITORÍA (FORMATOS CORREGIDOS)
    # ==============================================================================
    with tab_auditoria:
        clientes = sorted(df_resumen['Client'].unique())
        cliente_sel = st.selectbox("Auditar Cliente:", clientes)
        
        if cliente_sel:
            row = df_resumen[df_resumen['Client'] == cliente_sel].iloc[0]
            historia_cli = df_hist[df_hist['Client'] == cliente_sel]
            
            st.info(f"Estado: **{row['Fase_Vida']}** | AURA Score: **{row['Estado_AURA']}**")
            
            col_kpis, col_graph = st.columns([3, 2], gap="medium")

            with col_kpis:
                st.subheader("Resultados del Mes")
                
                kpis_vip = []      
                kpis_grid = []     

                for key, cfg in CONFIG_HOJAS.items():
                    # Prioridad
                    prio_col = cfg.get('prio_col', '')
                    try:
                        raw_prio = row.get(prio_col, 2)
                        prio = float(raw_prio) if pd.notna(raw_prio) else 2.0
                    except: prio = 2.0

                    # Lógica
                    st_msg, det_msg, color, _ = evaluar_cumplimiento_dinamico(row, historia_cli, cfg)
                    if prio == 0: color = 'secondary'

                    item = {
                        'key': key, 'cfg': cfg, 'prio': prio, 'val': row.get(cfg['kpi'], 0),
                        'st_msg': st_msg, 'det_msg': det_msg, 'color': color
                    }

                    if key in ['Transacciones', 'MRR']: kpis_vip.append(item)
                    else: kpis_grid.append(item)

                # Ordenar
                kpis_vip.sort(key=lambda x: 0 if x['key'] == 'Transacciones' else 1)
                kpis_grid.sort(key=lambda x: x['prio'], reverse=True)

                # --- RENDERIZADO VISUAL ---
                with st.container(height=600, border=True):
                    
                    # A) SECCIÓN VIP
                    if kpis_vip:
                        cols_vip = st.columns(2)
                        for idx, item in enumerate(kpis_vip):
                            with cols_vip[idx]:
                                titulo = f"**{item['key']}**"
                                if item['prio'] == 3: titulo += " <span style='color:#FFD700'>🌟</span>"
                                st.markdown(titulo, unsafe_allow_html=True)
                                
                                # --- FORMATEO VIP ---
                                if item['key'] == 'MRR': 
                                    # Moneda: $1,000,000 (standard) o $1.000.000 (Latino)
                                    # Usamos Latino reemplazando comas por puntos
                                    val_str = f"${item['val']:,.0f}".replace(",", ".")
                                else:
                                    # Transacciones: 1.000.000 (Sin decimales, con puntos)
                                    val_str = f"{item['val']:,.0f}".replace(",", ".")

                                # Pintar tarjeta
                                if item['color'] == 'secondary':
                                    html_gris = f"""<div class="gray-card"><p style="font-size: 1.4em; font-weight: bold; color: #E0E0E0; margin:0;">{val_str}</p><p style="font-size: 0.9em; color: #9CA0A6; margin:0;">⚪ {item['st_msg']}</p></div>"""
                                    st.markdown(html_gris, unsafe_allow_html=True)
                                elif item['color'] == 'success': st.success(f"{val_str}\n\n{item['st_msg']}")
                                elif item['color'] == 'warning': st.warning(f"{val_str}\n\n{item['st_msg']}")
                                elif item['color'] == 'error': st.error(f"{val_str}\n\n{item['st_msg']}")
                                else: st.info(f"{val_str}\n\n{item['st_msg']}")
                                
                                if item['key'] == 'Transacciones' and 'del Goal' in item['det_msg']:
                                    try:
                                        pct = float(item['det_msg'].split('%')[0]) / 100
                                        st.progress(min(pct, 1.0))
                                    except: pass

                                if item['color'] != 'secondary': st.caption(item['det_msg'])
                        st.divider()

                    # B) SECCIÓN GRID (EL RESTO)
                    cols_grid = st.columns(4)
                    for idx, item in enumerate(kpis_grid):
                        with cols_grid[idx % 4]:
                            titulo = f"**{item['key']}**"
                            if item['prio'] == 3: titulo += " <span style='color:#FFD700; font-size:0.9em'>🌟 (Estrella)</span>"
                            elif item['prio'] == 0: titulo += " <span style='color:#808495; font-size:0.8em'>(Irrelevante)</span>"
                            st.markdown(titulo, unsafe_allow_html=True)

                            # --- FORMATEO GRID ---
                            if item['cfg']['is_pct']:
                                # Porcentajes: Sin decimales (e.g. 86%)
                                val_str = f"{item['val']:.0%}"
                            else:
                                # Números: Sin decimales, separador de miles con puntos (1.500)
                                val_str = f"{item['val']:,.0f}".replace(",", ".")

                            # Pintar tarjeta
                            if item['color'] == 'secondary':
                                html_gris = f"""<div class="gray-card"><p style="font-size: 1.2em; font-weight: bold; color: #E0E0E0; margin:0;">{val_str}</p><p style="font-size: 0.9em; color: #9CA0A6; margin:0;">⚪ {item['st_msg']}</p></div>"""
                                st.markdown(html_gris, unsafe_allow_html=True)
                            elif item['color'] == 'success': st.success(f"{val_str}\n\n{item['st_msg']}")
                            elif item['color'] == 'warning': st.warning(f"{val_str}\n\n{item['st_msg']}")
                            elif item['color'] == 'error': st.error(f"{val_str}\n\n{item['st_msg']}")
                            else: st.info(f"{val_str}\n\n{item['st_msg']}")

                            if item['color'] != 'secondary': st.caption(item['det_msg'])
                            st.divider()

            with col_graph:
                 st.subheader("Tendencia Histórica")
                 kpi_grafico = st.selectbox("Selecciona KPI:", list(CONFIG_HOJAS.keys()))
                 col_tecnica = CONFIG_HOJAS[kpi_grafico]['kpi']
                 df_plot = df_hist[df_hist['Client'] == cliente_sel][['Date_Obj', col_tecnica]].set_index('Date_Obj').sort_index()
                 st.line_chart(df_plot, height=350)
                 st.caption(f"Visualizando: {CONFIG_HOJAS[kpi_grafico]['desc']}")

    # TABS RESTANTES
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

    with tab_maestro:
        st.dataframe(df_hist.drop(columns=['Date_Obj']), use_container_width=True)