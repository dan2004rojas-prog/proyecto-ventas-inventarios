
USE VentasInventario;
GO


/* ============================================================
   PARTE 1: CONSULTAS DE ANÁLISIS
   ============================================================ */

SELECT
    YEAR(v.fecha)   AS anio,
    MONTH(v.fecha)  AS mes,
    p.categoria,
    SUM(v.cantidad) AS unidades,
    SUM(v.monto)    AS ventas
FROM Ventas v
JOIN Productos p ON p.id_producto = v.id_producto
GROUP BY YEAR(v.fecha), MONTH(v.fecha), p.categoria
ORDER BY anio, mes, p.categoria;


-- ------------------------------------------------------------
-- 2) Media móvil de 3 meses por producto
-- ------------------------------------------------------------
WITH mensual AS (
    SELECT
        id_producto,
        DATEFROMPARTS(YEAR(fecha), MONTH(fecha), 1) AS mes,
        SUM(cantidad) AS unidades
    FROM Ventas
    GROUP BY id_producto, DATEFROMPARTS(YEAR(fecha), MONTH(fecha), 1)
)
SELECT
    id_producto,
    mes,
    unidades,
    ROUND(
        AVG(CAST(unidades AS FLOAT)) OVER (
            PARTITION BY id_producto
            ORDER BY mes
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ), 1) AS media_movil_3m
FROM mensual
ORDER BY id_producto, mes;


-- ------------------------------------------------------------
-- 3) Crecimiento mes a mes por categoría 
-- ------------------------------------------------------------
WITH mensual AS (
    SELECT
        p.categoria,
        DATEFROMPARTS(YEAR(v.fecha), MONTH(v.fecha), 1) AS mes,
        SUM(v.monto) AS ventas
    FROM Ventas v
    JOIN Productos p ON p.id_producto = v.id_producto
    GROUP BY p.categoria, DATEFROMPARTS(YEAR(v.fecha), MONTH(v.fecha), 1)
)
SELECT
    categoria,
    mes,
    ventas,
    LAG(ventas) OVER (PARTITION BY categoria ORDER BY mes) AS ventas_mes_anterior,
    CAST(
        100.0 * (ventas - LAG(ventas) OVER (PARTITION BY categoria ORDER BY mes))
        / NULLIF(LAG(ventas) OVER (PARTITION BY categoria ORDER BY mes), 0)
    AS DECIMAL(10, 2)) AS crecimiento_pct
FROM mensual
ORDER BY categoria, mes;


-- ------------------------------------------------------------
-- 4) Ranking de productos dentro de su categoría 
--    El producto con más ventas de cada categoría queda en el puesto 1.
-- ------------------------------------------------------------
SELECT
    p.categoria,
    p.nombre AS producto,
    SUM(v.monto) AS ventas_totales,
    RANK() OVER (PARTITION BY p.categoria ORDER BY SUM(v.monto) DESC) AS ranking
FROM Ventas v
JOIN Productos p ON p.id_producto = v.id_producto
GROUP BY p.categoria, p.nombre
ORDER BY p.categoria, ranking;


-- ------------------------------------------------------------
-- 5) Estado del inventario en el último día registrado
--    Clasifica cada producto: QUIEBRE, BAJO MÍNIMO, EXCESO u OK.
--    (Exceso = más de 3 veces el stock mínimo)
-- ------------------------------------------------------------
SELECT
    p.nombre AS producto,
    p.categoria,
    i.stock_actual,
    i.stock_minimo,
    CASE
        WHEN i.stock_actual = 0                  THEN 'QUIEBRE'
        WHEN i.stock_actual < i.stock_minimo     THEN 'BAJO MINIMO'
        WHEN i.stock_actual > 3 * i.stock_minimo THEN 'EXCESO'
        ELSE 'OK'
    END AS estado
FROM Inventario i
JOIN Productos p ON p.id_producto = i.id_producto
WHERE i.fecha = (SELECT MAX(fecha) FROM Inventario)
ORDER BY estado, p.categoria, p.nombre;


-- ------------------------------------------------------------
-- 6) Días de cobertura
--    Cuántos días durará el stock actual si se sigue vendiendo
--    al ritmo de los últimos 30 días.
--    días de cobertura = stock actual / venta diaria promedio
-- ------------------------------------------------------------
WITH ultimo_dia AS (
    SELECT MAX(fecha) AS fecha FROM Inventario
),
venta_30d AS (
    SELECT
        v.id_producto,
        SUM(v.cantidad) / 30.0 AS venta_diaria
    FROM Ventas v
    CROSS JOIN ultimo_dia u
    WHERE v.fecha > DATEADD(DAY, -30, u.fecha)
    GROUP BY v.id_producto
)
SELECT
    p.nombre AS producto,
    i.stock_actual,
    CAST(vd.venta_diaria AS DECIMAL(10, 2)) AS venta_diaria_30d,
    CAST(i.stock_actual / NULLIF(vd.venta_diaria, 0) AS DECIMAL(10, 1)) AS dias_cobertura,
    pr.lead_time_dias
