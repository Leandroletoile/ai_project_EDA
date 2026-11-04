from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT / "data" / "raw" / "covid_us_states_daily.csv"
OUTPUT_DIR = ROOT / "reports" / "initial_audit"

NEGATIVE_VARIABLES = [
    "positiveIncrease",
    "negativeIncrease",
    "totalTestResultsIncrease",
    "deathIncrease",
    "hospitalizedIncrease",
]


def load_data():
    """Load the original dataset and parse dates."""
    df = pd.read_csv(INPUT_FILE)

    df["date"] = pd.to_datetime(
        df["date"].astype(str),
        format="%Y%m%d",
        errors="coerce",
    )

    return df


def analyze_negative_values(df):
    """Identify negative values in daily increase variables."""
    results = []

    for column in NEGATIVE_VARIABLES:
        negative = df.loc[df[column] < 0].copy()

        if negative.empty:
            continue

        negative["variable"] = column
        negative["value"] = negative[column]

        results.append(
            negative[
                ["date", "state", "variable", "value"]
            ]
        )

    if results:
        return pd.concat(results, ignore_index=True)

    return pd.DataFrame(
        columns=["date", "state", "variable", "value"]
    )


def analyze_negative_values_by_state(negative_df):
    """Count negative records by variable and state."""
    if negative_df.empty:
        return pd.DataFrame(
            columns=["variable", "state", "negative_records"]
        )

    return (
        negative_df
        .groupby(["variable", "state"])
        .size()
        .rename("negative_records")
        .reset_index()
        .sort_values(
            ["variable", "negative_records"],
            ascending=[True, False],
        )
    )


def analyze_constant_columns(df):
    """Identify empty and constant columns."""
    results = []

    for column in df.columns:
        unique_values = df[column].nunique(dropna=True)
        null_values = int(df[column].isna().sum())

        results.append({
            "variable": column,
            "null_values": null_values,
            "unique_values": unique_values,
            "is_constant": unique_values == 1,
            "is_empty": df[column].isna().all(),
        })

    report = pd.DataFrame(results)

    return report[
        report["is_constant"] | report["is_empty"]
    ].reset_index(drop=True)


def generate_summary(df, negative_df, constant_df):
    """Generate a text summary of data quality findings."""
    lines = [
        "DATA QUALITY AUDIT",
        "=" * 50,
        "",
        f"Dataset records: {len(df)}",
        f"Dataset columns: {len(df.columns)}",
        "",
        "NEGATIVE VALUES",
        "-" * 50,
    ]

    for column in NEGATIVE_VARIABLES:
        total = int(df[column].notna().sum())
        count = int((df[column] < 0).sum())
        percentage = count / total * 100 if total else 0

        lines.append(
            f"{column}: {count} negative values ({percentage:.2f}%)"
        )

    lines.extend([
        "",
        f"Total negative records across variables: {len(negative_df)}",
        "",
        "CONSTANT AND EMPTY COLUMNS",
        "-" * 50,
    ])

    if constant_df.empty:
        lines.append("No constant or empty columns found.")
    else:
        for _, row in constant_df.iterrows():
            status = "EMPTY" if row["is_empty"] else "CONSTANT"
            lines.append(f"{row['variable']}: {status}")

    lines.extend([
        "",
        "IMPORTANT",
        "-" * 50,
        "No original records were modified or deleted.",
        "Negative values require contextual investigation.",
        "Constant and empty columns were identified, not removed.",
    ])

    return "\n".join(lines)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_data()

    negative_df = analyze_negative_values(df)
    state_report = analyze_negative_values_by_state(negative_df)
    constant_report = analyze_constant_columns(df)

    negative_df.to_csv(
        OUTPUT_DIR / "negative_values.csv",
        index=False,
    )

    state_report.to_csv(
        OUTPUT_DIR / "negative_values_by_state.csv",
        index=False,
    )

    constant_report.to_csv(
        OUTPUT_DIR / "constant_columns.csv",
        index=False,
    )

    summary = generate_summary(
        df,
        negative_df,
        constant_report,
    )

    (OUTPUT_DIR / "data_quality_summary.txt").write_text(
        summary,
        encoding="utf-8",
    )

    print(summary)
    print("\nReports generated in:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
