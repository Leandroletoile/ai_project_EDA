
import pandas as pd
import pytest

from src.analyze_temporal_quality import (
    analyze_jurisdiction_coverage,
    analyze_duplicates,
    analyze_date_gaps,
    analyze_cumulative_decreases,
    analyze_extreme_values,
    generate_summary,
)


def test_analyze_duplicates_detects_repeated_state_date():
    df = pd.DataFrame({
        "state": ["CA", "CA", "NY"],
        "date": pd.to_datetime([
            "2020-01-01",
            "2020-01-01",
            "2020-01-01",
        ]),
    })

    result = analyze_duplicates(df)

    assert len(result) == 2
    assert set(result["state"]) == {"CA"}


def test_analyze_duplicates_returns_empty_without_duplicates():
    df = pd.DataFrame({
        "state": ["CA", "CA", "NY"],
        "date": pd.to_datetime([
            "2020-01-01",
            "2020-01-02",
            "2020-01-01",
        ]),
    })

    result = analyze_duplicates(df)

    assert result.empty


def test_analyze_date_gaps_detects_missing_days():
    df = pd.DataFrame({
        "state": ["CA", "CA", "CA"],
        "date": pd.to_datetime([
            "2020-01-01",
            "2020-01-02",
            "2020-01-05",
        ]),
    })

    result = analyze_date_gaps(df)

    assert len(result) == 1
    assert result.iloc[0]["gap_days"] == 3
    assert result.iloc[0]["missing_days"] == 2


def test_analyze_date_gaps_returns_empty_for_continuous_series():
    df = pd.DataFrame({
        "state": ["CA", "CA", "CA"],
        "date": pd.to_datetime([
            "2020-01-01",
            "2020-01-02",
            "2020-01-03",
        ]),
    })

    result = analyze_date_gaps(df)

    assert result.empty


def test_analyze_cumulative_decreases_detects_decrease():
    df = pd.DataFrame({
        "state": ["CA", "CA", "CA"],
        "date": pd.to_datetime([
            "2020-01-01",
            "2020-01-02",
            "2020-01-03",
        ]),
        "positive": [100, 150, 120],
        "death": [10, 12, 14],
        "totalTestResults": [500, 600, 700],
        "hospitalizedCumulative": [20, 25, 30],
    })

    result = analyze_cumulative_decreases(df)

    assert len(result) == 1
    assert result.iloc[0]["variable"] == "positive"
    assert result.iloc[0]["previous_value"] == 150
    assert result.iloc[0]["current_value"] == 120
    assert result.iloc[0]["decrease_amount"] == 30


def test_analyze_cumulative_decreases_returns_empty_when_monotonic():
    df = pd.DataFrame({
        "state": ["CA", "CA", "CA"],
        "date": pd.to_datetime([
            "2020-01-01",
            "2020-01-02",
            "2020-01-03",
        ]),
        "positive": [100, 150, 200],
        "death": [10, 12, 14],
        "totalTestResults": [500, 600, 700],
        "hospitalizedCumulative": [20, 25, 30],
    })

    result = analyze_cumulative_decreases(df)

    assert result.empty


def test_analyze_extreme_values_detects_values_above_quantile():
    df = pd.DataFrame({
        "state": ["CA", "CA", "CA", "CA"],
        "date": pd.to_datetime([
            "2020-01-01",
            "2020-01-02",
            "2020-01-03",
            "2020-01-04",
        ]),
        "positiveIncrease": [1, 2, 3, 100],
        "deathIncrease": [1, 2, 3, 100],
        "totalTestResultsIncrease": [1, 2, 3, 100],
    })

    result = analyze_extreme_values(df, quantile=0.5)

    assert len(result) == 6

    assert set(result["variable"]) == {
        "positiveIncrease",
        "deathIncrease",
        "totalTestResultsIncrease",
    }

    assert (result["value"] > result["threshold"]).all()


