from pathlib import Path

from src import (
    download_data,
    audit_raw_data,
    analyze_missingness,
    analyze_state_coverage,
    analyze_data_quality,
    analyze_temporal_quality,
)


ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_FILE = ROOT / "data" / "raw" / "covid_us_states_daily.csv"


def run_pipeline(download=False):
    """
    Execute the complete COVID-19 data audit pipeline.

    Parameters
    ----------
    download : bool
        If True, download the latest dataset before running audits.

    Returns
    -------
    dict
        Pipeline execution summary.
    """

    total_steps = 5 + int(download)
    current_step = 0

    print("\n========== COVID-19 EDA PIPELINE ==========")

    if download:
        current_step += 1
        print(f"\n[{current_step}/{total_steps}] Downloading dataset...")
        download_data.download_dataset()

    if not RAW_DATA_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {RAW_DATA_FILE}. "
            "Run the pipeline with download=True to download it."
        )

    audits = [
        ("Running raw data audit...", audit_raw_data.audit_dataset),
        ("Analyzing missing values...", analyze_missingness.analyze_missingness),
        ("Analyzing state coverage...", analyze_state_coverage.analyze_state_coverage),
        ("Analyzing data quality...", analyze_data_quality.main),
        ("Analyzing temporal quality...", analyze_temporal_quality.main),
    ]

    for description, audit_function in audits:
        current_step += 1
        print(f"\n[{current_step}/{total_steps}] {description}")
        audit_function()

    print("\n========== PIPELINE COMPLETED ==========")

    return {
        "status": "success",
        "downloaded": download,
    }


if __name__ == "__main__":
    run_pipeline()
