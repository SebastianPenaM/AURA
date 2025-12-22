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
    
    # Tomamos solo los últimos 6 datos para sensibilidad reciente
    y = vals[-6:] 
    x = np.arange(len(y))
    
    if np.var(y) == 0: return 0 # Línea plana
    slope = np.polyfit(x, y, 1)[0]
    return slope

def calcular_tendencia_trx(serie_trx):
    """Lógica específica para Transacciones (Detectar caídas bruscas >40%)."""
    vals = serie_trx.values
    if len(vals) < 2: return "Estable ↔️"
    
    # Alerta de caída súbita
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
    prio_col = kpi_config.get('prio_col', '') # Nombre columna prioridad
    
    # 1. LEER PRIORIDAD DEL CLIENTE
    # Si no existe dato, asumimos Prioridad 2 (Importante/Normal)
    try:
        prioridad = float(row_cliente.get(prio_col, 2))
        if pd.isna(prioridad): prioridad = 2
    except:
        prioridad = 2 
        
    # --- CASO ESPECIAL: PRIORIDAD 0 (IRRELEVANTE) ---
    # Devuelve color 'secondary' (gris) para que la interfaz lo pinte apagado.
    if prioridad == 0:
        return "No Aplica ⚪", "Configurado como irrelevante (0)", "secondary", 0

    # 2. CONFIGURACIÓN DEL KPI (Desde config.py)
    mayor_es_mejor = kpi_config.get('mayor_mejor', True)
    estandar_aura = kpi_config.get('std', 0)
    
    val_actual = row_cliente[kpi]
    val_goal = row_cliente.get(goal_col, np.nan)
    
    # 3. CÁLCULO DE TENDENCIA
    if not df_historia_cliente.empty:
        serie_historia = df_historia_cliente.sort_values('Date_Obj')[kpi]
        pendiente = calcular_direccion_tendencia(serie_historia)
    else:
        pendiente = 0
        
    # Interpretación de la pendiente según si es bueno subir o bajar
    umb_slope = 0.001
    mejorando = False
    empeorando = False
    
    if mayor_es_mejor: # Ej: Ventas (Sube=Bien)
        if pendiente > umb_slope: mejorando = True
        elif pendiente < -umb_slope: empeorando = True
    else: # Ej: Cancelados (Baja=Bien)
        if pendiente < -umb_slope: mejorando = True
        elif pendiente > umb_slope: empeorando = True
        
    flecha = "↗️" if pendiente > umb_slope else ("↘️" if pendiente < -umb_slope else "↔️")

    # Icono visual para Prioridad 3 (Estrella)
    icono_prio = "🌟 " if prioridad == 3 else ""

    # 4. EVALUACIÓN DE CUMPLIMIENTO
    
    # ESCENARIO A: TIENE META DEFINIDA (GOAL)
    if pd.notna(val_goal) and val_goal != '':
        try:
            val_goal = float(val_goal)
            
            # Caso especial Transacciones (es un % de alcance, no un booleano directo)
            if kpi == 'Transacciones':
                alcance = (val_actual / val_goal) if val_goal > 0 else 0
                label = f"{alcance:.0%} del Goal"
                cumple = alcance >= 1.0
            else:
                cumple = val_actual >= val_goal if mayor_es_mejor else val_actual <= val_goal
                label = f"Goal: {val_goal}"

            if cumple: 
                return f"{icono_prio}Meta Cumplida 🎯", f"{label} ({flecha})", "success", 1
            else:
                # Regla de Oro: Si es Prioridad 3 y falla, es CRITICO (Rojo), aunque mejore.
                if prioridad == 3:
                     return f"{icono_prio}CRÍTICO 🚨", f"Fallo en KPI Estrella ({flecha})", "error", -1
                
                if mejorando: return f"{icono_prio}Recuperando 🌤️", f"No llega, pero mejora {flecha}", "warning", 0
                elif empeorando: return f"{icono_prio}Crítico 🚨", f"Bajo Goal y empeora {flecha}", "error", -1
                else: return f"{icono_prio}Estancado ⚠️", f"Bajo Goal estable {flecha}", "warning", -1
        except: pass 

    # ESCENARIO B: NO TIENE META (USA ESTÁNDAR AURA)
    
    # Caso especial: Transacciones sin goal depende 100% de la tendencia histórica
    if kpi == 'Transacciones':
        tendencia_txt = row_cliente.get('Tendencia_Trx', 'N/A')
        if "Crecimiento" in tendencia_txt: return f"{icono_prio}{tendencia_txt}", "Positiva", "success", 1
        elif "Riesgo" in tendencia_txt: 
            return f"{icono_prio}{tendencia_txt}", "Negativa", "error", -1
        else: return f"{icono_prio}{tendencia_txt}", "Estable", "off", 0

    # Evaluación contra estándar (config.py)
    cumple = val_actual >= estandar_aura if mayor_es_mejor else val_actual <= estandar_aura
    fmt = f"{estandar_aura:.1%}" if kpi_config['is_pct'] else f"{estandar_aura:.1f}"
    
    if cumple: 
        return f"{icono_prio}Estándar OK ✅", f"Std: {fmt} ({flecha})", "success", 1
    else:
         if prioridad == 3: 
             return f"{icono_prio}CRÍTICO 🚨", f"Fallo Std Estrella ({flecha})", "error", -1
         
         if mejorando: return f"{icono_prio}Mejorando 🌤️", f"Fuera std, mejora {flecha}", "warning", 0
         else: return f"{icono_prio}Crítico ⚠️", f"Fuera std, empeora {flecha}", "error", -1
    
    # Fallback
    return f"Tendencia {flecha}", "Informativo", "off", 0

