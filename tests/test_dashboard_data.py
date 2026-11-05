"""Tests de la lógica de datos del dashboard (src/dashboard_data.py).

La interfaz (app.py) es una capa fina; todo lo que filtra o calcula vive aquí para poder probarlo.
"""
import json
from datetime import date

import numpy as np
import pandas as pd

from src import build_features, clean_data
from src import dashboard_data as dd


def processed_frame():
    """Salida real del pipeline sobre un mini dataset: NY y TX (con población) y GU (territorio)."""
    dates = pd.date_range("2020-03-01", periods=10)
    parts = []
    for state, cases_step, deaths_step in [("NY", 100, 10), ("TX", 50, 15), ("GU", 1, 0)]:
        n = np.arange(1, 11)
        parts.append(pd.DataFrame({
            "date": dates.strftime("%Y%m%d").astype(int),
            "state": state,
            "positive": n * cases_step * 1.0,
            "death": n * deaths_step * 1.0,
            "totalTestResults": n * 1000.0,
            "hospitalizedCurrently": np.nan,
            "positiveIncrease": cases_step,
            "deathIncrease": deaths_step,
            "totalTestResultsIncrease": 1000,
            "hospitalizedIncrease": 0,
        }))
    raw = pd.concat(parts, ignore_index=True)
    clean, _ = clean_data.clean_pipeline(raw)
    pop = pd.DataFrame({"state": ["NY", "TX"], "name": ["New York", "Texas"],
                        "population": [20_000_000, 30_000_000]})
    return build_features.add_features(build_features.add_population(clean, pop))


def test_every_metric_column_exists_in_pipeline_output():
    df = processed_frame()
    for label, col in dd.METRICS.items():
        assert col in df.columns, f"{label}: falta la columna {col}"


def test_filter_data_by_states_and_dates():
    out = dd.filter_data(processed_frame(), states=["NY"], start=date(2020, 3, 3), end=date(2020, 3, 5))
    assert set(out["state"]) == {"NY"}
    assert out["date"].min() == pd.Timestamp("2020-03-03") and out["date"].max() == pd.Timestamp("2020-03-05")


def test_filter_data_excludes_territories_by_default():
    df = processed_frame()
    assert "GU" not in set(dd.filter_data(df)["state"])
    assert "GU" in set(dd.filter_data(df, include_territories=True)["state"])


def test_filter_data_empty_state_list_means_no_state_filter():
    df = processed_frame()
    assert set(dd.filter_data(df, states=[])["state"]) == {"NY", "TX"}


def test_filter_data_by_population_group():
    out = dd.filter_data(processed_frame(), sizes=["Muy grande"])
    assert set(out["state"]) == {"TX"}


def test_snapshot_one_row_per_state_sorted_descending():
    snap = dd.snapshot(processed_frame(), "deaths_per_100k")
    assert snap["state"].is_unique and len(snap) == 2
    assert snap["deaths_per_100k"].is_monotonic_decreasing
    assert (snap["date"] == pd.Timestamp("2020-03-10")).all()


def test_snapshot_as_of_uses_last_date_not_after_it():
    snap = dd.snapshot(processed_frame(), "cases_per_100k", as_of=date(2020, 3, 5))
    assert (snap["date"] == pd.Timestamp("2020-03-05")).all()


def test_snapshot_drops_rows_without_metric_and_does_not_crash_when_empty():
    # positivity_7d necesita 7 días de ventana: el 3-mar todavía no existe
    snap = dd.snapshot(processed_frame(), "positivity_7d", as_of=date(2020, 3, 3))
    assert snap.empty


def test_kpis_sum_last_day_across_selected_states():
    k = dd.kpis(dd.filter_data(processed_frame(), states=["NY", "TX"]))
    assert k["cases"] == 1000 + 500 and k["deaths"] == 100 + 150
    assert k["cfr"] == (250 / 1500 * 100) and k["n_states"] == 2
    assert k["last_date"] == pd.Timestamp("2020-03-10")


def test_kpis_of_empty_selection_are_zero_and_nan_cfr():
    k = dd.kpis(dd.filter_data(processed_frame(), states=["NY"], start=date(2030, 1, 1)))
    assert k["cases"] == 0 and k["deaths"] == 0 and k["n_states"] == 0 and np.isnan(k["cfr"])


def test_states_with_population_excludes_territories():
    assert dd.states_with_population(processed_frame()) == ["NY", "TX"]


def test_load_processed_parses_dates(tmp_path):
    p = tmp_path / "x.csv"
    processed_frame().to_csv(p, index=False)
    assert pd.api.types.is_datetime64_any_dtype(dd.load_processed(p)["date"])


def test_load_quality_report_returns_none_when_missing(tmp_path):
    assert dd.load_quality_report(tmp_path / "no.json") is None


def test_load_quality_report_reads_json(tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"rows_in": 5}), encoding="utf-8")
    assert dd.load_quality_report(p) == {"rows_in": 5}


def test_first_existing_returns_first_path_that_exists(tmp_path):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv.gz"
    b.write_text("x")
    assert dd.first_existing([a, b]) == b
    a.write_text("y")
    assert dd.first_existing([a, b]) == a


def test_first_existing_returns_none_when_nothing_exists(tmp_path):
    assert dd.first_existing([tmp_path / "no1", tmp_path / "no2"]) is None


def test_load_processed_reads_gzip_snapshot(tmp_path):
    p = tmp_path / "snap.csv.gz"
    processed_frame().to_csv(p, index=False, compression="gzip")
    out = dd.load_processed(p)
    assert pd.api.types.is_datetime64_any_dtype(out["date"]) and len(out) == 30
