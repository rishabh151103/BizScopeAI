import pandas as pd
import pytest

from Backend.analytics import analyze_customer_performance


DATASET_PATH = "dataset/sales_dataset.csv"


@pytest.fixture
def business_data():
    df = pd.read_csv(DATASET_PATH)
    return df


def test_customer_count(business_data):
    result = analyze_customer_performance(business_data)

    customer_data = result["customer_analysis"]

    assert len(customer_data) == 242


def test_highest_revenue_customer(business_data):
    result = analyze_customer_performance(business_data)

    assert result["highest_revenue_customer"] == 1050


def test_highest_profit_customer(business_data):
    result = analyze_customer_performance(business_data)

    assert result["highest_profit_customer"] == 1050


def test_total_revenue_matches_dataset(business_data):
    result = analyze_customer_performance(business_data)

    customer_data = result["customer_analysis"]

    assert customer_data["total_revenue"].sum() == pytest.approx(
        business_data["revenue"].sum()
    )


def test_total_profit_matches_dataset(business_data):
    result = analyze_customer_performance(business_data)

    customer_data = result["customer_analysis"]

    assert customer_data["total_profit"].sum() == pytest.approx(
        business_data["profit"].sum()
    )


def test_customer_order_counts(business_data):
    result = analyze_customer_performance(business_data)

    customer_data = result["customer_analysis"]

    expected_orders = (
        business_data.groupby("customer_id")["order_id"]
        .nunique()
    )

    actual_orders = customer_data.set_index("customer_id")["total_orders"]

    pd.testing.assert_series_equal(
        actual_orders.sort_index(),
        expected_orders.sort_index(),
        check_names=False
    )


def test_missing_customer_id_column():
    df = pd.DataFrame({
        "revenue": [100, 200],
        "profit": [20, 40],
        "order_id": [1, 2],
        "units": [1, 2]
    })

    with pytest.raises(KeyError):
        analyze_customer_performance(df)


def test_empty_dataframe():
    df = pd.DataFrame(columns=[
        "customer_id",
        "revenue",
        "profit",
        "order_id",
        "units"
    ])

    with pytest.raises((ValueError, KeyError)):
        analyze_customer_performance(df)