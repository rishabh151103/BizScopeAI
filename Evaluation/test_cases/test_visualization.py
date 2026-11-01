import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.append(
    str(Path(__file__).resolve().parents[2] / "Backend")
)

from Backend.visualization import (
    plot_revenue_trend,
    plot_monthly_performance,
    plot_product_performance,
    plot_regional_performance,
    plot_category_performance,
    plot_customer_type_performance,
    plot_profitability,
    plot_marketing_performance,
    plot_customer_retention,
    plot_significant_changes,
    plot_segment_changes,
    plot_change_contribution,
    plot_correlations,
    plot_business_comparison,
    plot_customer_performance,
    plot_distribution,
    plot_outliers
    )


def test_plot_revenue_trend_returns_figure():

    monthly_revenue = pd.DataFrame({
        "month": pd.period_range(
            "2025-01",
            periods=3,
            freq="M"
        ),
        "revenue": [
            1000,
            1500,
            1300
        ]
    })

    figure = plot_revenue_trend(monthly_revenue)

    assert figure is not None
    assert len(figure.data) == 1
    assert figure.data[0].type == "scatter"
    assert figure.data[0].mode == "lines+markers"


def test_plot_revenue_trend_missing_column():

    monthly_revenue = pd.DataFrame({
        "month": ["2025-01", "2025-02"],
        "sales": [1000, 1500]
    })

    with pytest.raises(ValueError):

        plot_revenue_trend(monthly_revenue)


def test_plot_revenue_trend_invalid_input():

    with pytest.raises(TypeError):

        plot_revenue_trend("invalid")


def test_plot_revenue_trend_empty_dataframe():

    monthly_revenue = pd.DataFrame(
        columns=["month", "revenue"]
    )

    with pytest.raises(ValueError):

        plot_revenue_trend(monthly_revenue)


def test_plot_monthly_performance_returns_figure():

    monthly_analysis = pd.DataFrame({
        "month": pd.period_range(
            "2025-01",
            periods=3,
            freq="M"
        ),
        "total_revenue": [
            1000,
            1500,
            1300
        ],
        "total_profit": [
            200,
            350,
            250
        ]
    })

    figure = plot_monthly_performance(monthly_analysis)

    assert figure is not None
    assert len(figure.data) == 2


def test_plot_monthly_performance_missing_column():

    monthly_analysis = pd.DataFrame({
        "month": ["2025-01"],
        "total_revenue": [1000]
    })

    with pytest.raises(ValueError):

        plot_monthly_performance(monthly_analysis)


def test_plot_monthly_performance_invalid_input():

    with pytest.raises(TypeError):

        plot_monthly_performance("invalid")


def test_plot_monthly_performance_empty_dataframe():

    monthly_analysis = pd.DataFrame(
        columns=[
            "month",
            "total_revenue",
            "total_profit"
        ]
    )

    with pytest.raises(ValueError):

        plot_monthly_performance(monthly_analysis)


def test_plot_product_performance_returns_figure():

    product_analysis = pd.DataFrame({
        "product": ["Laptop", "Monitor", "Keyboard"],
        "total_revenue": [5000, 3000, 1000],
        "total_profit": [1000, 600, 200]
    })

    figure = plot_product_performance(product_analysis)

    assert figure is not None
    assert len(figure.data) == 2


def test_plot_product_performance_missing_column():

    product_analysis = pd.DataFrame({
        "product": ["Laptop"],
        "total_revenue": [5000]
    })

    with pytest.raises(ValueError):
        plot_product_performance(product_analysis)


def test_plot_product_performance_invalid_input():

    with pytest.raises(TypeError):
        plot_product_performance("invalid")


def test_plot_product_performance_empty_dataframe():

    product_analysis = pd.DataFrame(
        columns=[
            "product",
            "total_revenue",
            "total_profit"
        ]
    )

    with pytest.raises(ValueError):
        plot_product_performance(product_analysis)


def test_plot_regional_performance_returns_figure():

    regional_analysis = pd.DataFrame({
        "region": ["North", "South", "East"],
        "total_revenue": [5000, 3000, 4000],
        "total_profit": [1000, 500, 800]
    })

    figure = plot_regional_performance(regional_analysis)

    assert figure is not None
    assert len(figure.data) == 2


