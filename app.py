import streamlit as st
import pandas as pd
import numpy as np
from functools import reduce

# ==============================================================================
#  CONFIGURACIÓN DE LA PÁGINA
# ==============================================================================
st.set_page_config(page_title="AURA - Dashboard Integral", page_icon="🧬", layout="wide")

st.title("🧬 AURA: Análisis Unificado del Ciclo de Vida")
st.markdown("Dashboard integral: Clasificación de Ciclo de Vida, Auditoría de Metas y Diagnóstico de Riesgo.")

# ==============================================================================
#  1. CONFIGURACIÓN DE DATOS Y DEFINICIONES DE NEGOCIO
# ==============================================================================
SHEET_ID = "1UpA9zZ3MbBRmP6M9qOd7G8NGouCufY-dU1cJ-ZB1cdU"
URL_EXPORT = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"

# Configuración técnica + Labels de Negocio
config_hojas = {
    'Transacciones':      {'kpi': 'Transacciones',            'is_pct': False, 'goal_col': 'Goal_Transacciones', 'desc': 'Potencial de Crecimiento'},
    'Tiendas':            {'kpi': 'Tiendas_Activas',          'is_pct': False, 'goal_col': 'Goal_Tiendas',       'desc': 'Rollout / Expansión'},
    'Pedidos_Abiertos':   {'kpi': 'Pedidos_Abiertos',         'is_pct': True,  'goal_col': 'Goal_Pedidos_Abiertos','desc': 'Uso Correcto Plataforma'}, 
    'Asignacion_Pickers': {'kpi': 'Tasa_Asignacion_Pickers',  'is_pct': True,  'goal_col': 'Goal_Asignacion_Pickers','desc': 'Automatización Picking'},
    'Asignacion_Drivers': {'kpi': 'Tasa_Asignacion_Drivers',  'is_pct': True,  'goal_col': 'Goal_Asignacion_Drivers','desc': 'Automatización Delivery'},
    'Ontime':             {'kpi': 'Tasa_Ontime',              'is_pct': True,  'goal_col': 'Goal_Ontime',        'desc': 'Puntualidad'},
    'infull':             {'kpi': 'Tasa_Infull',              'is_pct': True,  'goal_col': 'Goal_infull',        'desc': 'Completitud'},
    'cancelados':         {'kpi': 'Tasa_Cancelados',          'is_pct': True,  'goal_col': 'Goal_cancelados',    'desc': 'Fricción (Cancelados)'},
    'reprogramados':      {'kpi': 'Tasa_Reprogramados',       'is_pct': True,  'goal_col': 'Goal_reprogramados', 'desc': 'Fricción (Reprogramados)'},
    'uph':                {'kpi': 'UPH',                      'is_pct': False, 'goal_col': 'Goal_uph',           'desc': 'Productividad / Velocidad'},
    'DAC':                {'kpi': 'DAC',                      'is_pct': True,  'goal_col': 'Goal_DAC',           'desc': 'Satisfacción / Quejas'},
    'CIHS':               {'kpi': 'CIHS',                     'is_pct': False, 'goal_col': 'Goal_CIHS',          'desc': 'Adherencia (Features)'}
}

# ==============================================================================
#  2. MOTORES DE LÓGICA (BACKEND)
# ==============================================================================

def procesar_dataframe(df, kpi_name, is_percentage=False):
    """Limpieza estándar ETL"""
    client_col = df.columns[0]
    df = df.rename(columns={client_col: 'Client'})
    df = df.dropna(subset=['Client'])
    df['Client'] = df['Client'].astype(str).str.strip()
    df = df.set_index('Client')

    for col in df.columns:
        df[col] = df[col].astype(str).str.replace(',', '', regex=False)
        if is_percentage:
            df[col] = df[col].str.replace('%', '', regex=False)
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df = df.fillna(0)
    if is_percentage:
        df = df / 100.0
    return df.reset_index().melt(id_vars='Client', var_name='Date', value_name=kpi_name)

