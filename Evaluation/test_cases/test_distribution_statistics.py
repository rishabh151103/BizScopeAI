from pathlib import Path

import pandas as pd
import pytest

from Backend.analytics import analyze_distribution_statistics


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "dataset" / "sales_dataset.csv"


@pytest.fixture
def business_data():
    return pd.read_csv(DATASET_PATH)


def test_statistics_shape(business_data):
    result = analyze_distribution_statistics(business_data)

    statistics = result["distribution_statistics"]

    assert statistics.shape == (7, 7)


def test_statistics_columns(business_data):
    result = analyze_distribution_statistics(business_data)

    statistics = result["distribution_statistics"]

    expected_columns = [
        "mean",
        "median",
        "std",
        "min",
        "max",
        "q25",
        "q75"
    ]

    assert list(statistics.columns) == expected_columns


def test_statistics_index(business_data):
    result = analyze_distribution_statistics(business_data)

    statistics = result["distribution_statistics"]

    expected_columns = [
        "units",
        "unit_price",
        "revenue",
        "cost",
        "marketing_spend",
        "profit",
        "profit_margin_percent"
    ]

    assert list(statistics.index) == expected_columns


def test_revenue_statistics(business_data):
    result = analyze_distribution_statistics(business_data)

    statistics = result["distribution_statistics"]

    revenue = business_data["revenue"]

    assert statistics.loc["revenue", "mean"] == pytest.approx(
        revenue.mean()
    )

    assert statistics.loc["revenue", "median"] == pytest.approx(
        revenue.median()
    )

    assert statistics.loc["revenue", "std"] == pytest.approx(
        revenue.std()
    )


def test_revenue_min_max(business_data):
    result = analyze_distribution_statistics(business_data)

    statistics = result["distribution_statistics"]

    revenue = business_data["revenue"]

    assert statistics.loc["revenue", "min"] == pytest.approx(
        revenue.min()
    )

    assert statistics.loc["revenue", "max"] == pytest.approx(
        revenue.max()
    )


def test_revenue_quartiles(business_data):
    result = analyze_distribution_statistics(business_data)

    statistics = result["distribution_statistics"]

    revenue = business_data["revenue"]

    assert statistics.loc["revenue", "q25"] == pytest.approx(
        revenue.quantile(0.25)
    )

    assert statistics.loc["revenue", "q75"] == pytest.approx(
        revenue.quantile(0.75)
    )


def test_profit_margin_statistics(business_data):
    result = analyze_distribution_statistics(business_data)

    statistics = result["distribution_statistics"]

    margin = business_data["profit_margin_percent"]

    assert statistics.loc[
        "profit_margin_percent", "mean"
    ] == pytest.approx(margin.mean())

    assert statistics.loc[
        "profit_margin_percent", "median"
    ] == pytest.approx(margin.median())


def test_all_statistics_are_numeric(business_data):
    result = analyze_distribution_statistics(business_data)

    statistics = result["distribution_statistics"]

    assert all(
        pd.api.types.is_numeric_dtype(statistics[column])
        for column in statistics.columns
    )