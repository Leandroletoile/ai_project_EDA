"""Feature engineering y funciones de análisis sobre el dataset ya limpio."""
from __future__ import annotations

import numpy as np
import pandas as pd

POP_GROUP_LABELS = ["Pequeño", "Mediano", "Grande", "Muy grande"]


def per_100k(values, population):
    """Normaliza por cada 100.000 habitantes (permite comparar estados de distinto tamaño)."""
    return values / population * 100_000


def add_population(df: pd.DataFrame, pop: pd.DataFrame) -> pd.DataFrame:
    """Une la población (2ª fuente). Left join: los territorios quedan con población NaN."""
    pop = pop.rename(columns={"name": "state_name"})
    cols = [c for c in ["state", "state_name", "population"] if c in pop.columns]
    return df.merge(pop[cols], on="state", how="left", validate="many_to_one")


def rolling_by_state(df: pd.DataFrame, col: str, window: int = 7, how: str = "mean") -> pd.Series:
    """Media (o suma) móvil dentro de cada estado, sin mezclar estados.

    Exige ventana completa: los primeros `window-1` días de cada estado son NaN.
    Devuelve una Serie alineada con el índice de `df`.
    """
    ordered = df.sort_values(["state", "date"])
    grouped = ordered.groupby("state")[col]
    roll = grouped.transform(lambda s: getattr(s.rolling(window, min_periods=window), how)())
    return roll.reindex(df.index)


def assign_period(dates: pd.Series) -> pd.Series:
    """Etiqueta cada fecha con un periodo de la pandemia (aproximación por estaciones)."""
    d = pd.to_datetime(dates)
    labels = np.select(
        [d < "2020-03-01", d < "2020-06-01", d < "2020-10-01"],
        ["Pre-brote", "Primavera 2020", "Verano 2020"],
        default="Invierno 2020-21",
    )
    return pd.Series(labels, index=dates.index)


def case_fatality_rate(deaths: pd.Series, cases: pd.Series) -> pd.Series:
    """Letalidad aparente (%): muertes / casos confirmados. NaN si aún no hay casos."""
    return deaths / cases.where(cases > 0) * 100


def positivity_7d(df: pd.DataFrame, cap: bool = True) -> pd.Series:
    """Positividad (%) = casos nuevos / pruebas nuevas, sumados en 7 días (suaviza el día de la semana).

    Un valor por encima de 100 % es imposible (más positivos que pruebas): con `cap=True`
    se convierte en NaN; con `cap=False` se devuelve tal cual para poder contarlos.
    """
    cases = rolling_by_state(df, "new_cases", 7, "sum")
    tests = rolling_by_state(df, "new_tests", 7, "sum")
    ratio = cases / tests.where(tests > 0) * 100
    return ratio.where(ratio <= 100) if cap else ratio


def iqr_outliers(s: pd.Series, k: float = 1.5) -> pd.Series:
    """Máscara booleana de valores atípicos según la regla del rango intercuartílico (IQR).

    Atípico = por debajo de Q1 - k*IQR o por encima de Q3 + k*IQR. Los NaN nunca se marcan.
    """
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    return (s < q1 - k * iqr) | (s > q3 + k * iqr)


def population_group(pop: pd.DataFrame) -> pd.Series:
    """Cuartiles de población -> Pequeño / Mediano / Grande / Muy grande."""
    ranks = pop["population"].rank(method="first")
    if len(ranks) < 4:
        # con menos de 4 estados no hay cuartiles: se reparte por posición relativa
        idx = np.ceil(ranks / len(ranks) * 4).astype(int) - 1
        return idx.map(dict(enumerate(POP_GROUP_LABELS)))
    return pd.qcut(ranks, 4, labels=POP_GROUP_LABELS).astype(str)


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Crea las variables nuevas del análisis. Requiere haber unido la población antes."""
    out = df.sort_values(["state", "date"]).reset_index(drop=True)

    # partes de la fecha
    out["year_month"] = out["date"].dt.to_period("M").astype(str)
    out["week"] = out["date"].dt.isocalendar().week.astype(int)
    out["weekday"] = out["date"].dt.day_name()
    out["period"] = assign_period(out["date"])

    # ratios y medias móviles
    out["cfr"] = case_fatality_rate(out["deaths_cum"], out["cases_cum"])
    out["new_cases_7d"] = rolling_by_state(out, "new_cases", 7)
    out["new_deaths_7d"] = rolling_by_state(out, "new_deaths", 7)
    out["positivity_7d"] = positivity_7d(out)

    # normalización por población
    out["cases_per_100k"] = per_100k(out["cases_cum"], out["population"])
    out["deaths_per_100k"] = per_100k(out["deaths_cum"], out["population"])
    out["new_cases_per_100k_7d"] = per_100k(out["new_cases_7d"], out["population"])
    out["new_deaths_per_100k_7d"] = per_100k(out["new_deaths_7d"], out["population"])

    # grupo por tamaño de población
    pops = out.drop_duplicates("state")[["state", "population"]].dropna()
    groups = dict(zip(pops["state"], population_group(pops)))
    out["pop_group"] = out["state"].map(groups)
    return out


def state_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por estado: situación al último día + pico de casos (media 7 días)."""
    ordered = df.sort_values(["state", "date"])
    last = ordered.groupby("state").tail(1).reset_index(drop=True)
    peaks = (
        ordered.dropna(subset=["new_cases_7d"])
        .loc[lambda x: x.groupby("state")["new_cases_7d"].idxmax()]
        [["state", "date", "new_cases_7d"]]
        .rename(columns={"date": "peak_date", "new_cases_7d": "peak_new_cases_7d"})
    )
    return last.merge(peaks, on="state", how="left")


def national_daily(df: pd.DataFrame, only_states: bool = True) -> pd.DataFrame:
    """Serie diaria nacional (suma de estados). Por defecto excluye territorios."""
    base = df.loc[~df["is_territory"]] if only_states and "is_territory" in df else df
    nat = base.groupby("date")[["new_cases", "new_deaths", "new_tests"]].sum()
    nat["new_cases_7d"] = nat["new_cases"].rolling(7, min_periods=7).mean()
    nat["new_deaths_7d"] = nat["new_deaths"].rolling(7, min_periods=7).mean()
    return nat.reset_index()
