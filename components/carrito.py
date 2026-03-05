"""
Componente de carrito reutilizable para ventas, compras y concesiones.
Usa ui.table con botones ❌ por fila, actualización sin recarga.
"""
from nicegui import ui


class Carrito:
    """Carrito reactivo para cualquier tipo de operación."""
    
    def __init__(self, columns: list[dict], on_change=None):
        """
        columns: Lista de dicts con 'name', 'label', 'field' y opcionalmente 'format'.
        on_change: Callback que se ejecuta cuando el carrito cambia.
        """
        self.items = []
        self.columns = columns
        self.on_change = on_change
        self.table = None
        self.container = None
    
    def render(self):
        """Renderiza el carrito en la UI actual."""
        self.container = ui.column().classes('w-full')
        self._update_view()
        return self.container
    
    def agregar(self, item: dict):
        """Agrega un item al carrito y actualiza la vista."""
        self.items.append(item)
        self._update_view()
        if self.on_change:
            self.on_change(self.items)
    
    def eliminar(self, index: int):
        """Elimina un item por índice."""
        if 0 <= index < len(self.items):
            self.items.pop(index)
            self._update_view()
            if self.on_change:
                self.on_change(self.items)
    
    def vaciar(self):
        """Vacía el carrito completo."""
        self.items.clear()
        self._update_view()
        if self.on_change:
            self.on_change(self.items)
    
    def get_items(self):
        return self.items
    
    def esta_vacio(self):
        return len(self.items) == 0
    
    def _update_view(self):
        """Recrea la vista del carrito."""
        if self.container is None:
            return
        self.container.clear()
        
        with self.container:
            if not self.items:
                ui.label('El carrito está vacío').classes('text-gray-400 italic py-4 text-center')
                return
            
            # Tabla con items
            for i, item in enumerate(self.items):
                with ui.row().classes('w-full items-center gap-2 py-1 px-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800'):
                    for col in self.columns:
                        value = item.get(col['field'], '')
                        fmt = col.get('format', None)
                        if fmt and value != '':
                            display = fmt(value)
                        else:
                            display = str(value)
                        
                        classes = col.get('classes', 'flex-1')
                        ui.label(display).classes(classes)
                    
                    # Botón eliminar
                    idx = i  # Captura correcta del índice
                    ui.button(icon='close', on_click=lambda _, i=idx: self.eliminar(i)).props(
                        'flat dense round color=red size=sm'
                    )
            
            # Separador + botón vaciar
            ui.separator()
            with ui.row().classes('w-full justify-between items-center'):
                ui.label(f'{len(self.items)} items').classes('text-sm text-gray-500')
                ui.button('🗑️ Vaciar todo', on_click=self.vaciar).props('flat color=red size=sm')
