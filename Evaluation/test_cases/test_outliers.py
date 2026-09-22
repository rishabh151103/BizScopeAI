from pathlib import Path

import pandas as pd
import pytest

from Backend.analytics import analyze_outliers


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "dataset" / "sales_dataset.csv"


@pytest.fixture
def business_data():
    return pd.read_csv(DATASET_PATH)


def test_all_numerical_columns_present(business_data):
    result = analyze_outliers(business_data)

    summary = result["outlier_summary"]

    expected_columns = {
        "units",
        "unit_price",
        "revenue",
        "cost",
        "marketing_spend",
        "profit",
        "profit_margin_percent"
    }

    assert set(summary.keys()) == expected_columns


def test_expected_outlier_counts(business_data):
    result = analyze_outliers(business_data)

    summary = result["outlier_summary"]

    expected = {
        "units": 0,
        "unit_price": 152,
        "revenue": 124,
        "cost": 121,
        "marketing_spend": 138,
        "profit": 128,
        "profit_margin_percent": 0
    }

    for column, expected_count in expected.items():
        assert summary[column]["outlier_count"] == expected_count


def test_revenue_bounds(business_data):
    result = analyze_outliers(business_data)

    revenue_summary = result["outlier_summary"]["revenue"]

    q1 = business_data["revenue"].quantile(0.25)
    q3 = business_data["revenue"].quantile(0.75)

    iqr = q3 - q1

    expected_lower = q1 - (1.5 * iqr)
    expected_upper = q3 + (1.5 * iqr)

    assert revenue_summary["lower_bound"] == pytest.approx(
        expected_lower
    )

    assert revenue_summary["upper_bound"] == pytest.approx(
        expected_upper
    )


def test_profit_bounds(business_data):
    result = analyze_outliers(business_data)

    profit_summary = result["outlier_summary"]["profit"]

    q1 = business_data["profit"].quantile(0.25)
    q3 = business_data["profit"].quantile(0.75)

    iqr = q3 - q1

    assert profit_summary["lower_bound"] == pytest.approx(
        q1 - (1.5 * iqr)
    )

    assert profit_summary["upper_bound"] == pytest.approx(
        q3 + (1.5 * iqr)
    )


def test_lower_bound_less_than_upper_bound(business_data):
    result = analyze_outliers(business_data)

    summary = result["outlier_summary"]

    for column in summary:
        assert (
            summary[column]["lower_bound"]
            <= summary[column]["upper_bound"]
        )


def test_no_unit_outliers(business_data):
    result = analyze_outliers(business_data)

    assert (
        result["outlier_summary"]["units"]["outlier_count"]
        == 0
    )


def test_no_profit_margin_outliers(business_data):
    result = analyze_outliers(business_data)

    assert (
        result["outlier_summary"]
        ["profit_margin_percent"]
        ["outlier_count"]
        == 0
    )


def test_simple_known_outlier():
    df = pd.DataFrame({
        "units": [1, 2, 2, 2, 100],
        "unit_price": [10, 10, 10, 10, 10],
        "revenue": [10, 20, 20, 20, 1000],
        "cost": [5, 10, 10, 10, 500],
        "marketing_spend": [1, 1, 1, 1, 100],
        "profit": [5, 10, 10, 10, 500],
        "profit_margin_percent": [50, 50, 50, 50, 50]
    })

    result = analyze_outliers(df)

    summary = result["outlier_summary"]

    assert summary["units"]["outlier_count"] == 2
    assert summary["revenue"]["outlier_count"] == 2
    assert summary["cost"]["outlier_count"] == 2
    assert summary["marketing_spend"]["outlier_count"] == 1
    assert summary["profit"]["outlier_count"] == 2

    assert summary["unit_price"]["outlier_count"] == 0
    assert summary["profit_margin_percent"]["outlier_count"] == 0