import pandas as pd
import numpy as np
import pytest

from Backend.analytics import analyze_revenue_trend


def test_empty_dataframe():
    df = pd.DataFrame(columns=["date", "revenue"])

    with pytest.raises(ValueError):
        analyze_revenue_trend(df)


def test_missing_date_column():
    df = pd.DataFrame({
        "revenue": [100, 200, 300]
    })

    with pytest.raises(ValueError):
        analyze_revenue_trend(df)


def test_missing_revenue_column():
    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2025-01-01",
            "2025-02-01",
            "2025-03-01"
        ])
    })

    with pytest.raises(ValueError):
        analyze_revenue_trend(df)


def test_invalid_date_values():
    df = pd.DataFrame({
        "date": ["not-a-date", "2025-02-01"],
        "revenue": [100, 200]
    })

    with pytest.raises(ValueError):
        analyze_revenue_trend(df)


def test_zero_revenue_previous_month():
    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2025-01-01",
            "2025-02-01"
        ]),
        "revenue": [0, 200]
    })

    result = analyze_revenue_trend(df)

    assert np.isnan(
        result["monthly_revenue"].iloc[1]["percentage_change"]
    )


def test_zero_revenue_first_month():
    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2025-01-01",
            "2025-02-01"
        ]),
        "revenue": [0, 200]
    })

    result = analyze_revenue_trend(df)

    assert np.isnan(result["overall_change_percent"])
    assert result["trend"]=="undefined"


def test_single_month_dataset():
    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2025-01-01"
        ]),
        "revenue": [1000]
    })

    result = analyze_revenue_trend(df)

    assert len(result["monthly_revenue"]) == 1
    assert np.isnan(
        result["monthly_revenue"].iloc[0]["percentage_change"]
    )
    assert result["overall_change_percent"] == 0
    assert result["trend"] == "stable"