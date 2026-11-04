from pathlib import Path

import pandas as pd
import requests

URL = "https://api.covidtracking.com/v1/states/daily.json"

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "raw" / "covid_us_states_daily.csv"


def download_dataset():
    print("Conectando con la API...")

    response = requests.get(URL, timeout=120)
    response.raise_for_status()

    data = response.json()

    if not data:
        raise ValueError("La API no devolvio registros.")

    df = pd.DataFrame(data)

    required_columns = {"date", "state", "positive", "death"}

    missing = required_columns.difference(df.columns)

    if missing:
        raise ValueError(f"Faltan columnas obligatorias: {missing}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT, index=False, encoding="utf-8")

    dates = pd.to_datetime(
        df["date"].astype(str),
        format="%Y%m%d",
        errors="coerce"
    )

    print("\nDESCARGA COMPLETADA")
    print(f"Registros: {df.shape[0]:,}")
    print(f"Columnas: {df.shape[1]}")
    print(f"Fecha inicial: {dates.min()}")
    print(f"Fecha final: {dates.max()}")
    print(f"Archivo: {OUTPUT}")
    print("\nPrimeros registros:")
    print(df.head())


if __name__ == "__main__":
    download_dataset()
