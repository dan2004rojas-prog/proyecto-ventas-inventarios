# ============================================================
# 04_modelos_y_pronostico.py
# Compara 3 modelos de pronóstico, elige el mejor para cada producto
# y guarda el pronóstico de los próximos 6 meses en SQL Server.
# Uso: python python/04_modelos_y_pronostico.py
# ============================================================

import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX

from conexion import crear_motor

warnings.filterwarnings("ignore")


# ============================================================
# CONFIGURACIÓN
# ============================================================
MESES_PRUEBA = 6        # últimos meses que se guardan para evaluar los modelos
MESES_FUTURO = 6        # meses que vamos a pronosticar

CARPETA_DOCS = Path(__file__).resolve().parent.parent / "docs"

AZUL = "#2a78d6"
NARANJA = "#eb6834"
FONDO = "#fcfcfb"
TEXTO = "#0b0b0b"
TEXTO_SUAVE = "#52514e"
GRILLA = "#e6e5e1"


# ============================================================
# LOS 3 MODELOS
# Cada uno recibe la serie (números) y la cantidad de meses a pronosticar
# ============================================================
def modelo_naive(serie, n):
    # repite lo que se vendió el mismo mes del año anterior
    return serie[-12:][:n]


def modelo_holt_winters(serie, n):
    modelo = ExponentialSmoothing(serie, trend="add", seasonal="add", seasonal_periods=12).fit()
    return np.asarray(modelo.forecast(n))


def modelo_sarima(serie, n):
    modelo = SARIMAX(serie, order=(1, 1, 1), seasonal_order=(0, 1, 1, 12)).fit(disp=False)
    return np.asarray(modelo.forecast(n))


MODELOS = {
    "Naive estacional": modelo_naive,
    "Holt-Winters": modelo_holt_winters,
    "SARIMA": modelo_sarima,
}


# ============================================================
# PASO 1: Leer las ventas mensuales
# ============================================================
def leer_datos(motor):
    df = pd.read_sql("SELECT * FROM vw_ventas_mensuales", motor)
    df["mes"] = pd.to_datetime(df["mes"])
    tabla = df.pivot_table(index="mes", columns="id_producto", values="unidades", aggfunc="sum")
    return tabla.asfreq("MS").fillna(0)       # una columna por producto


# ============================================================
# PASO 2: Evaluar los modelos
# Entrenamos con los primeros meses y comparamos contra los últimos 6
# ============================================================
def calcular_errores(real, pred):
    mape = np.mean(np.abs((real - pred) / real)) * 100     # error en %
    rmse = np.sqrt(np.mean((real - pred) ** 2))
    mae = np.mean(np.abs(real - pred))
    return mape, rmse, mae


def evaluar_modelos(tabla):
    filas = []
    for id_producto in tabla.columns:
        serie = tabla[id_producto].values.astype(float)
        entrenamiento = serie[:-MESES_PRUEBA]
        prueba = serie[-MESES_PRUEBA:]

        for nombre, funcion in MODELOS.items():
            try:
                pred = np.clip(funcion(entrenamiento, MESES_PRUEBA), 0, None)
                mape, rmse, mae = calcular_errores(prueba, pred)
            except Exception:
                mape = rmse = mae = np.nan
            filas.append((id_producto, nombre, mape, rmse, mae))

    return pd.DataFrame(filas, columns=["id_producto", "modelo", "mape", "rmse", "mae"])


# ============================================================
# PASO 3: Pronosticar los próximos meses con el mejor modelo de cada producto
# ============================================================
def pronosticar_futuro(tabla, mejor_modelo):
    primer_mes = tabla.index[-1] + pd.offsets.MonthBegin(1)
    meses = pd.date_range(primer_mes, periods=MESES_FUTURO, freq="MS")

    filas = []
    for id_producto in tabla.columns:
        serie = tabla[id_producto].values.astype(float)
        nombre = mejor_modelo.get(id_producto, "Naive estacional")
        try:
            pred = MODELOS[nombre](serie, MESES_FUTURO)
        except Exception:
            nombre = "Naive estacional"
            pred = modelo_naive(serie, MESES_FUTURO)

        pred = np.clip(pred, 0, None).round()
        for mes, valor in zip(meses, pred):
            filas.append((id_producto, mes, int(valor), nombre))

    return pd.DataFrame(filas, columns=["id_producto", "mes", "unidades_pronosticadas", "modelo"])