def test_temporal_functions_handle_empty_dataframes():
    df = pd.DataFrame({
        "state": pd.Series(dtype="object"),
        "date": pd.Series(dtype="datetime64[ns]"),
        "positive": pd.Series(dtype="float64"),
        "death": pd.Series(dtype="float64"),
        "totalTestResults": pd.Series(dtype="float64"),
        "hospitalizedCumulative": pd.Series(dtype="float64"),
        "positiveIncrease": pd.Series(dtype="float64"),
        "deathIncrease": pd.Series(dtype="float64"),
        "totalTestResultsIncrease": pd.Series(dtype="float64"),
    })

    assert analyze_duplicates(df).empty
    assert analyze_date_gaps(df).empty
    assert analyze_cumulative_decreases(df).empty
    assert analyze_extreme_values(df).empty


def test_analyze_extreme_values_rejects_negative_quantile():
    df = pd.DataFrame({
        "state": ["CA"],
        "date": pd.to_datetime(["2020-01-01"]),
        "positiveIncrease": [100],
        "deathIncrease": [10],
        "totalTestResultsIncrease": [500],
    })

    with pytest.raises(ValueError, match="quantile"):
        analyze_extreme_values(df, quantile=-0.1)


def test_analyze_extreme_values_rejects_quantile_above_one():
    df = pd.DataFrame({
        "state": ["CA"],
        "date": pd.to_datetime(["2020-01-01"]),
        "positiveIncrease": [100],
        "deathIncrease": [10],
        "totalTestResultsIncrease": [500],
    })

    with pytest.raises(ValueError, match="quantile"):
        analyze_extreme_values(df, quantile=1.5)


def test_analyze_extreme_values_rejects_non_numeric_quantile():
    df = pd.DataFrame({
        "state": ["CA"],
        "date": pd.to_datetime(["2020-01-01"]),
        "positiveIncrease": [100],
        "deathIncrease": [10],
        "totalTestResultsIncrease": [500],
    })

    with pytest.raises(ValueError, match="quantile"):
        analyze_extreme_values(df, quantile="hola")



def test_generate_summary_includes_dataset_overview_and_quality_findings():
    df = pd.DataFrame({
        "state": ["CA", "CA", "NY"],
        "date": pd.to_datetime([
            "2020-01-01",
            "2020-01-02",
            "2020-01-05",
        ]),
        "positive": [100, 120, 150],
    })

    duplicates = pd.DataFrame()
    date_gaps = pd.DataFrame({
        "state": ["CA"],
        "gap_days": [3],
        "missing_days": [2],
    })
    cumulative_decreases = pd.DataFrame({
        "variable": ["positive"],
    })
    extreme_values = pd.DataFrame({
        "variable": ["positiveIncrease", "deathIncrease"],
    })

    summary = generate_summary(
        df,
        duplicates,
        date_gaps,
        cumulative_decreases,
        extreme_values,
    )

    assert "Dataset records: 3" in summary
    assert "Dataset columns: 3" in summary
    assert "Duplicate records: 0" in summary
    assert "Date gap intervals: 1" in summary
    assert "Missing calendar days: 2" in summary
    assert "Cumulative decreases: 1" in summary
    assert "Extreme daily values: 2" in summary
    assert "No original records were modified or deleted." in summary
    assert "Extreme values are statistical signals, not confirmed errors." in summary


