"""
Capa de acceso a datos centralizada.
Todas las queries SQL y operaciones de BD van acá.
"""
import pandas as pd
from sqlalchemy import text
from config import get_engine


# ============================================================
# CONSULTAS GENERALES
# ============================================================

def get_productos():
    """Productos con marca, stock y precios."""
    with get_engine().connect() as conn:
        return pd.read_sql(text("""
            SELECT p.id_producto, p.nombre, m.nombre as marca, 
                   p.stock_actual, p.stock_minimo, p.stock_concesion,
                   p.precio_venta, p.precio_venta_caja,
                   p.precio_costo_promedio, p.unidades_por_caja
            FROM productos p
            JOIN marcas m ON p.id_marca = m.id_marca
            ORDER BY p.nombre
        """), conn)

def get_clientes():
    with get_engine().connect() as conn:
        return pd.read_sql(text(
            "SELECT id_cliente, razon_social, telefono, direccion FROM clientes ORDER BY razon_social"
        ), conn)

def get_proveedores():
    with get_engine().connect() as conn:
        return pd.read_sql(text(
            "SELECT id_proveedor, nombre, telefono FROM proveedores ORDER BY nombre"
        ), conn)

def get_marcas():
    with get_engine().connect() as conn:
        return pd.read_sql(text(
            "SELECT id_marca, nombre FROM marcas ORDER BY nombre"
        ), conn)

def get_costo_promedio(id_producto: int) -> float:
    with get_engine().connect() as conn:
        result = conn.execute(
            text("SELECT precio_costo_promedio FROM productos WHERE id_producto = :id"),
            {"id": id_producto}
        ).fetchone()
        return float(result[0]) if result else 0.0


# ============================================================
# KPIs
# ============================================================

def get_kpis():
    """KPIs principales del dashboard."""
    with get_engine().connect() as conn:
        result = conn.execute(text("""
            WITH VentasCalculadas AS (
                SELECT 
                    (dv.cantidad_formato * CASE WHEN dv.formato_venta = 'Caja' THEN p.unidades_por_caja ELSE 1 END) as unidades_reales,
                    dv.precio_unitario_historico,
                    p.precio_costo_promedio
                FROM detalle_ventas dv
                JOIN ventas v ON dv.id_venta = v.id_venta
                JOIN productos p ON dv.id_producto = p.id_producto
                WHERE v.fecha >= CURRENT_DATE - INTERVAL '30 days'
            ),
            VentasTotales AS (
                SELECT 
                    SUM(unidades_reales * precio_unitario_historico) as total_ventas,
                    SUM(unidades_reales * precio_costo_promedio) as costo_total
                FROM VentasCalculadas
            ),
            StockValorizado AS (
                SELECT SUM(stock_actual * precio_costo_promedio) as valor_inventario
                FROM productos
            )
            SELECT 
                COALESCE(vt.total_ventas, 0),
                COALESCE(vt.total_ventas - vt.costo_total, 0),
                COALESCE(sv.valor_inventario, 0),
                (SELECT COUNT(*) FROM productos WHERE stock_actual <= stock_minimo)
            FROM VentasTotales vt, StockValorizado sv
        """)).fetchone()
        return {
            'ventas_mes': float(result[0]),
            'margen_bruto': float(result[1]),
            'valor_stock': float(result[2]),
            'productos_criticos': int(result[3])
        }

def get_kpis_concesion():
    """KPIs de mercadería en concesión."""
    with get_engine().connect() as conn:
        result = conn.execute(text("""
            SELECT 
                COALESCE(SUM(stock_concesion), 0),
                COALESCE(SUM(stock_concesion * precio_costo_promedio), 0),
                COALESCE(SUM(stock_concesion * precio_venta), 0)
            FROM productos
        """)).fetchone()
        return {
            'unidades_calle': int(result[0]),
            'capital_riesgo': float(result[1]),
            'venta_potencial': float(result[2])
        }


# ============================================================
# DASHBOARD - Inventario Master
# ============================================================

