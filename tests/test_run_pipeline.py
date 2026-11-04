from pathlib import Path

import pytest

from src import run_pipeline


def test_pipeline_fails_when_raw_dataset_does_not_exist(tmp_path, monkeypatch):
    missing_file = tmp_path / "missing.csv"

    monkeypatch.setattr(
        run_pipeline,
        "RAW_DATA_FILE",
        missing_file,
    )

    with pytest.raises(FileNotFoundError, match="Dataset"):
        run_pipeline.run_pipeline()


def test_pipeline_executes_all_audits_in_order(tmp_path, monkeypatch):
    raw_file = tmp_path / "covid.csv"
    raw_file.write_text("date,state\n20200101,CA\n", encoding="utf-8")

    monkeypatch.setattr(
        run_pipeline,
        "RAW_DATA_FILE",
        raw_file,
    )

    executed = []

    monkeypatch.setattr(
        run_pipeline.audit_raw_data,
        "audit_dataset",
        lambda: executed.append("raw_audit"),
    )
    monkeypatch.setattr(
        run_pipeline.analyze_missingness,
        "analyze_missingness",
        lambda: executed.append("missingness"),
    )
    monkeypatch.setattr(
        run_pipeline.analyze_state_coverage,
        "analyze_state_coverage",
        lambda: executed.append("state_coverage"),
    )
    monkeypatch.setattr(
        run_pipeline.analyze_data_quality,
        "main",
        lambda: executed.append("data_quality"),
    )
    monkeypatch.setattr(
        run_pipeline.analyze_temporal_quality,
        "main",
        lambda: executed.append("temporal_quality"),
    )

    result = run_pipeline.run_pipeline()

    assert executed == [
        "raw_audit",
        "missingness",
        "state_coverage",
        "data_quality",
        "temporal_quality",
    ]

    assert result["status"] == "success"
    assert result["downloaded"] is False


def test_pipeline_downloads_before_running_audits(tmp_path, monkeypatch):
    raw_file = tmp_path / "covid.csv"
    executed = []

    monkeypatch.setattr(
        run_pipeline,
        "RAW_DATA_FILE",
        raw_file,
    )

    def fake_download():
        executed.append("download")
        raw_file.write_text(
            "date,state\n20200101,CA\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        run_pipeline.download_data,
        "download_dataset",
        fake_download,
    )

    monkeypatch.setattr(
        run_pipeline.audit_raw_data,
        "audit_dataset",
        lambda: executed.append("raw_audit"),
    )
    monkeypatch.setattr(
        run_pipeline.analyze_missingness,
        "analyze_missingness",
        lambda: executed.append("missingness"),
    )
    monkeypatch.setattr(
        run_pipeline.analyze_state_coverage,
        "analyze_state_coverage",
        lambda: executed.append("state_coverage"),
    )
    monkeypatch.setattr(
        run_pipeline.analyze_data_quality,
        "main",
        lambda: executed.append("data_quality"),
    )
    monkeypatch.setattr(
        run_pipeline.analyze_temporal_quality,
        "main",
        lambda: executed.append("temporal_quality"),
    )

    result = run_pipeline.run_pipeline(download=True)

    assert executed == [
        "download",
        "raw_audit",
        "missingness",
        "state_coverage",
        "data_quality",
        "temporal_quality",
    ]

    assert result["status"] == "success"
    assert result["downloaded"] is True
