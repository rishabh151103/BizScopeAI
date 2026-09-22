from pathlib import Path

import pandas as pd
import pytest

from Backend.analytics import analyze_marketing_performance


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "dataset" / "sales_dataset.csv"


@pytest.fixture
def business_data():
    return pd.read_csv(DATASET_PATH)


def test_total_marketing_spend(business_data):
    result = analyze_marketing_performance(business_data)

    assert result["total_marketing_spend"] == pytest.approx(
        3686389.60,
        abs=0.01
    )


def test_total_revenue(business_data):
    result = analyze_marketing_performance(business_data)

    assert result["total_revenue"] == pytest.approx(
        57907192.64,
        abs=0.01
    )


def test_total_profit(business_data):
    result = analyze_marketing_performance(business_data)

    assert result["total_profit"] == pytest.approx(
        17393449.42,
        abs=0.01
    )


def test_marketing_spend_percent_of_revenue(business_data):
    result = analyze_marketing_performance(business_data)

    expected = (
        business_data["marketing_spend"].sum()
        / business_data["revenue"].sum()
    ) * 100

    assert result["marketing_spend_percent_of_revenue"] == pytest.approx(
        expected
    )


def test_revenue_per_marketing_spend(business_data):
    result = analyze_marketing_performance(business_data)

    expected = (
        business_data["revenue"].sum()
        / business_data["marketing_spend"].sum()
    )

    assert result["revenue_per_marketing_spend"] == pytest.approx(
        expected
    )


def test_profit_per_marketing_spend(business_data):
    result = analyze_marketing_performance(business_data)

    expected = (
        business_data["profit"].sum()
        / business_data["marketing_spend"].sum()
    )

    assert result["profit_per_marketing_spend"] == pytest.approx(
        expected
    )


def test_expected_marketing_metrics(business_data):
    result = analyze_marketing_performance(business_data)

    assert result["marketing_spend_percent_of_revenue"] == pytest.approx(
        6.3660,
        abs=1e-4
    )

    assert result["revenue_per_marketing_spend"] == pytest.approx(
        15.7084,
        abs=1e-4
    )

    assert result["profit_per_marketing_spend"] == pytest.approx(
        4.7183,
        abs=1e-4
    )


def test_all_metrics_present(business_data):
    result = analyze_marketing_performance(business_data)

    expected_keys = {
        "total_marketing_spend",
        "total_revenue",
        "total_profit",
        "marketing_spend_percent_of_revenue",
        "revenue_per_marketing_spend",
        "profit_per_marketing_spend"
    }

    assert set(result.keys()) == expected_keys