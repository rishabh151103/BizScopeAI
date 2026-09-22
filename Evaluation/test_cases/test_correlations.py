from pathlib import Path

import pandas as pd
import pytest

from Backend.analytics import analyze_correlations


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "dataset" / "sales_dataset.csv"


@pytest.fixture
def business_data():
    df = pd.read_csv(DATASET_PATH)
    return df


def test_correlation_matrix_shape(business_data):
    result = analyze_correlations(business_data)

    correlation_matrix = result["correlation_matrix"]

    assert correlation_matrix.shape == (7, 7)


def test_correlation_matrix_columns(business_data):
    result = analyze_correlations(business_data)

    correlation_matrix = result["correlation_matrix"]

    expected_columns = [
        "units",
        "unit_price",
        "revenue",
        "cost",
        "marketing_spend",
        "profit",
        "profit_margin_percent"
    ]

    assert list(correlation_matrix.columns) == expected_columns
    assert list(correlation_matrix.index) == expected_columns


def test_correlation_matrix_diagonal(business_data):
    result = analyze_correlations(business_data)

    correlation_matrix = result["correlation_matrix"]

    for column in correlation_matrix.columns:
        assert correlation_matrix.loc[column, column] == pytest.approx(1.0)


def test_correlation_matrix_is_symmetric(business_data):
    result = analyze_correlations(business_data)

    correlation_matrix = result["correlation_matrix"]

    assert correlation_matrix.equals(correlation_matrix.T)


def test_known_correlations(business_data):
    result = analyze_correlations(business_data)

    correlation_matrix = result["correlation_matrix"]

    assert correlation_matrix.loc["units", "revenue"] == pytest.approx(
        0.243453,
        abs=1e-5
    )

    assert correlation_matrix.loc["marketing_spend", "revenue"] == pytest.approx(
        0.917241835,
        abs=1e-5
    )

    assert correlation_matrix.loc[
        "profit_margin_percent", "revenue"
    ] == pytest.approx(
        -0.027520,
        abs=1e-5
    )


def test_correlation_values_are_within_valid_range(business_data):
    result = analyze_correlations(business_data)

    correlation_matrix = result["correlation_matrix"]

    assert ((correlation_matrix >= -1) & (correlation_matrix <= 1)).all().all()


def test_missing_numerical_column():
    df = pd.DataFrame({
        "units": [1, 2, 3],
        "unit_price": [100, 200, 300],
        "revenue": [100, 400, 900],
        "cost": [50, 200, 450],
        "marketing_spend": [10, 20, 30],
        "profit": [50, 200, 450]
    })

    with pytest.raises(KeyError):
        analyze_correlations(df)


def test_empty_dataframe():
    df = pd.DataFrame({
        "units": pd.Series([], dtype=float),
        "unit_price": pd.Series([], dtype=float),
        "revenue": pd.Series([], dtype=float),
        "cost": pd.Series([], dtype=float),
        "marketing_spend": pd.Series([], dtype=float),
        "profit": pd.Series([], dtype=float),
        "profit_margin_percent": pd.Series([], dtype=float)
    })

    result = analyze_correlations(df)

    correlation_matrix = result["correlation_matrix"]

    assert correlation_matrix.shape == (7, 7)