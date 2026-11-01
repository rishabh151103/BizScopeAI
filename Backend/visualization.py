import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def _validate_dataframe(df, name):
    """Validate a visualization DataFrame."""

    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            f"{name} must be a pandas DataFrame."
        )

    if df.empty:
        raise ValueError(
            f"{name} cannot be empty."
        )


def _validate_required_columns(df, required_columns):
    """Validate that required columns exist."""

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )



def plot_revenue_trend(monthly_revenue):
    """
    Plot monthly revenue over time.

    Expected input:
        DataFrame returned by:
        analyze_revenue_trend(df)["monthly_revenue"]
    """

    _validate_dataframe(
        monthly_revenue,
        "monthly_revenue"
    )

    _validate_required_columns(
        monthly_revenue,
        ["month", "revenue"]
    )

    plot_data = monthly_revenue.copy()

    # Pandas Period objects are not JSON serializable.
    plot_data["month"] = plot_data["month"].astype(str)

    figure = px.line(
        plot_data,
        x="month",
        y="revenue",
        markers=True,
        title="Monthly Revenue Trend",
        labels={
            "month": "Month",
            "revenue": "Revenue"
        }
    )

    return figure



def plot_category_revenue_trend(category_monthly_revenue):
    """Plot monthly revenue with a separate line for each category."""
    _validate_dataframe(category_monthly_revenue, "category_monthly_revenue")
    _validate_required_columns(
        category_monthly_revenue, ["month", "category", "revenue"]
    )
    plot_data = category_monthly_revenue.copy()
    plot_data["month"] = plot_data["month"].astype(str)
    return px.line(
        plot_data,
        x="month",
        y="revenue",
        color="category",
        markers=True,
        title="Monthly Revenue by Product Category",
        labels={"month": "Month", "revenue": "Revenue", "category": "Product Category"},
    )



def plot_monthly_performance(monthly_analysis):
    """
    Plot monthly revenue and profit.

    Expected input:
        DataFrame returned by:
        analyze_monthly_performance(df)
    """

    _validate_dataframe(
        monthly_analysis,
        "monthly_analysis"
    )

    _validate_required_columns(
        monthly_analysis,
        [
            "month",
            "total_revenue",
            "total_profit"
        ]
    )

    plot_data = monthly_analysis.copy()

    plot_data["month"] = plot_data["month"].astype(str)

    figure = px.line(
        plot_data,
        x="month",
        y=[
            "total_revenue",
            "total_profit"
        ],
        markers=True,
        title="Monthly Revenue and Profit",
        labels={
            "month": "Month",
            "value": "Amount",
            "variable": "Metric"
        }
    )

    return figure


def plot_product_performance(product_analysis):
    """
    Plot revenue and profit by product.

    Expected input:
        DataFrame returned by:
        analyze_product_performance(df)["product_analysis"]
    """

    _validate_dataframe(
        product_analysis,
        "product_analysis"
    )

    _validate_required_columns(
        product_analysis,
        [
            "product",
            "total_revenue",
            "total_profit"
        ]
    )

    plot_data = product_analysis.copy()

    figure = px.bar(
        plot_data,
        x="product",
        y=[
            "total_revenue",
            "total_profit"
        ],
        barmode="group",
        title="Revenue and Profit by Product",
        labels={
            "product": "Product",
            "value": "Amount",
            "variable": "Metric"
        }
    )

    return figure



def plot_regional_performance(regional_analysis):
    """
    Plot revenue and profit by region.

    Expected input:
        DataFrame returned by:
        analyze_regional_performance(df)["regional_analysis"]
    """

    _validate_dataframe(
        regional_analysis,
        "regional_analysis"
    )

    _validate_required_columns(
        regional_analysis,
        [
            "region",
            "total_revenue",
            "total_profit"
        ]
    )

    plot_data = regional_analysis.copy()
    for column in ("total_revenue", "total_profit"):
        plot_data[column] = pd.to_numeric(plot_data[column], errors="raise")

    figure = px.bar(
        plot_data,
        x="region",
        y=[
            "total_revenue",
            "total_profit"
        ],
        barmode="group",
        title="Revenue and Profit by Region",
        labels={
            "region": "Region",
            "value": "Amount",
            "variable": "Metric"
        }
    )

    if "average_profit_margin" in plot_data.columns:
        plot_data["average_profit_margin"] = pd.to_numeric(
            plot_data["average_profit_margin"],
            errors="raise",
        )
        figure.update_layout(
            yaxis2={
                "title": "Average Profit Margin (%)",
                "overlaying": "y",
                "side": "right",
                "showgrid": False,
            }
        )
        figure.add_trace(
            go.Scatter(
                x=plot_data["region"],
                y=plot_data["average_profit_margin"],
                name="Average Profit Margin (%)",
                mode="lines+markers",
                yaxis="y2",
                hovertemplate=(
                    "Region: %{x}<br>"
                    "Average Profit Margin: %{y:.2f}%"
                    "<extra></extra>"
                ),
            )
        )
    figure.update_layout(
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0}
    )

    return figure