def test_plot_regional_performance_includes_average_margin_when_available():
    regional_analysis = pd.DataFrame({
        "region": ["North", "South"],
        "total_revenue": [5000, 3000],
        "total_profit": [1000, 600],
        "average_profit_margin": [20.0, 20.0],
    })

    figure = plot_regional_performance(regional_analysis)

    assert len(figure.data) == 3
    assert figure.data[-1].name == "Average Profit Margin (%)"
    assert figure.data[-1].yaxis == "y2"
    assert figure.layout.yaxis2.title.text == "Average Profit Margin (%)"


def test_plot_regional_performance_missing_column():

    regional_analysis = pd.DataFrame({
        "region": ["North"],
        "total_revenue": [5000]
    })

    with pytest.raises(ValueError):
        plot_regional_performance(regional_analysis)


def test_plot_regional_performance_invalid_input():

    with pytest.raises(TypeError):
        plot_regional_performance("invalid")


def test_plot_regional_performance_empty_dataframe():

    regional_analysis = pd.DataFrame(
        columns=[
            "region",
            "total_revenue",
            "total_profit"
        ]
    )

    with pytest.raises(ValueError):
        plot_regional_performance(regional_analysis)


def test_plot_category_performance_returns_figure():

    category_analysis = pd.DataFrame({
        "category": ["Technology", "Furniture", "Office"],
        "total_revenue": [5000, 3000, 2000],
        "total_profit": [1200, 400, 500],
        "aggregate_profit_margin": [24.0, 13.3, 25.0],
    })

    figure = plot_category_performance(category_analysis)

    assert figure is not None
    assert len(figure.data) == 2


def test_plot_category_performance_missing_column():

    category_analysis = pd.DataFrame({
        "category": ["Technology"],
        "total_revenue": [5000]
    })

    with pytest.raises(ValueError):
        plot_category_performance(category_analysis)


def test_plot_category_performance_invalid_input():

    with pytest.raises(TypeError):
        plot_category_performance("invalid")


def test_plot_category_performance_empty_dataframe():

    category_analysis = pd.DataFrame(
        columns=[
            "category",
            "total_revenue",
            "total_profit"
        ]
    )

    with pytest.raises(ValueError):
        plot_category_performance(category_analysis)

def test_plot_revenue_trend_converts_period_to_string():

    monthly_revenue = pd.DataFrame({
        "month": pd.period_range(
            "2025-01",
            periods=3,
            freq="M"
        ),
        "revenue": [
            1000,
            1500,
            1300
        ]
    })

    figure = plot_revenue_trend(
        monthly_revenue
    )

    x_values = list(
        figure.data[0].x
    )

    assert all(
        isinstance(value, str)
        for value in x_values
    )      

def test_plot_customer_type_performance_returns_figure():

    customer_type_analysis = pd.DataFrame({
        "customer_type": [
            "New",
            "Returning"
        ],
        "total_revenue": [
            5000,
            8000
        ],
        "total_profit": [
            1000,
            2000
        ]
    })

    figure = plot_customer_type_performance(
        customer_type_analysis
    )

    assert figure is not None
    assert len(figure.data) == 2


def test_plot_customer_type_performance_missing_column():

    customer_type_analysis = pd.DataFrame({
        "customer_type": ["New"],
        "total_revenue": [5000]
    })

    with pytest.raises(ValueError):
        plot_customer_type_performance(
            customer_type_analysis
        )


def test_plot_customer_type_performance_invalid_input():

    with pytest.raises(TypeError):
        plot_customer_type_performance(
            "invalid"
        )


def test_plot_customer_type_performance_empty_dataframe():

    customer_type_analysis = pd.DataFrame(
        columns=[
            "customer_type",
            "total_revenue",
            "total_profit"
        ]
    )

    with pytest.raises(ValueError):
        plot_customer_type_performance(
            customer_type_analysis
        )


def test_plot_profitability_returns_figure():

    profit_by_product = pd.DataFrame({
        "product": [
            "Laptop",
            "Monitor",
            "Keyboard"
        ],
        "profit_margin_percent": [
            20.0,
            15.0,
            25.0
        ]
    })

    figure = plot_profitability(
        profit_by_product
    )

    assert figure is not None
    assert len(figure.data) == 1


