# modules/data.py
import pandas as pd
import streamlit as st
from functools import reduce
from modules.config import URL_EXPORT, CONFIG_HOJAS
from modules.logic import clasificar_ciclo_vida, calcular_tendencia_trx, generar_diagnostico_cliente

def procesar_dataframe(df, kpi_name, is_percentage=False):
    client_col = df.columns[0]
    df = df.rename(columns={client_col: 'Client'})
    df = df.dropna(subset=['Client'])
    df['Client'] = df['Client'].astype(str).str.strip()
    df = df.set_index('Client')
    for col in df.columns:
        df[col] = df[col].astype(str).str.replace(',', '', regex=False)
        if is_percentage: df[col] = df[col].str.replace('%', '', regex=False)
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.fillna(0)
    if is_percentage: df = df / 100.0
    return df.reset_index().melt(id_vars='Client', var_name='Date', value_name=kpi_name)

@st.cache_data(ttl=600)
def cargar_todo_aura():
    try:
        all_sheets = pd.read_excel(URL_EXPORT, sheet_name=None)
    except Exception as e:
        return None, None, None, f"Error Conexión: {e}"

    lista_dfs = []
    log = []
    for hoja, cfg in CONFIG_HOJAS.items():
        if hoja in all_sheets:
            lista_dfs.append(procesar_dataframe(all_sheets[hoja], cfg['kpi'], cfg['is_pct']))
        else:
            log.append(f"⚠️ Faltante: {hoja}")

    if not lista_dfs: return None, None, None, "No hay datos."

    # Unificación
    df_hist = reduce(lambda l, r: pd.merge(l, r, on=['Client', 'Date'], how='outer'), lista_dfs)
    df_hist['Date_Obj'] = pd.to_datetime(df_hist['Date'], format='%b-%Y', errors='coerce')
    df_hist = df_hist.dropna(subset=['Date_Obj']).sort_values(by=['Client', 'Date_Obj']).fillna(0)

    # Snapshot Último Mes
    df_last = df_hist.sort_values('Date_Obj').groupby('Client').tail(1).copy()

    # Goals
    if 'Goals' in all_sheets:
        df_goals = all_sheets['Goals'].copy()
        df_goals = df_goals.rename(columns={df_goals.columns[0]: 'Client'})
        df_goals['Client'] = df_goals['Client'].astype(str).str.strip()
        df_last = pd.merge(df_last, df_goals, on='Client', how='left')

    # FASE 1
    tendencias = {}
    for client in df_hist['Client'].unique():
        historia = df_hist[df_hist['Client'] == client].sort_values('Date_Obj')['Transacciones']
        tendencias[client] = calcular_tendencia_trx(historia)
    df_last['Tendencia_Trx'] = df_last['Client'].map(tendencias)

    df_trx_pivot = df_hist.pivot(index='Client', columns='Date_Obj', values='Transacciones').fillna(0)
    df_fase1 = df_trx_pivot.apply(clasificar_ciclo_vida, axis=1).reset_index()
    df_fase1.columns = ['Client', 'Fase_Vida']
    df_resumen = pd.merge(df_last, df_fase1, on='Client', how='left')

    # FASE 3 (DIAGNÓSTICO)
    resultados_diag = []
    for idx, row in df_resumen.iterrows():
        cliente = row['Client']
        historia_cliente = df_hist[df_hist['Client'] == cliente]
        res = generar_diagnostico_cliente(row, historia_cliente)
        resultados_diag.append(res)
        
    df_resumen['Estado_AURA'] = [x[0] for x in resultados_diag]
    df_resumen['Alertas_Detalle'] = [x[1] for x in resultados_diag]
    df_resumen['Motivo_Critico'] = [x[2] for x in resultados_diag]

    return df_hist, df_resumen, log