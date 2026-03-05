"""Página de Concesiones."""
from nicegui import ui
from components.layout import create_layout, require_login
from components.carrito import Carrito
import database as db


def setup():
    @ui.page('/concesiones')
    @require_login
    def concesiones_page():
        create_layout(current_path='/concesiones')
        
        prods = db.get_productos()
        clientes = db.get_clientes()
        
        carrito_cols = [
            {'field': 'Producto', 'classes': 'flex-[3] font-medium'},
            {'field': 'cantidad', 'classes': 'flex-1 text-center', 'format': lambda v: f"{v} un."},
        ]
        carrito = Carrito(columns=carrito_cols)
        
        with ui.column().classes('w-full p-6 gap-4'):
            ui.label('🤝 Gestión de Mercadería en Consignación').classes('text-2xl font-bold')
            
            # --- KPIs ---
            kpis = db.get_kpis_concesion()
            with ui.row().classes('w-full gap-4'):
                with ui.card().classes('flex-1 p-4'):
                    ui.label('📦 Unidades en la Calle').classes('text-xs text-gray-500')
                    ui.label(f"{kpis['unidades_calle']:,}").classes('text-2xl font-bold')
                with ui.card().classes('flex-1 p-4'):
                    ui.label('💸 Capital en Riesgo').classes('text-xs text-gray-500')
                    ui.label(f"${kpis['capital_riesgo']:,.2f}").classes('text-2xl font-bold text-red-600')
                with ui.card().classes('flex-1 p-4'):
                    ui.label('💰 Venta Potencial').classes('text-xs text-gray-500')
                    ui.label(f"${kpis['venta_potencial']:,.2f}").classes('text-2xl font-bold text-green-600')
            
            # --- Nueva entrega ---
            with ui.card().classes('w-full p-4'):
                ui.label('📦 Nueva Entrega de Concesión').classes('text-lg font-semibold mb-3')
                
                prod_options = {
                    int(r['id_producto']): f"{r['nombre']} (Stock: {int(r['stock_actual'])})"
                    for _, r in prods.iterrows()
                }
                
                with ui.row().classes('w-full gap-4 items-end'):
                    prod_select = ui.select(prod_options, label='Producto', with_input=True).classes('flex-[2]').props('outlined')
                    cant_input = ui.number('Cantidad', value=1, min=1, step=1).classes('flex-1').props('outlined')
                
                def agregar():
                    if prod_select.value is None:
                        ui.notify('Seleccioná un producto', type='warning')
                        return
                    row = prods[prods['id_producto'] == prod_select.value].iloc[0]
                    cant = int(cant_input.value or 1)
                    if cant > int(row['stock_actual']):
                        ui.notify('Stock insuficiente', type='negative')
                        return
                    carrito.agregar({
                        'id': int(prod_select.value),
                        'Producto': f"{row['nombre']} ({row['marca']})",
                        'cantidad': cant
                    })
                    ui.notify(f'✅ {row["nombre"]} agregado', type='positive')
                
                ui.button('➕ Agregar al envío', on_click=agregar).classes('w-full mt-2').props('color=primary')
                
                carrito.render()
                
                cli_select = ui.select(
                    {int(r['id_cliente']): r['razon_social'] for _, r in clientes.iterrows()},
                    label='Cliente destinatario'
                ).classes('w-full').props('outlined')
                
                async def registrar():
                    if carrito.esta_vacio():
                        ui.notify('Carrito vacío', type='warning')
                        return
                    if cli_select.value is None:
                        ui.notify('Seleccioná un cliente', type='warning')
                        return
                    try:
                        db.registrar_concesion(cli_select.value, carrito.get_items())
                        carrito.vaciar()
                        ui.notify('✅ Concesión registrada', type='positive')
                        ui.navigate.to('/concesiones')
                    except Exception as e:
                        ui.notify(f'Error: {e}', type='negative')
                
                ui.button('📤 Registrar Entrega', on_click=registrar).classes('w-full').props('color=green size=lg')
            
            # --- Pendientes ---
            ui.separator()
            with ui.card().classes('w-full p-4'):
                ui.label('📋 Concesiones Pendientes').classes('text-lg font-semibold mb-3')
                
                df_pend = db.get_concesiones_pendientes()
                
                if not df_pend.empty:
                    for _, row in df_pend.iterrows():
                        dias = int(row['dias'])
                        color = 'bg-red-50' if dias > 30 else ('bg-amber-50' if dias > 15 else 'bg-green-50')
                        
                        with ui.card().classes(f'w-full p-3 {color} mb-2'):
                            with ui.row().classes('w-full items-center gap-4'):
                                with ui.column().classes('flex-[3] gap-0'):
                                    ui.label(f"{row['producto']} ({row['marca']})").classes('font-medium')
                                    ui.label(f"Cliente: {row['cliente']} | {row['cantidad']} un. | {row['fecha']} ({dias} días)").classes('text-xs text-gray-500')
                                
                                precio_input = ui.number(
                                    'Precio venta',
                                    value=float(prods[prods['id_producto'] == row['id_producto']].iloc[0]['precio_venta']),
                                    min=0
                                ).classes('flex-1').props('outlined dense')
                                
                                id_det = int(row['id_detalle'])
                                id_cns = int(row['id_concesion'])
                                id_cli = int(row['id_cliente'])
                                id_prod = int(row['id_producto'])
                                cant = int(row['cantidad'])
                                
                                async def cobrar(id_d=id_det, id_c=id_cli, id_p=id_prod, c=cant, p=precio_input, cns=id_cns):
                                    try:
                                        db.procesar_concesion_cobrar(id_d, id_c, id_p, c, float(p.value), cns)
                                        ui.notify('✅ Cobro registrado', type='positive')
                                        ui.navigate.to('/concesiones')
                                    except Exception as e:
                                        ui.notify(f'Error: {e}', type='negative')
                                
                                async def devolver(cns=id_cns, id_p=id_prod, c=cant):
                                    try:
                                        db.procesar_concesion_devolver(cns, id_p, c)
                                        ui.notify('✅ Devolución registrada', type='positive')
                                        ui.navigate.to('/concesiones')
                                    except Exception as e:
                                        ui.notify(f'Error: {e}', type='negative')
                                
                                ui.button('💵 Cobrar', on_click=cobrar).props('color=green dense')
                                ui.button('↩️ Devolver', on_click=devolver).props('color=orange dense')
                else:
                    ui.label('No hay concesiones pendientes').classes('text-gray-400 italic')
            
            # --- Estado general ---
            with ui.expansion('📊 Estado General de Concesiones', icon='table_chart').classes('w-full'):
                df_estado = db.get_estado_concesiones()
                if not df_estado.empty:
                    columns = [
                        {'name': c, 'label': c, 'field': c, 'sortable': True, 'align': 'left'}
                        for c in df_estado.columns
                    ]
                    ui.table(columns=columns, rows=df_estado.to_dict('records'),
                             pagination={'rowsPerPage': 10}).classes('w-full')
