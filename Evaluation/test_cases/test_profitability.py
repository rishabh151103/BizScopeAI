import pandas as pd
import pytest

from Backend.analytics import analyze_profitability


DATASET_PATH = "dataset/sales_dataset.csv"


@pytest.fixture
def business_data():
    df = pd.read_csv(DATASET_PATH)
    return df


def test_total_revenue(business_data):
    result = analyze_profitability(business_data)

    assert result["total_revenue"] == pytest.approx(
        business_data["revenue"].sum()
    )


def test_total_cost(business_data):
    result = analyze_profitability(business_data)

    assert result["total_cost"] == pytest.approx(
        business_data["cost"].sum()
    )


def test_total_profit(business_data):
    result = analyze_profitability(business_data)

    assert result["total_profit"] == pytest.approx(
        business_data["profit"].sum()
    )


def test_overall_profit_margin(business_data):
    result = analyze_profitability(business_data)

    expected_margin = (
        business_data["profit"].sum()
        / business_data["revenue"].sum()
    ) * 100

    assert result["overall_profit_margin"] == pytest.approx(
        expected_margin
    )


def test_most_profitable_product(business_data):
    result = analyze_profitability(business_data)

    assert result["most_profitable_product"] == "Laptop Pro"


def test_highest_margin_product(business_data):
    result = analyze_profitability(business_data)

    assert result["highest_margin_product"] == "Headset H"


def test_product_profit_reconciliation(business_data):
    result = analyze_profitability(business_data)

    product_data = result["profit_by_product"]

    assert product_data["total_revenue"].sum() == pytest.approx(
        business_data["revenue"].sum()
    )

    assert product_data["total_cost"].sum() == pytest.approx(
        business_data["cost"].sum()
    )

    assert product_data["total_profit"].sum() == pytest.approx(
        business_data["profit"].sum()
    )


def test_zero_total_revenue():
    df = pd.DataFrame({
        "product": ["A", "B"],
        "revenue": [0, 0],
        "cost": [0, 0],
        "profit": [0, 0]
    })

    result = analyze_profitability(df)

    assert pd.isna(result["overall_profit_margin"])