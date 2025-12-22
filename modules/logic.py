# modules/logic.py
import pandas as pd
import numpy as np
from modules.config import CONFIG_HOJAS

# ==========================================
# FASE 1: CLASIFICACIÓN CICLO DE VIDA
# ==========================================
def clasificar_ciclo_vida(serie_trx):
    """Determina en qué etapa de vida está el cliente según sus transacciones históricas."""
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

# ==========================================
# UTILIDADES MATEMÁTICAS
# ==========================================
def calcular_direccion_tendencia(serie):
    """Calcula la pendiente de los últimos 6 meses para saber si sube o baja."""
    vals = serie.values
    if len(vals) < 2: return 0
    
    y = vals[-6:] 
    x = np.arange(len(y))
    
    if np.var(y) == 0: return 0 
    slope = np.polyfit(x, y, 1)[0]
    return slope

def calcular_tendencia_trx(serie_trx):
    """Lógica específica para Transacciones (Detectar caídas bruscas >40%)."""
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

# ==========================================
# FASE 2: EVALUACIÓN DINÁMICA (CON PRIORIDADES)
# ==========================================
def evaluar_cumplimiento_dinamico(row_cliente, df_historia_cliente, kpi_config):
    """
    Evalúa un KPI cruzando: Meta vs Actual vs Tendencia vs Prioridad.
    Retorna: (Mensaje Corto, Detalle, Color, Score Numérico)
    """
    kpi = kpi_config['kpi']
    goal_col = kpi_config['goal_col']
    prio_col = kpi_config.get('prio_col', '') 
    
    # 1. LEER PRIORIDAD
    try:
        raw_prio = row_cliente.get(prio_col, 2)
        prioridad = float(raw_prio) if pd.notna(raw_prio) else 2.0
    except:
        prioridad = 2.0
        
    # --- CASO 0: IRRELEVANTE ---
    if prioridad == 0:
        return "No Aplica ⚪", "Configurado como irrelevante (0)", "secondary", 0

    mayor_es_mejor = kpi_config.get('mayor_mejor', True)
    estandar_aura = kpi_config.get('std', 0)
    
    val_actual = row_cliente[kpi]
    val_goal = row_cliente.get(goal_col, np.nan)
    
    # Tendencia
    if not df_historia_cliente.empty:
        serie_historia = df_historia_cliente.sort_values('Date_Obj')[kpi]
        pendiente = calcular_direccion_tendencia(serie_historia)
    else:
        pendiente = 0
        
    umb_slope = 0.001
    mejorando = False
    empeorando = False
    
    if mayor_es_mejor:
        if pendiente > umb_slope: mejorando = True
        elif pendiente < -umb_slope: empeorando = True
    else:
        if pendiente < -umb_slope: mejorando = True
        elif pendiente > umb_slope: empeorando = True
        
    flecha = "↗️" if pendiente > umb_slope else ("↘️" if pendiente < -umb_slope else "↔️")
    icono_prio = "🌟 " if prioridad == 3 else ""

    # EVALUACIÓN
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

            if cumple: return f"{icono_prio}Meta Cumplida 🎯", f"{label} ({flecha})", "success", 1
            else:
                if prioridad == 3: return f"{icono_prio}CRÍTICO 🚨", f"Fallo KPI Estrella ({flecha})", "error", -1
                
                if mejorando: return f"{icono_prio}Recuperando 🌤️", f"No llega, pero mejora {flecha}", "warning", 0
                elif empeorando: return f"{icono_prio}Crítico 🚨", f"Bajo Goal y empeora {flecha}", "error", -1
                else: return f"{icono_prio}Estancado ⚠️", f"Bajo Goal estable {flecha}", "warning", -1
        except: pass 

    # B. SIN GOAL
    if kpi == 'Transacciones':
        tendencia = row_cliente.get('Tendencia_Trx', 'N/A')
        if "Crecimiento" in tendencia: return f"{icono_prio}{tendencia}", "Positiva", "success", 1
        elif "Riesgo" in tendencia: return f"{icono_prio}{tendencia}", "Negativa", "error", -1
        else: return f"{icono_prio}{tendencia}", "Estable", "off", 0

    cumple = val_actual >= estandar_aura if mayor_es_mejor else val_actual <= estandar_aura
    fmt = f"{estandar_aura:.1%}" if kpi_config['is_pct'] else f"{estandar_aura:.1f}"
    
    if cumple: return f"{icono_prio}Estándar OK ✅", f"Std: {fmt} ({flecha})", "success", 1
    else:
         if prioridad == 3: return f"{icono_prio}CRÍTICO 🚨", f"Fallo Std Estrella ({flecha})", "error", -1
         if mejorando: return f"{icono_prio}Mejorando 🌤️", f"Fuera std, mejora {flecha}", "warning", 0
         else: return f"{icono_prio}Crítico ⚠️", f"Fuera std, empeora {flecha}", "error", -1
    
    return f"Tendencia {flecha}", "Informativo", "off", 0

