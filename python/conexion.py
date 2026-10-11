import os
import urllib.parse
from pathlib import Path

import pyodbc
from dotenv import load_dotenv
from sqlalchemy import create_engine


_RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(_RAIZ / ".env")

SERVIDOR   = os.getenv("DB_SERVIDOR", "localhost")
BASE_DATOS = os.getenv("DB_BASE_DATOS", "VentasInventario")
DB_AUTH    = os.getenv("DB_AUTH", "windows").lower()
DB_USUARIO = os.getenv("DB_USUARIO", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")


def buscar_driver():
  
    drivers = [d for d in pyodbc.drivers() if d.startswith("ODBC Driver") and "SQL Server" in d]
    if not drivers:
        print("Drivers detectados:", pyodbc.drivers())
        raise SystemExit(
            "No se encontró un driver ODBC compatible. "
            "Instala 'ODBC Driver 18 for SQL Server' desde la página de Microsoft."
        )
    return sorted(drivers)[-1]


def crear_motor():
  
    driver = buscar_driver()

    if DB_AUTH == "windows":
        cadena = (
            f"DRIVER={{{driver}}};"
            f"SERVER={SERVIDOR};"
            f"DATABASE={BASE_DATOS};"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
        )
    elif DB_AUTH == "sql":
        if not DB_USUARIO or not DB_PASSWORD:
            raise SystemExit(
                "DB_AUTH=sql requiere que DB_USUARIO y DB_PASSWORD estén definidos en .env"
            )
        cadena = (
            f"DRIVER={{{driver}}};"
            f"SERVER={SERVIDOR};"
            f"DATABASE={BASE_DATOS};"
            f"UID={DB_USUARIO};"
            f"PWD={DB_PASSWORD};"
            "TrustServerCertificate=yes;"
        )
    else:
        raise SystemExit(f"DB_AUTH='{DB_AUTH}' no reconocido. Usa 'windows' o 'sql'.")

    url = "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(cadena)
    return create_engine(url, fast_executemany=True)
