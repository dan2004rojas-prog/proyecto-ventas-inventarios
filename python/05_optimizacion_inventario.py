
# 05_optimizacion_inventario.py
# Calcula stock de seguridad, punto de reorden,
# cobertura, alertas y unidades sugeridas de compra.

from pathlib import Path
import math

import numpy as np
import pandas as pd
from sqlalchemy import text

from conexion import crear_motor


# ------------------------------------------------------------
# CONFIGURACION
# ------------------------------------------------------------

CARPETA_PROYECTO = Path(__file__).resolve().parent.parent
CARPETA_DOCS = CARPETA_PROYECTO / "docs"

DIAS_HISTORICOS = 90
MESES_PRONOSTICO = 3
DIAS_REVISION = 30

# Factor Z aproximado para un nivel de servicio del 95 %
FACTOR_SEGURIDAD = 1.65

TABLA_SALIDA = "Recomendacion_Inventario"


def cargar_datos(motor):
    """Lee inventario actual, pronosticos y ventas historicas."""

    with motor.connect() as conn:
        inventario = pd.read_sql(
            text("SELECT * FROM dbo.vw_estado_inventario"),
            conn
        )

        pronosticos = pd.read_sql(
            text("""
                SELECT id_producto, mes,
                       unidades_pronosticadas, modelo
                FROM dbo.Pronostico_Ventas
            """),
            conn
        )

        if inventario.empty:
            raise ValueError(
                "La vista vw_estado_inventario no contiene registros."
            )

        if pronosticos.empty:
            raise ValueError(
                "Pronostico_Ventas no contiene pronosticos."
            )

        inventario["fecha"] = pd.to_datetime(inventario["fecha"])
        pronosticos["mes"] = pd.to_datetime(pronosticos["mes"])

        fecha_corte = inventario["fecha"].max()
        fecha_inicio = fecha_corte - pd.Timedelta(
            days=DIAS_HISTORICOS - 1
        )

        ventas = pd.read_sql(
            text("""
                SELECT id_producto, fecha, cantidad
                FROM dbo.Ventas
                WHERE fecha >= :inicio AND fecha <= :fin
            """),
            conn,
            params={
                "inicio": fecha_inicio.date(),
                "fin": fecha_corte.date()
            }
        )

    ventas["fecha"] = pd.to_datetime(ventas["fecha"])

    return inventario, pronosticos, ventas, fecha_corte


def calcular_demanda_diaria(pronosticos):
    """
    Calcula la demanda diaria prevista usando los primeros
    tres meses pronosticados, ponderados por sus dias.
    """

    pronosticos = pronosticos.copy()
    pronosticos["mes"] = pd.to_datetime(pronosticos["mes"])
    pronosticos["unidades_pronosticadas"] = pd.to_numeric(
        pronosticos["unidades_pronosticadas"],
        errors="coerce"
    ).fillna(0).clip(lower=0)

    pronosticos = pronosticos.sort_values(
        ["id_producto", "mes"]
    )

    pronosticos = (
        pronosticos.groupby("id_producto", group_keys=False)
        .head(MESES_PRONOSTICO)
        .copy()
    )

    pronosticos["dias_mes"] = pronosticos["mes"].dt.days_in_month

    resumen = pronosticos.groupby("id_producto").agg(
        unidades_previstas=("unidades_pronosticadas", "sum"),
        dias_previstos=("dias_mes", "sum")
    )

    resumen["demanda_diaria_pronosticada"] = (
        resumen["unidades_previstas"]
        / resumen["dias_previstos"].replace(0, np.nan)
    )

    return resumen[["demanda_diaria_pronosticada"]]


def calcular_variabilidad(ventas, inventario, fecha_corte):
    """
    Calcula la desviacion estandar de las ventas diarias
    de los ultimos 90 dias, incluidos los dias sin ventas.
    """

    fecha_inicio = fecha_corte - pd.Timedelta(
        days=DIAS_HISTORICOS - 1
    )

    fechas = pd.date_range(
        start=fecha_inicio,
        end=fecha_corte,
        freq="D"
    )

    ids = inventario["id_producto"].unique()

    if ventas.empty:
        ventas_diarias = pd.DataFrame(
            0.0, index=fechas, columns=ids
        )
    else:
        diario = (
            ventas.groupby(
                ["fecha", "id_producto"]
            )["cantidad"]
            .sum()
            .reset_index()
        )

        ventas_diarias = diario.pivot(
            index="fecha",
            columns="id_producto",
            values="cantidad"
        )

        ventas_diarias = ventas_diarias.reindex(
            index=fechas,
            columns=ids,
            fill_value=0
        ).fillna(0)

    return ventas_diarias.std(axis=0, ddof=1).fillna(0)


def clasificar_alerta(stock, minimo, reorden, objetivo):
    """Asigna una alerta segun el estado y la demanda prevista."""

    if stock <= 0:
        return "QUIEBRE"

    if stock <= reorden:
        return "REORDENAR"

    if stock < minimo:
        return "BAJO MINIMO"

    if stock > max(3 * minimo, 1.5 * objetivo):
        return "SOBRESTOCK"

    return "OK"