# ==========================================
# FASE 3: DIAGNÓSTICO INTEGRAL (ACTUALIZADO)
# ==========================================
def generar_diagnostico_cliente(row, df_historia_cliente):
    """
    Genera el estado de salud y la lista de alertas.
    - Prioridad 0: Se ignora.
    - Prioridad 3: Si falla, fuerza estado CRÍTICO.
    """
    alertas = []
    fallo_estrella = False # Nueva bandera
    
    # Prioridades para lógica Churn específica
    trx_prio = float(row.get('Prio_Transacciones', 2)) if pd.notna(row.get('Prio_Transacciones')) else 2.0
    dac_prio = float(row.get('Prio_DAC', 2)) if pd.notna(row.get('Prio_DAC')) else 2.0
    
    for key, cfg in CONFIG_HOJAS.items():
        _, _, color, score = evaluar_cumplimiento_dinamico(row, df_historia_cliente, cfg)
        
        # 1. FILTRAR IRRELEVANTES (Prioridad 0)
        if color == 'secondary':
            continue
            
        desc = cfg['desc']
        val = row[cfg['kpi']]
        fmt_val = f"{val:.1%}" if cfg['is_pct'] else f"{val:.1f}"
        
        # Obtenemos la prioridad de ESTE kpi actual
        prio_kpi_col = cfg.get('prio_col', '')
        try:
            kpi_prio = float(row.get(prio_kpi_col, 2)) if pd.notna(row.get(prio_kpi_col)) else 2.0
        except: kpi_prio = 2.0

        # 2. GENERAR ALERTAS
        if score == -1: 
            # Si es Estrella (3) y falla, marcamos la bandera de gravedad máxima
            if kpi_prio == 3:
                fallo_estrella = True
                alertas.append(f"🌟❌ **{key} (Estrella)**: {desc} CRÍTICO ({fmt_val})")
            else:
                alertas.append(f"❌ **{key}**: {desc} Crítico ({fmt_val})")
                
        elif score == 0: 
            if kpi_prio == 3:
                alertas.append(f"🌟⚠️ **{key} (Estrella)**: {desc} Recuperando ({fmt_val})")
            else:
                alertas.append(f"⚠️ **{key}**: {desc} Recuperando/Estancado ({fmt_val})")
            
    n_alertas_rojas = sum(1 for a in alertas if "❌" in a)
    
    # 3. LÓGICA DE ESTADO (Buckets)
    
    # Riesgo Churn Clásico (Volumen + Quejas)
    es_critico_churn = False
    motivo_critico = ""
    
    trx_stat = evaluar_cumplimiento_dinamico(row, df_historia_cliente, CONFIG_HOJAS['Transacciones'])
    dac_stat = evaluar_cumplimiento_dinamico(row, df_historia_cliente, CONFIG_HOJAS['DAC'])
    
    if trx_prio > 0 and dac_prio > 0:
        if trx_stat[3] == -1 and dac_stat[3] == -1:
            es_critico_churn = True
            motivo_critico = "🚨 ALERTA CHURN: Caída de volumen crítica + Insatisfacción."

    # --- REGLAS DE CLASIFICACIÓN FINAL ---
    if es_critico_churn:
        estado = "Crítico / Riesgo"
    elif fallo_estrella: 
        # Si falla una estrella, es crítico automáticamente
        estado = "Crítico / Riesgo"
        if not motivo_critico: motivo_critico = "Fallo en KPI Estrella (Prioridad 3)."
    elif n_alertas_rojas >= 3: 
        estado = "Revisión Profunda"
    elif len(alertas) >= 1: 
        estado = "Atención Operativa"
    else: 
        estado = "Saludable / Campeón 🏆"
    
    return estado, alertas, motivo_critico