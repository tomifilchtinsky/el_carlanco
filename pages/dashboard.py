"""Página Dashboard con KPIs e inventario master."""
from nicegui import ui
from components.layout import create_layout, require_login
import database as db


def setup():
    @ui.page('/')
    @require_login
    def dashboard_page():
        create_layout(current_path='/')
        
        with ui.column().classes('w-full p-6 gap-6'):
            ui.label('📈 Dashboard - El Galpón').classes('text-2xl font-bold')
            
            # --- KPIs ---
            kpis = db.get_kpis()
            
            with ui.row().classes('w-full gap-4'):
                _kpi_card('Ventas (30 días)', f"${kpis['ventas_mes']:,.0f}", 'trending_up', 'blue')
                
                margen_pct = (kpis['margen_bruto'] / kpis['ventas_mes'] * 100) if kpis['ventas_mes'] != 0 else 0
                _kpi_card('Margen Bruto', f"${kpis['margen_bruto']:,.0f}", 'account_balance', 
                          'green' if margen_pct > 0 else 'red', f"{margen_pct:.1f}%")
                
                _kpi_card('Valor en Stock', f"${kpis['valor_stock']:,.0f}", 'inventory_2', 'purple')
                
                _kpi_card('Productos Críticos', str(kpis['productos_criticos']), 'warning', 
                          'red' if kpis['productos_criticos'] > 0 else 'green',
                          'Reponer' if kpis['productos_criticos'] > 0 else 'OK')
            
            ui.separator()
            
            # --- Inventario Master ---
            ui.label('📦 Inventario Completo').classes('text-xl font-semibold')
            
            df_master = db.get_inventario_master()
            
            if not df_master.empty:
                # Filtro por estado
                with ui.row().classes('gap-2 items-center'):
                    ui.label('Filtrar:').classes('text-sm')
                    filter_select = ui.select(
                        ['Todos'] + df_master['Estado'].unique().tolist(),
                        value='Todos'
                    ).classes('w-48')
                
                # Tabla inventario
                columns = [
                    {'name': col, 'label': col, 'field': col, 'sortable': True, 'align': 'left'}
                    for col in ['Producto', 'Marca', 'Stock', 'Concesión', 'Venta 30d', 'Precio', 'Costo Prorr', 'Margen %', 'Valor Stock', 'Estado', 'Días Stock']
                ]
                rows = df_master.to_dict('records')
                
                table = ui.table(
                    columns=columns,
                    rows=rows,
                    row_key='Producto',
                    pagination={'rowsPerPage': 20}
                ).classes('w-full')
                
                def filter_table():
                    if filter_select.value == 'Todos':
                        table.rows = rows
                    else:
                        table.rows = [r for r in rows if r.get('Estado') == filter_select.value]
                    table.update()
                
                filter_select.on_value_change(lambda: filter_table())
            
            ui.separator()
            
            # --- Alertas ---
            ui.label('⚠️ Alertas y Recomendaciones').classes('text-xl font-semibold')
            
            with ui.row().classes('w-full gap-4'):
                sin_stock = df_master[df_master['Estado'] == '🔴 SIN STOCK'] if not df_master.empty else []
                bajo_stock = df_master[df_master['Estado'] == '🟡 BAJO'] if not df_master.empty else []
                sin_rotacion = df_master[df_master['Estado'] == '⚪ SIN ROTACIÓN'] if not df_master.empty else []
                
                with ui.card().classes('flex-1'):
                    ui.label(f'🔴 {len(sin_stock)} sin stock').classes('font-bold text-red-600')
                    if len(sin_stock) > 0:
                        for _, r in sin_stock.iterrows():
                            ui.label(f"  • {r['Producto']}").classes('text-sm')
                
                with ui.card().classes('flex-1'):
                    ui.label(f'🟡 {len(bajo_stock)} stock bajo').classes('font-bold text-amber-600')
                    if len(bajo_stock) > 0:
                        for _, r in bajo_stock.iterrows():
                            ui.label(f"  • {r['Producto']} ({r['Stock']} un.)").classes('text-sm')
                
                with ui.card().classes('flex-1'):
                    ui.label(f'⚪ {len(sin_rotacion)} sin rotación').classes('font-bold text-gray-600')
                    if len(sin_rotacion) > 0:
                        valor = sin_rotacion['Valor Stock'].sum()
                        ui.label(f"💰 Inmovilizado: ${valor:,.2f}").classes('text-sm text-red-500')


def _kpi_card(title, value, icon, color, subtitle=None):
    """Renderiza una card de KPI."""
    with ui.card().classes('flex-1 p-4'):
        with ui.row().classes('items-center gap-3'):
            ui.icon(icon).classes(f'text-2xl text-{color}-500')
            with ui.column().classes('gap-0'):
                ui.label(title).classes('text-xs text-gray-500 uppercase')
                ui.label(value).classes('text-2xl font-bold')
                if subtitle:
                    ui.label(subtitle).classes(f'text-sm text-{color}-600')
