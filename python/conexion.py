

import urllib.parse

import pyodbc
from sqlalchemy import create_engine

SERVIDOR = "DanServer"              # nombre de tu servidor SQL Server
BASE_DATOS = "VentasInventario"     # nombre de tu base de datos


def buscar_driver():
    # Busca el driver ODBC moderno instalado en tu PC (el más nuevo)
    drivers = [d for d in pyodbc.drivers() if d.startswith("ODBC Driver") and "SQL Server" in d]
    if len(drivers) == 0:
        print("Drivers que tienes instalados:", pyodbc.drivers())
        raise SystemExit("Falta instalar 'ODBC Driver 18 for SQL Server'.")
    return sorted(drivers)[-1]


def crear_motor():
    # Crea la conexión con tu usuario de Windows (Trusted_Connection)
    conexion = (
        f"DRIVER={{{buscar_driver()}}};"
        f"SERVER={SERVIDOR};"
        f"DATABASE={BASE_DATOS};"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )
    url = "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(conexion)
    return create_engine(url, fast_executemany=True)
