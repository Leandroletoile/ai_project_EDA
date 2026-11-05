"""Procesamiento reproducible: carga -> limpia -> enriquece -> guarda -> informe de calidad.

Uso (desde la raíz del repositorio, con el entorno virtual activado):

    python -m src.run_processing

Opciones:
    --download   descarga antes el dataset con src.download_data

Qué genera:
    data/processed/covid_clean.csv                    datos limpios + variables nuevas
    reports/data_quality/informe_calidad_datos.md     qué faltaba, qué se corrigió, qué quedó pendiente
    reports/data_quality/informe_calidad_datos.json   las mismas cifras en formato máquina
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src import build_features, clean_data, quality_report

ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_FILE = ROOT / "data" / "raw" / "covid_us_states_daily.csv"
POPULATION_FILE = ROOT / "data" / "external" / "population_2019.csv"
PROCESSED_FILE = ROOT / "data" / "processed" / "covid_clean.csv"
QUALITY_REPORT_FILE = ROOT / "reports" / "data_quality" / "informe_calidad_datos.md"


def run_processing(
    raw_path=RAW_DATA_FILE,
    population_path=POPULATION_FILE,
    out_path=PROCESSED_FILE,
    report_path=QUALITY_REPORT_FILE,
) -> pd.DataFrame:
    """Ejecuta todo el procesamiento y devuelve el DataFrame final."""
    raw_path = Path(raw_path)
    if not raw_path.exists():
        raise FileNotFoundError(
            f"Dataset no encontrado: {raw_path}. Ejecuta con --download para descargarlo."
        )

    raw = clean_data.load_raw(raw_path)
    clean, report = clean_data.clean_pipeline(raw)

    population = pd.read_csv(population_path)
    enriched = build_features.add_features(build_features.add_population(clean, population))
    report["positivity_over_100_rows"] = int(
        (build_features.positivity_7d(enriched, cap=False) > 100).sum()
    )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(out_path, index=False)

    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        quality_report.build_quality_report(raw, clean, report), encoding="utf-8"
    )
    report_path.with_suffix(".json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return enriched


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--download", action="store_true", help="descarga el dataset antes de procesarlo")
    args = parser.parse_args(argv)

    if args.download:
        from src import download_data  # import tardío: solo hace falta con --download

        download_data.download_dataset()

    df = run_processing()
    print(f"OK: {len(df):,} filas x {df.shape[1]} columnas -> {PROCESSED_FILE}")
    print(f"Informe de calidad -> {QUALITY_REPORT_FILE}")


if __name__ == "__main__":
    main()
