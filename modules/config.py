# modules/config.py

# ID del Google Sheet
SHEET_ID = "1UpA9zZ3MbBRmP6M9qOd7G8NGouCufY-dU1cJ-ZB1cdU"
URL_EXPORT = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"

# Configuración técnica + Labels de Negocio
CONFIG_HOJAS = {
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