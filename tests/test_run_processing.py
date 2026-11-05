"""Tests del procesamiento completo (src/run_processing.py)."""
import numpy as np
import pandas as pd
import pytest

from src import run_processing as rp


def mini_raw():
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


def test_run_processing_fails_when_raw_dataset_does_not_exist(tmp_path):
    with pytest.raises(FileNotFoundError):
        rp.run_processing(raw_path=tmp_path / "no_existe.csv")


def test_run_processing_writes_clean_csv_and_quality_reports(tmp_path):
    raw_path = tmp_path / "raw.csv"
    pop_path = tmp_path / "pop.csv"
    out_path = tmp_path / "processed" / "clean.csv"
    report_path = tmp_path / "reports" / "calidad.md"
    mini_raw().to_csv(raw_path, index=False)
    pd.DataFrame({"state": ["NY"], "name": ["New York"], "population": [20_000_000]}).to_csv(
        pop_path, index=False
    )

    df = rp.run_processing(raw_path, pop_path, out_path, report_path)

    assert len(df) == 6
    assert out_path.exists() and report_path.exists() and report_path.with_suffix(".json").exists()
    saved = pd.read_csv(out_path)
    assert "cases_per_100k" in saved.columns and "correction_flag" in saved.columns
    assert "## Qué quedó pendiente y por qué" in report_path.read_text(encoding="utf-8")
