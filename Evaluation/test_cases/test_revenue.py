import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from Backend.analytics import analyze_revenue_trend


DATASET_PATH = PROJECT_ROOT / "dataset" / "sales_dataset.csv"


@pytest.fixture
def business_data():
    df = pd.read_csv(DATASET_PATH)
    df["date"] = pd.to_datetime(df["date"])
    return df


def test_revenue_trend(business_data):
    result = analyze_revenue_trend(business_data)

    assert result["trend"] == "decreasing"

    assert result["overall_change_percent"] == pytest.approx(
        -39.66686883554345,
        rel=1e-5
    )


def test_monthly_revenue_change(business_data):
    result = analyze_revenue_trend(business_data)

    percentage_changes = result["monthly_revenue"]["percentage_change"]

    # February compared with January
    assert percentage_changes.iloc[1] == pytest.approx(
        -39.891505,
        rel=1e-5
    )

    # March compared with February
    assert percentage_changes.iloc[2] == pytest.approx(
        49.589891,
        rel=1e-5
    )


def test_monthly_revenue_values(business_data):
    result = analyze_revenue_trend(business_data)

    monthly_revenue = result["monthly_revenue"]

    # January revenue
    assert monthly_revenue.iloc[0]["revenue"] == pytest.approx(
        5778106.66,
        rel=1e-5
    )

    # December revenue
    assert monthly_revenue.iloc[-1]["revenue"] == pytest.approx(
        3486112.67,
        rel=1e-5
    )


def test_revenue_month_count(business_data):
    result = analyze_revenue_trend(business_data)

    monthly_revenue = result["monthly_revenue"]

    assert len(monthly_revenue) == 12


def test_revenue_change_direction(business_data):
    result = analyze_revenue_trend(business_data)

    monthly_revenue = result["monthly_revenue"]

    # February decreased
    assert monthly_revenue.iloc[1]["percentage_change"] < 0

    # March increased
    assert monthly_revenue.iloc[2]["percentage_change"] > 0    