def get_inventario_master():
    """Tabla maestra de inventario con stock, ventas, márgenes."""
    with get_engine().connect() as conn:
        return pd.read_sql(text("""
            WITH VentasTotales AS (
                SELECT id_producto, 
                       SUM(cantidad_formato) as total_vendido,
                       MAX(v.fecha) as ultima_venta
                FROM detalle_ventas dv
                JOIN ventas v ON dv.id_venta = v.id_venta
                GROUP BY id_producto
            ),
            VentasRecientes AS (
                SELECT id_producto, SUM(cantidad_formato) as vendido_30d
                FROM detalle_ventas dv
                JOIN ventas v ON dv.id_venta = v.id_venta
                WHERE v.fecha >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY id_producto
            )
            SELECT 
                p.nombre AS "Producto",
                m.nombre AS "Marca",
                p.stock_actual AS "Stock",
                p.stock_concesion AS "Concesión",
                COALESCE(vr.vendido_30d, 0) AS "Venta 30d",
                p.precio_venta AS "Precio",
                p.precio_costo_promedio AS "Costo Prorr",
                ROUND(((p.precio_venta - p.precio_costo_promedio) / NULLIF(p.precio_venta, 0) * 100)::numeric, 1) AS "Margen %",
                ROUND((p.stock_actual * p.precio_costo_promedio)::numeric, 2) AS "Valor Stock",
                CASE 
                    WHEN p.stock_actual = 0 THEN '🔴 SIN STOCK'
                    WHEN p.stock_actual <= p.stock_minimo THEN '🟡 BAJO'
                    WHEN COALESCE(vr.vendido_30d, 0) = 0 AND COALESCE(vt.total_vendido, 0) = 0 THEN '⚪ SIN ROTACIÓN'
                    ELSE '🟢 OK'
                END AS "Estado",
                CASE 
                    WHEN COALESCE(vr.vendido_30d, 0) > 0 THEN ROUND((p.stock_actual::numeric / vr.vendido_30d * 30), 0)
                    ELSE 999
                END AS "Días Stock"
            FROM productos p
            JOIN marcas m ON p.id_marca = m.id_marca
            LEFT JOIN VentasTotales vt ON p.id_producto = vt.id_producto
            LEFT JOIN VentasRecientes vr ON p.id_producto = vr.id_producto
            ORDER BY p.nombre
        """), conn)


# ============================================================
# VENTAS
# ============================================================

def registrar_venta(id_cliente, total_venta, nro_factura, metodo_pago, items, descripcion=""):
    """Registra una venta completa con todos sus detalles."""
    with get_engine().begin() as conn:
        res = conn.execute(text("""
            INSERT INTO ventas (id_cliente, total_venta, nro_factura, metodo_pago)
            VALUES (:idc, :tot, :fac, :mp) RETURNING id_venta
        """), {"idc": id_cliente, "tot": total_venta, "fac": nro_factura, "mp": metodo_pago})
        id_venta = res.fetchone()[0]
        
        for item in items:
            conn.execute(text("""
                INSERT INTO detalle_ventas (id_venta, id_producto, formato_venta, 
                    cantidad_formato, precio_unitario_historico, descripcion)
                VALUES (:id_v, :id_p, :formato, :cant, :precio, :desc)
            """), {
                "id_v": id_venta,
                "id_p": item['id_producto'],
                "formato": item['Formato'],
                "cant": item['Cantidad'],
                "precio": float(item['PrecioUnidad']),
                "desc": descripcion
            })
        return id_venta

def cancelar_venta(id_venta):
    """Cancela una venta. Los triggers DELETE revierten el stock."""
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM detalle_ventas WHERE id_venta = :id"), {"id": id_venta})
        conn.execute(text("DELETE FROM ventas WHERE id_venta = :id"), {"id": id_venta})

