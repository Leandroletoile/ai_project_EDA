"""Lógica de datos del dashboard (sin Streamlit, para poder probarla con pytest).

`app.py` solo dibuja; todo lo que filtra o calcula vive aquí.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.build_features import POP_GROUP_LABELS

SIZE_ORDER = list(POP_GROUP_LABELS)

# Etiqueta que ve el usuario -> columna del dataset procesado
METRICS = {
    "Casos nuevos por 100.000 hab. (media 7 días)": "new_cases_per_100k_7d",
    "Muertes nuevas por 100.000 hab. (media 7 días)": "new_deaths_per_100k_7d",
    "Casos nuevos (media 7 días)": "new_cases_7d",
    "Muertes nuevas (media 7 días)": "new_deaths_7d",
    "Positividad de las pruebas, % (7 días)": "positivity_7d",
    "Casos acumulados por 100.000 hab.": "cases_per_100k",
    "Muertes acumuladas por 100.000 hab.": "deaths_per_100k",
    "Letalidad aparente, %": "cfr",
}


def first_existing(paths) -> Path | None:
    """Primera ruta de la lista que existe, o None. Sirve para usar el CSV local o la copia comprimida."""
    for p in paths:
        if Path(p).exists():
            return Path(p)
    return None


def load_processed(path) -> pd.DataFrame:
    """Lee el CSV procesado (data/processed/covid_clean.csv) con la fecha ya como fecha."""
    return pd.read_csv(path, parse_dates=["date"])


def load_quality_report(path) -> dict | None:
    """Lee el informe de calidad en JSON; devuelve None si todavía no se ha generado."""
    path = Path(path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def states_with_population(df: pd.DataFrame) -> list[str]:
    """Códigos de los estados que tienen población (50 estados + DC), ordenados."""
    return sorted(df.loc[df["population"].notna(), "state"].unique())


def filter_data(df, states=None, start=None, end=None, sizes=None, include_territories=False) -> pd.DataFrame:
    """Filtra por estados, rango de fechas y tamaño de estado.

    Una lista vacía o None en `states` / `sizes` significa «sin filtro».
    Los territorios se excluyen salvo que se pida lo contrario.
    """
    out = df
    if not include_territories and "is_territory" in out:
        out = out[~out["is_territory"]]
    if states:
        out = out[out["state"].isin(states)]
    if sizes:
        out = out[out["pop_group"].isin(sizes)]
    if start is not None:
        out = out[out["date"] >= pd.Timestamp(start)]
    if end is not None:
        out = out[out["date"] <= pd.Timestamp(end)]
    return out.copy()


def snapshot(df: pd.DataFrame, metric: str, as_of=None) -> pd.DataFrame:
    """Una fila por estado con el último valor de `metric` hasta la fecha `as_of`.

    Quita los estados sin dato y ordena de mayor a menor.
    """
    base = df if as_of is None else df[df["date"] <= pd.Timestamp(as_of)]
    last = base.sort_values("date").groupby("state").tail(1)
    cols = [c for c in ["state", "state_name", "date", "population", metric] if c in last.columns]
    return last[cols].dropna(subset=[metric]).sort_values(metric, ascending=False).reset_index(drop=True)


def kpis(df: pd.DataFrame) -> dict:
    """Cifras de cabecera: acumulados al último día de cada estado seleccionado y letalidad aparente."""
    if df.empty:
        return {"cases": 0, "deaths": 0, "cfr": float("nan"), "n_states": 0, "last_date": pd.NaT}
    last = df.sort_values("date").groupby("state").tail(1)
    cases, deaths = float(last["cases_cum"].sum()), float(last["deaths_cum"].sum())
    return {
        "cases": cases,
        "deaths": deaths,
        "cfr": deaths / cases * 100 if cases > 0 else float("nan"),
        "n_states": int(last["state"].nunique()),
        "last_date": df["date"].max(),
    }
