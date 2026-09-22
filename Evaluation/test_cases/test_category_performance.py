import pandas as pd
import pytest

from Backend.analytics import analyze_category_performance


DATASET_PATH = "dataset/sales_dataset.csv"


@pytest.fixture
def business_data():
    df = pd.read_csv(DATASET_PATH)
    return df


def test_category_count(business_data):
    result = analyze_category_performance(business_data)

    category_data = result["category_analysis"]

    assert len(category_data) == 5


def test_highest_revenue_category(business_data):
    result = analyze_category_performance(business_data)

    assert result["highest_revenue_category"] == "Computing"


def test_highest_profit_category(business_data):
    result = analyze_category_performance(business_data)

    assert result["highest_profit_category"] == "Computing"


def test_highest_margin_category(business_data):
    result = analyze_category_performance(business_data)

    assert result["highest_margin_category"] == "Audio"


def test_revenue_share_sum(business_data):
    result = analyze_category_performance(business_data)

    category_data = result["category_analysis"]

    total_share = category_data["revenue_share_percent"].sum()

    assert total_share == pytest.approx(100.0, abs=0.01)


def test_total_revenue_matches_dataset(business_data):
    result = analyze_category_performance(business_data)

    category_data = result["category_analysis"]

    assert category_data["total_revenue"].sum() == pytest.approx(
        business_data["revenue"].sum()
    )


def test_total_profit_matches_dataset(business_data):
    result = analyze_category_performance(business_data)

    category_data = result["category_analysis"]

    assert category_data["total_profit"].sum() == pytest.approx(
        business_data["profit"].sum()
    )


def test_missing_category_column():
    df = pd.DataFrame({
        "revenue": [100, 200],
        "profit": [20, 40],
        "units": [1, 2],
        "profit_margin_percent": [20, 20]
    })

    with pytest.raises(KeyError):
        analyze_category_performance(df)


def test_empty_dataframe():
    df = pd.DataFrame(columns=[
        "category",
        "revenue",
        "profit",
        "units",
        "profit_margin_percent"
    ])

    result = analyze_category_performance(df)

    assert result["category_analysis"].empty