def get_historial_ventas():
    """Historial de ventas con detalles."""
    with get_engine().connect() as conn:
        return pd.read_sql(text("""
            SELECT 
                v.id_venta AS "N°",
                TO_CHAR(v.fecha, 'DD/MM/YY HH24:MI') AS "Fecha",
                c.razon_social AS "Cliente",
                p.nombre AS "Producto",
                m.nombre AS "Marca",
                dv.cantidad_formato || ' ' || dv.formato_venta AS "Cant.",
                dv.precio_unitario_historico AS "Precio Unit.",
                ROUND(dv.cantidad_formato * 
                    CASE 
                        WHEN dv.formato_venta = 'Caja' 
                        THEN (dv.precio_unitario_historico * p.unidades_por_caja)
                        ELSE dv.precio_unitario_historico END, 2
                ) AS "Subtotal"
            FROM ventas v
            JOIN clientes c ON v.id_cliente = c.id_cliente
            JOIN detalle_ventas dv ON v.id_venta = dv.id_venta
            JOIN productos p ON dv.id_producto = p.id_producto
            JOIN marcas m ON p.id_marca = m.id_marca
            ORDER BY v.fecha DESC
            LIMIT 100
        """), conn)


# ============================================================
# COMPRAS
# ============================================================

def registrar_compra(id_proveedor, total_compra, costo_flete, nro_factura, items):
    """Registra una compra completa. Los triggers INSERT actualizan stock y costo promedio."""
    with get_engine().begin() as conn:
        res = conn.execute(text("""
            INSERT INTO compras (id_proveedor, total_compra, costo_flete, nro_factura)
            VALUES (:id_p, :total, :flete, :fac) RETURNING id_compra
        """), {"id_p": id_proveedor, "total": total_compra, "flete": costo_flete, "fac": nro_factura})
        id_compra = res.fetchone()[0]
        
        for item in items:
            conn.execute(text("""
                INSERT INTO detalle_compras (id_compra, id_producto, cantidad_unidades, precio_compra_neto)
                VALUES (:id_c, :id_p, :cant, :precio)
            """), {
                "id_c": id_compra,
                "id_p": item['id_producto'],
                "cant": item['Cantidad'],
                "precio": float(item['Costo Neto'])
            })
        return id_compra

def cancelar_compra(id_compra):
    """Cancela una compra. Los triggers DELETE revierten el stock."""
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM detalle_compras WHERE id_compra = :id"), {"id": id_compra})
        conn.execute(text("DELETE FROM compras WHERE id_compra = :id"), {"id": id_compra})

def get_historial_compras():
    """Historial de compras."""
    with get_engine().connect() as conn:
        return pd.read_sql(text("""
            SELECT 
                c.id_compra AS "N°",
                TO_CHAR(c.fecha, 'DD/MM/YY HH24:MI') AS "Fecha",
                pr.nombre AS "Proveedor",
                p.nombre AS "Producto",
                dc.cantidad_unidades AS "Cant.",
                dc.precio_compra_neto AS "Costo Unit.",
                ROUND((dc.cantidad_unidades * dc.precio_compra_neto)::numeric, 2) AS "Subtotal",
                c.costo_flete AS "Flete",
                c.nro_factura AS "Factura"
            FROM compras c
            JOIN proveedores pr ON c.id_proveedor = pr.id_proveedor
            JOIN detalle_compras dc ON c.id_compra = dc.id_compra
            JOIN productos p ON dc.id_producto = p.id_producto
            ORDER BY c.fecha DESC
            LIMIT 100
        """), conn)

def actualizar_precio_venta(id_producto, nuevo_precio, nuevo_precio_caja):
    """Actualiza precio de venta y registra historial."""
    with get_engine().begin() as conn:
        conn.execute(text("""
            INSERT INTO historial_precios (id_producto, precio_anterior, precio_nuevo, fecha)
            SELECT id_producto, precio_venta, :nuevo, NOW()
            FROM productos WHERE id_producto = :id
        """), {"id": id_producto, "nuevo": nuevo_precio})
        
        conn.execute(text("""
            UPDATE productos 
            SET precio_venta = :pv, precio_venta_caja = :pvc
            WHERE id_producto = :id
        """), {"id": id_producto, "pv": nuevo_precio, "pvc": nuevo_precio_caja})


