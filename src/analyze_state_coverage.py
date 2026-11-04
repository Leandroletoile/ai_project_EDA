from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT / "data" / "raw" / "covid_us_states_daily.csv"
OUTPUT = ROOT / "reports" / "initial_audit"

VARIABLES = [
    "positive",
    "death",
    "hospitalizedCurrently",
    "totalTestResults",
    "negative",
    "positiveIncrease",
    "deathIncrease"
]


def analyze_state_coverage():
    df = pd.read_csv(INPUT)

    df["date"] = pd.to_datetime(
        df["date"].astype(str),
        format="%Y%m%d",
        errors="coerce"
    )

    available_variables = [
        col for col in VARIABLES if col in df.columns
    ]

    results = []

    for state, group in df.groupby("state"):
        results.append({
            "state": state,
            "total_records": len(group),
            "first_date": group["date"].min(),
            "last_date": group["date"].max(),
            "unique_dates": group["date"].nunique(),
            **{
                f"{col}_availability_pct": (
                    group[col].notna().mean() * 100
                )
                for col in available_variables
            }
        })

    coverage = pd.DataFrame(results)

    coverage = coverage.sort_values("state")

    coverage.to_csv(
        OUTPUT / "state_coverage.csv",
        index=False
    )

    print("\n--- COBERTURA POR ESTADO ---")
    print(coverage.to_string(index=False))

    print("\n--- RESUMEN DE REGISTROS POR ESTADO ---")
    print(coverage["total_records"].describe())

    print("\n--- DISPONIBILIDAD DE VARIABLES POR ESTADO ---")
    print(
        coverage[
            [
                f"{col}_availability_pct"
                for col in available_variables
            ]
        ].describe().round(2)
    )

    print("\nInforme guardado en state_coverage.csv")


if __name__ == "__main__":
    analyze_state_coverage()