def plot_category_performance(category_analysis):
    """
    Plot category-level profit and aggregate profit margin.

    Expected input:
        DataFrame returned by:
        analyze_category_performance(df)["category_analysis"]

    The primary chart shows total profit. A secondary y-axis shows
    aggregate profit margin, which should be calculated upstream as
    total_profit / total_revenue * 100.
    """

    _validate_dataframe(
        category_analysis,
        "category_analysis"
    )

    _validate_required_columns(
        category_analysis,
        [
            "category",
            "total_profit",
            "aggregate_profit_margin"
        ]
    )

    plot_data = category_analysis.copy()

    # Fail clearly rather than silently plotting non-numeric metrics.
    for column in ["total_profit", "aggregate_profit_margin"]:
        plot_data[column] = pd.to_numeric(
            plot_data[column],
            errors="raise"
        )

    figure = px.bar(
        plot_data,
        x="category",
        y="total_profit",
        title="Profit and Aggregate Profit Margin by Category",
        labels={
            "category": "Product Category",
            "total_profit": "Total Profit",
        },
        hover_data={
            "aggregate_profit_margin": ":.2f",
            "total_profit": ":,.2f",
        },
    )

    figure.update_layout(
        yaxis=dict(title="Total Profit"),
        yaxis2=dict(
            title="Aggregate Profit Margin (%)",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )

    # Add margin as a line on the secondary axis so dollars and percentages
    # are not visually conflated.
    import plotly.graph_objects as go

    figure.add_trace(
        go.Scatter(
            x=plot_data["category"],
            y=plot_data["aggregate_profit_margin"],
            name="Aggregate Profit Margin (%)",
            mode="lines+markers",
            yaxis="y2",
            hovertemplate=(
                "Category: %{x}<br>"
                "Aggregate Profit Margin: %{y:.2f}%"
                "<extra></extra>"
            ),
        )
    )

    return figure


def plot_discount_performance(discount_analysis):
    """Plot aggregate margin at observed discount levels by category."""
    _validate_dataframe(discount_analysis, "discount_analysis")
    _validate_required_columns(
        discount_analysis,
        ["category", "discount_level", "aggregate_profit_margin"],
    )
    return px.line(
        discount_analysis.sort_values("discount_level"),
        x="discount_level",
        y="aggregate_profit_margin",
        color="category",
        markers=True,
        title="Aggregate Profit Margin by Discount Level",
        labels={
            "discount_level": "Discount value (source scale)",
            "aggregate_profit_margin": "Aggregate Profit Margin (%)",
            "category": "Product Category",
        },
    )


def plot_customer_type_performance(customer_type_analysis):
    """
    Plot revenue and profit by customer type.

    Expected input:
        DataFrame returned by:
        analyze_customer_type(df)["customer_type_analysis"]
    """

    _validate_dataframe(
        customer_type_analysis,
        "customer_type_analysis"
    )

    _validate_required_columns(
        customer_type_analysis,
        [
            "customer_type",
            "total_revenue",
            "total_profit"
        ]
    )

    plot_data = customer_type_analysis.copy()

    figure = px.bar(
        plot_data,
        x="customer_type",
        y=[
            "total_revenue",
            "total_profit"
        ],
        barmode="group",
        title="Revenue and Profit by Customer Type",
        labels={
            "customer_type": "Customer Type",
            "value": "Amount",
            "variable": "Metric"
        }
    )

    return figure



def plot_profitability(profit_by_product):
    """
    Plot profit margin by product.

    Expected input:
        DataFrame returned by:
        analyze_profitability(df)["profit_by_product"]
    """

    _validate_dataframe(
        profit_by_product,
        "profit_by_product"
    )

    _validate_required_columns(
        profit_by_product,
        [
            "product",
            "profit_margin_percent"
        ]
    )

    plot_data = profit_by_product.copy()

    figure = px.bar(
        plot_data,
        x="product",
        y="profit_margin_percent",
        title="Profit Margin by Product",
        labels={
            "product": "Product",
            "profit_margin_percent": "Profit Margin (%)"
        }
    )

    return figure


def plot_marketing_performance(marketing_analysis):
    """
    Plot marketing spend, revenue, and profit.

    Expected input:
        Dictionary returned by:
        analyze_marketing_performance(df)
    """

    if not isinstance(marketing_analysis, dict):
        raise TypeError(
            "marketing_analysis must be a dictionary."
        )

    metric_keys = {
        "marketing_spend": ("total_marketing_spend", "marketing_spend"),
        "revenue": ("total_revenue", "revenue"),
        "profit": ("total_profit", "profit"),
    }

    missing = [
        metric
        for metric, keys in metric_keys.items()
        if not any(key in marketing_analysis for key in keys)
    ]

    if missing:
        raise ValueError(
            f"Missing required keys: {missing}"
        )

    plot_data = pd.DataFrame({
        "metric": [
            "Marketing Spend",
            "Revenue",
            "Profit"
        ],
        "value": [
            next(marketing_analysis[key] for key in metric_keys[metric] if key in marketing_analysis)
            for metric in metric_keys
        ]
    })

    if plot_data.empty:
        raise ValueError(
            "marketing_analysis cannot be empty."
        )

    figure = px.bar(
        plot_data,
        x="metric",
        y="value",
        title="Marketing Performance",
        labels={
            "metric": "Metric",
            "value": "Amount"
        }
    )

    return figure


def plot_customer_retention(retention_analysis):
    """
    Plot repeat customers versus one-time customers.

    Expected input:
        Dictionary returned by:
        analyze_customer_retention(df)
    """

    if not isinstance(retention_analysis, dict):
        raise TypeError(
            "retention_analysis must be a dictionary."
        )

    required_keys = [
        "repeat_customers",
        "one_time_customers"
    ]

    missing = [
        key
        for key in required_keys
        if key not in retention_analysis
    ]

    if missing:
        raise ValueError(
            f"Missing required keys: {missing}"
        )

    plot_data = pd.DataFrame({
        "customer_type": [
            "Repeat Customers",
            "One-Time Customers"
        ],
        "customer_count": [
            retention_analysis["repeat_customers"],
            retention_analysis["one_time_customers"]
        ]
    })

    if plot_data.empty:
        raise ValueError(
            "retention_analysis cannot be empty."
        )

    figure = px.bar(
        plot_data,
        x="customer_type",
        y="customer_count",
        title="Customer Retention",
        labels={
            "customer_type": "Customer Type",
            "customer_count": "Number of Customers"
        }
    )

    return figure


def plot_significant_changes(monthly_changes):
    _validate_dataframe(
        monthly_changes,
        "monthly_changes"
    )

    _validate_required_columns(
        monthly_changes,
        [
            "month",
            "revenue_change_percent",
            "profit_change_percent"
        ]
    )

    plot_data = monthly_changes.copy()

    plot_data["month"] = plot_data["month"].astype(str)

    figure = px.line(
        plot_data,
        x="month",
        y=[
            "revenue_change_percent",
            "profit_change_percent"
        ],
        markers=True,
        title="Monthly Revenue and Profit Changes",
        labels={
            "month": "Month",
            "value": "Percentage Change (%)",
            "variable": "Metric"
        }
    )

    return figure


def plot_segment_changes(segment_changes):
    _validate_dataframe(
        segment_changes,
        "segment_changes"
    )

    _validate_required_columns(
        segment_changes,
        ["revenue_change_percent"]
    )

    possible_dimensions = [
        "product",
        "region",
        "category",
        "customer_type"
    ]

    dimension = next(
        (
            column
            for column in possible_dimensions
            if column in segment_changes.columns
        ),
        None
    )

    if dimension is None:
        raise ValueError(
            "No supported segment dimension column found."
        )

    plot_data = segment_changes.copy()

    figure = px.bar(
        plot_data,
        x=dimension,
        y="revenue_change_percent",
        title="Revenue Change by Segment",
        labels={
            dimension: dimension.replace(
                "_", " "
            ).title(),
            "revenue_change_percent":
                "Revenue Change (%)"
        }
    )

    return figure


def plot_change_contribution(change_contribution):
    _validate_dataframe(
        change_contribution,
        "change_contribution"
    )

    _validate_required_columns(
        change_contribution,
        ["contribution_to_total_change_percent"]
    )

    possible_dimensions = [
        "product",
        "region",
        "category",
        "customer_type"
    ]

    dimension = next(
        (
            column
            for column in possible_dimensions
            if column in change_contribution.columns
        ),
        None
    )

    if dimension is None:
        raise ValueError(
            "No supported segment dimension column found."
        )

    plot_data = change_contribution.copy()

    figure = px.bar(
        plot_data,
        x=dimension,
        y="contribution_to_total_change_percent",
        title="Contribution to Revenue Change",
        labels={
            dimension: dimension.replace(
                "_", " "
            ).title(),
            "contribution_to_total_change_percent":
                "Contribution (%)"
        }
    )

    return figure


def plot_correlations(correlation_matrix):
    _validate_dataframe(
        correlation_matrix,
        "correlation_matrix"
    )

    figure = px.imshow(
        correlation_matrix,
        text_auto=".2f",
        aspect="auto",
        title="Business Metric Correlations",
        labels={
            "x": "Metric",
            "y": "Metric",
            "color": "Correlation"
        }
    )

    return figure

def plot_customer_performance(customer_analysis):
    _validate_dataframe(
        customer_analysis,
        "customer_analysis"
    )

    _validate_required_columns(
        customer_analysis,
        ["customer_id", "total_revenue", "total_profit"]
    )

    plot_data = customer_analysis.copy()

    figure = px.bar(
        plot_data,
        x="customer_id",
        y=["total_revenue", "total_profit"],
        barmode="group",
        title="Revenue and Profit by Customer",
        labels={
            "customer_id": "Customer",
            "value": "Amount",
            "variable": "Metric"
        }
    )

    return figure

def plot_distribution(df, column):
    _validate_dataframe(
        df,
        "df"
    )

    _validate_required_columns(
        df,
        [column]
    )

    if not pd.api.types.is_numeric_dtype(df[column]):
        raise TypeError(
            f"Column '{column}' must be numeric."
        )

    figure = px.histogram(
        df,
        x=column,
        nbins=30,
        title=f"Distribution of {column.replace('_', ' ').title()}",
        labels={
            column: column.replace(
                "_", " "
            ).title(),
            "count": "Frequency"
        }
    )

    return figure

def plot_outliers(df, column):
    _validate_dataframe(
        df,
        "df"
    )

    _validate_required_columns(
        df,
        [column]
    )

    if not pd.api.types.is_numeric_dtype(df[column]):
        raise TypeError(
            f"Column '{column}' must be numeric."
        )

    figure = px.box(
        df,
        y=column,
        points="outliers",
        title=f"Outlier Analysis: {column.replace('_', ' ').title()}",
        labels={
            column: column.replace(
                "_", " "
            ).title()
        }
    )

    return figure


def plot_outlier_summary(outlier_summary):
    """Plot the outlier counts produced by ``analyze_outliers``."""
    if not isinstance(outlier_summary, dict) or not outlier_summary:
        raise ValueError("outlier_summary must be a non-empty dictionary.")

    plot_data = pd.DataFrame(
        [
            {"metric": metric, "outlier_count": details["outlier_count"]}
            for metric, details in outlier_summary.items()
            if isinstance(details, dict) and "outlier_count" in details
        ]
    )
    if plot_data.empty:
        raise ValueError("outlier_summary has no outlier counts to plot.")

    return px.bar(
        plot_data,
        x="metric",
        y="outlier_count",
        title="Outlier Count by Metric",
        labels={"metric": "Metric", "outlier_count": "Outlier Count"},
    )

def plot_business_comparison(
    comparison,
    dimension=None
):
    if isinstance(comparison, dict):
        available_dimensions = [
            name for name, frame in comparison.items()
            if isinstance(frame, pd.DataFrame) and not frame.empty
        ]
        if not available_dimensions:
            raise ValueError("comparison contains no populated segment results.")
        if dimension is None:
            dimension = available_dimensions[0]
        if dimension not in comparison:
            raise ValueError(
                f"No comparison data is available for dimension '{dimension}'."
            )
        comparison = comparison[dimension]

    if dimension is None:
        raise ValueError("dimension is required when comparison is a DataFrame.")

    _validate_dataframe(
        comparison,
        "comparison"
    )

    _validate_required_columns(
        comparison,
        [
            dimension,
            "revenue",
            "profit"
        ]
    )

    figure = px.bar(
        comparison,
        x=dimension,
        y=["revenue", "profit"],
        barmode="group",
        title=(
            f"Revenue and Profit by "
            f"{dimension.replace('_', ' ').title()}"
        ),
        labels={
            dimension: dimension.replace(
                "_", " "
            ).title(),
            "value": "Amount",
            "variable": "Metric"
        }
    )

    return figure
