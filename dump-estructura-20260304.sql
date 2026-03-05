-- ============================================
-- DUMP ESTRUCTURA BD - El Galpon
-- Generado: 2026-03-04 01:23
-- Incluye: Tablas, Funciones, Triggers, FKs, Vista
-- ============================================

-- ============================================
-- FUNCIONES DE TRIGGER
-- ============================================

CREATE OR REPLACE FUNCTION public.procesar_compra() RETURNS trigger
    LANGUAGE plpgsql AS $$

DECLARE
    costo_actual NUMERIC;
    stock_ant INTEGER;
    nuevo_promedio NUMERIC;
BEGIN
    SELECT precio_costo_promedio, stock_actual INTO costo_actual, stock_ant FROM productos WHERE id_producto = NEW.id_producto;
    
    -- Evitar división por cero si es el primer ingreso
    IF (stock_ant + NEW.cantidad_unidades) > 0 THEN
        nuevo_promedio := ((stock_ant * costo_actual) + (NEW.cantidad_unidades * NEW.precio_compra_neto)) / (stock_ant + NEW.cantidad_unidades);
    ELSE
        nuevo_promedio := NEW.precio_compra_neto;
    END IF;

    UPDATE productos 
    SET stock_actual = stock_actual + NEW.cantidad_unidades,
        precio_costo_promedio = nuevo_promedio
    WHERE id_producto = NEW.id_producto;

    INSERT INTO inventario_movimientos (id_producto, tipo, cantidad, fecha)
    VALUES (NEW.id_producto, 'COMPRA', NEW.cantidad_unidades, NOW());

    RETURN NEW;
END;

$$;


CREATE OR REPLACE FUNCTION public.procesar_concesion() RETURNS trigger
    LANGUAGE plpgsql AS $$

BEGIN
    -- Resta del stock del galpon, suma al stock prestado
    UPDATE productos 
    SET stock_actual = stock_actual - NEW.cantidad,
        stock_concesion = stock_concesion + NEW.cantidad
    WHERE id_producto = NEW.id_producto;

    INSERT INTO inventario_movimientos (id_producto, tipo, cantidad, fecha)
    VALUES (NEW.id_producto, 'ENTREGA_CONCESION', NEW.cantidad, NOW());

    RETURN NEW;
END;

$$;


CREATE OR REPLACE FUNCTION public.procesar_venta() RETURNS trigger
    LANGUAGE plpgsql AS $$

DECLARE
    unidades_reales INTEGER;
    unidades_caja INTEGER;
BEGIN
    -- Obtenemos cuantas unidades tiene la caja de ese producto
    SELECT unidades_por_caja INTO unidades_caja 
    FROM productos WHERE id_producto = NEW.id_producto;

    -- Calculamos unidades reales
    IF NEW.formato_venta = 'Caja' THEN
        unidades_reales := NEW.cantidad_formato * unidades_caja;
    ELSE
        unidades_reales := NEW.cantidad_formato;
    END IF;

    -- ? LÓGICA CORREGIDA
    IF NEW.es_concesion = FALSE THEN
        -- Venta normal: descontar de stock físico
        UPDATE productos 
        SET stock_actual = stock_actual - unidades_reales 
        WHERE id_producto = NEW.id_producto;

        INSERT INTO inventario_movimientos (id_producto, tipo, cantidad, fecha)
        VALUES (NEW.id_producto, 'VENTA', -unidades_reales, NOW());
    ELSE
        -- Venta de concesión: descontar de stock_concesion
        UPDATE productos 
        SET stock_concesion = stock_concesion - unidades_reales 
        WHERE id_producto = NEW.id_producto;

        INSERT INTO inventario_movimientos (id_producto, tipo, cantidad, fecha)
        VALUES (NEW.id_producto, 'VENTA_CONCESION', -unidades_reales, NOW());
    END IF;

    RETURN NEW;
END;

$$;