# --- FASE 1: CICLO DE VIDA ---
def clasificar_ciclo_vida(serie_trx):
    vals = serie_trx.values
    total_historico = vals.sum()
    if total_historico == 0: return "Sin Actividad 🚫"
    
    trx_mes_actual = vals[-1]
    trx_mes_anterior = vals[-2] if len(vals) > 1 else 0
    meses_con_actividad = (vals > 0).sum()
    
    if trx_mes_actual > 0:
        if meses_con_actividad == 1: return "Deployment 🚀"
        elif meses_con_actividad in [2, 3]: return "Adopción 🌱"
        else: return "On Going ✅"
    else:
        if trx_mes_anterior > 0: return "Inactivo Reciente ⚠️"
        else: return "Churn 💔"

# --- FASE 2: TENDENCIAS ---
def calcular_tendencia_trx(serie_trx):
    vals = serie_trx.values
    if len(vals) < 2: return "Estable ↔️"
    
    # Caída abrupta (>40%)
    if len(vals) >= 4:
        ultimo = vals[-1]
        promedio = vals[-4:-1].mean()
        if promedio > 0 and ultimo < (promedio * 0.60):
            return "En Riesgo ↘️ (Caída >40%)"

    # Pendiente Lineal
    y = vals[-12:] if len(vals) > 12 else vals
    x = np.arange(len(y))
    if len(y) > 1 and np.var(y) > 0:
        slope = np.polyfit(x, y, 1)[0]
    else: slope = 0

    if slope > 0.5: return "Crecimiento ↗️"
    elif slope < -0.5: return "En Riesgo ↘️"
    else: return "Estable ↔️"

# --- EVALUACIÓN PUNTUAL ---
def evaluar_cumplimiento(row, kpi_config):
    """Retorna: Mensaje, Detalle, Color(success/warning/error), Score(-1, 0, 1)"""
    kpi = kpi_config['kpi']
    goal_col = kpi_config['goal_col']
    val_actual = row[kpi]
    val_goal = row.get(goal_col, np.nan)
    
    mayor_es_mejor = kpi in ['Transacciones', 'Tiendas_Activas', 'Tasa_Ontime', 'Tasa_Infull', 'UPH', 'CIHS']
    
    # 1. EVALUACIÓN CON META (GOAL)
    if pd.notna(val_goal) and val_goal != '':
        try:
            val_goal = float(val_goal)
            
            if kpi == 'Transacciones':
                alcance = (val_actual / val_goal) if val_goal > 0 else 0
                if alcance >= 1.0: return "Meta Cumplida 🎯", f"{alcance:.0%} del potencial", "success", 1
                else: return "Potencial no alcanzado ⚠️", f"{alcance:.0%} del potencial", "warning", -1
            
            if kpi == 'Tiendas_Activas':
                if val_actual >= val_goal: return "Rollout Completo ✅", f"{val_actual}/{val_goal} Tiendas", "success", 1
                else: return "Rollout Incompleto ⚠️", f"Faltan {int(val_goal - val_actual)} tiendas", "warning", -1

            cumple = val_actual >= val_goal if mayor_es_mejor else val_actual <= val_goal
            
            if cumple: return "Cumple Goal ✅", f"Goal: {val_goal}", "success", 1
            else: return "No Cumple ❌", f"Goal: {val_goal}", "error", -1
        except: pass

    # 2. EVALUACIÓN SIN META (ESTÁNDAR AURA)
    if kpi == 'Transacciones':
        tendencia = row.get('Tendencia_Trx', 'N/A')
        if "Crecimiento" in tendencia: return tendencia, "Tendencia Positiva", "success", 1
        elif "Riesgo" in tendencia: return tendencia, "Tendencia Negativa", "error", -1
        else: return tendencia, "Estable", "off", 0

    umb = None
    if kpi == 'Tasa_Ontime': umb = 0.80
    elif kpi == 'UPH': umb = 60
    elif kpi == 'CIHS': umb = 10
    elif kpi == 'DAC': umb = 0.50
    elif kpi in ['Pedidos_Abiertos', 'Tasa_Cancelados', 'Tasa_Reprogramados']: umb = 0.05
    elif 'Asignacion' in kpi: umb = 0.10
    else: return "Info", "Sin estándar", "off", 0

    cumple = val_actual >= umb if mayor_es_mejor else val_actual <= umb
    val_fmt = f"{val_actual:.1%}" if kpi_config['is_pct'] else f"{val_actual:.1f}"
    umb_fmt = f"{umb:.1%}" if kpi_config['is_pct'] else f"{umb:.1f}"
    
    if cumple: return "Estándar OK ✅", f"Std: {umb_fmt}", "success", 1
    else: return "Revisar ⚠️", f"Std: {umb_fmt}", "warning", -1

