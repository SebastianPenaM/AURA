# modules/logic.py
import pandas as pd
import numpy as np
from modules.config import CONFIG_HOJAS

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

# --- UTILIDAD: TENDENCIA MATEMÁTICA ---
def calcular_direccion_tendencia(serie):
    vals = serie.values
    if len(vals) < 2: return 0
    y = vals[-6:] 
    x = np.arange(len(y))
    if np.var(y) == 0: return 0
    slope = np.polyfit(x, y, 1)[0]
    return slope

# --- FASE 2: TENDENCIA TRX (ESPECÍFICA) ---
def calcular_tendencia_trx(serie_trx):
    vals = serie_trx.values
    if len(vals) < 2: return "Estable ↔️"
    if len(vals) >= 4:
        ultimo = vals[-1]
        promedio = vals[-4:-1].mean()
        if promedio > 0 and ultimo < (promedio * 0.60):
            return "En Riesgo ↘️ (Caída >40%)"
    slope = calcular_direccion_tendencia(serie_trx)
    if slope > 0.5: return "Crecimiento ↗️"
    elif slope < -0.5: return "En Riesgo ↘️"
    else: return "Estable ↔️"

# --- FASE 2: EVALUACIÓN DINÁMICA ---
def evaluar_cumplimiento_dinamico(row_cliente, df_historia_cliente, kpi_config):
    kpi = kpi_config['kpi']
    goal_col = kpi_config['goal_col']
    val_actual = row_cliente[kpi]
    val_goal = row_cliente.get(goal_col, np.nan)
    
    # Calcular tendencia histórica
    if not df_historia_cliente.empty:
        serie_historia = df_historia_cliente.sort_values('Date_Obj')[kpi]
        pendiente = calcular_direccion_tendencia(serie_historia)
    else:
        pendiente = 0

    mayor_es_mejor = kpi in ['Transacciones', 'Tiendas_Activas', 'Tasa_Ontime', 'Tasa_Infull', 'UPH', 'CIHS']
    
    # Interpretación
    mejorando = False
    empeorando = False
    umb_slope = 0.001
    
    if mayor_es_mejor:
        if pendiente > umb_slope: mejorando = True
        elif pendiente < -umb_slope: empeorando = True
    else:
        if pendiente < -umb_slope: mejorando = True
        elif pendiente > umb_slope: empeorando = True
        
    flecha = "↗️" if pendiente > umb_slope else ("↘️" if pendiente < -umb_slope else "↔️")

    # A. CON GOAL
    if pd.notna(val_goal) and val_goal != '':
        try:
            val_goal = float(val_goal)
            if kpi == 'Transacciones':
                alcance = (val_actual / val_goal) if val_goal > 0 else 0
                label = f"{alcance:.0%} del Goal"
                cumple = alcance >= 1.0
            else:
                cumple = val_actual >= val_goal if mayor_es_mejor else val_actual <= val_goal
                label = f"Goal: {val_goal}"

            if cumple: return "Meta Cumplida 🎯", f"{label} ({flecha})", "success", 1
            else:
                if mejorando: return "Recuperando 🌤️", f"No llega, pero mejora {flecha}", "warning", 0
                elif empeorando: return "Crítico 🚨", f"Bajo Goal y empeora {flecha}", "error", -1
                else: return "Estancado ⚠️", f"Bajo Goal estable {flecha}", "warning", -1
        except: pass 

    # B. SIN GOAL (ESTÁNDAR)
    umb = None
    if kpi == 'Tasa_Ontime': umb = 0.80
    elif kpi == 'UPH': umb = 60
    elif kpi == 'CIHS': umb = 10
    elif kpi == 'DAC': umb = 0.50
    elif kpi in ['Pedidos_Abiertos', 'Tasa_Cancelados', 'Tasa_Reprogramados']: umb = 0.05
    elif 'Asignacion' in kpi: umb = 0.10
    
    if umb is not None:
        cumple = val_actual >= umb if mayor_es_mejor else val_actual <= umb
        fmt = f"{umb:.1%}" if kpi_config['is_pct'] else f"{umb:.1f}"
        if cumple: return "Estándar OK ✅", f"Std: {fmt} ({flecha})", "success", 1
        else:
             if mejorando: return "Mejorando 🌤️", f"Fuera std, mejora {flecha}", "warning", 0
             else: return "Crítico ⚠️", f"Fuera std, empeora {flecha}", "error", -1
    
    return f"Tendencia {flecha}", "Informativo", "off", 0

# --- FASE 3: DIAGNÓSTICO ---
def generar_diagnostico_cliente(row, df_historia_cliente):
    alertas = []
    for key, cfg in CONFIG_HOJAS.items():
        _, _, _, score = evaluar_cumplimiento_dinamico(row, df_historia_cliente, cfg)
        desc = cfg['desc']
        val = row[cfg['kpi']]
        fmt_val = f"{val:.1%}" if cfg['is_pct'] else f"{val:.1f}"
        
        if score == -1: alertas.append(f"❌ **{key}**: {desc} Crítico ({fmt_val})")
        elif score == 0: alertas.append(f"⚠️ **{key}**: {desc} Recuperando/Estancado ({fmt_val})")
            
    n_alertas_rojas = sum(1 for a in alertas if "❌" in a)
    trx_stat = evaluar_cumplimiento_dinamico(row, df_historia_cliente, CONFIG_HOJAS['Transacciones'])
    dac_stat = evaluar_cumplimiento_dinamico(row, df_historia_cliente, CONFIG_HOJAS['DAC'])
    
    es_critico = False
    motivo_critico = ""
    if trx_stat[3] == -1 and dac_stat[3] == -1:
        es_critico = True
        motivo_critico = "🚨 ALERTA CHURN: Caída de volumen crítica + Insatisfacción."

    if es_critico: estado = "Crítico / Riesgo"
    elif n_alertas_rojas >= 3: estado = "Revisión Profunda"
    elif len(alertas) >= 1: estado = "Atención Operativa"
    else: estado = "Saludable / Campeón 🏆"
    
    return estado, alertas, motivo_critico