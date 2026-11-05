"""Tests de las funciones de limpieza (src/clean_data.py).

Escritos ANTES que las funciones (enfoque TDD): cada test describe una decisión
de limpieza que luego se justifica en el notebook y en el informe de calidad.
"""
import numpy as np
import pandas as pd
import pytest

from src import clean_data as c


# ----------------------------------------------------------------- helpers
def raw_frame():
    """Mini dataset con los mismos problemas que el real."""
    return pd.DataFrame(
        {
            "date": [20200301, 20200302, 20200303, 20200301, 20200302, 20200303],
            "state": ["NY", "NY", "NY", "AS", "AS", "AS"],
            "positive": [np.nan, 5.0, np.nan, 0.0, 0.0, 1.0],
            "death": [np.nan, np.nan, 2.0, 0.0, np.nan, 0.0],
            "totalTestResults": [10.0, 20.0, 30.0, 1.0, 2.0, 3.0],
            "hospitalizedCurrently": [np.nan, 4.0, np.nan, np.nan, np.nan, np.nan],
            "positiveIncrease": [0, 5, -2, 0, 0, 1],
            "deathIncrease": [0, 0, 2, 0, 0, 0],
            "totalTestResultsIncrease": [10, 10, 10, 1, 1, 1],
            "hospitalizedIncrease": [0, 0, -1, 0, 0, 0],
        }
    )


# ------------------------------------------------------------------- fechas
def test_parse_dates_converts_int_yyyymmdd_to_datetime():
    out = c.parse_dates(raw_frame())
    assert pd.api.types.is_datetime64_any_dtype(out["date"])
    assert out["date"].iloc[0] == pd.Timestamp("2020-03-01")


def test_parse_dates_raises_on_invalid_date():
    bad = raw_frame()
    bad.loc[0, "date"] = 20201399
    with pytest.raises(ValueError):
        c.parse_dates(bad)


def test_parse_dates_does_not_modify_input():
    df = raw_frame()
    c.parse_dates(df)
    assert df["date"].iloc[0] == 20200301


# --------------------------------------------------------------- duplicados
def test_remove_duplicates_drops_exact_copies():
    df = pd.concat([raw_frame(), raw_frame().iloc[[0]]], ignore_index=True)
    out = c.remove_duplicates(c.parse_dates(df))
    assert len(out) == 6


def test_remove_duplicates_keeps_last_when_same_state_and_date():
    df = c.parse_dates(raw_frame())
    dup = df.iloc[[0]].copy()
    dup["positive"] = 99.0
    out = c.remove_duplicates(pd.concat([df, dup], ignore_index=True))
    assert len(out) == 6
    ny_first = out[(out["state"] == "NY") & (out["date"] == pd.Timestamp("2020-03-01"))]
    assert ny_first["positive"].iloc[0] == 99.0


# ----------------------------------------------------------------- columnas
def test_columns_to_drop_detects_constant_and_empty_columns():
    df = raw_frame()
    df["allNaN"] = np.nan
    df["constant"] = 0
    reasons = c.columns_to_drop(df)
    assert reasons["allNaN"] == c.REASON_CONSTANT
    assert reasons["constant"] == c.REASON_CONSTANT


def test_columns_to_drop_detects_technical_metadata_and_redundant():
    df = raw_frame()
    for col in ["hash", "dateChecked", "total", "posNeg", "hospitalized"]:
        df[col] = np.arange(len(df))
    reasons = c.columns_to_drop(df)
    assert reasons["hash"] == c.REASON_METADATA
    assert reasons["dateChecked"] == c.REASON_METADATA
    assert reasons["total"] == c.REASON_REDUNDANT
    assert reasons["posNeg"] == c.REASON_REDUNDANT
    assert reasons["hospitalized"] == c.REASON_REDUNDANT


def test_columns_to_drop_uses_missing_threshold():
    df = raw_frame()
    df["mostly_missing"] = [1.0, 2.0, np.nan, np.nan, np.nan, np.nan]  # 67 %
    df["half_missing"] = [1.0, 2.0, 3.0, np.nan, np.nan, np.nan]  # 50 %
    reasons = c.columns_to_drop(df, missing_threshold=0.6)
    assert reasons["mostly_missing"] == c.REASON_MISSING
    assert "half_missing" not in reasons


def test_columns_to_drop_never_drops_key_columns():
    df = raw_frame()
    assert not {"date", "state", "positive", "death"} & set(c.columns_to_drop(df))


def test_drop_useless_columns_returns_frame_without_them():
    df = raw_frame()
    df["hash"] = "abc"
    out = c.drop_useless_columns(df)
    assert "hash" not in out.columns
    assert "positive" in out.columns