# --- FASE 3: DIAGNÓSTICO ESTRATÉGICO ---
def generar_diagnostico_cliente(row):
    alertas = []
    
    for key, cfg in config_hojas.items():
        _, _, _, score = evaluar_cumplimiento(row, cfg)
        desc = cfg['desc']
        val = row[cfg['kpi']]
        fmt_val = f"{val:.1%}" if cfg['is_pct'] else f"{val:.1f}"
        
        if score == -1: # Falló
            alertas.append(f"❌ **{key}**: {desc} deficiente ({fmt_val})")
            
    n_alertas = len(alertas)
    trx_status = evaluar_cumplimiento(row, config_hojas['Transacciones'])
    dac_status = evaluar_cumplimiento(row, config_hojas['DAC'])
    cihs_status = evaluar_cumplimiento(row, config_hojas['CIHS'])
    
    es_critico = False
    motivo_critico = ""
    
    if trx_status[2] in ['error', 'warning']:
        if dac_status[2] == 'error': 
            es_critico = True
            motivo_critico = "🚨 ALERTA CHURN: Caída de volumen + Alta insatisfacción (DAC)."
        elif cihs_status[2] == 'error': 
            es_critico = True
            motivo_critico = "🚨 RIESGO ADOPCIÓN: Cliente no crece y usa pocos features (CIHS bajo)."

    if es_critico: estado = "Crítico / Riesgo"
    elif n_alertas >= 4: estado = "Revisión Profunda"
    elif n_alertas >= 1: estado = "Atención Operativa"
    else: estado = "Saludable / Campeón 🏆"
        
    return estado, alertas, motivo_critico

@st.cache_data(ttl=600)
def cargar_todo_aura():
    try:
        all_sheets = pd.read_excel(URL_EXPORT, sheet_name=None)
    except Exception as e:
        return None, None, None, f"Error Conexión: {e}"

    # 1. Procesar KPIs
    lista_dfs = []
    log = []
    for hoja, cfg in config_hojas.items():
        if hoja in all_sheets:
            lista_dfs.append(procesar_dataframe(all_sheets[hoja], cfg['kpi'], cfg['is_pct']))
        else:
            log.append(f"⚠️ Faltante: {hoja}")

    if not lista_dfs: return None, None, None, "No hay datos."

    # 2. Master
    df_hist = reduce(lambda l, r: pd.merge(l, r, on=['Client', 'Date'], how='outer'), lista_dfs)
    df_hist['Date_Obj'] = pd.to_datetime(df_hist['Date'], format='%b-%Y', errors='coerce')
    df_hist = df_hist.dropna(subset=['Date_Obj']).sort_values(by=['Client', 'Date_Obj']).fillna(0)

    # 3. Snapshot
    df_last = df_hist.sort_values('Date_Obj').groupby('Client').tail(1).copy()
    
    tendencias = {}
    for client in df_hist['Client'].unique():
        historia = df_hist[df_hist['Client'] == client].sort_values('Date_Obj')['Transacciones']
        tendencias[client] = calcular_tendencia_trx(historia)
    df_last['Tendencia_Trx'] = df_last['Client'].map(tendencias)

    if 'Goals' in all_sheets:
        df_goals = all_sheets['Goals'].copy()
        df_goals = df_goals.rename(columns={df_goals.columns[0]: 'Client'})
        df_goals['Client'] = df_goals['Client'].astype(str).str.strip()
        df_last = pd.merge(df_last, df_goals, on='Client', how='left')

    # 4. Fase 1
    df_trx_pivot = df_hist.pivot(index='Client', columns='Date_Obj', values='Transacciones').fillna(0)
    df_fase1 = df_trx_pivot.apply(clasificar_ciclo_vida, axis=1).reset_index()
    df_fase1.columns = ['Client', 'Fase_Vida']
    
    df_resumen = pd.merge(df_last, df_fase1, on='Client', how='left')

    # 5. Fase 3
    diagnosticos = df_resumen.apply(generar_diagnostico_cliente, axis=1)
    df_resumen['Estado_AURA'] = [x[0] for x in diagnosticos]
    df_resumen['Alertas_Detalle'] = [x[1] for x in diagnosticos]
    df_resumen['Motivo_Critico'] = [x[2] for x in diagnosticos]

    return df_hist, df_resumen, log