def test_plot_profitability_missing_column():

    profit_by_product = pd.DataFrame({
        "product": ["Laptop"]
    })

    with pytest.raises(ValueError):
        plot_profitability(
            profit_by_product
        )


def test_plot_profitability_invalid_input():

    with pytest.raises(TypeError):
        plot_profitability(
            "invalid"
        )


def test_plot_profitability_empty_dataframe():

    profit_by_product = pd.DataFrame(
        columns=[
            "product",
            "profit_margin_percent"
        ]
    )

    with pytest.raises(ValueError):
        plot_profitability(
            profit_by_product
        )


def test_plot_marketing_performance_returns_figure():

    marketing_analysis = {
        "marketing_spend": 10000,
        "revenue": 50000,
        "profit": 15000
    }

    figure = plot_marketing_performance(
        marketing_analysis
    )

    assert figure is not None
    assert len(figure.data) == 1


def test_plot_marketing_performance_missing_key():

    marketing_analysis = {
        "marketing_spend": 10000,
        "revenue": 50000
    }

    with pytest.raises(ValueError):
        plot_marketing_performance(
            marketing_analysis
        )


def test_plot_marketing_performance_invalid_input():

    with pytest.raises(TypeError):
        plot_marketing_performance(
            "invalid"
        )


def test_plot_customer_retention_returns_figure():

    retention_analysis = {
        "repeat_customers": 228,
        "one_time_customers": 14
    }

    figure = plot_customer_retention(
        retention_analysis
    )

    assert figure is not None
    assert len(figure.data) == 1


def test_plot_customer_retention_missing_key():

    retention_analysis = {
        "repeat_customers": 228
    }

    with pytest.raises(ValueError):
        plot_customer_retention(
            retention_analysis
        )


def test_plot_customer_retention_invalid_input():

    with pytest.raises(TypeError):
        plot_customer_retention(
            "invalid"
        )


def test_plot_significant_changes():

    data = pd.DataFrame({
        "month": [
            "2025-01",
            "2025-02",
            "2025-03"
        ],
        "revenue": [
            1000,
            800,
            1200
        ],
        "profit": [
            200,
            150,
            300
        ],
        "revenue_change_percent": [
            None,
            -20.0,
            50.0
        ],
        "profit_change_percent": [
            None,
            -25.0,
            100.0
        ]
    })

    figure = plot_significant_changes(data)

    assert len(figure.data) == 2
    assert figure.data[0].type == "scatter"
    assert figure.data[1].type == "scatter"


def test_plot_significant_changes_missing_columns():

    data = pd.DataFrame({
        "month": ["2025-01"],
        "revenue_change_percent": [10]
    })

    with pytest.raises(ValueError):
        plot_significant_changes(data)


def test_plot_significant_changes_empty_dataframe():

    data = pd.DataFrame()

    with pytest.raises(ValueError):
        plot_significant_changes(data)


def test_plot_segment_changes_product():

    data = pd.DataFrame({
        "product": [
            "Laptop Pro",
            "Monitor X",
            "Mouse M"
        ],
        "start_revenue": [
            1000,
            2000,
            500
        ],
        "end_revenue": [
            1200,
            1500,
            750
        ],
        "revenue_change": [
            200,
            -500,
            250
        ],
        "revenue_change_percent": [
            20.0,
            -25.0,
            50.0
        ]
    })

    figure = plot_segment_changes(data)

    assert len(figure.data) == 1
    assert figure.data[0].type == "bar"


def test_plot_segment_changes_region():

    data = pd.DataFrame({
        "region": [
            "North",
            "South",
            "West"
        ],
        "revenue_change_percent": [
            10.0,
            -5.0,
            20.0
        ]
    })

    figure = plot_segment_changes(data)

    assert len(figure.data) == 1
    assert figure.data[0].type == "bar"


def test_plot_segment_changes_no_dimension():

    data = pd.DataFrame({
        "revenue_change_percent": [
            10.0,
            -5.0
        ]
    })

    with pytest.raises(ValueError):
        plot_segment_changes(data)


def test_plot_segment_changes_empty_dataframe():

    data = pd.DataFrame()

    with pytest.raises(ValueError):
        plot_segment_changes(data)


