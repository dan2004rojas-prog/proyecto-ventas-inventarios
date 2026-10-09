

from pathlib import Path

import matplotlib
matplotlib.use("Agg")                 
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller

from conexion import crear_motor


# CONFIGURACIÓN

CARPETA_GRAFICOS = Path(__file__).resolve().parent.parent / "docs" / "graficos"

FONDO = "#fcfcfb"


COLORES = {
    "Granos": "#2a78d6",         
    "Café y Cacao": "#eb6834",   
    "Frutas": "#1baf7a",         
    "Insumos": "#eda100",        
}
COLOR_TOTAL = "#2a78d6"          
TEXTO = "#0b0b0b"
TEXTO_SUAVE = "#52514e"
GRILLA = "#e6e5e1"
FONDO = "#fcfcfb"
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


# FUNCIONES PARA LOS GRÁFICOS
def preparar_estilo():
    
    plt.rcParams.update({
        "figure.facecolor": FONDO,
        "axes.facecolor": FONDO,
        "savefig.facecolor": FONDO,
        "text.color": TEXTO,
        "axes.labelcolor": TEXTO_SUAVE,
        "xtick.color": TEXTO_SUAVE,
        "ytick.color": TEXTO_SUAVE,
        "axes.edgecolor": GRILLA,
        "font.size": 10,
        "lines.linewidth": 2,
    })


def limpiar_ejes(ax):
    
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color=GRILLA, linewidth=0.8)
    ax.set_axisbelow(True)
    
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))


def eje_fechas(ax):
   
    def formato(x, _):
        fecha = mdates.num2date(x)
        return f"{MESES[fecha.month - 1]} {fecha.year}"
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
    ax.xaxis.set_major_formatter(FuncFormatter(formato))


def leyenda_abajo(ax, columnas=4):
    
    ax.legend(frameon=False, ncol=columnas, loc="upper center", bbox_to_anchor=(0.5, -0.12))


def titulo(ax, texto, subtexto=None):
    ax.set_title(texto, loc="left", fontsize=13, fontweight="bold", color=TEXTO, pad=22 if subtexto else 10)
    if subtexto:
        ax.text(0, 1.03, subtexto, transform=ax.transAxes, fontsize=9, color=TEXTO_SUAVE)


