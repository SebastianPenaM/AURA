import streamlit as st
import pandas as pd
import numpy as np
from functools import reduce

# ==============================================================================
#  CONFIGURACIÓN DE LA PÁGINA
# ==============================================================================
st.set_page_config(page_title="AURA - Dashboard Estratégico", page_icon="🧬", layout="wide")

st.title("🧬 AURA: Análisis Unificado del Ciclo de Vida")
st.markdown("Dashboard integral: Clasificación de Ciclo de Vida, Auditoría Dinámica (Meta + Tendencia) y Diagnóstico.")

# ==============================================================================
#  1. CONFIGURACIÓN DE DATOS
# ==============================================================================
SHEET_ID = "1UpA9zZ3MbBRmP6M9qOd7G8NGouCufY-dU1cJ-ZB1cdU"
URL_EXPORT = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"

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

# --- NUEVO MOTOR DE TENDENCIAS GENÉRICO ---
def calcular_direccion_tendencia(serie):
    """
    Retorna la pendiente matemática de cualquier serie de datos.
    > 0: Sube
    < 0: Baja
    """
    vals = serie.values
    # Necesitamos al menos 3 puntos para una tendencia fiable, sino usamos 2
    if len(vals) < 2: return 0
    
    # Usamos los últimos 6 meses máximo para que sea una tendencia reciente
    y = vals[-6:] 
    x = np.arange(len(y))
    
    if np.var(y) == 0: return 0 # Si todos los números son iguales
    
    slope = np.polyfit(x, y, 1)[0]
    return slope

# --- EVALUACIÓN DINÁMICA (META + TENDENCIA) ---
def evaluar_cumplimiento_dinamico(row_cliente, df_historia_cliente, kpi_config):
    """
    Evalúa:
    1. Si cumple el Goal del mes actual.
    2. Si la tendencia histórica es positiva o negativa.
    3. Cruza ambas variables para dar un semáforo inteligente.
    """
    kpi = kpi_config['kpi']
    goal_col = kpi_config['goal_col']
    
    # 1. Obtener Valor Actual y Meta
    val_actual = row_cliente[kpi]
    val_goal = row_cliente.get(goal_col, np.nan)
    
    # 2. Obtener Historia para calcular tendencia
    if not df_historia_cliente.empty:
        # Filtramos y ordenamos por fecha
        serie_historia = df_historia_cliente.sort_values('Date_Obj')[kpi]
        pendiente = calcular_direccion_tendencia(serie_historia)
    else:
        pendiente = 0

    # 3. Definir "Qué es bueno" (Dirección)
    # mayor_es_mejor: True para Ontime, False para Cancelados
    mayor_es_mejor = kpi in ['Transacciones', 'Tiendas_Activas', 'Tasa_Ontime', 'Tasa_Infull', 'UPH', 'CIHS']
    
    # Interpretación de la tendencia (¿Está mejorando?)
    mejorando = False
    empeorando = False
    
    umb_slope = 0.001 # Umbral para considerar que la pendiente no es cero
    
    if mayor_es_mejor:
        if pendiente > umb_slope: mejorando = True
        elif pendiente < -umb_slope: empeorando = True
    else: # Menor es mejor (ej: Cancelados)
        if pendiente < -umb_slope: mejorando = True # Si baja, mejora
        elif pendiente > umb_slope: empeorando = True # Si sube, empeora
        
    flecha = "↗️" if pendiente > umb_slope else ("↘️" if pendiente < -umb_slope else "↔️")

    # --- LÓGICA DE MATRIZ ---
    
    # A. TIENE GOAL DEFINIDO
    if pd.notna(val_goal) and val_goal != '':
        try:
            val_goal = float(val_goal)
            
            # Caso Transacciones (Porcentaje de alcance)
            if kpi == 'Transacciones':
                alcance = (val_actual / val_goal) if val_goal > 0 else 0
                label_goal = f"{alcance:.0%} del Goal"
                cumple_goal = alcance >= 1.0
            else:
                cumple_goal = val_actual >= val_goal if mayor_es_mejor else val_actual <= val_goal
                label_goal = f"Goal: {val_goal}"

            # CRUCE DE VARIABLES
            if cumple_goal:
                return "Meta Cumplida 🎯", f"{label_goal} ({flecha})", "success", 1
            else:
                # No cumple, pero...
                if mejorando:
                    return "Recuperando 🌤️", f"No llega al goal, pero mejora tendencia {flecha}", "warning", 0 # Amarillo
                elif empeorando:
                    return "Crítico 🚨", f"Bajo Goal y empeorando tendencia {flecha}", "error", -1 # Rojo
                else:
                    return "Estancado ⚠️", f"Bajo Goal y sin cambios {flecha}", "warning", -1 # Naranja/Rojo suave

        except: pass # Si falla, cae al estándar

    # B. NO TIENE GOAL (Usa estándar AURA + Tendencia)
    umb = None
    if kpi == 'Tasa_Ontime': umb = 0.80
    elif kpi == 'UPH': umb = 60
    elif kpi == 'CIHS': umb = 10
    elif kpi == 'DAC': umb = 0.50
    elif kpi in ['Pedidos_Abiertos', 'Tasa_Cancelados', 'Tasa_Reprogramados']: umb = 0.05
    elif 'Asignacion' in kpi: umb = 0.10
    
    if umb is not None:
        cumple_std = val_actual >= umb if mayor_es_mejor else val_actual <= umb
        fmt_std = f"{umb:.1%}" if kpi_config['is_pct'] else f"{umb:.1f}"
        
        if cumple_std:
            return "Estándar OK ✅", f"Std: {fmt_std} ({flecha})", "success", 1
        else:
             if mejorando:
                 return "Mejorando 🌤️", f"Fuera de std, pero tendencia positiva {flecha}", "warning", 0
             else:
                 return "Crítico ⚠️", f"Fuera de std y tendencia negativa {flecha}", "error", -1
    
    # Caso fallback
    return f"Tendencia {flecha}", "Informativo", "off", 0