def test_plot_change_contribution():

    data = pd.DataFrame({
        "product": [
            "Laptop Pro",
            "Monitor X",
            "Mouse M"
        ],
        "start_revenue": [
            1000,
            2000,
            500
        ],
        "end_revenue": [
            1200,
            1500,
            750
        ],
        "revenue_change": [
            200,
            -500,
            250
        ],
        "contribution_to_total_change_percent": [
            40.0,
            -100.0,
            50.0
        ]
    })

    figure = plot_change_contribution(data)

    assert len(figure.data) == 1
    assert figure.data[0].type == "bar"


def test_plot_change_contribution_no_dimension():

    data = pd.DataFrame({
        "contribution_to_total_change_percent": [
            50.0,
            50.0
        ]
    })

    with pytest.raises(ValueError):
        plot_change_contribution(data)


def test_plot_change_contribution_empty_dataframe():

    data = pd.DataFrame()

    with pytest.raises(ValueError):
        plot_change_contribution(data)


def test_plot_correlations():

    data = pd.DataFrame({
        "units": [1.0, 2.0, 3.0],
        "revenue": [100.0, 200.0, 300.0],
        "profit": [20.0, 40.0, 60.0]
    })

    correlation_matrix = data.corr()

    figure = plot_correlations(correlation_matrix)

    assert len(figure.data) == 1
    assert figure.data[0].type == "heatmap"


def test_plot_correlations_empty_dataframe():

    data = pd.DataFrame()

    with pytest.raises(ValueError):
        plot_correlations(data)

def test_plot_customer_performance():

    data = pd.DataFrame({
        "customer_id": [
            "C001",
            "C002",
            "C003"
        ],
        "total_revenue": [
            1000,
            2000,
            1500
        ],
        "total_profit": [
            200,
            500,
            300
        ]
    })

    figure = plot_customer_performance(data)

    assert len(figure.data) == 2
    assert figure.data[0].type == "bar"
    assert figure.data[1].type == "bar"


def test_plot_customer_performance_missing_column():

    data = pd.DataFrame({
        "customer_id": ["C001"],
        "total_revenue": [1000]
    })

    with pytest.raises(ValueError):
        plot_customer_performance(data)


def test_plot_distribution():

    data = pd.DataFrame({
        "revenue": [
            100,
            200,
            250,
            300,
            500
        ]
    })

    figure = plot_distribution(
        data,
        "revenue"
    )

    assert len(figure.data) == 1
    assert figure.data[0].type == "histogram"


def test_plot_distribution_non_numeric():

    data = pd.DataFrame({
        "revenue": [
            "100",
            "200"
        ]
    })

    with pytest.raises(TypeError):
        plot_distribution(
            data,
            "revenue"
        )


def test_plot_distribution_missing_column():

    data = pd.DataFrame({
        "profit": [10, 20]
    })

    with pytest.raises(ValueError):
        plot_distribution(
            data,
            "revenue"
        )


def test_plot_outliers():

    data = pd.DataFrame({
        "revenue": [
            100,
            120,
            130,
            150,
            1000
        ]
    })

    figure = plot_outliers(
        data,
        "revenue"
    )

    assert len(figure.data) == 1
    assert figure.data[0].type == "box"


def test_plot_outliers_non_numeric():

    data = pd.DataFrame({
        "revenue": [
            "100",
            "200"
        ]
    })

    with pytest.raises(TypeError):
        plot_outliers(
            data,
            "revenue"
        )


def test_plot_business_comparison():

    data = pd.DataFrame({
        "region": [
            "North",
            "South",
            "West"
        ],
        "revenue": [
            1000,
            2000,
            1500
        ],
        "profit": [
            200,
            500,
            300
        ]
    })

    figure = plot_business_comparison(
        data,
        "region"
    )

    assert len(figure.data) == 2
    assert figure.data[0].type == "bar"
    assert figure.data[1].type == "bar"


def test_plot_business_comparison_missing_column():

    data = pd.DataFrame({
        "region": ["North"],
        "revenue": [1000]
    })

    with pytest.raises(ValueError):
        plot_business_comparison(
            data,
            "region"
        )        