def guardar(fig, nombre):
    CARPETA_GRAFICOS.mkdir(parents=True, exist_ok=True)
    ruta = CARPETA_GRAFICOS / nombre
    fig.savefig(ruta, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Gráfico guardado:", ruta)


# PASO 1: Leer los datos desde SQL Server
def leer_datos():
    motor = crear_motor()
    df = pd.read_sql("SELECT * FROM vw_ventas_mensuales", motor)
    df["mes"] = pd.to_datetime(df["mes"])      
    return df


# PASO 2: Revisar que los datos estén completos
def revisar_datos(df):
    print("\n--- Revisión de los datos ---")
    print("Filas leídas      :", len(df))
    print("Productos         :", df["id_producto"].nunique())
    print("Primer mes        :", df["mes"].min().date())
    print("Último mes        :", df["mes"].max().date())

    meses_esperados = len(pd.date_range(df["mes"].min(), df["mes"].max(), freq="MS"))
    meses_por_producto = df.groupby("id_producto")["mes"].nunique()
    incompletos = meses_por_producto[meses_por_producto < meses_esperados]
    print("Meses esperados   :", meses_esperados)
    print("Productos con meses sin ventas:", len(incompletos))
    print("Valores nulos     :", int(df[["unidades", "ventas"]].isna().sum().sum()))


# PASO 3: Armar las series de tiempo
def armar_series(df):
    
    total = df.groupby("mes")["unidades"].sum()
    total = total.asfreq("MS", fill_value=0)      

    
    por_categoria = df.pivot_table(index="mes", columns="categoria", values="unidades", aggfunc="sum")
    por_categoria = por_categoria.asfreq("MS").fillna(0)
    por_categoria = por_categoria[[c for c in COLORES if c in por_categoria.columns]]   

    return total, por_categoria


# PASO 4: Los 4 gráficos
def grafico_total(total):
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(total.index, total.values, color=COLOR_TOTAL)
    limpiar_ejes(ax)
    eje_fechas(ax)
    ax.set_ylabel("Unidades vendidas por mes")
    titulo(ax, "Ventas totales por mes",
           "Todos los productos juntos, octubre 2023 a septiembre 2026")
    guardar(fig, "01_ventas_totales.png")


def grafico_por_categoria(por_categoria):
    fig, ax = plt.subplots(figsize=(10, 5))
    ultimo_mes = por_categoria.index[-1]

   
    posiciones = {c: por_categoria[c].iloc[-1] for c in por_categoria.columns}
    separacion = por_categoria.values.max() * 0.045
    ajustadas = {}
    anterior = None
    for categoria in sorted(posiciones, key=posiciones.get):
        y = posiciones[categoria]
        if anterior is not None and y - anterior < separacion:
            y = anterior + separacion
        ajustadas[categoria] = y
        anterior = y

    for categoria in por_categoria.columns:
        ax.plot(por_categoria.index, por_categoria[categoria],
                color=COLORES[categoria], label=categoria)
        ax.annotate(categoria, (ultimo_mes, ajustadas[categoria]),
                    xytext=(6, 0), textcoords="offset points", va="center",
                    fontsize=9, color=TEXTO_SUAVE)

    limpiar_ejes(ax)
    eje_fechas(ax)
    ax.set_ylabel("Unidades vendidas por mes")
    ax.set_xlim(por_categoria.index[0], ultimo_mes + pd.Timedelta(days=90))
    leyenda_abajo(ax)
    titulo(ax, "Ventas por categoría",
           "Cada categoría tiene su propio ritmo y su propia temporada alta")
    guardar(fig, "02_ventas_por_categoria.png")


def grafico_descomposicion(total):
    
    resultado = seasonal_decompose(total, model="additive", period=12)

    partes = [
        ("Serie observada", resultado.observed),
        ("Tendencia", resultado.trend),
        ("Estacionalidad", resultado.seasonal),
        ("Residuo", resultado.resid),
    ]
    fig, ejes = plt.subplots(4, 1, figsize=(10, 8), sharex=True)
    for ax, (nombre, serie) in zip(ejes, partes):
        ax.plot(serie.index, serie.values, color=COLOR_TOTAL, linewidth=1.8)
        limpiar_ejes(ax)
        eje_fechas(ax)
        ax.set_ylabel(nombre, fontsize=9)
    ejes[0].set_title("Descomposición de las ventas totales", loc="left",
                      fontsize=13, fontweight="bold", pad=10)
    guardar(fig, "03_descomposicion_total.png")


def grafico_estacionalidad(por_categoria):
    # Para cada mes del año: ¿cuánto se vende respecto al promedio?
    # 1.0 = promedio, 1.3 = 30% más que el promedio, 0.8 = 20% menos
    indice = por_categoria.groupby(por_categoria.index.month).mean() / por_categoria.mean()

    fig, ax = plt.subplots(figsize=(10, 4.8))
    for categoria in indice.columns:
        ax.plot(range(1, 13), indice[categoria], color=COLORES[categoria],
                marker="o", markersize=5, label=categoria)
    ax.axhline(1.0, color=TEXTO_SUAVE, linewidth=0.8, linestyle="--")
    limpiar_ejes(ax)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.1f}"))
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(MESES)
    ax.set_ylabel("Ventas vs. promedio (1.0 = promedio)")
    leyenda_abajo(ax)
    titulo(ax, "Estacionalidad por categoría",
           "Los meses con valores sobre 1.0 son temporada alta")
    guardar(fig, "04_estacionalidad_categoria.png")


# PASO 5: Prueba ADF (¿la serie es estacionaria?)
def prueba_adf(serie):
    # Devuelve el p-valor de la prueba.
    # p < 0.05  -> la serie es estacionaria (su promedio no cambia con el tiempo)
    # p >= 0.05 -> NO es estacionaria 
    # maxlag=4 porque nuestras series son cortas (36 meses)
    return adfuller(serie.dropna(), maxlag=4)[1]


def mostrar_adf(total, por_categoria):
    print("\n--- Prueba ADF (estacionariedad) ---")
    print("p < 0.05 = estacionaria | p >= 0.05 = NO estacionaria\n")
    print(f"{'Serie':<16}{'p original':>12}{'p diferenciada':>16}   Conclusión")

    series = {"Total": total}
    for categoria in por_categoria.columns:
        series[categoria] = por_categoria[categoria]

    for nombre, serie in series.items():
        p_original = prueba_adf(serie)
        p_diferenciada = prueba_adf(serie.diff())      
        if p_original < 0.05:
            conclusion = "ya es estacionaria"
        elif p_diferenciada < 0.05:
            conclusion = "se vuelve estacionaria al diferenciar (d = 1)"
        else:
            conclusion = "sigue sin ser estacionaria"
        print(f"{nombre:<16}{p_original:>12.3f}{p_diferenciada:>16.3f}   {conclusion}")


# PROGRAMA PRINCIPAL
if __name__ == "__main__":
    preparar_estilo()

    print("Leyendo datos de SQL Server...")
    df = leer_datos()
    revisar_datos(df)

    total, por_categoria = armar_series(df)

    print("\nCreando gráficos...")
    grafico_total(total)
    grafico_por_categoria(por_categoria)
    grafico_descomposicion(total)
    grafico_estacionalidad(por_categoria)

    mostrar_adf(total, por_categoria)
    print("\nListo. Revisa los gráficos en la carpeta docs/graficos/")
