"""Limpieza reutilizable del dataset COVID Tracking Project (states/daily).

Cada función hace UNA cosa y devuelve una copia (no modifica el DataFrame de
entrada). `clean_pipeline` las encadena y devuelve además un informe con lo que
se hizo, que alimenta el informe de calidad de datos.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

# ------------------------------------------------------------------ constantes
REASON_CONSTANT = "Vacía o con un único valor: no aporta información"
REASON_METADATA = "Metadato técnico de publicación (no describe la pandemia)"
REASON_REDUNDANT = "Redundante: duplica o está obsoleta frente a otra columna"
REASON_MISSING = "Más de 80 % de valores faltantes: no es analizable"

METADATA_COLUMNS = ["hash", "lastUpdateEt", "dateModified", "checkTimeEt", "dateChecked"]
# `hospitalized` es idéntica a `hospitalizedCumulative` (comprobado: 100 % iguales);
# `total` y `posNeg` son columnas obsoletas de la fuente (positive + negative).
REDUNDANT_COLUMNS = ["hospitalized", "total", "posNeg"]

# Columnas que nunca se eliminan automáticamente (claves y variables centrales).
PROTECTED_COLUMNS = {
    "date", "state", "fips",
    "positive", "death", "totalTestResults", "negative", "recovered",
    "hospitalizedCurrently", "inIcuCurrently", "onVentilatorCurrently",
    "hospitalizedCumulative",
    "positiveIncrease", "deathIncrease", "totalTestResultsIncrease",
    "hospitalizedIncrease", "negativeIncrease",
}

RENAME_MAP = {
    "positive": "cases_cum",
    "death": "deaths_cum",
    "totalTestResults": "tests_cum",
    "negative": "negative_cum",
    "recovered": "recovered_cum",
    "hospitalizedCurrently": "hosp_now",
    "inIcuCurrently": "icu_now",
    "onVentilatorCurrently": "vent_now",
    "hospitalizedCumulative": "hosp_cum",
    "positiveIncrease": "new_cases",
    "deathIncrease": "new_deaths",
    "totalTestResultsIncrease": "new_tests",
    "hospitalizedIncrease": "new_hosp",
    "negativeIncrease": "new_negative",
    "totalTestResultsSource": "tests_source",
}

INCREMENT_COLUMNS = ["new_cases", "new_deaths", "new_tests", "new_hosp"]
CUMULATIVE_COLUMNS = ["cases_cum", "deaths_cum", "tests_cum"]
ZERO_FILL_COLUMNS = ["cases_cum", "deaths_cum"]

TERRITORIES = {"AS", "GU", "MP", "PR", "VI"}


# ------------------------------------------------------------------------ carga
def load_raw(path: str | Path) -> pd.DataFrame:
    """Lee el CSV original tal cual viene de la API."""
    return pd.read_csv(path)


# ----------------------------------------------------------------------- fechas
def parse_dates(df: pd.DataFrame, col: str = "date") -> pd.DataFrame:
    """Convierte la fecha de entero YYYYMMDD (p. ej. 20210307) a datetime.

    Lanza ValueError si hay alguna fecha imposible (en vez de ocultarla).
    """
    out = df.copy()
    if pd.api.types.is_datetime64_any_dtype(out[col]):
        return out
    out[col] = pd.to_datetime(out[col].astype(str), format="%Y%m%d", errors="raise")
    return out


# ------------------------------------------------------------------- duplicados
def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Quita filas idénticas y, si queda más de una por (estado, fecha), se queda con la última.

    Una fila por estado y día es la unidad de análisis; la última publicada
    es la versión más reciente de ese dato.
    """
    out = df.drop_duplicates()
    out = out.drop_duplicates(subset=["state", "date"], keep="last")
    return out.reset_index(drop=True)


# --------------------------------------------------------------------- columnas
def columns_to_drop(df: pd.DataFrame, missing_threshold: float = 0.8) -> dict[str, str]:
    """Devuelve {columna: motivo} de las columnas que no merece la pena conservar."""
    reasons: dict[str, str] = {}
    for col in df.columns:
        if col in PROTECTED_COLUMNS:
            continue
        if col in METADATA_COLUMNS:
            reasons[col] = REASON_METADATA
        elif col in REDUNDANT_COLUMNS:
            reasons[col] = REASON_REDUNDANT
        elif df[col].nunique(dropna=True) <= 1:
            reasons[col] = REASON_CONSTANT
        elif df[col].isna().mean() > missing_threshold:
            reasons[col] = REASON_MISSING
    return reasons


def drop_useless_columns(df: pd.DataFrame, missing_threshold: float = 0.8) -> pd.DataFrame:
    """Elimina las columnas detectadas por `columns_to_drop`."""
    return df.drop(columns=list(columns_to_drop(df, missing_threshold)))