def generar_diagnostico_cliente(row, df_historia_cliente):
    """Genera diagnóstico textual basado en la lógica dinámica"""
    alertas = []
    for key, cfg in config_hojas.items():
        _, _, _, score = evaluar_cumplimiento_dinamico(row, df_historia_cliente, cfg)
        desc = cfg['desc']
        val = row[cfg['kpi']]
        fmt_val = f"{val:.1%}" if cfg['is_pct'] else f"{val:.1f}"
        
        if score == -1:
            alertas.append(f"❌ **{key}**: {desc} Crítico ({fmt_val})")
        elif score == 0:
            alertas.append(f"⚠️ **{key}**: {desc} Recuperando/Estancado ({fmt_val})")
            
    n_alertas_rojas = sum(1 for a in alertas if "❌" in a)
    
    trx_stat = evaluar_cumplimiento_dinamico(row, df_historia_cliente, config_hojas['Transacciones'])
    dac_stat = evaluar_cumplimiento_dinamico(row, df_historia_cliente, config_hojas['DAC'])
    
    es_critico = False
    motivo_critico = ""
    
    # Si Transacciones están en Rojo (No Goal + Tendencia Mala) Y hay quejas
    if trx_stat[3] == -1 and dac_stat[3] == -1:
        es_critico = True
        motivo_critico = "🚨 ALERTA CHURN: Caída de volumen crítica + Insatisfacción."

    if es_critico: estado = "Crítico / Riesgo"
    elif n_alertas_rojas >= 3: estado = "Revisión Profunda"
    elif len(alertas) >= 1: estado = "Atención Operativa"
    else: estado = "Saludable / Campeón 🏆"
    
    return estado, alertas, motivo_critico

@st.cache_data(ttl=600)
def cargar_todo_aura():
    try:
        all_sheets = pd.read_excel(URL_EXPORT, sheet_name=None)
    except Exception as e:
        return None, None, None, f"Error Conexión: {e}"

    lista_dfs = []
    log = []
    for hoja, cfg in config_hojas.items():
        if hoja in all_sheets:
            lista_dfs.append(procesar_dataframe(all_sheets[hoja], cfg['kpi'], cfg['is_pct']))
        else:
            log.append(f"⚠️ Faltante: {hoja}")

    if not lista_dfs: return None, None, None, "No hay datos."

    df_hist = reduce(lambda l, r: pd.merge(l, r, on=['Client', 'Date'], how='outer'), lista_dfs)
    df_hist['Date_Obj'] = pd.to_datetime(df_hist['Date'], format='%b-%Y', errors='coerce')
    df_hist = df_hist.dropna(subset=['Date_Obj']).sort_values(by=['Client', 'Date_Obj']).fillna(0)

    # Snapshot último mes
    df_last = df_hist.sort_values('Date_Obj').groupby('Client').tail(1).copy()

    # Goals
    if 'Goals' in all_sheets:
        df_goals = all_sheets['Goals'].copy()
        df_goals = df_goals.rename(columns={df_goals.columns[0]: 'Client'})
        df_goals['Client'] = df_goals['Client'].astype(str).str.strip()
        df_last = pd.merge(df_last, df_goals, on='Client', how='left')

    # Ciclo de Vida
    df_trx_pivot = df_hist.pivot(index='Client', columns='Date_Obj', values='Transacciones').fillna(0)
    df_fase1 = df_trx_pivot.apply(clasificar_ciclo_vida, axis=1).reset_index()
    df_fase1.columns = ['Client', 'Fase_Vida']
    df_resumen = pd.merge(df_last, df_fase1, on='Client', how='left')

    # DIAGNÓSTICO (Con pase de historia para calcular tendencias on-the-fly)
    # Esto es un poco más lento pero mucho más preciso. Iteramos row por row.
    resultados_diag = []
    for idx, row in df_resumen.iterrows():
        cliente = row['Client']
        # Filtramos la historia solo de este cliente para no pasar todo el DF gigante
        historia_cliente = df_hist[df_hist['Client'] == cliente]
        res = generar_diagnostico_cliente(row, historia_cliente)
        resultados_diag.append(res)
        
    df_resumen['Estado_AURA'] = [x[0] for x in resultados_diag]
    df_resumen['Alertas_Detalle'] = [x[1] for x in resultados_diag]
    df_resumen['Motivo_Critico'] = [x[2] for x in resultados_diag]

    return df_hist, df_resumen, log

