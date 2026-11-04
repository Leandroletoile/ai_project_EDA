from pathlib import Path
import math

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "data" / "raw" / "covid_us_states_daily.csv"
OUTPUT_DIR = ROOT / "reports" / "temporal_audit"


CUMULATIVE_VARIABLES = [
    "positive",
    "death",
    "totalTestResults",
    "hospitalizedCumulative",
]

DAILY_VARIABLES = [
    "positiveIncrease",
    "deathIncrease",
    "totalTestResultsIncrease",
]

DAILY_CUMULATIVE_MAPPING = {
    "positiveIncrease": "positive",
    "deathIncrease": "death",
    "totalTestResultsIncrease": "totalTestResults",
}

CONSISTENCY_DETAIL_COLUMNS = [
    "state",
    "date",
    "daily_variable",
    "cumulative_variable",
    "daily_value",
    "previous_date",
    "previous_cumulative",
    "current_cumulative",
    "cumulative_delta",
    "difference",
    "absolute_difference",
    "is_consistent",
]

CONSISTENCY_SUMMARY_COLUMNS = [
    "daily_variable",
    "cumulative_variable",
    "comparisons",
    "exact_matches",
    "discrepancies",
    "mean_absolute_difference",
]


def load_data():
    """Load the raw COVID dataset and prepare its date column."""
    df = pd.read_csv(INPUT_FILE)
    df["date"] = pd.to_datetime(
        df["date"].astype("Int64").astype("string"),
        format="%Y%m%d",
        errors="coerce",
    )
    df = df.sort_values(["state", "date"]).reset_index(drop=True)
    return df


def analyze_jurisdiction_coverage(df, expected_jurisdictions=None):
    """
    Measure daily jurisdiction coverage and availability of daily variables.

    Expected jurisdictions are inferred from the complete input dataset
    unless an explicit value is provided.
    """
    required_columns = ["state", "date", *DAILY_VARIABLES]
    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    if expected_jurisdictions is None:
        expected_jurisdictions = int(df["state"].nunique())
    elif (
        not isinstance(expected_jurisdictions, int)
        or expected_jurisdictions < 1
    ):
        raise ValueError(
            "expected_jurisdictions must be a positive integer."
        )

    result_columns = [
        "date",
        "jurisdictions_reported",
        "expected_jurisdictions",
        "is_complete_coverage",
        *[f"{column}_available" for column in DAILY_VARIABLES],
    ]

    if df.empty or df["date"].isna().all():
        return pd.DataFrame(columns=result_columns)

    data = df.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data.loc[data["date"].notna()].copy()

    if data.empty:
        return pd.DataFrame(columns=result_columns)

    aggregations = {
        "jurisdictions_reported": ("state", "nunique"),
    }

    for column in DAILY_VARIABLES:
        aggregations[f"{column}_available"] = (column, "count")

    daily_coverage = data.groupby("date").agg(**aggregations)

    calendar = pd.date_range(
        start=daily_coverage.index.min(),
        end=daily_coverage.index.max(),
        freq="D",
        name="date",
    )

    daily_coverage = daily_coverage.reindex(
        calendar,
        fill_value=0,
    )

    daily_coverage["expected_jurisdictions"] = (
        expected_jurisdictions
    )
    daily_coverage["is_complete_coverage"] = (
        daily_coverage["jurisdictions_reported"]
        == expected_jurisdictions
    )

    return daily_coverage.reset_index()[result_columns]


def analyze_duplicates(df):
    """Identify duplicated state-date records."""
    duplicated = df.duplicated(subset=["state", "date"], keep=False)
    return df.loc[duplicated].copy()


def analyze_date_gaps(df):
    """Identify gaps between consecutive dates for each state."""
    ordered = df.sort_values(["state", "date"]).copy()
    ordered["previous_date"] = ordered.groupby("state")["date"].shift(1)
    ordered["gap_days"] = (ordered["date"] - ordered["previous_date"]).dt.days
    gaps = ordered.loc[ordered["gap_days"] > 1].copy()
    gaps["missing_days"] = gaps["gap_days"] - 1
    return gaps


def analyze_cumulative_decreases(df):
    """Identify decreases in cumulative variables."""
    results = []
    ordered = df.sort_values(["state", "date"]).copy()

    for column in CUMULATIVE_VARIABLES:
        ordered["previous_value"] = ordered.groupby("state")[column].shift(1)

        decreases = ordered.loc[
            ordered[column] < ordered["previous_value"],
            ["state", "date", "previous_value", column],
        ].copy()

        if decreases.empty:
            continue

        decreases = decreases.rename(columns={column: "current_value"})
        decreases["variable"] = column
        decreases["decrease_amount"] = (
            decreases["previous_value"] - decreases["current_value"]
        )
        results.append(decreases)

    if not results:
        return pd.DataFrame(columns=[
            "state", "date", "previous_value", "current_value",
            "variable", "decrease_amount",
        ])

    return pd.concat(results, ignore_index=True)


