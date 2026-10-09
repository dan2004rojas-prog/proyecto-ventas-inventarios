# 01_generar_y_cargar_datos.py
# Crea datos de ejemplo (proveedores, productos, ventas e inventario),
# los guarda en CSV y los carga en SQL Server.
# Uso: python python/01_generar_y_cargar_datos.py

import math
import urllib.parse
from pathlib import Path

import numpy as np
import pandas as pd
import pyodbc
from sqlalchemy import create_engine, text


# CONFIGURACIÓN (lo único que quizás tengas que cambiar)
SERVIDOR = "DanServer"              # nombre de tu servidor SQL Server
BASE_DATOS = "VentasInventario"
SOLO_CSV = False                    # True = solo crea los CSV, sin tocar SQL Server
SEMILLA = 42

FECHA_INICIO = "2023-10-01"
FECHA_FIN = "2026-09-30"

CARPETA_DATA = Path(__file__).resolve().parent.parent / "data"


# DATOS BASE: proveedores, productos y categorías

# Proveedores: (nombre, país, días que tarda en entregar)
PROVEEDORES = [
    ("Molinos y Granos del Sur", "Perú", 7),
    ("Cooperativa Cafetalera del Norte", "Perú", 10),
    ("Cacao Selva Central", "Perú", 14),
    ("Agroexport Valle Verde", "Perú", 5),
    ("AgroInsumos Andinos", "Perú", 12),
    ("Importadora AgroGlobal", "Chile", 25),
]

# Qué proveedores (posición en la lista de arriba) abastecen cada categoría
PROVEEDORES_POR_CATEGORIA = {
    "Granos": [0],
    "Café y Cacao": [1, 2],
    "Frutas": [3],
    "Insumos": [4, 5],
}

# Productos: (nombre, categoría)
PRODUCTOS = [
    ("Arroz pilado 50 kg", "Granos"),
    ("Quinua orgánica 25 kg", "Granos"),
    ("Maíz amarillo duro 50 kg", "Granos"),
    ("Maíz morado 25 kg", "Granos"),
    ("Frejol canario 50 kg", "Granos"),
    ("Trigo grano 50 kg", "Granos"),
    ("Cebada grano 50 kg", "Granos"),
    ("Lenteja 25 kg", "Granos"),
    ("Kiwicha 25 kg", "Granos"),

    ("Café pergamino 60 kg", "Café y Cacao"),
    ("Café tostado molido 1 kg", "Café y Cacao"),
    ("Café verde exportación 69 kg", "Café y Cacao"),
    ("Cacao en grano 50 kg", "Café y Cacao"),
    ("Cacao en polvo 25 kg", "Café y Cacao"),
    ("Manteca de cacao 20 kg", "Café y Cacao"),
    ("Nibs de cacao 10 kg", "Café y Cacao"),
    ("Panela granulada 25 kg", "Café y Cacao"),
    ("Azúcar rubia 50 kg", "Café y Cacao"),

    ("Palta Hass caja 10 kg", "Frutas"),
    ("Mango Kent caja 10 kg", "Frutas"),
    ("Uva Red Globe caja 8 kg", "Frutas"),
    ("Arándano caja 2 kg", "Frutas"),
    ("Plátano orgánico caja 18 kg", "Frutas"),
    ("Limón sutil saco 20 kg", "Frutas"),
    ("Mandarina caja 10 kg", "Frutas"),
    ("Piña golden caja 15 kg", "Frutas"),
    ("Granada caja 8 kg", "Frutas"),

    ("Urea 50 kg", "Insumos"),
    ("Nitrato de amonio 50 kg", "Insumos"),
    ("Fosfato diamónico 50 kg", "Insumos"),
    ("Cloruro de potasio 50 kg", "Insumos"),
    ("Compost orgánico 40 kg", "Insumos"),
    ("Semilla de maíz híbrido 20 kg", "Insumos"),
    ("Herbicida glifosato 20 L", "Insumos"),
    ("Fungicida cobre 5 kg", "Insumos"),
    ("Insecticida biológico 1 L", "Insumos"),
]