FROM Inventario i
CROSS JOIN ultimo_dia u
JOIN Productos p     ON p.id_producto  = i.id_producto
JOIN Proveedores pr  ON pr.id_proveedor = p.id_proveedor
LEFT JOIN venta_30d vd ON vd.id_producto = i.id_producto
WHERE i.fecha = u.fecha
ORDER BY dias_cobertura;


-- ------------------------------------------------------------
-- 7) Rotación de inventario (últimos 12 meses)
--    rotación = unidades vendidas en 12 meses / stock promedio
--    Una rotación alta = el producto se mueve rápido.
--    Una rotación baja = hay inventario parado.
-- ------------------------------------------------------------
WITH ultimo_dia AS (
    SELECT MAX(fecha) AS fecha FROM Inventario
),
vendido AS (
    SELECT v.id_producto, SUM(v.cantidad) AS unidades_12m
    FROM Ventas v
    CROSS JOIN ultimo_dia u
    WHERE v.fecha > DATEADD(MONTH, -12, u.fecha)
    GROUP BY v.id_producto
),
stock AS (
    SELECT i.id_producto, AVG(CAST(i.stock_actual AS FLOAT)) AS stock_promedio
    FROM Inventario i
    CROSS JOIN ultimo_dia u
    WHERE i.fecha > DATEADD(MONTH, -12, u.fecha)
    GROUP BY i.id_producto
)
SELECT
    p.nombre AS producto,
    p.categoria,
    ve.unidades_12m,
    CAST(st.stock_promedio AS DECIMAL(12, 1)) AS stock_promedio,
    CAST(ve.unidades_12m / NULLIF(st.stock_promedio, 0) AS DECIMAL(10, 2)) AS rotacion
FROM Productos p
JOIN vendido ve ON ve.id_producto = p.id_producto
JOIN stock st   ON st.id_producto = p.id_producto
ORDER BY rotacion DESC;
GO


/* ============================================================
   PARTE 2: VISTAS
  
   ============================================================ */

/*-- ------------------------------------------------------------
-- Vista 1: ventas mensuales por producto
--          
-- ------------------------------------------------------------ */
CREATE OR ALTER VIEW vw_ventas_mensuales AS
SELECT
    p.id_producto,
    p.nombre    AS producto,
    p.categoria,
    pr.nombre   AS proveedor,
    DATEFROMPARTS(YEAR(v.fecha), MONTH(v.fecha), 1) AS mes,
    SUM(v.cantidad) AS unidades,
    SUM(v.monto)    AS ventas
FROM Ventas v
JOIN Productos p    ON p.id_producto   = v.id_producto
JOIN Proveedores pr ON pr.id_proveedor = p.id_proveedor
GROUP BY
    p.id_producto, p.nombre, p.categoria, pr.nombre,
    DATEFROMPARTS(YEAR(v.fecha), MONTH(v.fecha), 1);
GO


/*-- ------------------------------------------------------------
-- Vista 2: estado actual del inventario
--         
-- ------------------------------------------------------------*/
CREATE OR ALTER VIEW vw_estado_inventario AS
WITH ultimo_dia AS (
    SELECT MAX(fecha) AS fecha FROM Inventario
),
venta_30d AS (
    SELECT
        v.id_producto,
        SUM(v.cantidad) / 30.0 AS venta_diaria
    FROM Ventas v
    CROSS JOIN ultimo_dia u
    WHERE v.fecha > DATEADD(DAY, -30, u.fecha)
    GROUP BY v.id_producto
)
SELECT
    p.id_producto,
    p.nombre    AS producto,
    p.categoria,
    pr.nombre   AS proveedor,
    pr.lead_time_dias,
    i.fecha,
    i.stock_actual,
    i.stock_minimo,
    CAST(vd.venta_diaria AS DECIMAL(10, 2)) AS venta_diaria_30d,
    CAST(i.stock_actual / NULLIF(vd.venta_diaria, 0) AS DECIMAL(10, 1)) AS dias_cobertura,
    CASE
        WHEN i.stock_actual = 0                  THEN 'QUIEBRE'
        WHEN i.stock_actual < i.stock_minimo     THEN 'BAJO MINIMO'
        WHEN i.stock_actual > 3 * i.stock_minimo THEN 'EXCESO'
        ELSE 'OK'
    END AS estado
FROM Inventario i
CROSS JOIN ultimo_dia u
JOIN Productos p       ON p.id_producto   = i.id_producto
JOIN Proveedores pr    ON pr.id_proveedor = p.id_proveedor
LEFT JOIN venta_30d vd ON vd.id_producto  = i.id_producto
WHERE i.fecha = u.fecha;
GO


-- ------------------------------------------------------------
-- Comprobamos que las vistas funcionan
-- ------------------------------------------------------------
SELECT TOP 10 * FROM vw_ventas_mensuales ORDER BY mes, id_producto;
SELECT * FROM vw_estado_inventario ORDER BY estado, categoria;
GO
