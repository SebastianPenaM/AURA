# modules/data.py
import pandas as pd
import streamlit as st
from functools import reduce
from modules.config import URL_EXPORT, CONFIG_HOJAS
from modules.logic import clasificar_ciclo_vida, calcular_tendencia_trx, generar_diagnostico_cliente

def procesar_dataframe(df, kpi_name, is_percentage=False):
    """
    Función auxiliar ETL inteligente.
    Detecta automáticamente la columna 'Cliente' y descarta 'Razon Social'.
    """
    # 1. DETECCIÓN INTELIGENTE DE COLUMNA CLIENTE
    posibles_nombres = ['Client', 'Cliente', 'CLIENTE', 'client', 'CLIENT']
    col_cliente_detectada = None

    # Búsqueda por nombre
    for col in df.columns:
        if str(col).strip() in posibles_nombres:
            col_cliente_detectada = col
            break
    
    # Búsqueda por posición (Fallback)
    if col_cliente_detectada is None:
        first_col = str(df.columns[0]).lower()
        if 'razon' in first_col or 'social' in first_col:
            col_cliente_detectada = df.columns[1] 
        else:
            col_cliente_detectada = df.columns[0]

    # 2. RENOMBRAR Y LIMPIAR
    df = df.rename(columns={col_cliente_detectada: 'Client'})
    
    # 3. ELIMINAR COLUMNAS NO DESEADAS (Razón Social)
    cols_a_borrar = [c for c in df.columns if ('razon' in str(c).lower() or 'social' in str(c).lower()) and c != 'Client']
    if cols_a_borrar:
        df = df.drop(columns=cols_a_borrar)

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

@st.cache_data(ttl=600)
def cargar_todo_aura():
    """
    Función Principal ETL (Extract, Transform, Load).
    """
    try:
        all_sheets = pd.read_excel(URL_EXPORT, sheet_name=None)
    except Exception as e:
        return None, None, None, f"Error Conexión: {e}"

    # 1. PROCESAR HOJAS DE KPIs
    lista_dfs = []
    log = []
    for hoja, cfg in CONFIG_HOJAS.items():
        if hoja in all_sheets:
            lista_dfs.append(procesar_dataframe(all_sheets[hoja], cfg['kpi'], cfg['is_pct']))
        else:
            log.append(f"⚠️ Faltante: {hoja}")

    if not lista_dfs: return None, None, None, "No hay datos en el Excel."

    # 2. UNIFICAR HISTORIA
    df_hist = reduce(lambda l, r: pd.merge(l, r, on=['Client', 'Date'], how='outer'), lista_dfs)
    
    df_hist['Date_Obj'] = pd.to_datetime(df_hist['Date'], format='%b-%Y', errors='coerce')
    df_hist = df_hist.dropna(subset=['Date_Obj']).sort_values(by=['Client', 'Date_Obj']).fillna(0)

    # 3. CREAR SNAPSHOT (Resumen)
    df_last = df_hist.sort_values('Date_Obj').groupby('Client').tail(1).copy()

    # 4. MERGE MAESTROS (Goals, Prioridad, etc.)
    # Función auxiliar para merges de metadatos
    def merge_metadata(df_main, sheet_name):
        if sheet_name in all_sheets:
            df_meta = all_sheets[sheet_name].copy()
            # Detectar columna cliente
            col_cli = df_meta.columns[0]
            for c in df_meta.columns:
                if str(c).strip().lower() in ['client', 'cliente']: col_cli = c; break
            
            df_meta = df_meta.rename(columns={col_cli: 'Client'})
            df_meta['Client'] = df_meta['Client'].astype(str).str.strip()
            
            # Merge Left
            return pd.merge(df_main, df_meta, on='Client', how='left')
        return df_main

    df_last = merge_metadata(df_last, 'Goals')
    df_last = merge_metadata(df_last, 'Prioridad Goals')
    
    # --- NUEVO: CARGAR CARACTERÍSTICAS ---
    # Esto buscará la hoja "Caracteristicas cliente" y pegará Region, Vertical, etc.
    df_last = merge_metadata(df_last, 'Caracteristicas cliente')

    # 5. FASE 1: Ciclo de Vida
    tendencias = {}
    for client in df_hist['Client'].unique():
        historia = df_hist[df_hist['Client'] == client].sort_values('Date_Obj')['Transacciones']
        tendencias[client] = calcular_tendencia_trx(historia)
    df_last['Tendencia_Trx'] = df_last['Client'].map(tendencias)

    df_trx_pivot = df_hist.pivot(index='Client', columns='Date_Obj', values='Transacciones').fillna(0)
    df_fase1 = df_trx_pivot.apply(clasificar_ciclo_vida, axis=1).reset_index()
    df_fase1.columns = ['Client', 'Fase_Vida']
    
    df_resumen = pd.merge(df_last, df_fase1, on='Client', how='left')

    # 6. FASE 3: Diagnóstico
    resultados_diag = []
    for idx, row in df_resumen.iterrows():
        cliente = row['Client']
        historia_cliente = df_hist[df_hist['Client'] == cliente]
        res = generar_diagnostico_cliente(row, historia_cliente)
        resultados_diag.append(res)
        
    df_resumen['Estado_AURA'] = [x[0] for x in resultados_diag]
    df_resumen['Alertas_Detalle'] = [x[1] for x in resultados_diag]
    df_resumen['Motivo_Critico'] = [x[2] for x in resultados_diag]

    # Rellenar vacíos en características nuevas con "Sin Asignar" para que los gráficos no fallen
    cols_posibles = ['Region', 'Vertical', 'Año', 'Tipo', 'region', 'vertical', 'año', 'tipo']
    for col in df_resumen.columns:
        if col.lower() in cols_posibles:
            df_resumen[col] = df_resumen[col].fillna('Sin Asignar').astype(str)

    return df_hist, df_resumen, log