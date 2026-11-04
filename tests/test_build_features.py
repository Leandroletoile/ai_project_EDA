"""Tests de las funciones de análisis / feature engineering (src/build_features.py)."""
import numpy as np
import pandas as pd
import pytest

from src import build_features as a


def frame():
    dates = pd.date_range("2020-03-01", periods=8)
    ny = pd.DataFrame({"state": "NY", "date": dates, "cases_cum": np.arange(1, 9) * 100.0,
                       "deaths_cum": np.arange(1, 9) * 10.0, "new_cases": [100] * 8,
                       "new_deaths": [10] * 8, "new_tests": [1000] * 8})
    tx = ny.copy()
    tx["state"] = "TX"
    tx["new_cases"] = 50
    tx["cases_cum"] = np.arange(1, 9) * 50.0
    gu = ny.copy()
    gu["state"] = "GU"
    return pd.concat([ny, tx, gu], ignore_index=True)


POP = pd.DataFrame({"state": ["NY", "TX"], "name": ["New York", "Texas"],
                    "population": [20_000_000, 30_000_000]})


def test_per_100k_math():
    assert a.per_100k(50, 100_000) == 50
    assert a.per_100k(1, 1_000_000) == pytest.approx(0.1)


def test_add_population_left_join_keeps_territories_as_nan():
    out = a.add_population(frame(), POP)
    assert len(out) == len(frame())
    assert out.loc[out["state"] == "GU", "population"].isna().all()
    assert (out.loc[out["state"] == "NY", "population"] == 20_000_000).all()


def test_add_population_rejects_duplicated_population_rows():
    with pytest.raises(Exception):
        a.add_population(frame(), pd.concat([POP, POP]))


def test_rolling_by_state_does_not_leak_between_states():
    df = frame().sort_values(["state", "date"]).reset_index(drop=True)
    out = a.rolling_by_state(df, "new_cases", window=7)
    ny = out[df["state"] == "NY"]
    tx = out[df["state"] == "TX"]
    assert ny.iloc[:6].isna().all()          # ventana incompleta -> NaN
    assert ny.iloc[6] == 100 and tx.iloc[6] == 50


def test_assign_period_boundaries():
    d = pd.Series(pd.to_datetime(["2020-02-29", "2020-03-01", "2020-05-31", "2020-06-01",
                                  "2020-09-30", "2020-10-01", "2021-03-07"]))
    assert a.assign_period(d).tolist() == [
        "Pre-brote", "Primavera 2020", "Primavera 2020", "Verano 2020",
        "Verano 2020", "Invierno 2020-21", "Invierno 2020-21"]


def test_case_fatality_rate_is_nan_when_no_cases():
    out = a.case_fatality_rate(pd.Series([10.0, 5.0]), pd.Series([100.0, 0.0]))
    assert out.iloc[0] == pytest.approx(10.0)
    assert np.isnan(out.iloc[1])


def test_positivity_rate_uses_weekly_sums_and_nan_without_tests():
    df = frame().sort_values(["state", "date"]).reset_index(drop=True)
    out = a.positivity_7d(df)
    assert out[df["state"] == "NY"].iloc[6] == pytest.approx(10.0)  # 700/7000
    assert out[df["state"] == "NY"].iloc[:6].isna().all()
    df.loc[df["state"] == "TX", "new_tests"] = 0
    assert a.positivity_7d(df)[df["state"] == "TX"].isna().all()


def test_add_features_creates_expected_columns():
    out = a.add_features(a.add_population(frame(), POP))
    expected = {"year_month", "week", "weekday", "period", "cfr", "positivity_7d",
                "new_cases_7d", "new_deaths_7d", "cases_per_100k", "deaths_per_100k",
                "new_cases_per_100k_7d"}
    assert expected <= set(out.columns)
    ny_last = out[(out["state"] == "NY")].iloc[-1]
    assert ny_last["cases_per_100k"] == pytest.approx(800 / 20_000_000 * 100_000)
    assert out.loc[out["state"] == "GU", "cases_per_100k"].isna().all()


def test_state_summary_one_row_per_state_with_latest_values():
    df = a.add_features(a.add_population(frame(), POP))
    s = a.state_summary(df)
    assert s["state"].is_unique and len(s) == 3
    assert s.set_index("state").loc["NY", "cases_cum"] == 800


def test_population_groups_are_quartile_based_and_ordered():
    pop = pd.DataFrame({"state": list("ABCDEFGH"), "population": [1, 2, 3, 4, 5, 6, 7, 8]})
    g = a.population_group(pop)
    assert g.iloc[0] == "Pequeño" and g.iloc[-1] == "Muy grande"
    assert set(g.unique()) == {"Pequeño", "Mediano", "Grande", "Muy grande"}


def test_iqr_outliers_flags_extreme_values_only():
    s = pd.Series([10, 11, 12, 13, 14, 15, 500])
    mask = a.iqr_outliers(s)
    assert mask.tolist() == [False] * 6 + [True]


def test_iqr_outliers_ignores_nan_and_handles_constant_series():
    assert a.iqr_outliers(pd.Series([1.0, np.nan, 1.0])).sum() == 0
    assert a.iqr_outliers(pd.Series([5, 5, 5, 5])).sum() == 0


def test_positivity_over_100_percent_is_invalid_and_becomes_nan():
    df = frame().sort_values(["state", "date"]).reset_index(drop=True)
    df.loc[df["state"] == "TX", "new_cases"] = 5000   # 35.000 positivos con 7.000 pruebas
    assert a.positivity_7d(df)[df["state"] == "TX"].isna().all()
    raw = a.positivity_7d(df, cap=False)
    assert raw[df["state"] == "TX"].iloc[6] == pytest.approx(500.0)


def test_population_group_works_with_fewer_than_four_states():
    one = pd.DataFrame({"state": ["A"], "population": [5]})
    assert a.population_group(one).tolist() == ["Muy grande"]
    two = pd.DataFrame({"state": list("AB"), "population": [1, 2]})
    g = a.population_group(two)
    assert g.iloc[0] != g.iloc[1] and g.iloc[1] == "Muy grande"
