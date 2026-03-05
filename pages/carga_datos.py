"""Página de Carga de Datos (Maestros)."""
from nicegui import ui
from components.layout import create_layout, require_login
import database as db


def setup():
    @ui.page('/datos')
    @require_login
    def datos_page():
        create_layout(current_path='/datos')
        
        with ui.column().classes('w-full p-6 gap-4'):
            ui.label('📂 Carga de Datos y Maestros').classes('text-2xl font-bold')
            ui.label('Desde acá podés dar de alta Marcas, Clientes, Proveedores y Productos.').classes('text-gray-500')
            
            with ui.row().classes('w-full gap-4'):
                # --- Columna Izquierda ---
                with ui.column().classes('flex-1 gap-4'):
                    
                    # Marca
                    with ui.card().classes('w-full p-4'):
                        ui.label('1️⃣ Crear Marca').classes('text-lg font-semibold')
                        ui.label('Ej: Coca-Cola, Arcor, Villavicencio').classes('text-xs text-gray-400')
                        marca_input = ui.input('Nombre de la Marca').classes('w-full').props('outlined')
                        
                        async def crear_marca():
                            if not marca_input.value:
                                ui.notify('Escribí un nombre', type='warning')
                                return
                            try:
                                db.crear_marca(marca_input.value)
                                ui.notify(f'✅ Marca "{marca_input.value}" creada', type='positive')
                                marca_input.value = ''
                            except Exception as e:
                                ui.notify(f'Error: {e}', type='negative')
                        
                        ui.button('💾 Guardar Marca', on_click=crear_marca).classes('w-full').props('color=primary')
                    
                    # Proveedor
                    with ui.card().classes('w-full p-4'):
                        ui.label('2️⃣ Crear Proveedor').classes('text-lg font-semibold')
                        prov_nombre = ui.input('Nombre del Proveedor').classes('w-full').props('outlined')
                        prov_tel = ui.input('Teléfono / Contacto').classes('w-full').props('outlined')
                        prov_email = ui.input('Email (Opcional)').classes('w-full').props('outlined')
                        
                        async def crear_prov():
                            if not prov_nombre.value:
                                ui.notify('Escribí un nombre', type='warning')
                                return
                            try:
                                db.crear_proveedor(prov_nombre.value, prov_tel.value or '', prov_email.value or '')
                                ui.notify(f'✅ Proveedor "{prov_nombre.value}" creado', type='positive')
                                prov_nombre.value = ''
                                prov_tel.value = ''
                                prov_email.value = ''
                            except Exception as e:
                                ui.notify(f'Error: {e}', type='negative')
                        
                        ui.button('💾 Guardar Proveedor', on_click=crear_prov).classes('w-full').props('color=primary')
                
                # --- Columna Derecha ---
                with ui.column().classes('flex-1 gap-4'):
                    
                    # Cliente
                    with ui.card().classes('w-full p-4'):
                        ui.label('3️⃣ Crear Cliente').classes('text-lg font-semibold')
                        cli_nombre = ui.input('Nombre / Razón Social').classes('w-full').props('outlined')
                        cli_dir = ui.input('Dirección').classes('w-full').props('outlined')
                        cli_tel = ui.input('Teléfono').classes('w-full').props('outlined')
                        
                        async def crear_cli():
                            if not cli_nombre.value:
                                ui.notify('Escribí un nombre', type='warning')
                                return
                            try:
                                db.crear_cliente(cli_nombre.value, cli_dir.value or '', cli_tel.value or '')
                                ui.notify(f'✅ Cliente "{cli_nombre.value}" creado', type='positive')
                                cli_nombre.value = ''
                                cli_dir.value = ''
                                cli_tel.value = ''
                            except Exception as e:
                                ui.notify(f'Error: {e}', type='negative')
                        
                        ui.button('💾 Guardar Cliente', on_click=crear_cli).classes('w-full').props('color=primary')
            
            ui.separator()
            
            # --- Producto (ancho completo) ---
            with ui.card().classes('w-full p-4'):
                ui.label('4️⃣ Crear PRODUCTO NUEVO').classes('text-lg font-semibold')
                ui.label('ℹ️ Para crear un producto, necesitás haber creado la MARCA primero.').classes('text-sm text-blue-600 mb-3')
                
                marcas = db.get_marcas()
                
                if marcas.empty:
                    ui.label('⚠️ No hay marcas cargadas. Creá una marca primero.').classes('text-amber-600')
                else:
                    with ui.row().classes('w-full gap-4'):
                        prod_nombre = ui.input('Nombre del Producto').classes('flex-1').props('outlined')
                        marca_select = ui.select(
                            {int(r['id_marca']): r['nombre'] for _, r in marcas.iterrows()},
                            label='Marca'
                        ).classes('flex-1').props('outlined')
                    
                    with ui.row().classes('w-full gap-4'):
                        precio_vta = ui.number('Precio Venta Unitario ($)', value=0, min=0).classes('flex-1').props('outlined')
                        costo_ref = ui.number('Costo Compra Unitario ($)', value=0, min=0).classes('flex-1').props('outlined')
                        stock_ini = ui.number('Stock Inicial', value=0, min=0, step=1).classes('flex-1').props('outlined')
                    
                    unid_caja = ui.number('Unidades por Caja/Bulto', value=1, min=1, step=1).classes('w-48').props('outlined')
                    
                    async def crear_prod():
                        if not prod_nombre.value:
                            ui.notify('Falta el nombre del producto', type='warning')
                            return
                        if marca_select.value is None:
                            ui.notify('Seleccioná una marca', type='warning')
                            return
                        if float(precio_vta.value or 0) <= 0:
                            ui.notify('El precio debe ser mayor a 0', type='warning')
                            return
                        
                        u_caja = int(unid_caja.value or 1)
                        p_caja = float(precio_vta.value) * u_caja
                        
                        try:
                            db.crear_producto(
                                prod_nombre.value,
                                marca_select.value,
                                float(precio_vta.value),
                                float(costo_ref.value or 0),
                                int(stock_ini.value or 0),
                                u_caja
                            )
                            ui.notify(f'✅ Producto "{prod_nombre.value}" creado. Precio Caja: ${p_caja:,.2f}', type='positive')
                            prod_nombre.value = ''
                            precio_vta.value = 0
                            costo_ref.value = 0
                            stock_ini.value = 0
                        except Exception as e:
                            ui.notify(f'Error: {e}', type='negative')
                    
                    ui.button('🚀 CREAR PRODUCTO', on_click=crear_prod).classes('w-full').props('color=green size=lg')
