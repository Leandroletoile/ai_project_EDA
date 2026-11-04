from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT / "data" / "raw" / "covid_us_states_daily.csv"
OUTPUT = ROOT / "reports" / "initial_audit"


def analyze_missingness():
    OUTPUT.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(INPUT)

    df["date"] = pd.to_datetime(
        df["date"].astype(str),
        format="%Y%m%d",
        errors="coerce"
    )

    # --------------------------------------------------
    # 1. COBERTURA GENERAL DE VARIABLES
    # --------------------------------------------------

    results = []

    for column in df.columns:
        if column in ["date", "state"]:
            continue

        valid = df.loc[
            df[column].notna(),
            ["date", "state"]
        ]

        results.append({
            "variable": column,
            "available_records": int(df[column].notna().sum()),
            "missing_records": int(df[column].isna().sum()),
            "availability_percentage": (
                df[column].notna().mean() * 100
            ),
            "first_available_date": (
                valid["date"].min() if not valid.empty else None
            ),
            "last_available_date": (
                valid["date"].max() if not valid.empty else None
            ),
            "states_with_data": valid["state"].nunique()
        })

    coverage = pd.DataFrame(results)

    coverage = coverage.sort_values(
        "availability_percentage",
        ascending=False
    )

    coverage.to_csv(
        OUTPUT / "temporal_coverage.csv",
        index=False
    )

    # --------------------------------------------------
    # 2. DISPONIBILIDAD MENSUAL Y PORCENTAJE DE COBERTURA
    # --------------------------------------------------

    main_variables = [
        "positive",
        "negative",
        "death",
        "hospitalizedCurrently",
        "inIcuCurrently",
        "totalTestResults",
        "deathIncrease",
        "positiveIncrease"
    ]

    available_variables = [
        col for col in main_variables if col in df.columns
    ]

    dated_df = df.dropna(subset=["date"]).copy()

    dated_df["month"] = (
        dated_df["date"].dt.to_period("M").astype(str)
    )

    # Número de registros publicados en cada mes.
    dataset_records = (
        dated_df.groupby("month").size()
        .rename("dataset_records")
    )

    # Número de valores no nulos por variable y mes.
    monthly_available = (
        dated_df.groupby("month")[available_variables]
        .count()
    )

    monthly = pd.DataFrame(index=dataset_records.index)

    monthly["dataset_records"] = dataset_records

    for variable in available_variables:
        monthly[f"{variable}_available"] = (
            monthly_available[variable]
        )

        monthly[f"{variable}_coverage_pct"] = (
            monthly_available[variable]
            / dataset_records
            * 100
        ).round(2)

    monthly.to_csv(
        OUTPUT / "monthly_data_availability.csv"
    )

    # --------------------------------------------------
    # 3. RESULTADOS
    # --------------------------------------------------

    print("\n--- COBERTURA GENERAL DE VARIABLES ---")

    numeric_columns = [
        "available_records",
        "missing_records",
        "availability_percentage",
        "states_with_data"
    ]

    display_coverage = coverage.copy()

    display_coverage[numeric_columns] = (
        display_coverage[numeric_columns].round(2)
    )

    print(display_coverage.to_string(index=False))

    print("\n--- DISPONIBILIDAD MENSUAL ---")
    print(monthly.to_string())

    print("\nInformes generados correctamente.")


if __name__ == "__main__":
    analyze_missingness()