# Unidades que se venden por día, en promedio, según la categoría
DEMANDA_BASE = {"Granos": 40, "Café y Cacao": 25, "Frutas": 60, "Insumos": 20}

# Rango de precios (en soles) según la categoría
RANGO_PRECIO = {
    "Granos": (90, 260),
    "Café y Cacao": (35, 900),
    "Frutas": (25, 180),
    "Insumos": (60, 420),
}

# Estacionalidad: cuánto sube o baja la venta en cada mes (enero a diciembre)
# 1.0 = normal, 1.3 = 30% más de lo normal, 0.8 = 20% menos
ESTACIONALIDAD = {
    "Granos":       [0.90, 0.90, 1.00, 1.15, 1.25, 1.15, 1.00, 0.95, 0.90, 0.90, 0.95, 1.05],
    "Café y Cacao": [0.80, 0.80, 0.85, 0.95, 1.10, 1.30, 1.35, 1.20, 1.00, 0.90, 0.95, 1.10],
    "Frutas":       [1.30, 1.35, 1.25, 1.05, 0.90, 0.80, 0.75, 0.80, 0.90, 1.00, 1.10, 1.25],
    "Insumos":      [0.85, 0.90, 1.20, 1.25, 0.90, 0.80, 0.80, 0.90, 1.20, 1.35, 1.25, 0.95],
}

# Tipos de manejo de inventario (para que haya productos bien y mal gestionados)
#   primer número  = cuándo se pide mercadería (más alto = se pide antes)
#   segundo número = cuántos días de venta se compran en cada pedido
PERFILES = {
    "equilibrado": (1.80, 15),      # manejo normal
    "riesgo_quiebre": (0.90, 8),    # pide tarde y poco -> se queda sin stock
    "sobrestock": (1.80, 70),       # compra de más -> inventario excesivo
}


