import pandas as pd
import pytest
from pathlib import Path

from Backend.analytics import analyze_monthly_performance


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET_PATH = PROJECT_ROOT / "dataset" / "sales_dataset.csv"


@pytest.fixture
def business_data():
    df = pd.read_csv(DATASET_PATH)
    df["date"] = pd.to_datetime(df["date"])
    return df


def test_month_count(business_data):
    result = analyze_monthly_performance(business_data)

    monthly_data = result["monthly_analysis"]

    assert len(monthly_data) == 12


def test_monthly_revenue_matches_dataset(business_data):
    result = analyze_monthly_performance(business_data)

    monthly_data = result["monthly_analysis"]

    assert monthly_data["total_revenue"].sum() == pytest.approx(
        business_data["revenue"].sum()
    )


def test_monthly_profit_matches_dataset(business_data):
    result = analyze_monthly_performance(business_data)

    monthly_data = result["monthly_analysis"]

    assert monthly_data["total_profit"].sum() == pytest.approx(
        business_data["profit"].sum()
    )


def test_monthly_cost_matches_dataset(business_data):
    result = analyze_monthly_performance(business_data)

    monthly_data = result["monthly_analysis"]

    assert monthly_data["total_cost"].sum() == pytest.approx(
        business_data["cost"].sum()
    )


def test_monthly_units_match_dataset(business_data):
    result = analyze_monthly_performance(business_data)

    monthly_data = result["monthly_analysis"]

    assert monthly_data["units_sold"].sum() == pytest.approx(
        business_data["units"].sum()
    )


def test_monthly_order_count(business_data):
    result = analyze_monthly_performance(business_data)

    monthly_data = result["monthly_analysis"]

    assert monthly_data["total_orders"].sum() == business_data["order_id"].nunique()


def test_february_revenue_growth(business_data):
    result = analyze_monthly_performance(business_data)

    monthly_data = result["monthly_analysis"]

    february = monthly_data.loc[
        monthly_data["month"] == pd.Period("2025-02", freq="M")
    ].iloc[0]

    assert february["revenue_growth_percent"] == pytest.approx(
        -39.891505,
        abs=1e-5
    )


def test_march_revenue_growth(business_data):
    result = analyze_monthly_performance(business_data)

    monthly_data = result["monthly_analysis"]

    march = monthly_data.loc[
        monthly_data["month"] == pd.Period("2025-03", freq="M")
    ].iloc[0]

    assert march["revenue_growth_percent"] == pytest.approx(
        49.589891,
        abs=1e-5
    )


def test_february_profit_growth(business_data):
    result = analyze_monthly_performance(business_data)

    monthly_data = result["monthly_analysis"]

    february = monthly_data.loc[
        monthly_data["month"] == pd.Period("2025-02", freq="M")
    ].iloc[0]

    assert february["profit_growth_percent"] == pytest.approx(
        -41.736638,
        abs=1e-5
    )


def test_march_profit_growth(business_data):
    result = analyze_monthly_performance(business_data)

    monthly_data = result["monthly_analysis"]

    march = monthly_data.loc[
        monthly_data["month"] == pd.Period("2025-03", freq="M")
    ].iloc[0]

    assert march["profit_growth_percent"] == pytest.approx(
        61.772770,
        abs=1e-5
    )


def test_first_month_growth_is_nan(business_data):
    result = analyze_monthly_performance(business_data)

    monthly_data = result["monthly_analysis"]

    assert pd.isna(monthly_data.iloc[0]["revenue_growth_percent"])
    assert pd.isna(monthly_data.iloc[0]["profit_growth_percent"])


def test_monthly_profit_margin(business_data):
    result = analyze_monthly_performance(business_data)

    monthly_data = result["monthly_analysis"]

    first_month = monthly_data.iloc[0]

    expected_margin = (
        first_month["total_profit"]
        / first_month["total_revenue"]
    ) * 100

    assert first_month["profit_margin_percent"] == pytest.approx(
        expected_margin
    )


def test_missing_date_column():
    df = pd.DataFrame({
        "revenue": [100, 200],
        "cost": [50, 100],
        "profit": [50, 100],
        "units": [1, 2],
        "order_id": [1, 2]
    })

    with pytest.raises(KeyError):
        analyze_monthly_performance(df)


def test_missing_revenue_column():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2025-01-01", "2025-02-01"]),
        "cost": [50, 100],
        "profit": [50, 100],
        "units": [1, 2],
        "order_id": [1, 2]
    })

    with pytest.raises(KeyError):
        analyze_monthly_performance(df)


def test_empty_dataframe():
    df = pd.DataFrame({
        "date": pd.Series([], dtype="datetime64[ns]"),
        "revenue": pd.Series([], dtype=float),
        "cost": pd.Series([], dtype=float),
        "profit": pd.Series([], dtype=float),
        "units": pd.Series([], dtype=float),
        "order_id": pd.Series([], dtype=int)
    })

    result = analyze_monthly_performance(df)

    assert result["monthly_analysis"].empty