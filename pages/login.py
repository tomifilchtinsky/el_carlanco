"""Página de login."""
from nicegui import ui, app
from config import ADMIN_PASSWORD


def setup():
    @ui.page('/login')
    def login_page():
        # Si ya está logueado, redirigir al dashboard
        if app.storage.user.get('authenticated', False):
            ui.navigate.to('/')
            return
        
        # Centrar el formulario
        with ui.column().classes('absolute-center items-center gap-6'):
            # Logo / Header
            with ui.column().classes('items-center gap-2'):
                ui.icon('sports_bar', size='xl').classes('text-amber-500')
                ui.label('El Galpón').classes('text-3xl font-bold text-blue-900')
                ui.label('Sistema de Gestión').classes('text-sm text-gray-500')
            
            # Card de login
            with ui.card().classes('w-80 p-6'):
                ui.label('🔒 Acceso Restringido').classes('text-lg font-semibold text-center w-full mb-4')
                
                password_input = ui.input(
                    'Contraseña',
                    password=True,
                    password_toggle_button=True,
                    placeholder='Escribí la clave acá...'
                ).classes('w-full').props('outlined')
                
                error_label = ui.label('').classes('text-red-500 text-sm text-center w-full')
                error_label.set_visibility(False)
                
                async def do_login():
                    if password_input.value == ADMIN_PASSWORD:
                        app.storage.user['authenticated'] = True
                        ui.navigate.to('/')
                    else:
                        error_label.text = '⛔ Clave incorrecta. Probá de nuevo.'
                        error_label.set_visibility(True)
                
                ui.button('🚀 Entrar al Sistema', on_click=do_login).classes('w-full mt-4').props('color=primary size=lg')
                
                # Enter para submit
                password_input.on('keydown.enter', do_login)
