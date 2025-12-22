# modules/data.py
import pandas as pd
import streamlit as st
from functools import reduce
from modules.config import URL_EXPORT, CONFIG_HOJAS
from modules.logic import clasificar_ciclo_vida, calcular_tendencia_trx, generar_diagnostico_cliente

def procesar_dataframe(df, kpi_name, is_percentage=False):
    """
    Función auxiliar para limpiar los datos crudos de Excel.
    Convierte textos a números, maneja porcentajes y limpia nombres de clientes.
    """
    client_col = df.columns[0]
    df = df.rename(columns={client_col: 'Client'})
    df = df.dropna(subset=['Client'])
    df['Client'] = df['Client'].astype(str).str.strip()
    df = df.set_index('Client')

    for col in df.columns:
        # Limpieza de caracteres no numéricos
        df[col] = df[col].astype(str).str.replace(',', '', regex=False)
        if is_percentage:
            df[col] = df[col].str.replace('%', '', regex=False)
        # Conversión a números
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df = df.fillna(0)
    if is_percentage:
        df = df / 100.0
        
    # Transformación a formato largo (Tidy Data) para facilitar gráficas
    return df.reset_index().melt(id_vars='Client', var_name='Date', value_name=kpi_name)

@st.cache_data(ttl=600)
def cargar_todo_aura():
    """
    Función Principal ETL (Extract, Transform, Load).
    Descarga el Excel, procesa todas las hojas, une metas y prioridades,
    y ejecuta la lógica de negocio (Fase 1 y Fase 3).
    """
    try:
        # Descarga optimizada: lee todas las hojas de una sola vez
        all_sheets = pd.read_excel(URL_EXPORT, sheet_name=None)
    except Exception as e:
        return None, None, None, f"Error Conexión: {e}"

    # 1. PROCESAR HOJAS DE KPIs (Histórico)
    lista_dfs = []
    log = []
    for hoja, cfg in CONFIG_HOJAS.items():
        if hoja in all_sheets:
            lista_dfs.append(procesar_dataframe(all_sheets[hoja], cfg['kpi'], cfg['is_pct']))
        else:
            log.append(f"⚠️ Faltante: {hoja}")

    if not lista_dfs: return None, None, None, "No hay datos en el Excel."

    # 2. UNIFICAR HISTORIA (Merge masivo)
    df_hist = reduce(lambda l, r: pd.merge(l, r, on=['Client', 'Date'], how='outer'), lista_dfs)
    
    # Convertir fechas para ordenamiento correcto
    df_hist['Date_Obj'] = pd.to_datetime(df_hist['Date'], format='%b-%Y', errors='coerce')
    df_hist = df_hist.dropna(subset=['Date_Obj']).sort_values(by=['Client', 'Date_Obj']).fillna(0)

    # 3. CREAR SNAPSHOT (Resumen del último mes)
    df_last = df_hist.sort_values('Date_Obj').groupby('Client').tail(1).copy()

    # 4. MERGE DATOS MAESTROS: GOALS (Metas)
    if 'Goals' in all_sheets:
        df_goals = all_sheets['Goals'].copy()
        df_goals = df_goals.rename(columns={df_goals.columns[0]: 'Client'})
        df_goals['Client'] = df_goals['Client'].astype(str).str.strip()
        df_last = pd.merge(df_last, df_goals, on='Client', how='left')

    # 5. MERGE DATOS MAESTROS: PRIORIDAD (NUEVO)
    # Aquí cargamos la hoja donde defines 0 (Irrelevante), 3 (Crítico), etc.
    if 'Prioridad Goals' in all_sheets:
        df_prio = all_sheets['Prioridad Goals'].copy()
        df_prio = df_prio.rename(columns={df_prio.columns[0]: 'Client'})
        df_prio['Client'] = df_prio['Client'].astype(str).str.strip()
        df_last = pd.merge(df_last, df_prio, on='Client', how='left')

    # 6. EJECUTAR FASE 1: Ciclo de Vida y Tendencias
    tendencias = {}
    for client in df_hist['Client'].unique():
        historia = df_hist[df_hist['Client'] == client].sort_values('Date_Obj')['Transacciones']
        tendencias[client] = calcular_tendencia_trx(historia)
    df_last['Tendencia_Trx'] = df_last['Client'].map(tendencias)

    # Matriz para clasificar ciclo de vida
    df_trx_pivot = df_hist.pivot(index='Client', columns='Date_Obj', values='Transacciones').fillna(0)
    df_fase1 = df_trx_pivot.apply(clasificar_ciclo_vida, axis=1).reset_index()
    df_fase1.columns = ['Client', 'Fase_Vida']
    
    # Unir Fase 1 al resumen
    df_resumen = pd.merge(df_last, df_fase1, on='Client', how='left')

    # 7. EJECUTAR FASE 3: Diagnóstico Inteligente
    resultados_diag = []
    for idx, row in df_resumen.iterrows():
        cliente = row['Client']
        # Pasamos la historia de ESTE cliente específico para calcular tendencias de cada KPI
        historia_cliente = df_hist[df_hist['Client'] == cliente]
        res = generar_diagnostico_cliente(row, historia_cliente)
        resultados_diag.append(res)
        
    df_resumen['Estado_AURA'] = [x[0] for x in resultados_diag]
    df_resumen['Alertas_Detalle'] = [x[1] for x in resultados_diag]
    df_resumen['Motivo_Critico'] = [x[2] for x in resultados_diag]

    return df_hist, df_resumen, log