from pathlib import Path

import pandas as pd
import pytest

from Backend.analytics import analyze_order_metrics


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "dataset" / "sales_dataset.csv"


@pytest.fixture
def business_data():
    return pd.read_csv(DATASET_PATH)


def test_total_orders(business_data):
    result = analyze_order_metrics(business_data)

    assert result["total_orders"] == 1000


def test_total_revenue(business_data):
    result = analyze_order_metrics(business_data)

    assert result["total_revenue"] == pytest.approx(
        57907192.64,
        abs=0.01
    )


def test_average_order_value(business_data):
    result = analyze_order_metrics(business_data)

    expected = (
        business_data["revenue"].sum()
        / business_data["order_id"].nunique()
    )

    assert result["average_order_value"] == pytest.approx(
        expected
    )


def test_median_order_value(business_data):
    result = analyze_order_metrics(business_data)

    expected = (
        business_data.groupby("order_id")["revenue"]
        .sum()
        .median()
    )

    assert result["median_order_value"] == pytest.approx(
        expected
    )


def test_average_units_per_order(business_data):
    result = analyze_order_metrics(business_data)

    expected = (
        business_data["units"].sum()
        / business_data["order_id"].nunique()
    )

    assert result["average_units_per_order"] == pytest.approx(
        expected
    )


def test_revenue_per_unit(business_data):
    result = analyze_order_metrics(business_data)

    expected = (
        business_data["revenue"].sum()
        / business_data["units"].sum()
    )

    assert result["revenue_per_unit"] == pytest.approx(
        expected
    )


def test_all_metrics_present(business_data):
    result = analyze_order_metrics(business_data)

    expected_keys = {
        "total_orders",
        "total_revenue",
        "average_order_value",
        "median_order_value",
        "average_units_per_order",
        "revenue_per_unit"
    }

    assert set(result.keys()) == expected_keys


def test_multiple_rows_same_order():
    df = pd.DataFrame({
        "order_id": [1, 1, 2],
        "revenue": [100, 50, 200],
        "units": [2, 1, 4]
    })

    result = analyze_order_metrics(df)

    assert result["total_orders"] == 2
    assert result["total_revenue"] == 350

    # Order 1 = 150, Order 2 = 200
    assert result["median_order_value"] == 175

    assert result["average_order_value"] == 175
    assert result["average_units_per_order"] == 3.5
    assert result["revenue_per_unit"] == 50