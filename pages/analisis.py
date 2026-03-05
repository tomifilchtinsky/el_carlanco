"""Página de Análisis con gráficos Plotly."""
from nicegui import ui
import plotly.express as px
import plotly.graph_objects as go
from components.layout import create_layout, require_login
import database as db


def setup():
    @ui.page('/analisis')
    @require_login
    def analisis_page():
        create_layout(current_path='/analisis')
        
        with ui.column().classes('w-full p-6 gap-4'):
            ui.label('📈 Análisis del Negocio').classes('text-2xl font-bold')
            
            # Selector de período
            periodos = {'7 días': 7, '15 días': 15, '30 días': 30, '60 días': 60, '90 días': 90}
            periodo_select = ui.select(periodos, value=30, label='Período de análisis').classes('w-48').props('outlined')
            
            # Containers para contenido dinámico
            content_container = ui.column().classes('w-full gap-6')
            
            def render_analisis():
                dias = periodo_select.value or 30
                content_container.clear()
                
                with content_container:
                    # --- Rentabilidad por Producto ---
                    with ui.card().classes('w-full p-4'):
                        ui.label('💰 Rentabilidad por Producto').classes('text-lg font-semibold')
                        
                        df_rent = db.get_rentabilidad(dias)
                        if not df_rent.empty:
                            columns = [
                                {'name': c, 'label': c, 'field': c, 'sortable': True, 'align': 'left'}
                                for c in df_rent.columns
                            ]
                            ui.table(columns=columns, rows=df_rent.to_dict('records'),
                                     row_key='Producto', pagination={'rowsPerPage': 20}).classes('w-full')
                            
                            # Gráfico
                            fig = px.bar(
                                df_rent, x='Producto', y='Ganancia',
                                color='Margen %', color_continuous_scale='RdYlGn',
                                title='Ganancia por Producto'
                            )
                            fig.update_layout(height=400)
                            ui.plotly(fig).classes('w-full')
                        else:
                            ui.label('No hay datos de ventas en el período').classes('text-gray-400')
                    
                    # --- Evolución de Ventas ---
                    with ui.card().classes('w-full p-4'):
                        ui.label('📊 Evolución de Ventas').classes('text-lg font-semibold')
                        
                        df_evo = db.get_evolucion_ventas(dias)
                        if not df_evo.empty:
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(
                                x=df_evo['fecha'], y=df_evo['ventas_dia'],
                                mode='lines+markers', name='Ventas ($)',
                                line=dict(color='#2563eb', width=3),
                                fill='tozeroy', fillcolor='rgba(37, 99, 235, 0.1)'
                            ))
                            fig.update_layout(
                                title='Ventas diarias',
                                xaxis_title='Fecha', yaxis_title='Ventas ($)',
                                height=400
                            )
                            ui.plotly(fig).classes('w-full')
                        else:
                            ui.label('No hay datos de ventas en el período').classes('text-gray-400')
                    
                    # --- Rendimiento por Marca ---
                    with ui.card().classes('w-full p-4'):
                        ui.label('🏷️ Rendimiento por Marca').classes('text-lg font-semibold')
                        
                        df_marcas = db.get_rendimiento_marcas(dias)
                        if not df_marcas.empty:
                            columns = [
                                {'name': c, 'label': c, 'field': c, 'sortable': True, 'align': 'left'}
                                for c in df_marcas.columns
                            ]
                            ui.table(columns=columns, rows=df_marcas.to_dict('records'),
                                     row_key='Marca').classes('w-full')
                            
                            fig = px.pie(
                                df_marcas, values='Ingresos', names='Marca',
                                title='Distribución de Ingresos por Marca'
                            )
                            fig.update_layout(height=400)
                            ui.plotly(fig).classes('w-full')
                        else:
                            ui.label('No hay datos en el período').classes('text-gray-400')
            
            # Render inicial
            render_analisis()
            
            # Actualizar al cambiar período
            periodo_select.on_value_change(lambda: render_analisis())
