from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT / "data" / "raw" / "covid_us_states_daily.csv"
OUTPUT = ROOT / "reports" / "initial_audit"


def audit_dataset():
    print("INICIANDO AUDITORIA DEL DATASET...")

    df = pd.read_csv(INPUT)
    OUTPUT.mkdir(parents=True, exist_ok=True)

    # 1. Estructura
    print("\n--- ESTRUCTURA ---")
    print(f"Filas: {df.shape[0]:,}")
    print(f"Columnas: {df.shape[1]}")

    # 2. Tipos de datos
    dtypes = df.dtypes.astype(str).rename("dtype").to_frame()
    dtypes.to_csv(OUTPUT / "data_types.csv")

    # 3. Valores faltantes
    missing = pd.DataFrame({
        "missing_count": df.isna().sum(),
        "missing_percentage": df.isna().mean() * 100
    }).sort_values("missing_percentage", ascending=False)

    missing.to_csv(OUTPUT / "missing_values.csv")

    print("\n--- VALORES FALTANTES ---")
    print(missing.head(15).round(2))

    # 4. Duplicados
    exact_duplicates = df.duplicated().sum()
    key_duplicates = df.duplicated(
        subset=["date", "state"]
    ).sum()

    # 5. Estadisticas descriptivas
    numeric_stats = df.describe().T
    numeric_stats.to_csv(OUTPUT / "numeric_statistics.csv")

    # 6. Estados y fechas
    dates = pd.to_datetime(
        df["date"].astype(str),
        format="%Y%m%d",
        errors="coerce"
    )

    states = sorted(df["state"].dropna().unique())

    # 7. Resumen general
    summary = [
        "AUDITORIA INICIAL DEL DATASET COVID-19",
        "=" * 50,
        f"Registros: {len(df)}",
        f"Columnas: {len(df.columns)}",
        f"Estados/territorios: {len(states)}",
        f"Fecha inicial: {dates.min()}",
        f"Fecha final: {dates.max()}",
        f"Duplicados exactos: {exact_duplicates}",
        f"Duplicados por fecha y estado: {key_duplicates}",
        f"Columnas con nulos: {(df.isna().sum() > 0).sum()}",
        f"Columnas completamente vacias: {(df.isna().all()).sum()}",
        "",
        "ESTADOS Y TERRITORIOS:",
        ", ".join(states),
    ]

    report = "\n".join(summary)

    (OUTPUT / "audit_summary.txt").write_text(
        report,
        encoding="utf-8"
    )

    print("\n--- RESUMEN ---")
    print(report)

    print(f"\nInformes guardados en: {OUTPUT}")


if __name__ == "__main__":
    audit_dataset()
