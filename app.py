# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from modules.config import CONFIG_HOJAS
from modules.data import cargar_todo_aura
from modules.logic import evaluar_cumplimiento_dinamico

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="AURA - Dashboard Integral", page_icon="🧬", layout="wide")

# --- GESTIÓN DE ESTADO ---
if 'view' not in st.session_state:
    st.session_state.view = 'Visión Global'

if 'kpi_selected' not in st.session_state:
    st.session_state.kpi_selected = 'Transacciones'

def set_view(view_name):
    st.session_state.view = view_name

# --- CSS PERSONALIZADO ---
st.markdown("""
    <style>
        .block-container { padding-top: 3rem; padding-bottom: 2rem; }
        
        /* TARJETAS HTML */
        .aura-card {
            border-radius: 0.5rem;
            padding: 1rem;
            height: 125px !important;
            margin-bottom: 5px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            box-sizing: border-box;
            border: 1px solid transparent;
        }

        /* COLORES */
        .card-success { background-color: rgba(9, 171, 59, 0.15); border-color: rgba(9, 171, 59, 0.2); color: #09AB3B; }
        .card-error { background-color: rgba(255, 75, 75, 0.15); border-color: rgba(255, 75, 75, 0.2); color: #FF4B4B; }
        .card-warning { background-color: rgba(255, 189, 69, 0.15); border-color: rgba(255, 189, 69, 0.2); color: #FFBD45; }
        .card-info { background-color: rgba(49, 51, 63, 0.6); border-color: rgba(250, 250, 250, 0.2); color: #E0E0E0; }
        .card-gray { background-color: #262730; border-color: #41444b; color: #9CA0A6; }

        /* TIPOGRAFÍA */
        .kpi-value { font-size: 1.5rem; font-weight: bold; color: #E0E0E0; margin-bottom: 0.2rem; line-height: 1.2; }
        .kpi-msg { font-size: 0.9rem; font-weight: normal; line-height: 1.2; }
        .stMarkdown p { font-size: 0.9rem; margin-bottom: 0px; }
        
        hr { margin-top: 0.5rem; margin-bottom: 0.5rem; }
        
        .diag-header {
            font-size: 1.2rem; font-weight: bold; padding-bottom: 10px;
            border-bottom: 1px solid #41444b; margin-bottom: 15px; text-align: center;
        }
        
        div[data-testid="stMetricValue"] { font-size: 2rem; }
        
        /* BOTONERA NAVEGACIÓN */
        div.stButton > button { width: 100%; border-radius: 8px; height: 3em; font-weight: bold; }
        
        /* BOTONES DE ACCIÓN (DENTRO DE TARJETAS) */
        button[kind="secondary"] {
            border: 1px solid #41444b;
            font-size: 0.8rem;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🧬 AURA: Análisis Unificado del Ciclo de Vida")

# --- MENÚ DE NAVEGACIÓN ---
menu_cols = st.columns(5)
opciones = ["📈 Visión Global", "🧠 Diagnóstico", "🎯 Auditoría", "🧬 Ciclo Vida", "📂 Datos Maestros"]

for i, opcion in enumerate(opciones):
    tipo_boton = "primary" if st.session_state.view == opcion else "secondary"
    if menu_cols[i].button(opcion, key=f"nav_{i}", type=tipo_boton, use_container_width=True):
        set_view(opcion)
        st.rerun()

st.divider()

if st.button('🔄 Recargar Datos'):
    with st.spinner('Conectando con la nube...'):
        hist, resumen, logs = cargar_todo_aura()
        if hist is not None:
            st.session_state['hist'] = hist
            st.session_state['resumen'] = resumen
            st.success("¡Datos actualizados!")
        else:
            st.error(logs)

# --- LÓGICA PRINCIPAL ---
if 'resumen' in st.session_state:
    df_resumen = st.session_state['resumen']
    df_hist = st.session_state['hist']

    # 1. VISIÓN GLOBAL
    if st.session_state.view == "📈 Visión Global":
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
        kpi1.metric("📦 Volumen Total", f"{total_trx:,.0f}".replace(",", "."), "Transacciones")
        kpi2.metric("🚨 Volumen en Riesgo", f"{riesgo_volumen:,.0f}".replace(",", "."), f"-{pct_riesgo_vol:.0%} del total", delta_color="inverse")
        kpi3.metric("📉 Clientes Críticos", f"{n_criticos}", f"{pct_criticos:.0%} de la cartera", delta_color="inverse")
        kpi4.metric("⏱️ Ontime Global", f"{avg_ontime:.0%}", "Promedio Compañía")
        st.divider()

        st.subheader("📊 Análisis por Segmento")
        cols_segmentacion = [c for c in df_resumen.columns if c in ['Region', 'Vertical', 'Año', 'Tipo', 'region', 'vertical', 'año', 'tipo']]
        if cols_segmentacion:
            segmento = st.selectbox("Selecciona Dimensión para Analizar:", cols_segmentacion)
            sg1, sg2 = st.columns(2)
            color_map_health = {'Saludable / Campeón 🏆': '#09AB3B', 'Atención Operativa': '#FFD700', 'Revisión Profunda': '#FFA500', 'Crítico / Riesgo': '#FF4B4B'}
            with sg1:
                st.markdown(f"**Distribución de Riesgo por {segmento}**")
                df_seg_count = df_resumen.groupby([segmento, 'Estado_AURA']).size().reset_index(name='Clientes')
                fig_seg_risk = px.bar(df_seg_count, x=segmento, y='Clientes', color='Estado_AURA', color_discrete_map=color_map_health, barmode='stack')
                st.plotly_chart(fig_seg_risk, use_container_width=True)
            with sg2:
                metric_y = 'MRR' if ('MRR' in df_resumen.columns and df_resumen['MRR'].sum() > 0) else 'Transacciones'
                lbl = "Económico (MRR)" if metric_y == 'MRR' else "Operativo (Volumen)"
                st.markdown(f"**Impacto {lbl} por {segmento}**")
                df_seg_val = df_resumen.groupby([segmento, 'Estado_AURA'])[metric_y].sum().reset_index()
                fig_seg_val = px.bar(df_seg_val, x=segmento, y=metric_y, color='Estado_AURA', color_discrete_map=color_map_health)
                st.plotly_chart(fig_seg_val, use_container_width=True)
        else:
            st.info("💡 Agrega la hoja 'Caracteristicas cliente' para activar esta sección.")

    # 2. DIAGNÓSTICO
    elif st.session_state.view == "🧠 Diagnóstico":
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
        
        def render_list(col, df, empty_msg, alert_type):
            with col:
                st.markdown(f'<div class="diag-header" style="color:{"#FF4B4B" if alert_type=="error" else "#FFA500" if alert_type=="warning" else "#FFD700" if alert_type=="info" else "#09AB3B"};">{col_names[alert_type]}</div>', unsafe_allow_html=True)
                if df.empty: st.caption(empty_msg)
                else:
                    if alert_type == "success": 
                        st.dataframe(df[['Client', 'Fase_Vida']], hide_index=True, use_container_width=True)
                    else:
                        for index, row in df.iterrows():
                            with st.expander(f"{row['Client']}"):
                                if alert_type == "error": st.error(f"**Estado:** {row['Fase_Vida']}")
                                elif alert_type == "warning": st.warning(f"**Alertas:** {len(row['Alertas_Detalle'])}")
                                else: st.info("Detalles:")
                                if row.get('Motivo_Critico'): st.markdown(f"**Causa:** {row['Motivo_Critico']}")
                                st.markdown("---")
                                for alerta in row['Alertas_Detalle']: st.markdown(f"- {alerta}")

        col_names = {"error": "🚨 Críticos", "warning": "🟠 Revisión", "info": "⚠️ Atención", "success": "🏆 Saludables"}
        render_list(col_crit, criticos, "Limpio.", "error")
        render_list(col_rev, revision, "Limpio.", "warning")
        render_list(col_attn, atencion, "Limpio.", "info")
        render_list(col_ok, saludables, "Sin clientes perfectos.", "success")

    # 3. AUDITORÍA
    elif st.session_state.view == "🎯 Auditoría":
        clientes = sorted(df_resumen['Client'].unique())
        idx_sel = 0
        if 'last_client' in st.session_state and st.session_state.last_client in clientes:
            idx_sel = clientes.index(st.session_state.last_client)
        cliente_sel = st.selectbox("Auditar Cliente:", clientes, index=idx_sel)
        st.session_state.last_client = cliente_sel
        
        if cliente_sel:
            row = df_resumen[df_resumen['Client'] == cliente_sel].iloc[0]
            historia_cli = df_hist[df_hist['Client'] == cliente_sel]
            meta_info = []
            meta_str = " | ".join(meta_info)
            if meta_str: meta_str = f" | {meta_str}"
            st.info(f"Estado: **{row['Fase_Vida']}** | AURA Score: **{row['Estado_AURA']}**{meta_str}")
            
            col_kpis, col_graph = st.columns([3, 2], gap="medium")
            
            # Helper
            def render_card_html(item, val_str):
                return f"""
                <div class="aura-card {item['css_class']}">
                    <div class="kpi-value">{val_str}</div>
                    <div class="kpi-msg">{item['st_msg']}</div>
                </div>
                """

            with col_kpis:
                st.subheader("Resultados del Mes")
                kpis_vip, kpis_grid = [], []

                for key, cfg in CONFIG_HOJAS.items():
                    prio_col = cfg.get('prio_col', '')
                    try: raw_prio = row.get(prio_col, 2); prio = float(raw_prio) if pd.notna(raw_prio) else 2.0
                    except: prio = 2.0

                    st_msg, det_msg, color, _ = evaluar_cumplimiento_dinamico(row, historia_cli, cfg)
                    
                    css_class = "card-gray"
                    if prio > 0:
                        if color == 'success': css_class = "card-success"
                        elif color == 'error': css_class = "card-error"
                        elif color == 'warning': css_class = "card-warning"
                        elif color == 'info': css_class = "card-info"
                    
                    if prio == 0: det_msg = "• No Aplica / Sin Estándar"
                    elif not det_msg: det_msg = "&nbsp;"

                    item = {'key': key, 'cfg': cfg, 'prio': prio, 'val': row.get(cfg['kpi'], 0),
                            'st_msg': st_msg, 'det_msg': det_msg, 'css_class': css_class}

                    if key in ['Transacciones', 'MRR']: kpis_vip.append(item)
                    else: kpis_grid.append(item)

                kpis_vip.sort(key=lambda x: 0 if x['key'] == 'Transacciones' else 1)
                kpis_grid.sort(key=lambda x: x['prio'], reverse=True)

                # --- CONTENEDOR DE ALTURA FIJA ---
                with st.container(height=650, border=True):
                    if kpis_vip:
                        cols_vip = st.columns(2)
                        for idx, item in enumerate(kpis_vip):
                            with cols_vip[idx]:
                                titulo = f"**{item['key']}**"
                                if item['prio'] == 3: titulo += " <span style='color:#FFD700'>🌟</span>"
                                st.markdown(titulo, unsafe_allow_html=True)
                                
                                val_str = f"${item['val']:,.0f}".replace(",", ".") if item['key'] == 'MRR' else f"{item['val']:,.0f}".replace(",", ".")
                                st.markdown(render_card_html(item, val_str), unsafe_allow_html=True)
                                
                                if item['key'] == 'Transacciones' and 'del Goal' in item['det_msg']:
                                    try: st.progress(min(float(item['det_msg'].split('%')[0]) / 100, 1.0))
                                    except: pass
                                
                                col_txt, col_btn = st.columns([1, 1]) 
                                st.caption(item['det_msg'])
                                if st.button("📊 Ver Tendencia", key=f"btn_{item['key']}", use_container_width=True):
                                    st.session_state.kpi_selected = item['key']
                                    st.rerun()

                        st.divider()

                    cols_grid = st.columns(4)
                    for idx, item in enumerate(kpis_grid):
                        with cols_grid[idx % 4]:
                            titulo = f"**{item['key']}**"
                            if item['prio'] == 3: titulo += " <span style='color:#FFD700; font-size:0.9em'>🌟</span>"
                            elif item['prio'] == 0: titulo += " <span style='color:#808495; font-size:0.8em'>(Irrelevante)</span>"
                            st.markdown(titulo, unsafe_allow_html=True)
                            
                            val_str = f"{item['val']:.0%}" if item['cfg']['is_pct'] else f"{item['val']:,.0f}".replace(",", ".")
                            st.markdown(render_card_html(item, val_str), unsafe_allow_html=True)
                            
                            st.caption(item['det_msg'])
                            if st.button("📊 Ver", key=f"btn_{item['key']}", use_container_width=True):
                                st.session_state.kpi_selected = item['key']
                                st.rerun()
                            st.divider()

            with col_graph:
                 st.subheader("Tendencia Histórica")
                 
                 current_kpi = st.session_state.kpi_selected
                 if current_kpi not in CONFIG_HOJAS:
                     current_kpi = 'Transacciones'
                 
                 def update_kpi_selector():
                     st.session_state.kpi_selected = st.session_state.kpi_selector_widget
                 
                 kpi_grafico = st.selectbox(
                     "Selecciona KPI:", 
                     list(CONFIG_HOJAS.keys()), 
                     index=list(CONFIG_HOJAS.keys()).index(current_kpi),
                     key='kpi_selector_widget',
                     on_change=update_kpi_selector
                 )
                 
                 col_tecnica = CONFIG_HOJAS[kpi_grafico]['kpi']
                 df_plot = df_hist[df_hist['Client'] == cliente_sel][['Date_Obj', col_tecnica]].set_index('Date_Obj').sort_index()
                 
                 title_plot = f"Evolución de {kpi_grafico}"
                 fig = px.line(df_plot, y=col_tecnica, markers=True, title=title_plot)
                 
                 # === AJUSTE DE ALTURA ===
                 # Igualamos la altura a 650px para coincidir con el contenedor de la izquierda
                 fig.update_layout(
                     height=500, 
                     margin=dict(l=20, r=20, t=40, b=20),
                     plot_bgcolor='rgba(0,0,0,0)',
                     paper_bgcolor='rgba(0,0,0,0)',
                     xaxis_title=None,
                     yaxis_title=None
                 )
                 st.plotly_chart(fig, use_container_width=True)
                 
                 st.info(f"💡 {CONFIG_HOJAS[kpi_grafico]['desc']}")

    # 4. OTRAS VISTAS
    elif st.session_state.view == "🧬 Ciclo Vida":
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

    elif st.session_state.view == "📂 Datos Maestros":
        st.dataframe(df_hist.drop(columns=['Date_Obj']), use_container_width=True)