# ==============================================================================
#  FRONTEND
# ==============================================================================

if st.button('🔄 Cargar Dashboard AURA Completo'):
    with st.spinner('Conectando con la nube y procesando datos...'):
        hist, resumen, logs = cargar_todo_aura()
        if hist is not None:
            st.session_state['hist'] = hist
            st.session_state['resumen'] = resumen
            st.success("¡Datos actualizados en la nube!")

if 'resumen' in st.session_state:
    df_resumen = st.session_state['resumen']
    df_hist = st.session_state['hist']

    tab_auditoria, tab_ciclo, tab_diag, tab_maestro = st.tabs(["🎯 Auditoría (F2)", "🧬 Ciclo Vida (F1)", "🧠 Diagnóstico (F3)", "📂 Datos Maestros"])

    # ==========================
    # TAB 1: AUDITORÍA (F2) - DINÁMICA
    # ==========================
    with tab_auditoria:
        st.header("Auditoría Individual Dinámica")
        st.markdown("Evaluación combinada: **Meta del Mes** vs **Tendencia Reciente**.")
        clientes = sorted(df_resumen['Client'].unique())
        cliente_sel = st.selectbox("Auditar Cliente:", clientes)
        
        if cliente_sel:
            row = df_resumen[df_resumen['Client'] == cliente_sel].iloc[0]
            # Extraemos historia para pasar a la función
            historia_cli = df_hist[df_hist['Client'] == cliente_sel]
            
            st.info(f"Estado: {row['Fase_Vida']} | AURA Score: {row['Estado_AURA']}")
            
            cols = st.columns(4)
            idx = 0
            for key in config_hojas.keys():
                cfg = config_hojas[key]
                st_msg, det_msg, color, _ = evaluar_cumplimiento_dinamico(row, historia_cli, cfg)
                
                with cols[idx % 4]:
                    st.markdown(f"**{key}**")
                    val = row[cfg['kpi']]
                    val_str = f"{val:.1%}" if cfg['is_pct'] else f"{val:.1f}"
                    
                    if key == 'Transacciones' and 'del Goal' in det_msg:
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
            
            st.divider()
            st.subheader("📉 Análisis Visual")
            col_sel, col_graph = st.columns([1, 3])
            with col_sel:
                kpi_grafico = st.selectbox("Selecciona KPI:", list(config_hojas.keys()))
            with col_graph:
                col_tecnica = config_hojas[kpi_grafico]['kpi']
                df_plot = df_hist[df_hist['Client'] == cliente_sel][['Date_Obj', col_tecnica]].copy()
                df_plot = df_plot.set_index('Date_Obj').sort_index()
                st.line_chart(df_plot)

    # ==========================
    # TAB 2: CICLO DE VIDA (F1)
    # ==========================
    with tab_ciclo:
        st.header("Mapa de Ciclo de Vida")
        col1, col2 = st.columns([2, 1])
        conteo = df_resumen['Fase_Vida'].value_counts().reset_index()
        conteo.columns = ['Fase', 'Clientes']
        with col1: st.bar_chart(conteo.set_index('Fase'), color="#4A90E2")
        with col2: st.dataframe(conteo, hide_index=True, use_container_width=True)
            
        st.divider()
        st.subheader("🔍 Detalle de Clientes por Fase")
        fases_ordenadas = sorted(df_resumen['Fase_Vida'].unique())
        for fase in fases_ordenadas:
            clientes_en_fase = df_resumen[df_resumen['Fase_Vida'] == fase]['Client']
            with st.expander(f"{fase} ({len(clientes_en_fase)} clientes)"):
                st.write(", ".join(clientes_en_fase))

    # ==========================
    # TAB 3: DIAGNÓSTICO (F3)
    # ==========================
    with tab_diag:
        st.header("🧠 Diagnóstico Estratégico")
        st.markdown("Foco en clientes Activos. Alertas basadas en **Goal + Tendencia**.")
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
            st.error("🚨 **RIESGO CRÍTICO** (No cumplen Goal y Tendencia Negativa)")
            for index, row in criticos.iterrows():
                with st.expander(f"🔴 {row['Client']} ({row['Fase_Vida']})"):
                    if row['Motivo_Critico']: st.markdown(f"**Causa Raíz:** {row['Motivo_Critico']}")
                    st.markdown("**Alertas:**")
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

    with tab_maestro:
        st.header("📂 Datos Maestros")
        st.dataframe(df_hist.drop(columns=['Date_Obj']), use_container_width=True)