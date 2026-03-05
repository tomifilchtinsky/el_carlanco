"""Página de Compras con carrito reactivo."""
from nicegui import ui
from components.layout import create_layout, require_login
from components.carrito import Carrito
import database as db


def setup():
    @ui.page('/compras')
    @require_login
    def compras_page():
        create_layout(current_path='/compras')
        
        prods = db.get_productos()
        provs = db.get_proveedores()
        
        carrito_cols = [
            {'field': 'Producto', 'classes': 'flex-[3] font-medium'},
            {'field': 'Cantidad', 'classes': 'flex-1 text-center', 'format': lambda v: f"{v} un."},
            {'field': 'Costo Neto', 'classes': 'flex-1 text-right', 'format': lambda v: f"${v:,.2f}"},
            {'field': 'Subtotal', 'classes': 'flex-1 text-right font-bold', 'format': lambda v: f"${v:,.2f}"},
        ]
        
        totales_container = None
        
        def on_change(items):
            _update_totales()
        
        carrito = Carrito(columns=carrito_cols, on_change=on_change)
        
        with ui.column().classes('w-full p-6 gap-4'):
            ui.label('📦 Gestión de Stock y Precios').classes('text-2xl font-bold')
            
            # --- Agregar producto ---
            with ui.card().classes('w-full p-4'):
                ui.label('🚚 Ingreso de Mercadería por Lote').classes('text-lg font-semibold mb-3')
                
                prod_options = {
                    int(r['id_producto']): r['nombre'] for _, r in prods.iterrows()
                }
                
                with ui.row().classes('w-full gap-4 items-end'):
                    prod_select = ui.select(prod_options, label='Producto', with_input=True).classes('flex-[3]').props('outlined')
                    cant_input = ui.number('Cantidad Unidades', value=1, min=1, step=1).classes('flex-1').props('outlined')
                    precio_input = ui.number('Costo Unitario Neto ($)', value=0, min=0, step=0.1).classes('flex-1').props('outlined')
                
                def agregar():
                    if prod_select.value is None:
                        ui.notify('Seleccioná un producto', type='warning')
                        return
                    nombre = prod_options[prod_select.value]
                    cant = int(cant_input.value or 1)
                    precio = float(precio_input.value or 0)
                    
                    carrito.agregar({
                        'id_producto': int(prod_select.value),
                        'Producto': nombre,
                        'Cantidad': cant,
                        'Costo Neto': precio,
                        'Subtotal': cant * precio
                    })
                    ui.notify(f'✅ {nombre} agregado', type='positive')
                
                ui.button('🛒 Agregar al listado', on_click=agregar).classes('w-full mt-2').props('color=primary size=lg')
            
            # --- Carrito ---
            with ui.card().classes('w-full p-4'):
                ui.label('📋 Detalle del Pedido').classes('text-lg font-semibold mb-2')
                carrito.render()
                totales_container = ui.column().classes('w-full')
                
                def _update_totales():
                    nonlocal totales_container
                    if totales_container is None:
                        return
                    totales_container.clear()
                    items = carrito.get_items()
                    if not items:
                        return
                    with totales_container:
                        total = sum(i['Subtotal'] for i in items)
                        ui.label(f'💰 Total mercadería: ${total:,.2f}').classes('text-xl font-bold text-blue-700')
            
            # --- Finalizar compra ---
            with ui.card().classes('w-full p-4'):
                ui.label('✅ Registrar Ingreso').classes('text-lg font-semibold mb-2')
                
                with ui.row().classes('w-full gap-4 items-end'):
                    prov_select = ui.select(
                        {int(r['id_proveedor']): r['nombre'] for _, r in provs.iterrows()},
                        label='Proveedor'
                    ).classes('flex-1').props('outlined')
                    
                    nro_fac = ui.input('N° Factura').classes('flex-1').props('outlined')
                    flete_input = ui.number('Costo Flete ($)', value=0, min=0, step=100).classes('flex-1').props('outlined')
                
                async def finalizar():
                    if carrito.esta_vacio():
                        ui.notify('El carrito está vacío', type='warning')
                        return
                    if prov_select.value is None:
                        ui.notify('Seleccioná un proveedor', type='warning')
                        return
                    
                    items = carrito.get_items()
                    total = sum(i['Subtotal'] for i in items)
                    flete = float(flete_input.value or 0)
                    
                    try:
                        id_compra = db.registrar_compra(
                            id_proveedor=prov_select.value,
                            total_compra=total + flete,
                            costo_flete=flete,
                            nro_factura=nro_fac.value or "",
                            items=items
                        )
                        carrito.vaciar()
                        ui.notify(f'✅ Compra N° {id_compra} registrada', type='positive')
                    except Exception as e:
                        ui.notify(f'Error: {e}', type='negative')
                
                ui.button('💾 Guardar Compra', on_click=finalizar).classes('w-full').props('color=green size=lg')
            
            # --- Actualizar precios ---
            ui.separator()
            with ui.expansion('💲 Actualizar Precios de Venta', icon='edit').classes('w-full'):
                with ui.row().classes('w-full gap-4 items-end'):
                    prod_upd = ui.select(prod_options, label='Producto', with_input=True).classes('flex-[2]').props('outlined')
                    nuevo_precio = ui.number('Nuevo Precio Unitario ($)', value=0, min=0).classes('flex-1').props('outlined')
                
                def update_price_info():
                    if prod_upd.value:
                        row = prods[prods['id_producto'] == prod_upd.value].iloc[0]
                        nuevo_precio.value = float(row['precio_venta'])
                
                prod_upd.on_value_change(lambda: update_price_info())
                
                async def actualizar_precio():
                    if prod_upd.value is None or nuevo_precio.value is None:
                        ui.notify('Completá los campos', type='warning')
                        return
                    row = prods[prods['id_producto'] == prod_upd.value].iloc[0]
                    u_caja = int(row['unidades_por_caja'])
                    try:
                        db.actualizar_precio_venta(
                            prod_upd.value,
                            float(nuevo_precio.value),
                            float(nuevo_precio.value) * u_caja
                        )
                        ui.notify('✅ Precio actualizado', type='positive')
                    except Exception as e:
                        ui.notify(f'Error: {e}', type='negative')
                
                ui.button('💾 Actualizar Precio', on_click=actualizar_precio).props('color=blue')
            
            # --- Historial ---
            with ui.expansion('📋 Historial de Compras', icon='history').classes('w-full'):
                df_hc = db.get_historial_compras()
                if not df_hc.empty:
                    columns = [
                        {'name': c, 'label': c, 'field': c, 'sortable': True, 'align': 'left'}
                        for c in df_hc.columns
                    ]
                    ui.table(columns=columns, rows=df_hc.to_dict('records'),
                             row_key='N°', pagination={'rowsPerPage': 10}).classes('w-full')
                    
                    with ui.card().classes('w-full p-3 mt-2 bg-red-50'):
                        ui.label('⚠️ Cancelar un Ingreso').classes('font-semibold text-red-700')
                        with ui.row().classes('gap-2 items-end'):
                            id_del = ui.select(
                                {int(v): f"Compra #{v}" for v in df_hc['N°'].unique()},
                                label='Compra a cancelar'
                            ).classes('flex-1')
                            
                            async def eliminar():
                                if id_del.value:
                                    try:
                                        db.cancelar_compra(id_del.value)
                                        ui.notify('Compra eliminada. Stock ajustado.', type='positive')
                                        ui.navigate.to('/compras')
                                    except Exception as e:
                                        ui.notify(f'Error: {e}', type='negative')
                            
                            ui.button('🗑️ Eliminar', on_click=eliminar).props('color=red')
                else:
                    ui.label('No hay compras registradas').classes('text-gray-400')
