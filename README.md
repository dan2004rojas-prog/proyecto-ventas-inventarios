# 📊 Sistema de Análisis de Ventas, Pronóstico y Optimización de Inventarios

## 📌 Descripción del proyecto

Este proyecto desarrolla una solución de análisis de datos para gestionar y analizar las ventas y el inventario de una empresa comercial.

Mediante SQL Server y Python, se procesan datos de ventas, productos, proveedores e inventario para obtener información útil para la toma de decisiones.

El proyecto incluye análisis exploratorio, consultas SQL, visualización de datos, modelos de pronóstico de ventas y recomendaciones para optimizar el inventario.

## 🎯 Objetivos

* Analizar el comportamiento histórico de las ventas.
* Identificar patrones de ventas por producto, categoría y período.
* Explorar tendencias y estacionalidad en las series temporales.
* Construir modelos para pronosticar las ventas de los próximos meses.
* Evaluar y comparar el rendimiento de los modelos.
* Identificar productos que requieren reposición de inventario.
* Generar recomendaciones para apoyar la planificación de compras.

## 🛠️ Tecnologías utilizadas

* **Python:** procesamiento de datos, análisis y modelos de pronóstico.
* **SQL Server:** almacenamiento, consultas y transformación de datos.
* **SQL:** creación de tablas, consultas analíticas y vistas.
* **Pandas y NumPy:** manipulación y análisis de datos.
* **Matplotlib:** generación de gráficos.
* **Git y GitHub:** control de versiones y publicación del proyecto.

## 📁 Estructura del proyecto

```text
proyecto-ventas-inventarios/
│
├── data/
│   ├── inventario.csv
│   ├── productos.csv
│   ├── proveedores.csv
│   └── ventas.csv
│
├── docs/
│   ├── graficos/
│   │   ├── 01_ventas_totales.png
│   │   ├── 02_ventas_por_categoria.png
│   │   ├── 03_descomposicion_total.png
│   │   ├── 04_estacionalidad_categoria.png
│   │   ├── 05_pronostico_total.png
│   │   └── 06_error_por_modelo.png
│   │
│   ├── resultados_modelos.csv
│   └── recomendaciones_inventario.csv
│
├── python/
│   ├── 01_generar_y_cargar_datos.py
│   ├── 03_explorar_series.py
│   ├── 04_modelos_y_pronostico.py
│   ├── 05_optimizacion_inventario.py
│   └── conexion.py
│
├── sql/
│   ├── 01_crear_base.sql
│   ├── 02_tablas.sql
│   └── 03_consultas_y_vistas.sql
│
├── Dashboard_Ventas_Inventario.pbix
│
├── esquema_guide.pdf
│
└── README.md
```

## 🗄️ Base de datos

El proyecto utiliza SQL Server con una base de datos llamada `VentasInventario`.

Las principales entidades son:

* **Productos:** información de productos, categorías, costos y precios.
* **Proveedores:** información de proveedores y tiempos de entrega.
* **Ventas:** registros históricos de ventas, cantidades y montos.
* **Inventario:** existencias disponibles y niveles mínimos de stock.

También se utilizan vistas para consultar las ventas mensuales y el estado actual del inventario.

## 📈 Análisis de datos

El análisis contempla:

* Ventas totales y evolución temporal.
* Comparación de ventas por categoría.
* Descomposición de series temporales.
* Identificación de patrones estacionales.
* Comparación de modelos de pronóstico mediante métricas de error.

Los gráficos y los resultados de los modelos se guardan en la carpeta `docs/`.

## 🔮 Pronóstico de ventas

El módulo `04_modelos_y_pronostico.py` construye pronósticos de ventas para los próximos seis meses y almacena los resultados en la tabla `Pronostico_Ventas` de SQL Server.

Estos resultados permiten explorar la demanda futura y utilizarlos como referencia para la planificación del inventario.

## 📦 Optimización del inventario

El módulo `05_optimizacion_inventario.py` utiliza información del inventario actual, el historial de ventas y los pronósticos para calcular indicadores y generar recomendaciones.

Entre los resultados se incluyen:

* Demanda diaria estimada.
* Stock de seguridad.
* Punto de reorden.
* Nivel de inventario objetivo.
* Días estimados de cobertura.
* Cantidades sugeridas de reposición.
* Alertas sobre posibles quiebres de stock, niveles bajos y sobrestock.

Las recomendaciones se exportan a `docs/recomendaciones_inventario.csv` y se almacenan en la tabla `Recomendacion_Inventario` de SQL Server.