CREATE OR REPLACE FUNCTION public.revertir_compra() RETURNS trigger
    LANGUAGE plpgsql AS $$

        DECLARE
            stock_ant INTEGER;
            costo_actual NUMERIC;
            nuevo_promedio NUMERIC;
        BEGIN
            -- Obtenemos el estado actual del producto
            SELECT stock_actual, precio_costo_promedio 
            INTO stock_ant, costo_actual 
            FROM productos WHERE id_producto = OLD.id_producto;

            -- Revertimos el stock
            UPDATE productos 
            SET stock_actual = stock_actual - OLD.cantidad_unidades,
                -- Recalculamos el costo promedio sin esta compra
                precio_costo_promedio = CASE 
                    WHEN (stock_ant - OLD.cantidad_unidades) > 0 THEN
                        ((stock_ant * costo_actual) - (OLD.cantidad_unidades * OLD.precio_compra_neto)) 
                        / (stock_ant - OLD.cantidad_unidades)
                    ELSE 0
                END
            WHERE id_producto = OLD.id_producto;

            INSERT INTO inventario_movimientos (id_producto, tipo, cantidad, fecha)
            VALUES (OLD.id_producto, 'CANCELACION_COMPRA', -OLD.cantidad_unidades, NOW());

            RETURN OLD;
        END;
        
$$;


CREATE OR REPLACE FUNCTION public.revertir_concesion() RETURNS trigger
    LANGUAGE plpgsql AS $$

        BEGIN
            -- Revertimos: devolver al stock físico, quitar del stock concesión
            UPDATE productos 
            SET stock_actual = stock_actual + OLD.cantidad,
                stock_concesion = stock_concesion - OLD.cantidad
            WHERE id_producto = OLD.id_producto;

            INSERT INTO inventario_movimientos (id_producto, tipo, cantidad, fecha)
            VALUES (OLD.id_producto, 'CANCELACION_CONCESION', OLD.cantidad, NOW());

            RETURN OLD;
        END;
        
$$;


CREATE OR REPLACE FUNCTION public.revertir_venta() RETURNS trigger
    LANGUAGE plpgsql AS $$

        DECLARE
            unidades_reales INTEGER;
            unidades_caja INTEGER;
        BEGIN
            -- Calculamos cuántas unidades reales se habían descontado
            SELECT unidades_por_caja INTO unidades_caja 
            FROM productos WHERE id_producto = OLD.id_producto;

            IF OLD.formato_venta = 'Caja' THEN
                unidades_reales := OLD.cantidad_formato * unidades_caja;
            ELSE
                unidades_reales := OLD.cantidad_formato;
            END IF;

            -- Revertimos el stock según si fue venta normal o concesión
            IF OLD.es_concesion = FALSE THEN
                -- Venta normal: devolver al stock físico
                UPDATE productos 
                SET stock_actual = stock_actual + unidades_reales 
                WHERE id_producto = OLD.id_producto;

                INSERT INTO inventario_movimientos (id_producto, tipo, cantidad, fecha)
                VALUES (OLD.id_producto, 'CANCELACION_VENTA', unidades_reales, NOW());
            ELSE
                -- Venta de concesión: devolver al stock_concesion
                UPDATE productos 
                SET stock_concesion = stock_concesion + unidades_reales 
                WHERE id_producto = OLD.id_producto;

                INSERT INTO inventario_movimientos (id_producto, tipo, cantidad, fecha)
                VALUES (OLD.id_producto, 'CANCELACION_VENTA_CONCESION', unidades_reales, NOW());
            END IF;

            RETURN OLD;
        END;
        
$$;

-- ============================================
-- TABLAS
-- ============================================

-- TABLE: clientes
CREATE TABLE IF NOT EXISTS public.clientes (
    id_cliente integer DEFAULT nextval('clientes_id_cliente_seq'::regclass) NOT NULL,
    razon_social text NOT NULL,
    telefono text,
    direccion text
);

-- TABLE: compras
CREATE TABLE IF NOT EXISTS public.compras (
    id_compra integer DEFAULT nextval('compras_id_compra_seq'::regclass) NOT NULL,
    id_proveedor integer,
    total_compra numeric(12,2),
    costo_flete numeric(10,2) DEFAULT 0,
    nro_factura text,
    fecha timestamp with time zone DEFAULT now()
);

-- TABLE: concesiones
CREATE TABLE IF NOT EXISTS public.concesiones (
    id_concesion integer DEFAULT nextval('concesiones_id_concesion_seq'::regclass) NOT NULL,
    id_cliente integer,
    fecha timestamp with time zone DEFAULT now(),
    estado text DEFAULT 'ACTIVA'::text
);

