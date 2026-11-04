"""Tests del informe de calidad de datos (src/quality_report.py)."""
import numpy as np
import pandas as pd

from src import clean_data as c
from src import quality_report as q


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


def test_build_quality_report_has_the_three_required_sections():
    raw = raw_frame()
    clean, rep = c.clean_pipeline(raw)
    md = q.build_quality_report(raw, clean, rep)
    assert "## Qué faltaba" in md
    assert "## Qué se corrigió" in md
    assert "## Qué quedó pendiente y por qué" in md


def test_build_quality_report_mentions_row_counts_and_negative_fixes():
    raw = raw_frame()
    clean, rep = c.clean_pipeline(raw)
    md = q.build_quality_report(raw, clean, rep)
    assert "6 filas" in md
    assert "new_cases" in md and "new_hosp" in md


def test_md_table_renders_header_separator_and_rows():
    out = q.md_table(["a", "b"], [[1, 2], [3, 4]])
    assert out.splitlines() == ["| a | b |", "|---|---|", "| 1 | 2 |", "| 3 | 4 |"]