# ============================================================
# PASO 4: Gráficos
# ============================================================
def estilo_ejes(ax):
    ax.set_facecolor(FONDO)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRILLA)
    ax.spines["bottom"].set_color(GRILLA)
    ax.grid(axis="y", color=GRILLA, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=TEXTO_SUAVE)


def titulo(ax, texto, subtexto):
    ax.set_title(texto, loc="left", fontsize=13, fontweight="bold", color=TEXTO, pad=22)
    ax.text(0, 1.03, subtexto, transform=ax.transAxes, fontsize=9, color=TEXTO_SUAVE)


def guardar(fig, nombre):
    carpeta = CARPETA_DOCS / "graficos"
    carpeta.mkdir(parents=True, exist_ok=True)
    fig.savefig(carpeta / nombre, dpi=150, bbox_inches="tight", facecolor=FONDO)
    plt.close(fig)
    print("Gráfico guardado:", carpeta / nombre)


def grafico_pronostico(tabla, pronostico):
    historico = tabla.sum(axis=1)
    futuro = pronostico.groupby("mes")["unidades_pronosticadas"].sum()

    # unimos el último mes real con el pronóstico para que la línea no quede cortada
    futuro = pd.concat([historico.iloc[[-1]], futuro])

    fig, ax = plt.subplots(figsize=(10, 4.8), facecolor=FONDO)
    ax.plot(historico.index, historico.values, color=AZUL, linewidth=2, label="Histórico")
    ax.plot(futuro.index, futuro.values, color=NARANJA, linewidth=2, linestyle="--", label="Pronóstico")
    estilo_ejes(ax)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.set_ylabel("Unidades por mes", color=TEXTO_SUAVE)
    ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    titulo(ax, "Pronóstico de ventas totales", "Próximos 6 meses, suma de todos los productos")
    guardar(fig, "05_pronostico_total.png")


def grafico_errores(promedios):
    fig, ax = plt.subplots(figsize=(8, 4.5), facecolor=FONDO)
    barras = ax.bar(promedios.index, promedios["mape"], color=AZUL, width=0.45)
    estilo_ejes(ax)
    ax.set_ylabel("Error promedio (MAPE, %)", color=TEXTO_SUAVE)
    for barra in barras:
        ax.text(barra.get_x() + barra.get_width() / 2, barra.get_height(),
                f"{barra.get_height():.1f}%", ha="center", va="bottom", fontsize=10, color=TEXTO)
    ax.set_ylim(0, promedios["mape"].max() * 1.15)
    titulo(ax, "Error de cada modelo", "Menor es mejor. Evaluado con los últimos 6 meses")
    guardar(fig, "06_error_por_modelo.png")


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================
if __name__ == "__main__":
    motor = crear_motor()

    print("Leyendo ventas mensuales...")
    tabla = leer_datos(motor)
    print("Productos:", tabla.shape[1], "| Meses:", tabla.shape[0])

    print("\nEvaluando modelos (puede tardar un par de minutos)...")
    resultados = evaluar_modelos(tabla)

    promedios = resultados.groupby("modelo")[["mape", "rmse", "mae"]].mean().round(2)
    print("\n--- Error promedio por modelo ---")
    print(promedios)

    # el mejor modelo de cada producto es el que tiene menor MAPE
    validos = resultados.dropna(subset=["mape"])
    ganadores = validos.loc[validos.groupby("id_producto")["mape"].idxmin()]
    mejor_modelo = dict(zip(ganadores["id_producto"], ganadores["modelo"]))
    print("\n--- Productos en los que ganó cada modelo ---")
    print(ganadores["modelo"].value_counts())

    CARPETA_DOCS.mkdir(parents=True, exist_ok=True)
    resultados.round(2).to_csv(CARPETA_DOCS / "resultados_modelos.csv", index=False)

    print("\nPronosticando los próximos", MESES_FUTURO, "meses...")
    pronostico = pronosticar_futuro(tabla, mejor_modelo)

    grafico_pronostico(tabla, pronostico)
    grafico_errores(promedios)

    # guardamos el pronóstico en SQL Server (reemplaza la tabla si ya existía)
    pronostico["mes"] = pronostico["mes"].dt.date
    pronostico.to_sql("Pronostico_Ventas", motor, if_exists="replace", index=False)
    print("\nTabla Pronostico_Ventas guardada en SQL Server:", len(pronostico), "filas")