# PASO 1: Crear los datos
def crear_datos():
    rng = np.random.default_rng(SEMILLA)
    fechas = pd.date_range(FECHA_INICIO, FECHA_FIN, freq="D")
    n_dias = len(fechas)

    # ---------- Tabla Proveedores ----------
    proveedores = pd.DataFrame(PROVEEDORES, columns=["nombre", "pais", "lead_time_dias"])
    proveedores.insert(0, "id_proveedor", range(1, len(proveedores) + 1))

    # ---------- Tabla Productos ----------
    lista_productos = []
    for numero, (nombre, categoria) in enumerate(PRODUCTOS, start=1):
        opciones = PROVEEDORES_POR_CATEGORIA[categoria]
        id_proveedor = int(rng.choice(opciones)) + 1

        precio_min, precio_max = RANGO_PRECIO[categoria]
        precio = round(float(rng.uniform(precio_min, precio_max)), 2)
        costo = round(precio * float(rng.uniform(0.62, 0.80)), 2)

        lista_productos.append((numero, nombre, categoria, id_proveedor, costo, precio))

    productos = pd.DataFrame(
        lista_productos,
        columns=["id_producto", "nombre", "categoria", "id_proveedor", "costo_unitario", "precio"],
    )
    n_productos = len(productos)

    lead_time = []
    for id_prov in productos["id_proveedor"]:
        lead_time.append(PROVEEDORES[id_prov - 1][2])

    demanda = np.zeros((n_dias, n_productos), dtype=int)
    demanda_base_producto = []

    meses = fechas.month.to_numpy() - 1
    dia_semana = fechas.dayofweek.to_numpy()
    anios_pasados = np.arange(n_dias) / 365.25

    factor_dia = np.where(dia_semana < 5, 1.05, np.where(dia_semana == 5, 0.90, 0.50))

    for j in range(n_productos):
        categoria = productos.loc[j, "categoria"]

        base = DEMANDA_BASE[categoria] * rng.uniform(0.5, 1.6)
        demanda_base_producto.append(base)

        crecimiento = rng.uniform(-0.05, 0.20)
        tendencia = (1 + crecimiento) ** anios_pasados

        estacional = np.array(ESTACIONALIDAD[categoria])[meses]

        ruido = rng.lognormal(0, 0.12, n_dias)
        picos = np.where(rng.random(n_dias) < 0.005, 1.8, 1.0)

        esperada = base * tendencia * estacional * factor_dia * ruido * picos
        demanda[:, j] = rng.poisson(esperada)

    tipos = rng.choice(list(PERFILES), size=n_productos, p=[0.70, 0.15, 0.15])

    # Día por día: llega mercadería, se vende, y se pide más si el stock está bajo.
    # Si no hay stock suficiente, la venta se pierde (así aparecen los quiebres).
    registros_ventas = []
    registros_inventario = []

    for j in range(n_productos):
        id_producto = int(productos.loc[j, "id_producto"])
        precio = float(productos.loc[j, "precio"])
        dias_entrega = lead_time[j]
        factor_pedido, dias_ciclo = PERFILES[tipos[j]]

        promedio = demanda_base_producto[j]
        stock_minimo = max(1, math.ceil(promedio * (dias_entrega + 5)))
        punto_pedido = max(1, math.ceil(stock_minimo * factor_pedido))
        objetivo = punto_pedido + math.ceil(promedio * dias_ciclo)

        stock = objetivo
        pedido_pendiente = 0
        dia_llegada = -1

        for t in range(n_dias):

            # cada 30 días recalculamos las reglas con las ventas de los últimos 60 días
            if t >= 60 and t % 30 == 0:
                promedio = max(1.0, demanda[t - 60:t, j].mean())
                stock_minimo = max(1, math.ceil(promedio * (dias_entrega + 5)))
                punto_pedido = max(1, math.ceil(stock_minimo * factor_pedido))
                objetivo = punto_pedido + math.ceil(promedio * dias_ciclo)

            # 1) ¿llegó el pedido?
            if pedido_pendiente > 0 and t >= dia_llegada:
                stock = stock + pedido_pendiente
                pedido_pendiente = 0

            # 2) vendemos lo que se pueda (no más del stock que hay)
            vendido = int(min(demanda[t, j], stock))
            stock = stock - vendido

            if vendido > 0:
                precio_dia = precio * (1 + 0.04 * anios_pasados[t]) * rng.uniform(0.97, 1.03)
                monto = round(vendido * precio_dia, 2)
                registros_ventas.append((fechas[t], id_producto, vendido, monto))

            # 3) si el stock está bajo y no hay pedido en camino, pedimos más
            if pedido_pendiente == 0 and stock <= punto_pedido:
                pedido_pendiente = max(1, objetivo - stock)
                demora = max(1, dias_entrega + int(rng.integers(-1, 3)))
                dia_llegada = t + demora

            # 4) guardamos cómo quedó el inventario al final del día
            registros_inventario.append((id_producto, fechas[t], int(stock), int(stock_minimo)))

    ventas = pd.DataFrame(registros_ventas, columns=["fecha", "id_producto", "cantidad", "monto"])
    inventario = pd.DataFrame(
        registros_inventario,
        columns=["id_producto", "fecha", "stock_actual", "stock_minimo"],
    )

    return {
        "Proveedores": proveedores,
        "Productos": productos,
        "Ventas": ventas,
        "Inventario": inventario,
    }


# PASO 2: Mostrar un resumen para revisar que los datos tengan sentido
def mostrar_resumen(datos):
    ventas = datos["Ventas"]
    inventario = datos["Inventario"]

    print("\n--- Resumen de los datos creados ---")
    for nombre, tabla in datos.items():
        print(f"{nombre:<12} {len(tabla):>8,} filas")

    print(f"Fechas: del {ventas['fecha'].min().date()} al {ventas['fecha'].max().date()}")
    print(f"Ventas totales: S/ {ventas['monto'].sum():,.0f}")

    quiebres = (inventario["stock_actual"] == 0).mean() * 100
    bajo_minimo = (inventario["stock_actual"] < inventario["stock_minimo"]).mean() * 100
    print(f"Días con stock en cero: {quiebres:.1f}%")
    print(f"Días con stock bajo el mínimo: {bajo_minimo:.1f}%")