# ==========================================
# FASE 3: DIAGNÓSTICO INTEGRAL
# ==========================================
def generar_diagnostico_cliente(row, df_historia_cliente):
    """Genera el estado de salud general del cliente basado en sus alertas."""
    alertas = []
    
    # Obtenemos prioridades clave para la lógica de Churn
    # Usamos .get con default 2 por seguridad
    trx_prio = float(row.get('Prio_Transacciones', 2)) if pd.notna(row.get('Prio_Transacciones')) else 2
    dac_prio = float(row.get('Prio_DAC', 2)) if pd.notna(row.get('Prio_DAC')) else 2
    
    for key, cfg in CONFIG_HOJAS.items():
        # Evaluamos cada KPI
        _, _, color, score = evaluar_cumplimiento_dinamico(row, df_historia_cliente, cfg)
        
        # FILTRO DE RELEVANCIA:
        # Si el KPI tiene Prioridad 0 (color 'secondary'), lo ignoramos completamente en las alertas.
        if color == 'secondary':
            continue
            
        desc = cfg['desc']
        val = row[cfg['kpi']]
        fmt_val = f"{val:.1%}" if cfg['is_pct'] else f"{val:.1f}"
        
        if score == -1: alertas.append(f"❌ **{key}**: {desc} Crítico ({fmt_val})")
        elif score == 0: alertas.append(f"⚠️ **{key}**: {desc} Recuperando/Estancado ({fmt_val})")
            
    n_alertas_rojas = sum(1 for a in alertas if "❌" in a)
    
    # Lógica de Diagnóstico Crítico (Churn Risk)
    trx_stat = evaluar_cumplimiento_dinamico(row, df_historia_cliente, CONFIG_HOJAS['Transacciones'])
    dac_stat = evaluar_cumplimiento_dinamico(row, df_historia_cliente, CONFIG_HOJAS['DAC'])
    
    es_critico = False
    motivo_critico = ""
    
    # Solo activamos alarma de Churn si Transacciones y DAC son importantes para este cliente (>0)
    if trx_prio > 0 and dac_prio > 0:
        if trx_stat[3] == -1 and dac_stat[3] == -1:
            es_critico = True
            motivo_critico = "🚨 ALERTA CHURN: Caída de volumen crítica + Insatisfacción."

    if es_critico: estado = "Crítico / Riesgo"
    elif n_alertas_rojas >= 3: estado = "Revisión Profunda"
    elif len(alertas) >= 1: estado = "Atención Operativa"
    else: estado = "Saludable / Campeón 🏆"
    
    return estado, alertas, motivo_critico