-- TABLE: detalle_compras
CREATE TABLE IF NOT EXISTS public.detalle_compras (
    id_detalle integer DEFAULT nextval('detalle_compras_id_detalle_seq'::regclass) NOT NULL,
    id_compra integer,
    id_producto integer,
    cantidad_unidades integer,
    precio_compra_neto numeric(10,2),
    descripcion text
);

-- TABLE: detalle_concesiones
CREATE TABLE IF NOT EXISTS public.detalle_concesiones (
    id_detalle integer DEFAULT nextval('detalle_concesiones_id_detalle_seq'::regclass) NOT NULL,
    id_concesion integer,
    id_producto integer,
    cantidad integer
);

-- TABLE: detalle_ventas
CREATE TABLE IF NOT EXISTS public.detalle_ventas (
    id_detalle integer DEFAULT nextval('detalle_ventas_id_detalle_seq'::regclass) NOT NULL,
    id_venta integer,
    id_producto integer,
    formato_venta text,
    cantidad_formato integer,
    precio_unitario_historico numeric(10,2),
    es_concesion boolean DEFAULT false,
    descripcion text,
    metodo_pago text DEFAULT 'Efectivo'::text
);

-- TABLE: historial_precios
CREATE TABLE IF NOT EXISTS public.historial_precios (
    id_historial integer DEFAULT nextval('historial_precios_id_historial_seq'::regclass) NOT NULL,
    id_producto integer,
    precio_anterior numeric(10,2),
    precio_nuevo numeric(10,2),
    fecha timestamp with time zone DEFAULT now()
);

-- TABLE: inventario_movimientos
CREATE TABLE IF NOT EXISTS public.inventario_movimientos (
    id_movimiento integer DEFAULT nextval('inventario_movimientos_id_movimiento_seq'::regclass) NOT NULL,
    id_producto integer,
    tipo text,
    cantidad integer,
    fecha timestamp with time zone DEFAULT now()
);

-- TABLE: marcas
CREATE TABLE IF NOT EXISTS public.marcas (
    id_marca integer DEFAULT nextval('marcas_id_marca_seq'::regclass) NOT NULL,
    nombre text NOT NULL
);

-- TABLE: productos
CREATE TABLE IF NOT EXISTS public.productos (
    id_producto integer DEFAULT nextval('productos_id_producto_seq'::regclass) NOT NULL,
    nombre text NOT NULL,
    id_marca integer,
    stock_actual integer DEFAULT 0,
    stock_minimo integer DEFAULT 5,
    stock_concesion integer DEFAULT 0,
    precio_costo_promedio numeric(10,2) DEFAULT 0,
    precio_venta numeric(10,2) DEFAULT 0,
    precio_venta_caja numeric(10,2) DEFAULT 0,
    unidades_por_caja integer DEFAULT 1
);

-- TABLE: proveedores
CREATE TABLE IF NOT EXISTS public.proveedores (
    id_proveedor integer DEFAULT nextval('proveedores_id_proveedor_seq'::regclass) NOT NULL,
    nombre text NOT NULL,
    telefono text,
    email text
);

-- TABLE: ventas
CREATE TABLE IF NOT EXISTS public.ventas (
    id_venta integer DEFAULT nextval('ventas_id_venta_seq'::regclass) NOT NULL,
    id_cliente integer,
    total_venta numeric(12,2),
    nro_factura text,
    fecha timestamp with time zone DEFAULT now(),
    metodo_pago text DEFAULT 'Efectivo'::text
);

-- ============================================
-- TRIGGERS
-- ============================================
CREATE TRIGGER trg_procesar_venta AFTER INSERT ON public.detalle_ventas FOR EACH ROW EXECUTE FUNCTION public.procesar_venta();
CREATE TRIGGER trg_revertir_venta BEFORE DELETE ON public.detalle_ventas FOR EACH ROW EXECUTE FUNCTION public.revertir_venta();
CREATE TRIGGER trg_procesar_compra AFTER INSERT ON public.detalle_compras FOR EACH ROW EXECUTE FUNCTION public.procesar_compra();
CREATE TRIGGER trg_revertir_compra BEFORE DELETE ON public.detalle_compras FOR EACH ROW EXECUTE FUNCTION public.revertir_compra();
CREATE TRIGGER trg_procesar_concesion AFTER INSERT ON public.detalle_concesiones FOR EACH ROW EXECUTE FUNCTION public.procesar_concesion();
CREATE TRIGGER trg_revertir_concesion BEFORE DELETE ON public.detalle_concesiones FOR EACH ROW EXECUTE FUNCTION public.revertir_concesion();