# PASO 3: Guardar los CSV
def guardar_csv(datos):
    CARPETA_DATA.mkdir(parents=True, exist_ok=True)
    for nombre, tabla in datos.items():
        ruta = CARPETA_DATA / (nombre.lower() + ".csv")
        tabla.to_csv(ruta, index=False, encoding="utf-8-sig")
        print("CSV guardado:", ruta)


# PASO 4: Cargar los datos en SQL Server
def buscar_driver():
    # usa solo los drivers modernos (el antiguo 'SQL Server' no sirve)
    drivers = [d for d in pyodbc.drivers() if d.startswith("ODBC Driver") and "SQL Server" in d]
    if len(drivers) == 0:
        print("Drivers que tienes instalados:", pyodbc.drivers())
        raise SystemExit(
            "Falta el driver moderno. Instala 'ODBC Driver 18 for SQL Server' "
            "(búscalo en Google: 'Download ODBC Driver for SQL Server' de Microsoft) "
            "y vuelve a ejecutar el script."
        )
    return sorted(drivers)[-1]


def cargar_en_sql_server(datos):
    driver = buscar_driver()
    print(f"\nConectando a {SERVIDOR} / {BASE_DATOS} (driver: {driver})")

    conexion = (
        f"DRIVER={{{driver}}};"
        f"SERVER={SERVIDOR};"
        f"DATABASE={BASE_DATOS};"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )
    url = "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(conexion)
    motor = create_engine(url, fast_executemany=True)

    ventas = datos["Ventas"].copy()
    ventas["fecha"] = ventas["fecha"].dt.date
    inventario = datos["Inventario"].copy()
    inventario["fecha"] = inventario["fecha"].dt.date

    proveedores = datos["Proveedores"]
    productos = datos["Productos"]

    ventas.insert(0, "id_venta", range(1, len(ventas) + 1))

    with motor.begin() as conn:
        # Borramos lo que hubiera antes (primero las tablas "hijas")
        print("Borrando datos anteriores...")
        for tabla in ["Inventario", "Ventas", "Productos", "Proveedores"]:
            conn.execute(text("DELETE FROM " + tabla))

        # Primero las tablas "padre" y al final las "hijas"
        # IDENTITY_INSERT permite escribir nosotros los id (1, 2, 3...)
        orden = [
            ("Proveedores", proveedores, True),
            ("Productos", productos, True),
            ("Ventas", ventas, True),
            ("Inventario", inventario, False),
        ]
        for nombre, tabla, tiene_identity in orden:
            if tiene_identity:
                conn.execute(text(f"SET IDENTITY_INSERT {nombre} ON"))

            tabla.to_sql(nombre, conn, if_exists="append", index=False, chunksize=5000)

            if tiene_identity:
                conn.execute(text(f"SET IDENTITY_INSERT {nombre} OFF"))
            print(f"  {nombre:<12} {len(tabla):>8,} filas cargadas")

    print("\nFilas que hay ahora en SQL Server:")
    with motor.connect() as conn:
        for nombre in ["Proveedores", "Productos", "Ventas", "Inventario"]:
            total = conn.execute(text("SELECT COUNT(*) FROM " + nombre)).scalar()
            print(f"  {nombre:<12} {total:>8,}")


# PROGRAMA PRINCIPAL
if __name__ == "__main__":
    print("Creando datos de ejemplo...")
    datos = crear_datos()
    mostrar_resumen(datos)
    guardar_csv(datos)

    if SOLO_CSV:
        print("\nListo: solo se crearon los CSV (SOLO_CSV = True).")
    else:
        cargar_en_sql_server(datos)
        print("\nListo: los datos ya están en SQL Server.")