# ============================================================
# CONCESIONES
# ============================================================

def registrar_concesion(id_cliente, items):
    """Registra una entrega de concesión. Los triggers mueven stock_actual → stock_concesion."""
    with get_engine().begin() as conn:
        res = conn.execute(text("""
            INSERT INTO concesiones (id_cliente) VALUES (:idc) RETURNING id_concesion
        """), {"idc": id_cliente})
        id_concesion = res.fetchone()[0]
        
        for item in items:
            conn.execute(text("""
                INSERT INTO detalle_concesiones (id_concesion, id_producto, cantidad)
                VALUES (:id_c, :id_p, :cant)
            """), {
                "id_c": id_concesion,
                "id_p": item['id'],
                "cant": item['cantidad']
            })
        return id_concesion

def get_concesiones_pendientes():
    """Detalle de concesiones pendientes para gestión."""
    with get_engine().connect() as conn:
        return pd.read_sql(text("""
            SELECT 
                dc.id_detalle, dc.id_concesion, dc.id_producto,
                p.nombre AS producto, m.nombre AS marca,
                dc.cantidad, dc.estado, dc.precio_venta,
                c.id_cliente, cl.razon_social AS cliente,
                TO_CHAR(c.fecha, 'DD/MM/YY') AS fecha,
                EXTRACT(DAY FROM NOW() - c.fecha)::int AS dias
            FROM detalle_concesiones dc
            JOIN concesiones c ON dc.id_concesion = c.id_concesion
            JOIN productos p ON dc.id_producto = p.id_producto
            JOIN marcas m ON p.id_marca = m.id_marca
            JOIN clientes cl ON c.id_cliente = cl.id_cliente
            WHERE dc.estado = 'PENDIENTE'
            ORDER BY c.fecha DESC
        """), conn)

def procesar_concesion_cobrar(id_detalle, id_cliente, id_producto, cantidad, precio):
    """Cobra una concesión: crea venta con es_concesion=TRUE."""
    with get_engine().begin() as conn:
        total = float(cantidad * precio)
        res = conn.execute(text("""
            INSERT INTO ventas (id_cliente, total_venta, nro_factura)
            VALUES (:idc, :tot, 'CONCESION') RETURNING id_venta
        """), {"idc": id_cliente, "tot": total})
        id_venta = res.fetchone()[0]
        
        conn.execute(text("""
            INSERT INTO detalle_ventas (id_venta, id_producto, formato_venta, 
                cantidad_formato, precio_unitario_historico, es_concesion)
            VALUES (:idv, :idp, 'Unidad', :cant, :precio, TRUE)
        """), {"idv": id_venta, "idp": id_producto, "cant": cantidad, "precio": precio})
        
        conn.execute(text("""
            UPDATE detalle_concesiones 
            SET estado = 'VENDIDO', precio_venta = :precio 
            WHERE id_detalle = :id
        """), {"id": id_detalle, "precio": precio})

def procesar_concesion_devolver(id_detalle, id_producto, cantidad):
    """Devuelve una concesión: mueve stock_concesion → stock_actual."""
    with get_engine().begin() as conn:
        conn.execute(text("""
            UPDATE productos 
            SET stock_actual = stock_actual + :cant,
                stock_concesion = stock_concesion - :cant
            WHERE id_producto = :id
        """), {"id": id_producto, "cant": cantidad})
        
        conn.execute(text("""
            UPDATE detalle_concesiones SET estado = 'DEVUELTO' WHERE id_detalle = :id
        """), {"id": id_detalle})
        
        conn.execute(text("""
            INSERT INTO inventario_movimientos (id_producto, tipo, cantidad, fecha)
            VALUES (:id, 'DEVOLUCION_CONCESION', :cant, NOW())
        """), {"id": id_producto, "cant": cantidad})