**Nota:** las recomendaciones son estimaciones analíticas y deben validarse con las condiciones reales de compra, disponibilidad y demanda.

## ⚙️ Instalación y configuración

### 1. Requisitos previos

* Python instalado.
* SQL Server y SQL Server Management Studio (SSMS).
* Controlador ODBC compatible con SQL Server.
* Git instalado.
* Acceso a la base de datos utilizada por el proyecto.

### 2. Clonar el repositorio

```bash
git clone https://github.com/dan2004rojas-prog/proyecto-ventas-inventarios.git
cd proyecto-ventas-inventarios
```

### 3. Crear un entorno virtual

```bash
python -m venv .venv
```

Activarlo en Git Bash:

```bash
source .venv/Scripts/activate
```

### 4. Instalar las dependencias

Instala las bibliotecas que utilizan los scripts del proyecto. Como punto de partida:

```bash
python -m pip install pandas numpy matplotlib sqlalchemy pyodbc statsmodels scikit-learn
```

### 5. Configurar la conexión a SQL Server

Revisa `python/conexion.py` y configura el servidor, el nombre de la base de datos, el controlador ODBC y el método de autenticación según tu entorno.

No publiques contraseñas, tokens ni otros datos de acceso en GitHub.

## ▶️ Ejecución del proyecto

Desde la raíz del repositorio, ejecuta los scripts según las dependencias del proyecto:

```bash
python sql/01_crear_base.sql
```

El comando anterior es únicamente una referencia del archivo SQL: los scripts `.sql` deben ejecutarse en SQL Server Management Studio o mediante una herramienta compatible, no directamente con Python.

Después de preparar la base de datos y las tablas, ejecuta en el orden correspondiente:

```bash
python python/01_generar_y_cargar_datos.py
python python/03_explorar_series.py
python python/04_modelos_y_pronostico.py
python python/05_optimizacion_inventario.py
```

**Importante:** `01_generar_y_cargar_datos.py` elimina los datos existentes de las tablas del proyecto antes de volver a cargarlos. Ejecútalo únicamente cuando quieras regenerar los datos y hayas considerado las consecuencias.

## 📊 Resultados generados

Los principales resultados se encuentran en `docs/`:

| Archivo                           | Descripción                                 |
| --------------------------------- | ------------------------------------------- |
| `resultados_modelos.csv`          | Resultados de evaluación de los modelos     |
| `recomendaciones_inventario.csv`  | Indicadores y recomendaciones de inventario |
| `01_ventas_totales.png`           | Evolución de las ventas                     |
| `02_ventas_por_categoria.png`     | Comparación por categoría                   |
| `03_descomposicion_total.png`     | Componentes de la serie temporal            |
| `04_estacionalidad_categoria.png` | Patrones estacionales                       |
| `05_pronostico_total.png`         | Visualización del pronóstico                |
| `06_error_por_modelo.png`         | Comparación de errores                      |

## Dashboard de Power BI

Se desarrolló un dashboard interactivo para analizar las ventas y controlar el inventario, utilizando Power BI Desktop y SQL Server como fuente de datos.

### Análisis de ventas

* Evolución mensual de las ventas.
* Ventas totales por categoría.
* Indicadores de ventas totales y unidades vendidas.

### Control de inventario

* Tabla de productos con categoría, stock actual, stock mínimo, días de cobertura y estado.
* Indicadores de productos en quiebre, bajo mínimo, con stock normal y en exceso.
* Gráfico de barras para comparar los productos por estado de inventario.
* Formato condicional para identificar visualmente los estados del inventario.

### Herramientas utilizadas

* SQL Server: almacenamiento y consulta de datos.
* Power BI Desktop: visualización y análisis.
* Git y GitHub: control de versiones del proyecto.


## 💡 Aplicaciones del proyecto

Esta solución puede servir como apoyo para:

* La planificación de compras.
* La identificación de productos que necesitan reposición.
* El seguimiento de tendencias de ventas.
* La reducción del riesgo de quiebres de stock.
* La toma de decisiones basada en datos.

## 👨‍💻 Autor

**Jesus Daniel Rojas Garcia**

Proyecto de análisis de ventas, pronóstico y optimización de inventarios desarrollado con Python y SQL Server.

## 📄 Licencia

Este proyecto se publica con fines educativos y de demostración. Si deseas permitir su reutilización por terceros, considera agregar una licencia de código abierto.
