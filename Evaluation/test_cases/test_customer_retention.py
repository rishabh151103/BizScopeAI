from pathlib import Path

import pandas as pd
import pytest

from Backend.analytics import analyze_customer_retention


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "dataset" / "sales_dataset.csv"


@pytest.fixture
def business_data():
    return pd.read_csv(DATASET_PATH)


def test_total_customers(business_data):
    result = analyze_customer_retention(business_data)

    assert result["total_customers"] == 242


def test_repeat_customers(business_data):
    result = analyze_customer_retention(business_data)

    assert result["repeat_customers"] == 228


def test_one_time_customers(business_data):
    result = analyze_customer_retention(business_data)

    assert result["one_time_customers"] == 14


def test_customer_counts_reconcile(business_data):
    result = analyze_customer_retention(business_data)

    assert (
        result["repeat_customers"]
        + result["one_time_customers"]
        == result["total_customers"]
    )


def test_repeat_customer_share(business_data):
    result = analyze_customer_retention(business_data)

    expected = (
        result["repeat_customers"]
        / result["total_customers"]
    ) * 100

    assert result["repeat_customer_share_percent"] == pytest.approx(
        expected
    )


def test_repeat_customer_share_expected_value(business_data):
    result = analyze_customer_retention(business_data)

    assert result["repeat_customer_share_percent"] == pytest.approx(
        94.214876,
        abs=1e-5
    )


def test_repeat_revenue_share(business_data):
    result = analyze_customer_retention(business_data)

    expected = (
        result["repeat_customer_revenue"]
        / result["customer_analysis"]["total_revenue"].sum()
    ) * 100

    assert result["repeat_revenue_share_percent"] == pytest.approx(
        expected
    )


def test_repeat_revenue_share_expected_value(business_data):
    result = analyze_customer_retention(business_data)

    assert result["repeat_revenue_share_percent"] == pytest.approx(
        99.6312,
        abs=1e-4
    )


def test_customer_analysis_structure(business_data):
    result = analyze_customer_retention(business_data)

    customer_analysis = result["customer_analysis"]

    expected_columns = [
        "customer_id",
        "total_orders",
        "total_revenue",
        "total_profit"
    ]

    assert list(customer_analysis.columns) == expected_columns
    assert len(customer_analysis) == 242