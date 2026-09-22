import pandas as pd
import pytest

from Backend.analytics import analyze_customer_type


DATASET_PATH = "dataset/sales_dataset.csv"


@pytest.fixture
def business_data():
    df = pd.read_csv(DATASET_PATH)
    return df


def test_customer_type_count(business_data):
    result = analyze_customer_type(business_data)

    customer_type_data = result["customer_type_analysis"]

    assert len(customer_type_data) == 2


def test_customer_types_exist(business_data):
    result = analyze_customer_type(business_data)

    customer_type_data = result["customer_type_analysis"]

    assert set(customer_type_data["customer_type"]) == {
        "New",
        "Returning"
    }


def test_revenue_share_sum(business_data):
    result = analyze_customer_type(business_data)

    customer_type_data = result["customer_type_analysis"]

    total_share = customer_type_data["revenue_share_percent"].sum()

    assert total_share == pytest.approx(100.0, abs=0.01)


def test_total_revenue_matches_dataset(business_data):
    result = analyze_customer_type(business_data)

    customer_type_data = result["customer_type_analysis"]

    assert customer_type_data["total_revenue"].sum() == pytest.approx(
        business_data["revenue"].sum()
    )


def test_total_profit_matches_dataset(business_data):
    result = analyze_customer_type(business_data)

    customer_type_data = result["customer_type_analysis"]

    assert customer_type_data["total_profit"].sum() == pytest.approx(
        business_data["profit"].sum()
    )


def test_total_orders_matches_dataset(business_data):
    result = analyze_customer_type(business_data)

    customer_type_data = result["customer_type_analysis"]

    assert customer_type_data["total_orders"].sum() == pytest.approx(
        business_data["order_id"].nunique()
    )


def test_missing_customer_type_column():
    df = pd.DataFrame({
        "revenue": [100, 200],
        "profit": [20, 40],
        "order_id": [1, 2],
        "units": [1, 2],
        "profit_margin_percent": [20, 20]
    })

    with pytest.raises(KeyError):
        analyze_customer_type(df)


def test_empty_dataframe():
    df = pd.DataFrame(columns=[
        "customer_type",
        "revenue",
        "profit",
        "order_id",
        "units",
        "profit_margin_percent"
    ])

    result = analyze_customer_type(df)

    assert result["customer_type_analysis"].empty