# ------------------------------------------------------------------ nombres
def test_rename_columns_uses_explicit_map_and_snake_case():
    df = raw_frame()
    df["totalTestsPeopleViral"] = 1.0
    out = c.rename_columns(df)
    assert {"cases_cum", "deaths_cum", "tests_cum", "hosp_now", "new_cases",
            "new_deaths", "new_tests", "new_hosp"} <= set(out.columns)
    assert "total_tests_people_viral" in out.columns
    assert "date" in out.columns and "state" in out.columns


# -------------------------------------------------------------------- nulos
def prepared():
    return c.rename_columns(c.parse_dates(raw_frame()))


def test_fill_cumulative_gaps_forward_fills_inside_a_state():
    out = c.fill_cumulative_gaps(prepared())
    ny = out[out["state"] == "NY"].sort_values("date")
    # 5 -> el hueco del día 3 se rellena con el último valor conocido
    assert ny["cases_cum"].tolist() == [0.0, 5.0, 5.0]


def test_fill_cumulative_gaps_leading_missing_become_zero():
    out = c.fill_cumulative_gaps(prepared())
    ny = out[out["state"] == "NY"].sort_values("date")
    assert ny["deaths_cum"].tolist() == [0.0, 0.0, 2.0]


def test_fill_cumulative_gaps_does_not_leak_between_states():
    df = prepared()
    df.loc[(df["state"] == "AS") & (df["date"] == pd.Timestamp("2020-03-01")), "deaths_cum"] = np.nan
    out = c.fill_cumulative_gaps(df)
    as_first = out[(out["state"] == "AS") & (out["date"] == pd.Timestamp("2020-03-01"))]
    ny_last = out[(out["state"] == "NY") & (out["date"] == pd.Timestamp("2020-03-03"))]
    assert as_first["deaths_cum"].iloc[0] == 0.0  # no hereda el 2 de NY
    assert ny_last["deaths_cum"].iloc[0] == 2.0


def test_fill_cumulative_gaps_keeps_current_hospitalizations_as_nan():
    out = c.fill_cumulative_gaps(prepared())
    # "missing" no es "cero": no se imputan las variables de ingresos actuales
    assert out["hosp_now"].isna().sum() == 5


# --------------------------------------------------------------- correcciones
def test_fix_negative_increments_clips_to_zero_and_flags_rows():
    out = c.fix_negative_increments(prepared())
    assert (out[["new_cases", "new_deaths", "new_tests", "new_hosp"]] >= 0).all().all()
    flagged = out[out["correction_flag"]]
    assert len(flagged) == 1
    assert flagged["state"].iloc[0] == "NY"


def test_fix_negative_increments_leaves_valid_values_untouched():
    out = c.fix_negative_increments(prepared())
    assert out.loc[out["new_cases"] > 0, "new_cases"].tolist() == [5, 1]


# ------------------------------------------------------------ inconsistencias
def test_flag_impossible_values_marks_positives_above_tests():
    df = prepared()
    df.loc[0, "cases_cum"] = 50.0  # 50 positivos con 10 pruebas
    out = c.flag_impossible_values(df)
    assert bool(out.loc[0, "cases_gt_tests"]) is True
    assert out["cases_gt_tests"].sum() == 1


def test_flag_impossible_values_ignores_missing():
    df = prepared()
    df.loc[0, "cases_cum"] = np.nan
    assert c.flag_impossible_values(df)["cases_gt_tests"].sum() == 0


# --------------------------------------------------------------- territorios
def test_add_territory_flag():
    out = c.add_territory_flag(prepared())
    assert out.loc[out["state"] == "AS", "is_territory"].all()
    assert not out.loc[out["state"] == "NY", "is_territory"].any()


# ------------------------------------------------------------------ pipeline
def test_clean_pipeline_end_to_end():
    clean, report = c.clean_pipeline(raw_frame())
    assert pd.api.types.is_datetime64_any_dtype(clean["date"])
    assert not clean.duplicated(["state", "date"]).any()
    assert clean["cases_cum"].notna().all() and clean["deaths_cum"].notna().all()
    assert clean.equals(clean.sort_values(["state", "date"]).reset_index(drop=True))
    for key in ["rows_in", "rows_out", "columns_dropped", "nulls_filled",
                "negative_increments_fixed", "cases_gt_tests_rows"]:
        assert key in report
    assert report["negative_increments_fixed"] == {"new_cases": 1, "new_deaths": 0,
                                                    "new_tests": 0, "new_hosp": 1}


def test_clean_pipeline_is_idempotent_on_row_count():
    clean, _ = c.clean_pipeline(raw_frame())
    assert len(clean) == len(raw_frame())