def analyze_extreme_values(df, quantile=0.99):
    """Identify daily values above state-specific quantile thresholds."""
    if isinstance(quantile, bool):
        raise ValueError("quantile must be a numeric value between 0 and 1.")

    try:
        quantile = float(quantile)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(
            "quantile must be a numeric value between 0 and 1."
        ) from None

    if not math.isfinite(quantile) or not 0 <= quantile <= 1:
        raise ValueError("quantile must be a numeric value between 0 and 1.")

    results = []

    for column in DAILY_VARIABLES:
        thresholds = df.groupby("state")[column].transform(
            lambda values: values.quantile(quantile)
        )

        mask = df[column] > thresholds

        if not mask.any():
            continue

        detected = df.loc[mask, ["state", "date", column]].copy()
        detected = detected.rename(columns={column: "value"})
        detected["variable"] = column
        detected["threshold"] = thresholds.loc[mask]
        detected["quantile"] = quantile
        results.append(detected)

    columns = ["state", "date", "variable", "value", "threshold", "quantile"]

    if not results:
        return pd.DataFrame(columns=columns)

    return pd.concat(results, ignore_index=True)


def analyze_daily_cumulative_consistency(df):
    """
    Compare daily increases with consecutive-day cumulative differences.

    Only observations with consecutive calendar dates and non-null values
    are included. Duplicate state-date records raise an error because they
    make the previous observation ambiguous.
    """
    required_columns = {
        "state",
        "date",
        *DAILY_CUMULATIVE_MAPPING.keys(),
        *DAILY_CUMULATIVE_MAPPING.values(),
    }

    missing_columns = required_columns.difference(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    if df.duplicated(subset=["state", "date"]).any():
        raise ValueError(
            "Cannot compare daily and cumulative values: "
            "duplicate state-date records were found."
        )

    ordered = df.sort_values(["state", "date"]).copy()

    grouped = ordered.groupby("state", sort=False)

    ordered["previous_date"] = grouped["date"].shift(1)

    results = []

    for daily_variable, cumulative_variable in DAILY_CUMULATIVE_MAPPING.items():
        previous_cumulative = grouped[cumulative_variable].shift(1)

        daily_values = pd.to_numeric(
            ordered[daily_variable], errors="coerce"
        )
        current_cumulative = pd.to_numeric(
            ordered[cumulative_variable], errors="coerce"
        )
        previous_values = pd.to_numeric(
            previous_cumulative, errors="coerce"
        )

        consecutive_dates = (
            ordered["date"] - ordered["previous_date"]
        ).dt.days.eq(1)

        valid = (
            consecutive_dates
            & daily_values.notna()
            & current_cumulative.notna()
            & previous_values.notna()
        )

        if not valid.any():
            continue

        details = pd.DataFrame({
            "state": ordered.loc[valid, "state"],
            "date": ordered.loc[valid, "date"],
            "daily_variable": daily_variable,
            "cumulative_variable": cumulative_variable,
            "daily_value": daily_values.loc[valid],
            "previous_date": ordered.loc[valid, "previous_date"],
            "previous_cumulative": previous_values.loc[valid],
            "current_cumulative": current_cumulative.loc[valid],
        })

        details["cumulative_delta"] = (
            details["current_cumulative"]
            - details["previous_cumulative"]
        )

        details["difference"] = (
            details["daily_value"] - details["cumulative_delta"]
        )

        details["absolute_difference"] = details["difference"].abs()
        details["is_consistent"] = details["difference"].eq(0)

        results.append(details[CONSISTENCY_DETAIL_COLUMNS])

    if not results:
        return pd.DataFrame(columns=CONSISTENCY_DETAIL_COLUMNS)

    return pd.concat(results, ignore_index=True)


def summarize_daily_cumulative_consistency(details):
    """Summarize exact matches and discrepancies by variable."""
    summaries = []

    for daily_variable, cumulative_variable in DAILY_CUMULATIVE_MAPPING.items():
        subset = details.loc[
            details["daily_variable"] == daily_variable
        ]

        comparisons = len(subset)
        exact_matches = int(subset["is_consistent"].sum())

        discrepancies = comparisons - exact_matches

        mean_absolute_difference = (
            float(subset["absolute_difference"].mean())
            if comparisons
            else 0.0
        )

        summaries.append({
            "daily_variable": daily_variable,
            "cumulative_variable": cumulative_variable,
            "comparisons": comparisons,
            "exact_matches": exact_matches,
            "discrepancies": discrepancies,
            "mean_absolute_difference": mean_absolute_difference,
        })

    return pd.DataFrame(
        summaries,
        columns=CONSISTENCY_SUMMARY_COLUMNS,
    )


def generate_summary(
    df,
    duplicates,
    date_gaps,
    cumulative_decreases,
    extreme_values,
    consistency_summary=None,
):
    """Generate a comprehensive summary of the temporal quality audit."""
    missing_calendar_days = (
        int(date_gaps["missing_days"].sum())
        if not date_gaps.empty
        else 0
    )

    summary = [
        "TEMPORAL DATA QUALITY AUDIT",
        "=" * 60,
        "",
        "DATASET OVERVIEW",
        "-" * 60,
        f"Dataset records: {len(df)}",
        f"Dataset columns: {len(df.columns)}",
        "",
        "TEMPORAL FINDINGS",
        "-" * 60,
        f"Duplicate records: {len(duplicates)}",
        f"Date gap intervals: {len(date_gaps)}",
        f"Missing calendar days: {missing_calendar_days}",
        f"Cumulative decreases: {len(cumulative_decreases)}",
        f"Extreme daily values: {len(extreme_values)}",
    ]

    if consistency_summary is not None:
        summary.extend([
            "",
            "DAILY-CUMULATIVE CONSISTENCY",
            "-" * 60,
        ])

        total_comparisons = int(consistency_summary["comparisons"].sum())
        total_matches = int(consistency_summary["exact_matches"].sum())
        total_discrepancies = int(consistency_summary["discrepancies"].sum())

        summary.extend([
            f"Comparisons: {total_comparisons}",
            f"Exact matches: {total_matches}",
            f"Discrepancies: {total_discrepancies}",
        ])

        for _, row in consistency_summary.iterrows():
            summary.append(
                f"{row['daily_variable']} vs {row['cumulative_variable']}: "
                f"{int(row['exact_matches'])}/{int(row['comparisons'])} "
                f"exact matches"
            )

    summary.extend([
        "",
        "IMPORTANT",
        "-" * 60,
        "Detected anomalies require contextual investigation.",
        "No original records were modified or deleted.",
        "Extreme values are statistical signals, not confirmed errors.",
        "Arithmetic consistency does not prove epidemiological accuracy.",
        "",
    ])

    return "\n".join(summary)


def main():
    """Run the temporal quality audit and save its reports."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_data()

    jurisdiction_coverage = analyze_jurisdiction_coverage(df)

    duplicates = analyze_duplicates(df)
    date_gaps = analyze_date_gaps(df)
    cumulative_decreases = analyze_cumulative_decreases(df)
    extreme_values = analyze_extreme_values(df)

    consistency_details = analyze_daily_cumulative_consistency(df)
    consistency_summary = summarize_daily_cumulative_consistency(
        consistency_details
    )

    jurisdiction_coverage.to_csv(
        OUTPUT_DIR / "jurisdiction_coverage.csv",
        index=False,
    )

    duplicates.to_csv(
        OUTPUT_DIR / "duplicate_records.csv", index=False
    )
    date_gaps.to_csv(
        OUTPUT_DIR / "date_gaps.csv", index=False
    )
    cumulative_decreases.to_csv(
        OUTPUT_DIR / "cumulative_decreases.csv", index=False
    )
    extreme_values.to_csv(
        OUTPUT_DIR / "extreme_values.csv", index=False
    )

    consistency_details.to_csv(
        OUTPUT_DIR / "daily_cumulative_consistency_details.csv",
        index=False,
    )

    consistency_summary.to_csv(
        OUTPUT_DIR / "cumulative_daily_consistency.csv",
        index=False,
    )

    mismatches = consistency_details.loc[
        ~consistency_details["is_consistent"]
    ].copy()

    mismatches.to_csv(
        OUTPUT_DIR / "cumulative_daily_mismatches.csv",
        index=False,
    )

    summary = generate_summary(
        df,
        duplicates,
        date_gaps,
        cumulative_decreases,
        extreme_values,
        consistency_summary,
    )

    complete_days = jurisdiction_coverage.loc[
        jurisdiction_coverage["is_complete_coverage"],
        "date",
    ]

    partial_days = len(jurisdiction_coverage) - len(complete_days)

    coverage_lines = [
        "JURISDICTION COVERAGE",
        "---------------------",
        f"Expected jurisdictions: {int(df['state'].nunique())}",
        f"Calendar days analyzed: {len(jurisdiction_coverage)}",
        f"Days with complete coverage: {len(complete_days)}",
        f"Days with partial coverage: {partial_days}",
    ]

    if not complete_days.empty:
        coverage_lines.extend([
            f"First complete coverage date: {complete_days.min().date()}",
            f"Last complete coverage date: {complete_days.max().date()}",
        ])

    with open(
        OUTPUT_DIR / "jurisdiction_coverage_summary.txt",
        "w",
        encoding="utf-8",
    ) as file:
        file.write("\n".join(coverage_lines))

    with open(
        OUTPUT_DIR / "temporal_quality_summary.txt",
        "w",
        encoding="utf-8",
    ) as file:
        file.write(summary)

    print(summary)
    print(f"\nReports saved in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
