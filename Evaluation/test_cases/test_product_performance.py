import pandas as pd
import pytest

from Backend.analytics import analyze_product_performance


DATASET_PATH = "dataset/sales_dataset.csv"


@pytest.fixture
def business_data():
    df = pd.read_csv(DATASET_PATH)
    return df


def test_product_count(business_data):
    result = analyze_product_performance(business_data)

    product_data = result["product_analysis"]

    assert len(product_data) == 6


def test_highest_revenue_product(business_data):
    result = analyze_product_performance(business_data)

    assert result["highest_revenue_product"] == "Laptop Pro"


def test_highest_profit_product(business_data):
    result = analyze_product_performance(business_data)

    assert result["highest_profit_product"] == "Laptop Pro"


def test_revenue_share_sum(business_data):
    result = analyze_product_performance(business_data)

    product_data = result["product_analysis"]

    total_share = product_data["revenue_share_percent"].sum()

    assert total_share == pytest.approx(100.0, abs=0.01)


def test_total_revenue_matches_dataset(business_data):
    result = analyze_product_performance(business_data)

    product_data = result["product_analysis"]

    product_total = product_data["total_revenue"].sum()
    dataset_total = business_data["revenue"].sum()

    assert product_total == pytest.approx(dataset_total)


def test_missing_product_column():
    df = pd.DataFrame({
        "revenue": [100, 200, 300],
        "profit": [20, 40, 60],
        "units": [1, 2, 3],
        "profit_margin_percent": [20, 20, 20]
    })

    with pytest.raises(KeyError):
        analyze_product_performance(df)


def test_empty_dataframe():
    df = pd.DataFrame(columns=[
        "product",
        "revenue",
        "profit",
        "units",
        "profit_margin_percent"
    ])

    with pytest.raises((ValueError, KeyError)):
        analyze_product_performance(df)

def test_missing_revenue_column():
    df = pd.DataFrame({
        "product": ["A", "B"],
        "profit": [100, 200],
        "units": [10, 20],
        "profit_margin_percent": [10, 20]
    })

    with pytest.raises(KeyError):
        analyze_product_performance(df)

def test_zero_total_revenue():
    df = pd.DataFrame({
        "product": ["A", "B"],
        "revenue": [0, 0],
        "profit": [0, 0],
        "units": [10, 20],
        "profit_margin_percent": [0, 0]
    })

    result = analyze_product_performance(df)

    assert result["product_analysis"]["revenue_share_percent"].isna().all()

                