def get_estado_concesiones():
    """Estado completo de mercadería en concesión por cliente."""
    with get_engine().connect() as conn:
        return pd.read_sql(text("""
            SELECT 
                cl.razon_social AS "Cliente",
                p.nombre AS "Producto",
                dc.cantidad AS "Cantidad",
                dc.estado AS "Estado",
                TO_CHAR(c.fecha, 'DD/MM/YY') AS "Fecha Entrega",
                EXTRACT(DAY FROM NOW() - c.fecha)::int AS "Días"
            FROM detalle_concesiones dc
            JOIN concesiones c ON dc.id_concesion = c.id_concesion
            JOIN productos p ON dc.id_producto = p.id_producto
            JOIN clientes cl ON c.id_cliente = cl.id_cliente
            ORDER BY c.fecha DESC
        """), conn)


# ============================================================
# ANÁLISIS
# ============================================================

def get_rentabilidad(dias):
    with get_engine().connect() as conn:
        return pd.read_sql(text(f"""
            WITH VentasPeriodo AS (
                SELECT 
                    dv.id_producto,
                    SUM(dv.cantidad_formato * CASE WHEN dv.formato_venta = 'Caja' THEN p.unidades_por_caja ELSE 1 END) as unidades_vendidas,
                    SUM(dv.cantidad_formato * CASE WHEN dv.formato_venta = 'Caja' THEN p.unidades_por_caja ELSE 1 END * dv.precio_unitario_historico) as ingresos,
                    SUM(dv.cantidad_formato * CASE WHEN dv.formato_venta = 'Caja' THEN p.unidades_por_caja ELSE 1 END * p.precio_costo_promedio) as costos
                FROM detalle_ventas dv
                JOIN ventas v ON dv.id_venta = v.id_venta
                JOIN productos p ON dv.id_producto = p.id_producto
                WHERE v.fecha >= CURRENT_DATE - INTERVAL '{dias} days'
                GROUP BY dv.id_producto
            )
            SELECT 
                p.nombre AS "Producto", m.nombre AS "Marca",
                vp.unidades_vendidas AS "Unidades",
                vp.ingresos AS "Ingresos", vp.costos AS "Costos",
                (vp.ingresos - vp.costos) AS "Ganancia",
                ROUND(((vp.ingresos - vp.costos) / NULLIF(vp.ingresos, 0) * 100), 1) AS "Margen %",
                ROUND((vp.ingresos - vp.costos) / NULLIF(vp.unidades_vendidas, 0), 2) AS "Ganancia/Unidad"
            FROM VentasPeriodo vp
            JOIN productos p ON vp.id_producto = p.id_producto
            JOIN marcas m ON p.id_marca = m.id_marca
            WHERE vp.unidades_vendidas > 0
            ORDER BY "Ganancia" DESC
        """), conn)

def get_evolucion_ventas(dias):
    with get_engine().connect() as conn:
        return pd.read_sql(text(f"""
            SELECT 
                DATE_TRUNC('day', v.fecha) AS fecha,
                SUM(v.total_venta) as ventas_dia,
                COUNT(DISTINCT v.id_venta) as num_ventas
            FROM ventas v
            WHERE v.fecha >= CURRENT_DATE - INTERVAL '{dias} days'
            GROUP BY DATE_TRUNC('day', v.fecha)
            ORDER BY fecha
        """), conn)

def get_rendimiento_marcas(dias):
    with get_engine().connect() as conn:
        return pd.read_sql(text(f"""
            SELECT 
                m.nombre AS "Marca",
                COUNT(DISTINCT p.id_producto) AS "Productos",
                SUM(dv.cantidad_formato * CASE WHEN dv.formato_venta = 'Caja' THEN p.unidades_por_caja ELSE 1 END) AS "Unidades Vendidas",
                SUM(dv.cantidad_formato * CASE WHEN dv.formato_venta = 'Caja' THEN p.unidades_por_caja ELSE 1 END * dv.precio_unitario_historico) AS "Ingresos"
            FROM detalle_ventas dv
            JOIN ventas v ON dv.id_venta = v.id_venta
            JOIN productos p ON dv.id_producto = p.id_producto
            JOIN marcas m ON p.id_marca = m.id_marca
            WHERE v.fecha >= CURRENT_DATE - INTERVAL '{dias} days'
            GROUP BY m.nombre
            ORDER BY "Ingresos" DESC
        """), conn)


