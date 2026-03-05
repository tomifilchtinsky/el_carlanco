"""
Layout compartido: header, sidebar de navegación, y decorator de autenticación.
"""
from functools import wraps
from nicegui import ui, app


MENU_ITEMS = [
    {"label": "📊 Dashboard", "icon": "dashboard", "path": "/"},
    {"label": "💰 Ventas", "icon": "point_of_sale", "path": "/ventas"},
    {"label": "🚚 Compras", "icon": "local_shipping", "path": "/compras"},
    {"label": "🤝 Concesiones", "icon": "handshake", "path": "/concesiones"},
    {"label": "📈 Análisis", "icon": "analytics", "path": "/analisis"},
    {"label": "🔍 Auditoría", "icon": "fact_check", "path": "/auditoria"},
    {"label": "📂 Carga de Datos", "icon": "add_circle", "path": "/datos"},
]


def is_authenticated() -> bool:
    """Verifica si el usuario está logueado."""
    return app.storage.user.get('authenticated', False)


def require_login(func):
    """Decorator para proteger páginas. Redirige a /login si no está autenticado."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            ui.navigate.to('/login')
            return
        return func(*args, **kwargs)
    return wrapper


def create_layout(current_path: str = "/"):
    """Crea el layout base con header y sidebar para la página actual."""
    
    # --- Header ---
    with ui.header().classes('items-center justify-between bg-blue-900 px-6'):
        with ui.row().classes('items-center gap-3'):
            ui.icon('sports_bar', size='sm').classes('text-amber-400')
            ui.label('El Galpón').classes('text-xl font-bold text-white')
        
        with ui.row().classes('items-center gap-2'):
            ui.label('Sistema de Gestión').classes('text-sm text-blue-200')
            ui.button(icon='logout', on_click=lambda: logout()).props('flat color=white size=sm')
    
    # --- Sidebar ---
    with ui.left_drawer(value=True).classes('bg-blue-950 p-0') as drawer:
        ui.label('MENÚ').classes('text-xs text-blue-300 px-4 pt-4 pb-2 font-bold tracking-wider')
        
        for item in MENU_ITEMS:
            is_active = current_path == item['path']
            bg = 'bg-blue-800' if is_active else 'hover:bg-blue-900'
            text_color = 'text-white font-bold' if is_active else 'text-blue-200'
            
            with ui.element('div').classes(f'flex items-center gap-3 px-4 py-3 cursor-pointer {bg} transition-all'):
                ui.icon(item['icon']).classes(f'text-lg {"text-amber-400" if is_active else "text-blue-400"}')
                link = ui.link(item['label'], item['path']).classes(f'no-underline {text_color} text-sm')
    
    return drawer


def logout():
    """Cierra la sesión del usuario."""
    app.storage.user['authenticated'] = False
    ui.navigate.to('/login')
