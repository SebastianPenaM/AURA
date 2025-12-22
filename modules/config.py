# modules/config.py

# ID del Google Sheet
SHEET_ID = "1UpA9zZ3MbBRmP6M9qOd7G8NGouCufY-dU1cJ-ZB1cdU"
URL_EXPORT = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"

# --- CONFIGURACIÓN MAESTRA DE KPIs ---
# Aquí definimos cómo se comporta cada indicador en AURA.
#
# CAMPOS:
# kpi:          Nombre exacto de la columna en las hojas de datos mensuales.
# is_pct:       True si es porcentaje (0.8 = 80%), False si es número entero.
# goal_col:     Nombre de la columna en la hoja 'Goals' (Meta específica).
# prio_col:     Nombre de la columna en la hoja 'Prioridad Goals' (0=Gris, 3=Estrella).
# desc:         Texto amigable que ve el usuario en pantalla.
# std:          Valor Estándar por defecto (si no hay Goal definido).
# mayor_mejor:  True (Queremos que suba, ej: Ventas), False (Queremos que baje, ej: Cancelados).

CONFIG_HOJAS = {
    'Transacciones': {
        'kpi': 'Transacciones', 
        'is_pct': False, 
        'goal_col': 'Goal_Transacciones',
        'prio_col': 'Prio_Transacciones',
        'desc': 'Potencial de Crecimiento',
        'std': 0,          # Depende puramente de tendencia
        'mayor_mejor': True
    },
    'Tiendas': {
        'kpi': 'Tiendas_Activas', 
        'is_pct': False, 
        'goal_col': 'Goal_Tiendas',
        'prio_col': 'Prio_Tiendas',
        'desc': 'Rollout / Expansión',
        'std': 0,          # Depende del plan de expansión
        'mayor_mejor': True
    },
    'Pedidos_Abiertos': {
        'kpi': 'Pedidos_Abiertos', 
        'is_pct': True,  
        'goal_col': 'Goal_Pedidos_Abiertos',
        'prio_col': 'Prio_Pedidos_Abiertos',
        'desc': 'Uso Correcto Plataforma',
        'std': 0.05,       # Menos del 5% es saludable
        'mayor_mejor': False
    }, 
    'Asignacion_Pickers': {
        'kpi': 'Tasa_Asignacion_Pickers', 
        'is_pct': True,  
        'goal_col': 'Goal_Asignacion_Pickers',
        'prio_col': 'Prio_Asignacion_Pickers',
        'desc': 'Automatización Picking',
        'std': 0.99,       # Menos del 10% manual
        'mayor_mejor': False
    },
    'Asignacion_Drivers': {
        'kpi': 'Tasa_Asignacion_Drivers', 
        'is_pct': True,  
        'goal_col': 'Goal_Asignacion_Drivers',
        'prio_col': 'Prio_Asignacion_Drivers',
        'desc': 'Automatización Delivery',
        'std': 0.99,       # Menos del 10% manual
        'mayor_mejor': False
    },
    'Ontime': {
        'kpi': 'Tasa_Ontime', 
        'is_pct': True,  
        'goal_col': 'Goal_Ontime', 
        'prio_col': 'Prio_Ontime',
        'desc': 'Puntualidad',
        'std': 0.80,       # Mínimo aceptable industria
        'mayor_mejor': True
    },
    'infull': {
        'kpi': 'Tasa_Infull', 
        'is_pct': True,  
        'goal_col': 'Goal_infull', 
        'prio_col': 'Prio_infull',
        'desc': 'Completitud',
        'std': 0.95,       # Mínimo aceptable industria
        'mayor_mejor': True
    },
    'cancelados': {
        'kpi': 'Tasa_Cancelados', 
        'is_pct': True,  
        'goal_col': 'Goal_cancelados', 
        'prio_col': 'Prio_cancelados',
        'desc': 'Fricción (Cancelados)',
        'std': 0.15,       # Máximo tolerable
        'mayor_mejor': False
    },
    'reprogramados': {
        'kpi': 'Tasa_Reprogramados', 
        'is_pct': True,  
        'goal_col': 'Goal_reprogramados', 
        'prio_col': 'Prio_reprogramados',
        'desc': 'Fricción (Reprogramados)',
        'std': 0.15,       # Máximo tolerable
        'mayor_mejor': False
    },
    
    'uph': {
        'kpi': 'UPH', 
        'is_pct': False, 
        'goal_col': 'Goal_uph', 
        'prio_col': 'Prio_uph',
        'desc': 'Productividad / Velocidad',
        'std': 60,         # Unidades por Hora base
        'mayor_mejor': True
    },
    'DAC': {
        'kpi': 'DAC', 
        'is_pct': True,  
        'goal_col': 'Goal_DAC', 
        'prio_col': 'Prio_DAC',
        'desc': 'Satisfacción / Quejas',
        'std': 0.50,       # Tolerancia máxima de reclamos
        'mayor_mejor': False
    },
    'CIHS': {
        'kpi': 'CIHS', 
        'is_pct': False, 
        'goal_col': 'Goal_CIHS', 
        'prio_col': 'Prio_CIHS',
        'desc': 'Adherencia (Features)',
        'std': 10,         # Uso mínimo de funcionalidades
        'mayor_mejor': True
    },
    'MRR': {
        'kpi': 'MRR', 
        'is_pct': False, 
        'goal_col': 'Goal_MRR',
        'prio_col': 'Prio_MRR',
        'desc': 'Ingresos Recurrentes ($)',
        'std': 0, 
        'mayor_mejor': True
    }
}