def test_analyze_extreme_values_calculates_thresholds_independently_by_state():
    df = pd.DataFrame({
        "state": ["CA"] * 4 + ["NY"] * 4,
        "date": pd.date_range("2020-01-01", periods=8),
        "positiveIncrease": [
            1, 2, 3, 100,
            1000, 2000, 3000, 100000,
        ],
        "deathIncrease": [
            1, 2, 3, 100,
            1000, 2000, 3000, 100000,
        ],
        "totalTestResultsIncrease": [
            1, 2, 3, 100,
            1000, 2000, 3000, 100000,
        ],
    })

    result = analyze_extreme_values(df, quantile=0.5)

    assert len(result) == 12

    for variable in [
        "positiveIncrease",
        "deathIncrease",
        "totalTestResultsIncrease",
    ]:
        detected = result[result["variable"] == variable]

        california = detected[detected["state"] == "CA"]
        new_york = detected[detected["state"] == "NY"]

        assert len(california) == 2
        assert len(new_york) == 2

        assert set(california["value"]) == {3, 100}
        assert california.iloc[0]["threshold"] == 2.5

        assert set(new_york["value"]) == {3000, 100000}
        assert new_york.iloc[0]["threshold"] == 2500

from src.analyze_temporal_quality import (
    analyze_daily_cumulative_consistency,
    summarize_daily_cumulative_consistency,
)


def build_consistency_dataframe():
    """Build a small dataset with consecutive dates and known values."""
    return pd.DataFrame({
        "state": ["CA", "CA", "CA", "NY", "NY"],
        "date": pd.to_datetime([
            "2020-01-01",
            "2020-01-02",
            "2020-01-03",
            "2020-01-01",
            "2020-01-02",
        ]),
        "positiveIncrease": [10, 5, 9, 20, 4],
        "positive": [10, 15, 23, 20, 24],
        "deathIncrease": [1, 1, 2, 2, 1],
        "death": [1, 2, 4, 2, 3],
        "totalTestResultsIncrease": [100, 50, 80, 200, 40],
        "totalTestResults": [100, 150, 230, 200, 240],
    })


def test_daily_cumulative_consistency_detects_exact_matches():
    df = build_consistency_dataframe()

    result = analyze_daily_cumulative_consistency(df)

    ca_day_two = result.loc[
        (result["state"] == "CA")
        & (result["date"] == pd.Timestamp("2020-01-02"))
    ]

    assert len(ca_day_two) == 3
    assert ca_day_two["is_consistent"].all()
    assert (ca_day_two["difference"] == 0).all()


def test_daily_cumulative_consistency_detects_discrepancies():
    df = build_consistency_dataframe()

    result = analyze_daily_cumulative_consistency(df)

    mismatch = result.loc[
        (result["state"] == "CA")
        & (result["date"] == pd.Timestamp("2020-01-03"))
        & (result["daily_variable"] == "positiveIncrease")
    ]

    assert len(mismatch) == 1
    assert mismatch.iloc[0]["daily_value"] == 9
    assert mismatch.iloc[0]["cumulative_delta"] == 8
    assert mismatch.iloc[0]["difference"] == 1
    assert not mismatch.iloc[0]["is_consistent"]


def test_daily_cumulative_consistency_excludes_non_consecutive_dates():
    df = build_consistency_dataframe()

    df = df.loc[
        ~(
            (df["state"] == "CA")
            & (df["date"] == pd.Timestamp("2020-01-02"))
        )
    ].copy()

    result = analyze_daily_cumulative_consistency(df)

    ca_results = result.loc[result["state"] == "CA"]

    assert ca_results.empty


def test_daily_cumulative_consistency_excludes_null_values():
    df = build_consistency_dataframe()

    df.loc[
        df["date"] == pd.Timestamp("2020-01-02"),
        "positiveIncrease",
    ] = None

    result = analyze_daily_cumulative_consistency(df)

    positive_results = result.loc[
        result["daily_variable"] == "positiveIncrease"
    ]

    assert len(positive_results) == 1
    assert positive_results.iloc[0]["state"] == "CA"
    assert positive_results.iloc[0]["date"] == pd.Timestamp("2020-01-03")


def test_daily_cumulative_consistency_keeps_states_independent():
    df = build_consistency_dataframe()

    result = analyze_daily_cumulative_consistency(df)

    ny_results = result.loc[result["state"] == "NY"]

    assert len(ny_results) == 3
    assert ny_results["is_consistent"].all()