def calcular_recomendaciones(
    inventario, pronosticos, ventas, fecha_corte
):
    """Calcula indicadores y recomendaciones para cada producto."""

    demanda = calcular_demanda_diaria(pronosticos)
    variabilidad = calcular_variabilidad(
        ventas, inventario, fecha_corte
    )

    resultado = inventario.copy()

    resultado = resultado.drop_duplicates(
        subset=["id_producto"]
    )

    resultado["demanda_diaria_pronosticada"] = (
        resultado["id_producto"].map(
            demanda["demanda_diaria_pronosticada"]
        )
    )

    if resultado["demanda_diaria_pronosticada"].isna().any():
        raise ValueError(
            "Hay productos sin pronostico. Revisa Pronostico_Ventas."
        )

    resultado["desviacion_demanda_diaria"] = (
        resultado["id_producto"].map(variabilidad).fillna(0)
    )

    resultado["stock_seguridad"] = (
        FACTOR_SEGURIDAD
        * resultado["desviacion_demanda_diaria"]
        * np.sqrt(resultado["lead_time_dias"].clip(lower=0))
    ).apply(math.ceil)

    resultado["punto_reorden"] = (
        resultado["demanda_diaria_pronosticada"]
        * resultado["lead_time_dias"]
        + resultado["stock_seguridad"]
    ).apply(math.ceil)

    resultado["stock_objetivo"] = (
        resultado["demanda_diaria_pronosticada"]
        * (
            resultado["lead_time_dias"]
            + DIAS_REVISION
        )
        + resultado["stock_seguridad"]
    ).apply(math.ceil)

    resultado["dias_cobertura_pronosticados"] = (
        resultado["stock_actual"]
        / resultado["demanda_diaria_pronosticada"].replace(0, np.nan)
    ).round(1)

    resultado["unidades_a_comprar"] = resultado.apply(
        lambda fila: max(
            0,
            int(fila["stock_objetivo"] - fila["stock_actual"])
        )
        if fila["stock_actual"] <= max(
            fila["punto_reorden"], fila["stock_minimo"]
        )
        else 0,
        axis=1
    )

    resultado["estado_alerta"] = resultado.apply(
        lambda fila: clasificar_alerta(
            fila["stock_actual"],
            fila["stock_minimo"],
            fila["punto_reorden"],
            fila["stock_objetivo"]
        ),
        axis=1
    )

    resultado["fecha_corte"] = fecha_corte.date()

    columnas = [
        "id_producto",
        "producto",
        "categoria",
        "proveedor",
        "fecha_corte",
        "stock_actual",
        "stock_minimo",
        "lead_time_dias",
        "demanda_diaria_pronosticada",
        "desviacion_demanda_diaria",
        "stock_seguridad",
        "punto_reorden",
        "stock_objetivo",
        "dias_cobertura_pronosticados",
        "unidades_a_comprar",
        "estado_alerta"
    ]

    resultado = resultado[columnas].copy()

    resultado["demanda_diaria_pronosticada"] = (
        resultado["demanda_diaria_pronosticada"].round(2)
    )
    resultado["desviacion_demanda_diaria"] = (
        resultado["desviacion_demanda_diaria"].round(2)
    )

    return resultado.sort_values(
        ["estado_alerta", "categoria", "producto"]
    )


def guardar_resultados(resultado, motor):
    """Guarda un CSV y una tabla nueva en SQL Server."""

    CARPETA_DOCS.mkdir(parents=True, exist_ok=True)

    ruta_csv = CARPETA_DOCS / "recomendaciones_inventario.csv"
    resultado.to_csv(
        ruta_csv, index=False, encoding="utf-8-sig"
    )

    # Solo reemplaza la tabla de recomendaciones,
    # no las tablas originales de ventas o inventario.
    resultado.to_sql(
        TABLA_SALIDA,
        motor,
        schema="dbo",
        if_exists="replace",
        index=False
    )

    print(f"\nCSV guardado en: {ruta_csv}")
    print(f"Tabla SQL actualizada: dbo.{TABLA_SALIDA}")


def main():
    print("Calculando recomendaciones de inventario...")

    motor = crear_motor()

    try:
        inventario, pronosticos, ventas, fecha_corte = (
            cargar_datos(motor)
        )

        resultado = calcular_recomendaciones(
            inventario,
            pronosticos,
            ventas,
            fecha_corte
        )

        guardar_resultados(resultado, motor)

        print("\n--- Resumen de alertas ---")
        print(
            resultado["estado_alerta"]
            .value_counts()
            .to_string()
        )

        print("\n--- Productos que requieren atencion ---")
        columnas = [
            "producto",
            "stock_actual",
            "punto_reorden",
            "unidades_a_comprar",
            "estado_alerta"
        ]

        print(
            resultado.loc[
                resultado["estado_alerta"] != "OK",
                columnas
            ].to_string(index=False)
        )

        print("\nProceso completado.")

    finally:
        motor.dispose()


if __name__ == "__main__":
    main()