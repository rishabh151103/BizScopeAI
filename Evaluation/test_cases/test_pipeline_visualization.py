import pandas as pd
import pytest

from Backend.pipeline import (
    run_analysis,
    run_visualization,
)
from Backend.schema_mapper import map_business_columns


def create_test_dataframe():
    return pd.DataFrame({
        "date": pd.to_datetime([
            "2025-01-01",
            "2025-01-15",
            "2025-02-01",
            "2025-02-15",
        ]),
        "product": [
            "Laptop",
            "Monitor",
            "Laptop",
            "Monitor",
        ],
        "revenue": [
            1000,
            1500,
            1200,
            1800,
        ],
        "profit": [
            200,
            300,
            240,
            360,
        ],
        "cost": [
            800,
            1200,
            960,
            1440,
        ],
        "order_id": ["A", "B", "C", "D"],
        "units": [
            10,
            15,
            12,
            18,
        ],
        "profit_margin_percent": [
            20.0,
            20.0,
            20.0,
            20.0,
        ],
    })


def test_run_revenue_visualization():

    df = create_test_dataframe()

    mapping = map_business_columns(df)

    analysis = run_analysis(
        df,
        mapping,
        "revenue_trend"
    )

    figure = run_visualization(
        "revenue_trend",
        analysis
    )

    assert figure is not None
    assert len(figure.data) == 1


def test_run_profitability_visualization():

    df = create_test_dataframe()

    mapping = map_business_columns(df)

    analysis = run_analysis(
        df,
        mapping,
        "profitability"
    )

    figure = run_visualization(
        "profitability",
        analysis
    )

    assert figure is not None
    assert len(figure.data) == 1


def test_run_monthly_performance_visualization_uses_analysis_result_key():
    df = create_test_dataframe()
    mapping = map_business_columns(df)

    analysis = run_analysis(df, mapping, "monthly_performance")
    figure = run_visualization("monthly_performance", analysis)

    assert figure is not None
    assert len(figure.data) == 2


def test_run_product_performance_visualization_is_registered():
    df = create_test_dataframe()
    mapping = map_business_columns(df)

    analysis = run_analysis(df, mapping, "product_performance")
    figure = run_visualization("product_performance", analysis)

    assert figure is not None
    assert len(figure.data) == 2


def test_run_outlier_visualization_uses_analytic_summary():
    analysis = {
        "outlier_summary": {
            "revenue": {"outlier_count": 2},
            "profit": {"outlier_count": 1},
        }
    }

    figure = run_visualization("outliers", analysis)

    assert figure is not None
    assert len(figure.data) == 1
    assert list(figure.data[0].y) == [2, 1]


def test_run_marketing_visualization_uses_analytic_result_field_names():
    analysis = {
        "total_marketing_spend": 100,
        "total_revenue": 500,
        "total_profit": 125,
        "marketing_spend_percent_of_revenue": 20,
        "revenue_per_marketing_spend": 5,
        "profit_per_marketing_spend": 1.25,
    }

    figure = run_visualization("marketing_performance", analysis)

    assert figure is not None
    assert len(figure.data) == 1
    assert list(figure.data[0].y) == [100, 500, 125]


def test_run_business_comparison_visualization_accepts_analytic_groups():
    analysis = run_analysis(
        create_test_dataframe(),
        map_business_columns(create_test_dataframe()),
        "business_comparisons",
    )

    figure = run_visualization("business_comparisons", analysis)

    assert figure is not None
    assert len(figure.data) == 2


def test_unknown_visualization_raises_error():

    with pytest.raises(
        ValueError,
        match="No visualization registered"
    ):
        run_visualization(
            "does_not_exist",
            {}
        )
