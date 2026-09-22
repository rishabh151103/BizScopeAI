import pandas as pd
import pytest

from Backend.analytics import analyze_regional_performance


DATASET_PATH = "dataset/sales_dataset.csv"


@pytest.fixture
def business_data():
    df = pd.read_csv(DATASET_PATH)
    return df


def test_region_count(business_data):
    result = analyze_regional_performance(business_data)

    regional_data = result["regional_analysis"]

    assert len(regional_data) == 4


def test_highest_revenue_region(business_data):
    result = analyze_regional_performance(business_data)

    assert result["highest_revenue_region"] == "West"


def test_highest_profit_region(business_data):
    result = analyze_regional_performance(business_data)

    assert result["highest_profit_region"] == "West"


def test_revenue_share_sum(business_data):
    result = analyze_regional_performance(business_data)

    regional_data = result["regional_analysis"]

    total_share = regional_data["revenue_share_percent"].sum()

    assert total_share == pytest.approx(100.0, abs=0.01)


def test_total_revenue_matches_dataset(business_data):
    result = analyze_regional_performance(business_data)

    regional_data = result["regional_analysis"]

    regional_total = regional_data["total_revenue"].sum()
    dataset_total = business_data["revenue"].sum()

    assert regional_total == pytest.approx(dataset_total)


def test_missing_region_column():
    df = pd.DataFrame({
        "revenue": [100, 200, 300],
        "profit": [20, 40, 60],
        "units": [1, 2, 3],
        "profit_margin_percent": [20, 20, 20]
    })

    with pytest.raises(KeyError):
        analyze_regional_performance(df)


def test_empty_dataframe():
    df = pd.DataFrame(columns=[
        "region",
        "revenue",
        "profit",
        "units",
        "profit_margin_percent"
    ])

    with pytest.raises((ValueError, KeyError)):
        analyze_regional_performance(df)


def test_zero_total_revenue():
    df = pd.DataFrame({
        "region": ["North", "South"],
        "revenue": [0, 0],
        "profit": [0, 0],
        "units": [10, 20],
        "profit_margin_percent": [0, 0]
    })

    result = analyze_regional_performance(df)

    assert result["regional_analysis"]["revenue_share_percent"].isna().all()