# ==============================================================================
#  FRONTEND
# ==============================================================================

if st.button('🔄 Cargar Dashboard AURA Completo'):
    with st.spinner('Ejecutando diagnóstico integral de cartera...'):
        hist, resumen, logs = cargar_todo_aura()
        if hist is not None:
            st.session_state['hist'] = hist
            st.session_state['resumen'] = resumen
            st.success("¡Diagnóstico finalizado!")

if 'resumen' in st.session_state:
    df_resumen = st.session_state['resumen']
    df_hist = st.session_state['hist']

    # --- NUEVO ORDEN DE PESTAÑAS ---
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Auditoría (F2)", "🧬 Ciclo Vida (F1)", "🧠 Diagnóstico (F3)", "📂 Datos Maestros"])
    # ==========================
    # TAB 1: AUDITORÍA (F2)
    # ==========================
    with tab1:
        st.header("Auditoría Individual")
        clientes = sorted(df_resumen['Client'].unique())
        cliente_sel = st.selectbox("Auditar Cliente:", clientes)
        
        if cliente_sel:
            row = df_resumen[df_resumen['Client'] == cliente_sel].iloc[0]
            st.info(f"Estado: {row['Fase_Vida']} | AURA Score: {row['Estado_AURA']}")
            
            # --- CARDS DE KPIs ---
            kpis_orden = ['Transacciones', 'Tiendas', 'Ontime', 'infull', 'Pedidos_Abiertos', 
                          'Asignacion_Pickers', 'Asignacion_Drivers', 'cancelados', 'DAC', 'CIHS', 'uph']
            cols = st.columns(4)
            idx = 0
            for key in config_hojas.keys():
                cfg = config_hojas[key]
                st_msg, det_msg, color, _ = evaluar_cumplimiento(row, cfg)
                with cols[idx % 4]:
                    st.markdown(f"**{key}**")
                    val = row[cfg['kpi']]
                    val_str = f"{val:.1%}" if cfg['is_pct'] else f"{val:.1f}"
                    if key == 'Transacciones' and 'potencial' in det_msg:
                        try:
                            pct = float(det_msg.split('%')[0]) / 100
                            st.progress(min(pct, 1.0))
                        except: pass
                    
                    if color == 'success': st.success(f"{val_str}\n\n{st_msg}")
                    elif color == 'warning': st.warning(f"{val_str}\n\n{st_msg}")
                    elif color == 'error': st.error(f"{val_str}\n\n{st_msg}")
                    else: st.info(f"{val_str}\n\n{st_msg}")
                    st.caption(det_msg)
                    st.divider()
                idx += 1
            
            # --- GRÁFICO HISTÓRICO ---
            st.divider()
            st.subheader("📉 Análisis de Tendencia Histórica")
            col_sel, col_graph = st.columns([1, 3])
            
            with col_sel:
                kpi_grafico = st.selectbox("Selecciona KPI para visualizar historia:", list(config_hojas.keys()))
                st.caption(f"Visualizando: {config_hojas[kpi_grafico]['desc']}")
            
            with col_graph:
                col_tecnica = config_hojas[kpi_grafico]['kpi']
                df_plot = df_hist[df_hist['Client'] == cliente_sel][['Date_Obj', col_tecnica]].copy()
                df_plot = df_plot.set_index('Date_Obj').sort_index()
                st.line_chart(df_plot)
 # ==========================
    # TAB 2: CICLO DE VIDA (F1)
    # ==========================
    with tab2:
        st.header("Mapa de Ciclo de Vida")
        col1, col2 = st.columns([2, 1])
        
        conteo = df_resumen['Fase_Vida'].value_counts().reset_index()
        conteo.columns = ['Fase', 'Clientes']
        
        with col1: 
            st.bar_chart(conteo.set_index('Fase'), color="#4A90E2")
        with col2: 
            st.dataframe(conteo, hide_index=True, use_container_width=True)
            
        # --- NUEVO: DESPLEGABLES CON DETALLE ---
        st.divider()
        st.subheader("🔍 Detalle de Clientes por Fase")
        st.caption("Haz clic en cada categoría para ver qué clientes pertenecen a ella.")
        
        # Ordenamos las fases para que aparezcan siempre igual
        fases_ordenadas = sorted(df_resumen['Fase_Vida'].unique())
        
        for fase in fases_ordenadas:
            # Filtramos los clientes de esta fase
            clientes_en_fase = df_resumen[df_resumen['Fase_Vida'] == fase][['Client', 'Transacciones', 'Tendencia_Trx']]
            count = len(clientes_en_fase)
            
            with st.expander(f"{fase} ({count} clientes)"):
                st.dataframe(clientes_en_fase, use_container_width=True, hide_index=True)
    # ==========================
    # TAB 3: DIAGNÓSTICO (F3)
    # ==========================
    with tab3:
        st.header("🧠 Diagnóstico Estratégico (Clientes Activos)")
        st.markdown("Foco en clientes **On Going**, **Deployment** y **Adopción**.")
        
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
        
        if not criticos.empty:
            st.error("🚨 **RIESGO CRÍTICO**")
            for index, row in criticos.iterrows():
                with st.expander(f"🔴 {row['Client']} ({row['Fase_Vida']})"):
                    if row['Motivo_Critico']: st.markdown(f"**Causa Raíz:** {row['Motivo_Critico']}")
                    st.markdown("**Hallazgos:**")
                    for alerta in row['Alertas_Detalle']: st.markdown(f"- {alerta}")
        
        col_rev, col_ok = st.columns(2)
        with col_rev:
            st.warning("⚠️ **Necesitan Revisión**")
            df_view = pd.concat([revision, atencion])
            if not df_view.empty:
                for index, row in df_view.iterrows():
                     with st.expander(f"🔸 {row['Client']}"):
                        for alerta in row['Alertas_Detalle']: st.markdown(f"- {alerta}")
            else: st.success("Sin alertas operativas.")

        with col_ok:
            st.success("🏆 **Saludables**")
            if not saludables.empty:
                st.dataframe(saludables[['Client', 'Fase_Vida']], hide_index=True, use_container_width=True)
            else: st.info("No hay clientes 100% saludables hoy.")

    # ==========================
    # TAB 4: DATOS MAESTROS (Último)
    # ==========================
    with tab4:
        st.header("📂 Datos Maestros")
        st.markdown("Tabla consolidada de todas las fuentes de datos.")
        st.dataframe(df_hist.drop(columns=['Date_Obj']), use_container_width=True)
        csv_m = df_hist.drop(columns=['Date_Obj']).to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Maestro", csv_m, "aura_master.csv", "text/csv")