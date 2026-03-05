"""Página de Auditoría de movimientos e integridad de stock."""
from nicegui import ui
from components.layout import create_layout, require_login
import database as db


def setup():
    @ui.page('/auditoria')
    @require_login
    def auditoria_page():
        create_layout(current_path='/auditoria')
        
        with ui.column().classes('w-full p-6 gap-4'):
            ui.label('🔍 Auditoría de Movimientos').classes('text-2xl font-bold')
            
            # Selector de período
            periodos = {7: '7 días', 15: '15 días', 30: '30 días', 60: '60 días', 90: '90 días'}
            periodo_select = ui.select(periodos, value=30, label='Período').classes('w-48').props('outlined')
            
            content = ui.column().classes('w-full gap-4')
            
            def render():
                dias = periodo_select.value or 30
                content.clear()
                with content:
                    # --- Log de Movimientos ---
                    with ui.card().classes('w-full p-4'):
                        ui.label('📋 Log de Movimientos').classes('text-lg font-semibold mb-2')
                        
                        df_mov = db.get_movimientos_auditoria(dias)
                        if not df_mov.empty:
                            columns = [
                                {'name': c, 'label': c, 'field': c, 'sortable': True, 'align': 'left'}
                                for c in df_mov.columns
                            ]
                            ui.table(columns=columns, rows=df_mov.to_dict('records'),
                                     pagination={'rowsPerPage': 15}).classes('w-full')
                        else:
                            ui.label('No hay movimientos en el período').classes('text-gray-400')
                    
                    # --- Integridad de Stock ---
                    with ui.card().classes('w-full p-4'):
                        ui.label('🔒 Auditoría de Integridad de Stock').classes('text-lg font-semibold mb-2')
                        ui.label('Verifica que stock físico + concesión coincida con el historial de movimientos.').classes('text-sm text-gray-500 mb-3')
                        
                        df_audit = db.get_auditoria_integridad()
                        
                        if not df_audit.empty:
                            problemas = df_audit[df_audit['Diferencia'] != 0]
                            
                            if len(problemas) > 0:
                                ui.label(f'⚠️ {len(problemas)} productos con diferencias').classes('text-red-600 font-bold text-lg')
                                
                                columns = [
                                    {'name': c, 'label': c, 'field': c, 'sortable': True, 'align': 'left'}
                                    for c in ['nombre', 'Físico', 'Concesión', 'Total Real', 'Calculado', 'Diferencia']
                                ]
                                rows = problemas[['nombre', 'Físico', 'Concesión', 'Total Real', 'Calculado', 'Diferencia']].to_dict('records')
                                ui.table(columns=columns, rows=rows).classes('w-full')
                                
                                with ui.card().classes('w-full p-3 bg-amber-50 mt-2'):
                                    ui.label('Guía de solución:').classes('font-semibold')
                                    ui.label('• Diferencia < 0: Falta mercadería (posible venta no cargada)').classes('text-sm')
                                    ui.label('• Diferencia > 0: Sobra mercadería (posible compra no cargada)').classes('text-sm')
                            else:
                                ui.label('✅ ¡PERFECTO! La contabilidad cierra exacta (0 errores).').classes('text-green-600 font-bold text-lg')
                                ui.label('El stock en depósito + concesión coincide con el historial de movimientos.').classes('text-sm text-gray-500')
            
            render()
            periodo_select.on_value_change(lambda: render())
