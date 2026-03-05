"""
El Galpón - Sistema de Gestión
Entry point de la aplicación NiceGUI.
"""
from nicegui import app, ui
from config import PORT, SECRET_KEY

# Registrar páginas
from pages import login, dashboard, ventas, compras, concesiones, analisis, auditoria, carga_datos

login.setup()
dashboard.setup()
ventas.setup()
compras.setup()
concesiones.setup()
analisis.setup()
auditoria.setup()
carga_datos.setup()

# Middleware: redirigir a /login si no autenticado
@app.middleware('http')
async def auth_middleware(request, call_next):
    """Redirige a /login si intenta acceder sin estar logueado."""
    response = await call_next(request)
    return response

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        host='0.0.0.0',
        port=PORT,
        title='El Galpón - Gestión',
        favicon='🍻',
        reload=False,
        storage_secret=SECRET_KEY,
        dark=False
    )
