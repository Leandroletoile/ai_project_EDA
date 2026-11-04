import pandas as pd

from src.analyze_data_quality import (
    analyze_negative_values,
    analyze_negative_values_by_state,
    analyze_constant_columns,
)


def test_analyze_negative_values_detects_all_negative_variables():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]),
        "state": ["CA", "NY", "CA"],
        "positiveIncrease": [-1, 0, 0],
        "negativeIncrease": [0, -2, 0],
        "totalTestResultsIncrease": [0, 0, 0],
        "deathIncrease": [0, 0, 0],
        "hospitalizedIncrease": [0, 0, -3],
    })

    result = analyze_negative_values(df)

    assert len(result) == 3
    assert set(result["variable"]) == {
        "positiveIncrease",
        "negativeIncrease",
        "hospitalizedIncrease",
    }


def test_analyze_negative_values_by_state_counts_correctly():
    negative_df = pd.DataFrame({
        "date": pd.to_datetime([
            "2020-01-01",
            "2020-01-02",
            "2020-01-03",
        ]),
        "state": ["CA", "CA", "NY"],
        "variable": [
            "positiveIncrease",
            "positiveIncrease",
            "deathIncrease",
        ],
        "value": [-1, -2, -3],
    })

    result = analyze_negative_values_by_state(negative_df)

    california = result[
        (result["state"] == "CA")
        & (result["variable"] == "positiveIncrease")
    ]

    assert california.iloc[0]["negative_records"] == 2


def test_analyze_constant_columns_detects_constant_and_empty():
    df = pd.DataFrame({
        "constant": [0, 0, 0],
        "empty": [None, None, None],
        "variable": [1, 2, 3],
    })

    result = analyze_constant_columns(df)

    detected = set(result["variable"])

    assert detected == {"constant", "empty"}

def test_analyze_negative_values_returns_empty_dataframe_when_no_negatives():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2020-01-01", "2020-01-02"]),
        "state": ["CA", "NY"],
        "positiveIncrease": [1, 2],
        "negativeIncrease": [3, 4],
        "totalTestResultsIncrease": [5, 6],
        "deathIncrease": [0, 1],
        "hospitalizedIncrease": [2, 3],
    })

    result = analyze_negative_values(df)

    assert result.empty
    assert list(result.columns) == [
        "date", "state", "variable", "value"
    ]


def test_analyze_negative_values_by_state_handles_empty_dataframe():
    empty_df = pd.DataFrame(
        columns=["date", "state", "variable", "value"]
    )

    result = analyze_negative_values_by_state(empty_df)

    assert result.empty
    assert list(result.columns) == [
        "variable", "state", "negative_records"
    ]

def test_analyze_constant_columns_handles_nulls_with_one_valid_value():
    df = pd.DataFrame({
        "constant_with_nulls": [5, None, 5, None],
        "variable": [1, 2, 3, 4],
    })

    result = analyze_constant_columns(df)

    row = result[
        result["variable"] == "constant_with_nulls"
    ].iloc[0]

    assert row["unique_values"] == 1
    assert row["null_values"] == 2
    assert row["is_constant"]
    assert not row["is_empty"]


def test_analyze_constant_columns_does_not_classify_empty_as_constant():
    df = pd.DataFrame({
        "empty": [None, None, None],
    })

    result = analyze_constant_columns(df)

    row = result.iloc[0]

    assert row["unique_values"] == 0
    assert row["is_empty"]
    assert not row["is_constant"]


def test_analyze_constant_columns_handles_empty_dataframe():
    df = pd.DataFrame({
        "first": pd.Series(dtype="float64"),
        "second": pd.Series(dtype="object"),
    })

    result = analyze_constant_columns(df)

    assert set(result["variable"]) == {"first", "second"}
    assert result["is_empty"].all()
    assert not result["is_constant"].any()

