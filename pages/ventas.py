"""Página de Ventas con carrito reactivo."""
from nicegui import ui
from components.layout import create_layout, require_login
from components.carrito import Carrito
import database as db


def setup():
    @ui.page('/ventas')
    @require_login
    def ventas_page():
        create_layout(current_path='/ventas')
        
        # --- Estado local ---
        prods = db.get_productos()
        clientes = db.get_clientes()
        
        carrito_cols = [
            {'field': 'Producto', 'classes': 'flex-[3] font-medium'},
            {'field': 'Formato', 'classes': 'flex-1 text-center'},
            {'field': 'UnidadesTotales', 'classes': 'flex-1 text-center', 'format': lambda v: f"{v} un."},
            {'field': 'PrecioUnidad', 'classes': 'flex-1 text-right', 'format': lambda v: f"${v:,.2f}"},
            {'field': 'Subtotal', 'classes': 'flex-1 text-right font-bold', 'format': lambda v: f"${v:,.2f}"},
        ]
        
        # Containers para actualización dinámica
        totales_container = None
        
        def on_carrito_change(items):
            _update_totales()
        
        carrito = Carrito(columns=carrito_cols, on_change=on_carrito_change)
        
        with ui.column().classes('w-full p-6 gap-4'):
            ui.label('🛒 Armar Pedido de Venta').classes('text-2xl font-bold')
            
            # --- Selector de producto ---
            with ui.card().classes('w-full p-4'):
                ui.label('🍻 Selección de Producto').classes('text-lg font-semibold mb-3')
                
                if not prods.empty:
                    prod_options = {
                        int(r['id_producto']): f"{r['nombre']} ({r['marca']})"
                        for _, r in prods.iterrows()
                    }
                    
                    with ui.row().classes('w-full gap-4 items-end'):
                        prod_select = ui.select(
                            prod_options, label='Producto',
                            with_input=True
                        ).classes('flex-[3]').props('outlined')
                        
                        stock_label = ui.label('').classes('flex-1 text-lg font-bold')
                    
                    ui.separator()
                    
                    with ui.row().classes('w-full gap-4 items-end'):
                        formato = ui.toggle(['Unidad', 'Caja'], value='Unidad').classes('flex-1')
                        cantidad = ui.number('Cantidad', value=1, min=1, step=1).classes('flex-1').props('outlined')
                        precio_input = ui.number('Precio Unitario ($)', value=0, min=0, step=10.0).classes('flex-1').props('outlined')
                    
                    # Info dinámica
                    with ui.row().classes('w-full gap-4'):
                        info_unidades = ui.label('').classes('text-sm')
                        info_subtotal = ui.label('').classes('text-sm font-bold')
                        info_margen = ui.label('').classes('text-sm')
                    
                    stock_warning = ui.label('').classes('text-red-500 font-bold')
                    stock_warning.set_visibility(False)
                    
                    def update_info():
                        if prod_select.value is None:
                            return
                        row = prods[prods['id_producto'] == prod_select.value].iloc[0]
                        stk = int(row['stock_actual'])
                        u_caja = int(row['unidades_por_caja'])
                        
                        stock_label.text = f'Stock: {stk} un. ({stk // u_caja} cajas)'
                        precio_input.value = float(row['precio_venta'])
                        
                        fmt = formato.value or 'Unidad'
                        cant = int(cantidad.value or 1)
                        precio = float(precio_input.value or 0)
                        costo = float(row['precio_costo_promedio'])
                        
                        uni_total = cant * u_caja if fmt == 'Caja' else cant
                        sub = uni_total * precio
                        costo_total = uni_total * costo
                        margen = ((sub - costo_total) / sub * 100) if sub > 0 else 0
                        
                        info_unidades.text = f'📦 {uni_total} unidades totales'
                        info_subtotal.text = f'💵 Subtotal: ${sub:,.2f}'
                        
                        if margen < 0:
                            info_margen.text = f'📉 Margen: {margen:.1f}% (PÉRDIDA)'
                            info_margen.classes(replace='text-sm text-red-600 font-bold')
                        elif margen < 10:
                            info_margen.text = f'⚠️ Margen: {margen:.1f}% (BAJO)'
                            info_margen.classes(replace='text-sm text-amber-600')
                        else:
                            info_margen.text = f'✅ Margen: {margen:.1f}%'
                            info_margen.classes(replace='text-sm text-green-600')
                        
                        if uni_total > stk:
                            stock_warning.text = f'⚠️ Stock insuficiente: querés vender {uni_total} pero solo hay {stk}'
                            stock_warning.set_visibility(True)
                        else:
                            stock_warning.set_visibility(False)
                    
                    prod_select.on_value_change(lambda: update_info())
                    formato.on_value_change(lambda: update_info())
                    cantidad.on_value_change(lambda: update_info())
                    precio_input.on_value_change(lambda: update_info())
                    
                    def agregar_al_carrito():
                        if prod_select.value is None:
                            ui.notify('Seleccioná un producto', type='warning')
                            return
                        
                        row = prods[prods['id_producto'] == prod_select.value].iloc[0]
                        fmt = formato.value or 'Unidad'
                        cant = int(cantidad.value or 1)
                        precio = float(precio_input.value or 0)
                        u_caja = int(row['unidades_por_caja'])
                        costo = float(row['precio_costo_promedio'])
                        
                        uni_total = cant * u_caja if fmt == 'Caja' else cant
                        stk = int(row['stock_actual'])
                        
                        if uni_total > stk:
                            ui.notify('Stock insuficiente', type='negative')
                            return
                        
                        sub = uni_total * precio
                        costo_total = uni_total * costo
                        margen = ((sub - costo_total) / sub * 100) if sub > 0 else 0
                        
                        carrito.agregar({
                            'id_producto': int(prod_select.value),
                            'Producto': f"{row['nombre']} ({row['marca']})",
                            'Formato': f"{cant} {fmt}",
                            'Cantidad': cant,
                            'FormatoVenta': fmt,
                            'PrecioUnidad': precio,
                            'UnidadesTotales': uni_total,
                            'Subtotal': sub,
                            'Costo': costo_total,
                            'Margen': margen
                        })
                        ui.notify(f'✅ {row["nombre"]} agregado al carrito', type='positive')
                    
                    ui.button('🛒 Agregar al Pedido', on_click=agregar_al_carrito).classes('w-full mt-2').props('color=primary size=lg')
            
            # --- Carrito ---
            with ui.card().classes('w-full p-4'):
                ui.label('📝 Detalle de la Venta').classes('text-lg font-semibold mb-2')
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
                        costo = sum(i['Costo'] for i in items)
                        margen = ((total - costo) / total * 100) if total > 0 else 0
                        
                        with ui.row().classes('w-full justify-around'):
                            with ui.column().classes('items-center'):
                                ui.label('Total a Cobrar').classes('text-xs text-gray-500')
                                ui.label(f'${total:,.2f}').classes('text-2xl font-bold text-blue-700')
                            with ui.column().classes('items-center'):
                                ui.label('Costo Total').classes('text-xs text-gray-500')
                                ui.label(f'${costo:,.2f}').classes('text-xl')
                            with ui.column().classes('items-center'):
                                ui.label('Margen').classes('text-xs text-gray-500')
                                color = 'text-green-600' if margen > 0 else 'text-red-600'
                                ui.label(f'{margen:.1f}%').classes(f'text-xl font-bold {color}')
            
            # --- Finalizar venta ---
            with ui.card().classes('w-full p-4'):
                ui.label('✅ Finalizar Venta').classes('text-lg font-semibold mb-2')
                
                with ui.row().classes('w-full gap-4 items-end'):
                    cli_select = ui.select(
                        {int(r['id_cliente']): r['razon_social'] for _, r in clientes.iterrows()},
                        label='Cliente'
                    ).classes('flex-1').props('outlined')
                    
                    metodo = ui.select(
                        ['Efectivo', 'Transferencia', 'Mercado Pago'],
                        value='Efectivo', label='Método de Pago'
                    ).classes('flex-1').props('outlined')
                    
                    desc_input = ui.input('Descripción (opcional)').classes('flex-1').props('outlined')
                
                async def finalizar_venta():
                    if carrito.esta_vacio():
                        ui.notify('El carrito está vacío', type='warning')
                        return
                    if cli_select.value is None:
                        ui.notify('Seleccioná un cliente', type='warning')
                        return
                    
                    items = carrito.get_items()
                    total = sum(i['Subtotal'] for i in items)
                    
                    try:
                        id_venta = db.registrar_venta(
                            id_cliente=cli_select.value,
                            total_venta=total,
                            nro_factura="",
                            metodo_pago=metodo.value,
                            items=items,
                            descripcion=desc_input.value or ""
                        )
                        carrito.vaciar()
                        ui.notify(f'✅ Venta N° {id_venta} ({metodo.value}) registrada', type='positive')
                    except Exception as e:
                        ui.notify(f'Error: {e}', type='negative')
                
                ui.button('💾 Registrar Venta', on_click=finalizar_venta).classes('w-full').props('color=green size=lg')
            
            # --- Historial ---
            ui.separator()
            with ui.expansion('📋 Historial de Ventas', icon='history').classes('w-full'):
                df_hv = db.get_historial_ventas()
                if not df_hv.empty:
                    columns = [
                        {'name': c, 'label': c, 'field': c, 'sortable': True, 'align': 'left'}
                        for c in df_hv.columns
                    ]
                    ui.table(columns=columns, rows=df_hv.to_dict('records'), 
                             row_key='N°', pagination={'rowsPerPage': 10}).classes('w-full')
                    
                    # Cancelar venta
                    with ui.card().classes('w-full p-3 mt-2 bg-red-50'):
                        ui.label('⚠️ Cancelar una Venta').classes('font-semibold text-red-700')
                        with ui.row().classes('gap-2 items-end'):
                            id_del = ui.select(
                                {int(v): f"Venta #{v}" for v in df_hv['N°'].unique()},
                                label='Venta a cancelar'
                            ).classes('flex-1')
                            
                            async def eliminar():
                                if id_del.value:
                                    try:
                                        db.cancelar_venta(id_del.value)
                                        ui.notify('Venta eliminada y stock recompuesto', type='positive')
                                        ui.navigate.to('/ventas')
                                    except Exception as e:
                                        ui.notify(f'Error: {e}', type='negative')
                            
                            ui.button('🗑️ Eliminar', on_click=eliminar).props('color=red')
                else:
                    ui.label('No hay ventas registradas').classes('text-gray-400')