def test_daily_cumulative_consistency_rejects_duplicate_state_dates():
    df = build_consistency_dataframe()

    duplicated_row = df.iloc[[0]].copy()
    df = pd.concat([df, duplicated_row], ignore_index=True)

    with pytest.raises(ValueError, match="duplicate state-date"):
        analyze_daily_cumulative_consistency(df)


def test_consistency_summary_reports_comparisons_and_discrepancies():
    df = build_consistency_dataframe()

    details = analyze_daily_cumulative_consistency(df)
    summary = summarize_daily_cumulative_consistency(details)

    assert len(summary) == 3

    positive = summary.loc[
        summary["daily_variable"] == "positiveIncrease"
    ].iloc[0]

    assert positive["comparisons"] == 3
    assert positive["exact_matches"] == 2
    assert positive["discrepancies"] == 1
    assert positive["mean_absolute_difference"] == pytest.approx(1 / 3)

def test_analyze_jurisdiction_coverage_identifies_complete_and_partial_days():
    df = pd.DataFrame({
        "state": ["CA", "NY", "CA", "NY"],
        "date": pd.to_datetime([
            "2020-01-01",
            "2020-01-01",
            "2020-01-02",
            "2020-01-02",
        ]),
        "positiveIncrease": [10, 20, 15, None],
        "deathIncrease": [1, 2, 1, 3],
        "totalTestResultsIncrease": [100, 200, 150, 250],
    })

    result = analyze_jurisdiction_coverage(df)

    assert len(result) == 2
    assert result.iloc[0]["jurisdictions_reported"] == 2
    assert result.iloc[0]["is_complete_coverage"]
    assert result.iloc[1]["jurisdictions_reported"] == 2
    assert result.iloc[1]["is_complete_coverage"]
    assert result.iloc[1]["positiveIncrease_available"] == 1
    assert result.iloc[1]["deathIncrease_available"] == 2


def test_analyze_jurisdiction_coverage_includes_missing_calendar_dates():
    df = pd.DataFrame({
        "state": ["CA", "NY", "CA", "NY"],
        "date": pd.to_datetime([
            "2020-01-01",
            "2020-01-01",
            "2020-01-03",
            "2020-01-03",
        ]),
        "positiveIncrease": [10, 20, 15, 25],
        "deathIncrease": [1, 2, 1, 3],
        "totalTestResultsIncrease": [100, 200, 150, 250],
    })

    result = analyze_jurisdiction_coverage(df)

    assert len(result) == 3
    assert result.iloc[1]["date"] == pd.Timestamp("2020-01-02")
    assert result.iloc[1]["jurisdictions_reported"] == 0
    assert not result.iloc[1]["is_complete_coverage"]


def test_analyze_jurisdiction_coverage_supports_expected_jurisdictions_override():
    df = pd.DataFrame({
        "state": ["CA", "NY"],
        "date": pd.to_datetime(["2020-01-01", "2020-01-01"]),
        "positiveIncrease": [10, 20],
        "deathIncrease": [1, 2],
        "totalTestResultsIncrease": [100, 200],
    })

    result = analyze_jurisdiction_coverage(
        df,
        expected_jurisdictions=3,
    )

    assert result.iloc[0]["expected_jurisdictions"] == 3
    assert result.iloc[0]["jurisdictions_reported"] == 2
    assert not result.iloc[0]["is_complete_coverage"]


def test_analyze_jurisdiction_coverage_returns_empty_dataframe_for_empty_input():
    df = pd.DataFrame({
        "state": pd.Series(dtype="object"),
        "date": pd.Series(dtype="datetime64[ns]"),
        "positiveIncrease": pd.Series(dtype="float64"),
        "deathIncrease": pd.Series(dtype="float64"),
        "totalTestResultsIncrease": pd.Series(dtype="float64"),
    })

    result = analyze_jurisdiction_coverage(df)

    assert result.empty
    assert "is_complete_coverage" in result.columns