-- ============================================
-- FOREIGN KEYS
-- ============================================
ALTER TABLE ONLY public.compras ADD CONSTRAINT compras_id_proveedor_fkey FOREIGN KEY (id_proveedor) REFERENCES public.proveedores(id_proveedor);
ALTER TABLE ONLY public.concesiones ADD CONSTRAINT concesiones_id_cliente_fkey FOREIGN KEY (id_cliente) REFERENCES public.clientes(id_cliente);
ALTER TABLE ONLY public.detalle_compras ADD CONSTRAINT detalle_compras_id_compra_fkey FOREIGN KEY (id_compra) REFERENCES public.compras(id_compra) ON DELETE CASCADE;
ALTER TABLE ONLY public.detalle_compras ADD CONSTRAINT detalle_compras_id_producto_fkey FOREIGN KEY (id_producto) REFERENCES public.productos(id_producto);
ALTER TABLE ONLY public.detalle_concesiones ADD CONSTRAINT detalle_concesiones_id_producto_fkey FOREIGN KEY (id_producto) REFERENCES public.productos(id_producto);
ALTER TABLE ONLY public.detalle_concesiones ADD CONSTRAINT detalle_concesiones_id_concesion_fkey FOREIGN KEY (id_concesion) REFERENCES public.concesiones(id_concesion) ON DELETE CASCADE;
ALTER TABLE ONLY public.detalle_ventas ADD CONSTRAINT detalle_ventas_id_venta_fkey FOREIGN KEY (id_venta) REFERENCES public.ventas(id_venta) ON DELETE CASCADE;
ALTER TABLE ONLY public.detalle_ventas ADD CONSTRAINT detalle_ventas_id_producto_fkey FOREIGN KEY (id_producto) REFERENCES public.productos(id_producto);
ALTER TABLE ONLY public.historial_precios ADD CONSTRAINT historial_precios_id_producto_fkey FOREIGN KEY (id_producto) REFERENCES public.productos(id_producto);
ALTER TABLE ONLY public.inventario_movimientos ADD CONSTRAINT inventario_movimientos_id_producto_fkey FOREIGN KEY (id_producto) REFERENCES public.productos(id_producto);
ALTER TABLE ONLY public.productos ADD CONSTRAINT productos_id_marca_fkey FOREIGN KEY (id_marca) REFERENCES public.marcas(id_marca);
ALTER TABLE ONLY public.ventas ADD CONSTRAINT ventas_id_cliente_fkey FOREIGN KEY (id_cliente) REFERENCES public.clientes(id_cliente);

-- ============================================
-- VISTAS
-- ============================================
CREATE OR REPLACE VIEW public.v_comparacion_costos AS  SELECT id_producto,
    nombre,
    stock_actual,
    precio_costo_promedio AS costo_promedio,
    ( SELECT dc.precio_compra_neto
           FROM (detalle_compras dc
             JOIN compras c ON ((dc.id_compra = c.id_compra)))
          WHERE (dc.id_producto = p.id_producto)
          ORDER BY c.fecha DESC
         LIMIT 1) AS costo_ultima_compra,
    (( SELECT dc.precio_compra_neto
           FROM (detalle_compras dc
             JOIN compras c ON ((dc.id_compra = c.id_compra)))
          WHERE (dc.id_producto = p.id_producto)
          ORDER BY c.fecha DESC
         LIMIT 1) - precio_costo_promedio) AS diferencia,
        CASE
            WHEN (precio_costo_promedio > (0)::numeric) THEN round((((( SELECT dc.precio_compra_neto
               FROM (detalle_compras dc
                 JOIN compras c ON ((dc.id_compra = c.id_compra)))
              WHERE (dc.id_producto = p.id_producto)
              ORDER BY c.fecha DESC
             LIMIT 1) - precio_costo_promedio) / precio_costo_promedio) * (100)::numeric), 2)
            ELSE (0)::numeric
        END AS variacion_porcentual
   FROM productos p;;