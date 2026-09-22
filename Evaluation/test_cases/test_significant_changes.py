from pathlib import Path

import pandas as pd
import pytest

from Backend.analytics import analyze_significant_changes


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "dataset" / "sales_dataset.csv"


@pytest.fixture
def business_data():
    df = pd.read_csv(DATASET_PATH)
    df["date"] = pd.to_datetime(df["date"])
    return df


def test_monthly_changes_count(business_data):
    result = analyze_significant_changes(business_data)

    monthly_changes = result["monthly_changes"]

    assert len(monthly_changes) == 12


def test_monthly_changes_columns(business_data):
    result = analyze_significant_changes(business_data)

    monthly_changes = result["monthly_changes"]

    expected_columns = [
        "month",
        "revenue",
        "profit",
        "revenue_change_percent",
        "profit_change_percent"
    ]

    assert list(monthly_changes.columns) == expected_columns


def test_largest_revenue_increase(business_data):
    result = analyze_significant_changes(business_data)

    increase = result["largest_revenue_increase"]

    assert increase["month"] == "2025-03"
    assert increase["change_percent"] == pytest.approx(
        49.589891,
        abs=1e-5
    )


def test_largest_revenue_decrease(business_data):
    result = analyze_significant_changes(business_data)

    decrease = result["largest_revenue_decrease"]

    assert decrease["month"] == "2025-02"
    assert decrease["change_percent"] == pytest.approx(
        -39.891505,
        abs=1e-5
    )


def test_largest_profit_increase(business_data):
    result = analyze_significant_changes(business_data)

    increase = result["largest_profit_increase"]

    assert increase["month"] == "2025-03"
    assert increase["change_percent"] == pytest.approx(
        61.772770,
        abs=1e-5
    )


def test_largest_profit_decrease(business_data):
    result = analyze_significant_changes(business_data)

    decrease = result["largest_profit_decrease"]

    assert decrease["month"] == "2025-02"
    assert decrease["change_percent"] == pytest.approx(
        -41.736638,
        abs=1e-5
    )


def test_first_month_changes_are_nan(business_data):
    result = analyze_significant_changes(business_data)

    monthly_changes = result["monthly_changes"]

    assert pd.isna(
        monthly_changes.iloc[0]["revenue_change_percent"]
    )

    assert pd.isna(
        monthly_changes.iloc[0]["profit_change_percent"]
    )


def test_revenue_reconciliation(business_data):
    result = analyze_significant_changes(business_data)

    monthly_changes = result["monthly_changes"]

    assert monthly_changes["revenue"].sum() == pytest.approx(
        business_data["revenue"].sum()
    )


def test_profit_reconciliation(business_data):
    result = analyze_significant_changes(business_data)

    monthly_changes = result["monthly_changes"]

    assert monthly_changes["profit"].sum() == pytest.approx(
        business_data["profit"].sum()
    )