def _snake_case(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Nombres explícitos para las variables centrales y snake_case para el resto."""
    new_names = {c: RENAME_MAP.get(c, _snake_case(c)) for c in df.columns}
    return df.rename(columns=new_names)


# ------------------------------------------------------------------------ nulos
def fill_cumulative_gaps(
    df: pd.DataFrame,
    cols: list[str] | tuple[str, ...] = tuple(CUMULATIVE_COLUMNS),
    zero_fill: list[str] | tuple[str, ...] = tuple(ZERO_FILL_COLUMNS),
) -> pd.DataFrame:
    """Rellena huecos en columnas ACUMULADAS, siempre dentro de cada estado.

    * Hueco intermedio -> último valor conocido (un acumulado no baja ni se
      inventa: si hoy no se reportó, lo más honesto es mantener el anterior).
    * Hueco inicial (antes del primer reporte) -> 0 solo en casos y muertes:
      el estado aún no tenía casos/muertes registrados.
    No se tocan los ingresos "actuales" (hosp_now, icu_now...): ahí un hueco
    significa "no reportado", no "cero".
    """
    out = df.sort_values(["state", "date"]).copy()
    cols = [c for c in cols if c in out.columns]
    out[cols] = out.groupby("state")[cols].ffill()
    for col in zero_fill:
        if col in out.columns:
            out[col] = out[col].fillna(0.0)
    return out.reset_index(drop=True)


# ---------------------------------------------------------------- correcciones
def fix_negative_increments(
    df: pd.DataFrame, cols: list[str] | tuple[str, ...] = tuple(INCREMENT_COLUMNS)
) -> pd.DataFrame:
    """Los incrementos diarios negativos son correcciones de los estados.

    Un día no puede tener "-200 muertes". Se marcan en `correction_flag` y se
    dejan en 0 para no distorsionar medias, gráficos ni sumas.
    """
    out = df.copy()
    cols = [c for c in cols if c in out.columns]
    out["correction_flag"] = (out[cols] < 0).any(axis=1)
    for col in cols:
        out[col] = out[col].clip(lower=0)
    return out


# --------------------------------------------------------------- inconsistencias
def flag_impossible_values(df: pd.DataFrame) -> pd.DataFrame:
    """Marca filas con valores lógicamente imposibles (no se borran, se marcan).

    * cases_gt_tests: más positivos acumulados que pruebas acumuladas.
    * deaths_gt_cases: más muertes que casos acumulados.
    Los NaN nunca se marcan (comparar con NaN da False).
    """
    out = df.copy()
    out["cases_gt_tests"] = out["cases_cum"] > out["tests_cum"]
    out["deaths_gt_cases"] = out["deaths_cum"] > out["cases_cum"]
    return out


def add_territory_flag(df: pd.DataFrame) -> pd.DataFrame:
    """Marca los 5 territorios (AS, GU, MP, PR, VI) para poder separarlos de los 50 estados + DC."""
    out = df.copy()
    out["is_territory"] = out["state"].isin(TERRITORIES)
    return out


# --------------------------------------------------------------------- pipeline
def clean_pipeline(raw: pd.DataFrame, missing_threshold: float = 0.8) -> tuple[pd.DataFrame, dict]:
    """Aplica toda la limpieza y devuelve (dataframe limpio, informe de lo hecho)."""
    report: dict = {"rows_in": len(raw), "columns_in": raw.shape[1]}

    df = parse_dates(raw)
    df = remove_duplicates(df)
    report["duplicates_removed"] = report["rows_in"] - len(df)

    dropped = columns_to_drop(df, missing_threshold)
    report["columns_dropped"] = dropped
    df = df.drop(columns=list(dropped))
    df = rename_columns(df)

    cols = [c for c in CUMULATIVE_COLUMNS if c in df.columns]
    before = df[cols].isna().sum()
    df = fill_cumulative_gaps(df)
    after = df[cols].isna().sum()
    report["nulls_filled"] = {c: int(before[c] - after[c]) for c in cols}
    report["nulls_left"] = {c: int(after[c]) for c in cols}

    inc = [c for c in INCREMENT_COLUMNS if c in df.columns]
    report["negative_increments_fixed"] = {c: int((df[c] < 0).sum()) for c in inc}
    df = fix_negative_increments(df)
    report["rows_with_correction"] = int(df["correction_flag"].sum())

    df = flag_impossible_values(df)
    report["cases_gt_tests_rows"] = int(df["cases_gt_tests"].sum())
    report["deaths_gt_cases_rows"] = int(df["deaths_gt_cases"].sum())

    df = add_territory_flag(df)
    df = df.sort_values(["state", "date"]).reset_index(drop=True)

    report["rows_out"] = len(df)
    report["columns_out"] = df.shape[1]
    report["date_min"] = str(df["date"].min().date())
    report["date_max"] = str(df["date"].max().date())
    report["n_states"] = int(df["state"].nunique())
    return df, report