# ============================================================
# AUDITORÍA
# ============================================================

def get_movimientos_auditoria(dias):
    with get_engine().connect() as conn:
        return pd.read_sql(text(f"""
            SELECT 
                im.id_movimiento AS "N° Mov",
                TO_CHAR(im.fecha, 'DD/MM/YY HH24:MI') AS "Fecha/Hora",
                p.nombre AS "Producto", m.nombre AS "Marca",
                im.tipo AS "Tipo", im.cantidad AS "Cantidad",
                p.stock_actual AS "Stock Depósito"
            FROM inventario_movimientos im
            JOIN productos p ON im.id_producto = p.id_producto
            JOIN marcas m ON p.id_marca = m.id_marca
            WHERE im.fecha >= CURRENT_DATE - INTERVAL '{dias} days'
            ORDER BY im.fecha DESC
            LIMIT 500
        """), conn)

def get_auditoria_integridad():
    with get_engine().connect() as conn:
        return pd.read_sql(text("""
            SELECT 
                p.nombre,
                p.stock_actual AS "Físico",
                p.stock_concesion AS "Concesión",
                (p.stock_actual + p.stock_concesion) AS "Total Real",
                COALESCE(SUM(im.cantidad), 0) AS "Calculado",
                (p.stock_actual + p.stock_concesion) - COALESCE(SUM(im.cantidad), 0) AS "Diferencia"
            FROM productos p
            LEFT JOIN inventario_movimientos im ON p.id_producto = im.id_producto
            GROUP BY p.id_producto, p.nombre, p.stock_actual, p.stock_concesion
            ORDER BY ABS((p.stock_actual + p.stock_concesion) - COALESCE(SUM(im.cantidad), 0)) DESC
        """), conn)


# ============================================================
# CARGA DE DATOS (MAESTROS)
# ============================================================

def crear_marca(nombre):
    with get_engine().begin() as conn:
        conn.execute(text("INSERT INTO marcas (nombre) VALUES (:n)"), {"n": nombre})

def crear_proveedor(nombre, telefono, email=""):
    with get_engine().begin() as conn:
        conn.execute(text(
            "INSERT INTO proveedores (nombre, telefono, email) VALUES (:n, :t, :e)"
        ), {"n": nombre, "t": telefono, "e": email})

def crear_cliente(razon_social, direccion, telefono):
    with get_engine().begin() as conn:
        conn.execute(text(
            "INSERT INTO clientes (razon_social, direccion, telefono) VALUES (:r, :d, :t)"
        ), {"r": razon_social, "d": direccion, "t": telefono})

def crear_producto(nombre, id_marca, precio_venta, costo_ref, stock_inicial, unidades_caja):
    precio_caja = precio_venta * unidades_caja
    with get_engine().begin() as conn:
        conn.execute(text("""
            INSERT INTO productos 
            (nombre, id_marca, precio_venta, precio_costo_promedio, stock_actual, unidades_por_caja, precio_venta_caja)
            VALUES (:nom, :m, :pv, :pc, :stk, :upc, :pvc)
        """), {
            "nom": nombre, "m": id_marca, "pv": precio_venta,
            "pc": costo_ref, "stk": stock_inicial, "upc": unidades_caja,
            "pvc": precio_caja
        })
        
        if stock_inicial > 0:
            id_new = conn.execute(text("SELECT MAX(id_producto) FROM productos")).fetchone()[0]
            conn.execute(text("""
                INSERT INTO inventario_movimientos (id_producto, tipo, cantidad, fecha)
                VALUES (:id, 'STOCK_INICIAL', :cant, NOW())
            """), {"id": id_new, "cant": stock_inicial})
