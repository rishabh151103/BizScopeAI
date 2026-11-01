import numpy as np
import pandas as pd


def validate_dataframe(df):
    """Validate the basic analytics input."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")
    if df.empty:
        raise ValueError("Business dataset cannot be empty.")


def require_columns(df, columns):
    """Raise a clear error when required columns are missing."""
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def safe_divide(numerator, denominator):
    """Return NaN instead of raising/producing an invalid zero division."""
    if denominator == 0:
        return np.nan
    return numerator / denominator


def validate_dates(df, column="date"):
    """Convert the date column and report invalid values."""
    require_columns(df, [column])
    result = df.copy()

    original_non_null = result[column].notna()
    result[column] = pd.to_datetime(result[column], errors="coerce")

    invalid_count = int(
        (original_non_null & result[column].isna()).sum()
    )

    warnings = []
    if invalid_count:
        warnings.append(
            f"{invalid_count} invalid date value(s) found in '{column}'."
        )

    return result, warnings


def add_common_validation(df, required_columns):
    """Run lightweight validation without changing the DataFrame."""
    validate_dataframe(df)
    require_columns(df, required_columns)

    warnings = []

    missing = df[required_columns].isna().sum()
    for column, count in missing.items():
        if count:
            warnings.append(
                f"Column '{column}' contains {int(count)} missing value(s)."
            )

    duplicate_count = int(df.duplicated().sum())
    if duplicate_count:
        warnings.append(
            f"Dataset contains {duplicate_count} duplicate row(s)."
        )

    return warnings



def analyze_revenue_trend(df):
    validate_dataframe(df)
    require_columns(df, ["date", "revenue"])

    df = df.copy()

    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        raise ValueError("The 'date' column must contain datetime values.")

    df["month"] = df["date"].dt.to_period("M")

    monthly_revenue = (
        df.groupby("month")["revenue"]
        .sum()
        .reset_index()
    )

    revenue_values = monthly_revenue["revenue"].to_numpy()

    
    change = np.diff(revenue_values)

    percentage_change = np.full(len(change), np.nan)

    previous_values = revenue_values[:-1]

    non_zero = previous_values != 0

    percentage_change[non_zero] = (
        change[non_zero] / previous_values[non_zero]
    ) * 100

    
    monthly_revenue["percentage_change"] = np.nan
    monthly_revenue.loc[1:, "percentage_change"] = percentage_change

    
    if revenue_values[0] == 0:
        overall_change = np.nan
    else:
        overall_change = (
            (revenue_values[-1] - revenue_values[0])
            / revenue_values[0]
        ) * 100

    
    if np.isnan(overall_change):
        trend = "undefined"
    elif overall_change > 0:
        trend = "increasing"
    elif overall_change < 0:
        trend = "decreasing"
    else:
        trend = "stable"

    return {
        "monthly_revenue": monthly_revenue,
        "overall_change_percent": overall_change,
        "trend": trend
    }







def analyze_category_revenue_trend(df):
    """Calculate monthly revenue per category and month-over-month changes."""
    validate_dataframe(df)
    require_columns(df, ["date", "category", "revenue"])

    data = df.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["revenue"] = pd.to_numeric(data["revenue"], errors="coerce")
    data = data.dropna(subset=["date", "category", "revenue"])
    if data.empty:
        raise ValueError("No valid rows remain for category revenue trend analysis.")

    data["month"] = data["date"].dt.to_period("M").astype(str)
    monthly = (
        data.groupby(["month", "category"], as_index=False, dropna=False)["revenue"]
        .sum()
        .sort_values(["category", "month"])
        .reset_index(drop=True)
    )
    grouped = monthly.groupby("category")["revenue"]
    monthly["revenue_change"] = grouped.diff()
    previous = grouped.shift(1)
    monthly["percentage_change"] = np.where(
        previous.notna() & previous.ne(0),
        (monthly["revenue"] - previous) / previous * 100,
        np.nan,
    )

    summary = (
        monthly.groupby("category", as_index=False)
        .agg(
            first_month_revenue=("revenue", "first"),
            latest_month_revenue=("revenue", "last"),
            total_revenue=("revenue", "sum"),
            month_count=("month", "nunique"),
        )
    )
    summary["change_from_first_to_last"] = (
        summary["latest_month_revenue"] - summary["first_month_revenue"]
    )
    summary["change_from_first_to_last_percent"] = np.where(
        summary["first_month_revenue"].ne(0),
        summary["change_from_first_to_last"] / summary["first_month_revenue"] * 100,
        np.nan,
    )
    return {
        "category_monthly_revenue": monthly,
        "category_summary": summary,
    }



def analyze_product_performance(df):

    product_analysis=(
    df.groupby("product")
    .agg(
        total_revenue=("revenue","sum"),
        total_profit=("profit","sum"),
        units_sold=("units","sum"),
        average_profit_margin=("profit_margin_percent","mean")    
     )
     .reset_index()
    )

    product_analysis["revenue_share_percent"]=(product_analysis["total_revenue"]/product_analysis["total_revenue"].sum())*100

    highest_revenue_product = product_analysis.loc[product_analysis["total_revenue"].idxmax()]

    highest_profit_product = product_analysis.loc[product_analysis["total_profit"].idxmax()]

    return {
    "product_analysis": product_analysis,
    "highest_revenue_product": highest_revenue_product["product"],
    "highest_profit_product": highest_profit_product["product"]
    }



def analyze_regional_performance(df):

    regional_analysis=(
        df.groupby("region")
        .agg(
            total_revenue=("revenue","sum"),
            total_profit=("profit","sum"),
            units_sold=("units","sum"),
            average_profit_margin=("profit_margin_percent","mean")    
        ).reset_index()
    )

    regional_analysis["revenue_share_percent"] = (
        regional_analysis["total_revenue"]
        / regional_analysis["total_revenue"].sum()
    ) * 100

    highest_revenue_region = regional_analysis.loc[
        regional_analysis["total_revenue"].idxmax()
    ]

    highest_profit_region = regional_analysis.loc[
        regional_analysis["total_profit"].idxmax()
    ]

    return {
        "regional_analysis": regional_analysis,
        "highest_revenue_region": highest_revenue_region["region"],
        "highest_profit_region": highest_profit_region["region"]
    }



def analyze_profitability(df):

    total_revenue = df["revenue"].sum()
    total_cost = df["cost"].sum()
    total_profit = df["profit"].sum()

    if total_revenue == 0:
        overall_profit_margin = np.nan
    else:
        overall_profit_margin = (
        total_profit / total_revenue
    ) * 100

    profit_by_product = (
        df.groupby("product")
        .agg(
            total_revenue=("revenue", "sum"),
            total_cost=("cost", "sum"),
            total_profit=("profit", "sum")
        )
        .reset_index()
    )

    profit_by_product["profit_margin_percent"] = np.nan

    non_zero_revenue = profit_by_product["total_revenue"] != 0

    profit_by_product.loc[non_zero_revenue, "profit_margin_percent"] = (
    profit_by_product.loc[non_zero_revenue, "total_profit"]
    / profit_by_product.loc[non_zero_revenue, "total_revenue"]
    ) * 100

    most_profitable_product = profit_by_product.loc[
        profit_by_product["total_profit"].idxmax()
    ]

    if profit_by_product["profit_margin_percent"].notna().any():
        highest_margin_product = profit_by_product.loc[
        profit_by_product["profit_margin_percent"].idxmax()
        ]
        highest_margin_product_name = highest_margin_product["product"]
    else:
        highest_margin_product_name = None

    return {
        "total_revenue": total_revenue,
        "total_cost": total_cost,
        "total_profit": total_profit,
        "overall_profit_margin": overall_profit_margin,
        "profit_by_product": profit_by_product,
        "most_profitable_product": most_profitable_product["product"],
        "highest_margin_product": highest_margin_product_name
    }

def analyze_customer_performance(df):

    customer_analysis = (
        df.groupby("customer_id")
        .agg(
            total_revenue=("revenue", "sum"),
            total_profit=("profit", "sum"),
            total_orders=("order_id", "nunique"),
            total_units=("units", "sum")
        )
        .reset_index()
    )

    customer_analysis["average_order_value"] = (
        customer_analysis["total_revenue"]
        / customer_analysis["total_orders"]
    )

    customer_analysis["profit_margin_percent"] = (
        customer_analysis["total_profit"]
        / customer_analysis["total_revenue"]
    ) * 100

    highest_revenue_customer = customer_analysis.loc[
        customer_analysis["total_revenue"].idxmax()
    ]

    highest_profit_customer = customer_analysis.loc[
        customer_analysis["total_profit"].idxmax()
    ]

    return {
        "customer_analysis": customer_analysis,
        "highest_revenue_customer": highest_revenue_customer["customer_id"],
        "highest_profit_customer": highest_profit_customer["customer_id"]
    }


def analyze_customer_type(df):

    customer_type_analysis = (
        df.groupby("customer_type")
        .agg(
            total_revenue=("revenue", "sum"),
            total_profit=("profit", "sum"),
            total_orders=("order_id", "nunique"),
            total_units=("units", "sum"),
            average_order_value=("revenue", "mean"),
            average_profit_margin=("profit_margin_percent", "mean")
        )
        .reset_index()
    )

    customer_type_analysis["revenue_share_percent"] = (
        customer_type_analysis["total_revenue"]
        / customer_type_analysis["total_revenue"].sum()
    ) * 100

    return {
        "customer_type_analysis": customer_type_analysis
    }


def analyze_category_performance(df):

    category_analysis = (
        df.groupby("category")
        .agg(
            total_revenue=("revenue", "sum"),
            total_profit=("profit", "sum"),
            units_sold=("units", "sum"),
            average_profit_margin=("profit_margin_percent", "mean")
        )
        .reset_index()
    )

    category_analysis["aggregate_profit_margin"] = (
        100
        * category_analysis["total_profit"]
        / category_analysis["total_revenue"].replace(0, float("nan"))
    )

    category_analysis["revenue_share_percent"] = (
        category_analysis["total_revenue"]
        / category_analysis["total_revenue"].sum()
    ) * 100

    if category_analysis.empty:
        return {
            "category_analysis": category_analysis,
            "highest_revenue_category": None,
            "highest_profit_category": None,
            "highest_margin_category": None,
            "highest_average_profit_margin_category": None,
            "highest_aggregate_profit_margin_category": None,
        }

    def category_with_maximum(metric):
        usable = category_analysis[metric].dropna()
        if usable.empty:
            return None
        return category_analysis.loc[usable.idxmax(), "category"]

    highest_revenue_category = category_with_maximum("total_revenue")
    highest_profit_category = category_with_maximum("total_profit")
    highest_average_margin_category = category_with_maximum(
        "average_profit_margin"
    )
    highest_aggregate_margin_category = category_with_maximum(
        "aggregate_profit_margin"
    )

    return {
        "category_analysis": category_analysis,
        "highest_revenue_category": highest_revenue_category,
        "highest_profit_category": highest_profit_category,
        # Legacy field retains its former average-margin meaning.
        "highest_margin_category": highest_average_margin_category,
        "highest_average_profit_margin_category": highest_average_margin_category,
        "highest_aggregate_profit_margin_category": highest_aggregate_margin_category,
    }


def analyze_discount_performance(df, category_filter=None):
    """Compare profit outcomes across observed discount levels and categories."""
    validate_dataframe(df)
    require_columns(df, ["category", "discount", "revenue", "profit"])

    data = df.copy()
    if category_filter:
        matches = data["category"].astype(str).str.casefold() == str(category_filter).casefold()
        if not matches.any():
            raise ValueError(
                f"Category '{category_filter}' is not present in the dataset."
            )
        data = data.loc[matches].copy()
    data["discount"] = pd.to_numeric(data["discount"], errors="coerce")
    data["revenue"] = pd.to_numeric(data["revenue"], errors="coerce")
    data["profit"] = pd.to_numeric(data["profit"], errors="coerce")
    data = data.dropna(subset=["category", "discount", "revenue", "profit"])

    if data.empty:
        raise ValueError(
            "The dataset has no usable category, discount, revenue, and profit rows."
        )

    aggregations = {
        "total_revenue": ("revenue", "sum"),
        "total_profit": ("profit", "sum"),
        "transaction_count": ("profit", "size"),
    }
    if "units" in data.columns:
        data["units"] = pd.to_numeric(data["units"], errors="coerce")
        aggregations["units_sold"] = ("units", "sum")
    if "profit_margin_percent" in data.columns:
        data["profit_margin_percent"] = pd.to_numeric(
            data["profit_margin_percent"], errors="coerce"
        )
        aggregations["average_profit_margin"] = (
            "profit_margin_percent", "mean"
        )

    discount_analysis = (
        data.groupby(["category", "discount"], dropna=False)
        .agg(**aggregations)
        .reset_index()
        .rename(columns={"discount": "discount_level"})
    )
    discount_analysis["aggregate_profit_margin"] = (
        100
        * discount_analysis["total_profit"]
        / discount_analysis["total_revenue"].replace(0, float("nan"))
    )
    return {
        "discount_analysis": discount_analysis,
        "category_filter": category_filter,
        "discount_source_values": "Values use the source dataset's discount scale.",
    }

def analyze_monthly_performance(df):

    df = df.copy()

    df["month"] = df["date"].dt.to_period("M")

    monthly_analysis = (
        df.groupby("month")
        .agg(
            total_revenue=("revenue", "sum"),
            total_cost=("cost", "sum"),
            total_profit=("profit", "sum"),
            units_sold=("units", "sum"),
            total_orders=("order_id", "nunique")
        )
        .reset_index()
    )

    monthly_analysis["profit_margin_percent"] = (
        monthly_analysis["total_profit"]
        / monthly_analysis["total_revenue"]
    ) * 100

    monthly_analysis["revenue_growth_percent"] = (
        monthly_analysis["total_revenue"]
        .pct_change() * 100
    )

    monthly_analysis["profit_growth_percent"] = (
        monthly_analysis["total_profit"]
        .pct_change() * 100
    )

    return {
        "monthly_analysis": monthly_analysis
    }


def analyze_correlations(df):

    numerical_columns = [
        "units",
        "unit_price",
        "revenue",
        "cost",
        "marketing_spend",
        "profit",
        "profit_margin_percent"
    ]

    correlation_matrix = df[numerical_columns].corr()

    return {
        "correlation_matrix": correlation_matrix
    }



def analyze_business_comparisons(df):

    comparisons = {}

    if "customer_type" in df.columns:
        customer_type = (
            df.groupby("customer_type")
            .agg(
                revenue=("revenue", "sum"),
                profit=("profit", "sum"),
                orders=("order_id", "count"),
                units=("units", "sum")
            )
            .reset_index()
        )

        comparisons["customer_type"] = customer_type

    if "region" in df.columns:
        region = (
            df.groupby("region")
            .agg(
                revenue=("revenue", "sum"),
                profit=("profit", "sum"),
                orders=("order_id", "count"),
                units=("units", "sum")
            )
            .reset_index()
        )

        comparisons["region"] = region

    if "product" in df.columns:
        product = (
            df.groupby("product")
            .agg(
                revenue=("revenue", "sum"),
                profit=("profit", "sum"),
                orders=("order_id", "count"),
                units=("units", "sum")
            )
            .reset_index()
        )

        comparisons["product"] = product

    if "category" in df.columns:
        category = (
            df.groupby("category")
            .agg(
                revenue=("revenue", "sum"),
                profit=("profit", "sum"),
                orders=("order_id", "count"),
                units=("units", "sum")
            )
            .reset_index()
        )

        comparisons["category"] = category

    return comparisons



def analyze_significant_changes(df):

    df = df.copy()

    df["month"] = df["date"].dt.to_period("M")

    monthly = (
        df.groupby("month")
        .agg(
            revenue=("revenue", "sum"),
            profit=("profit", "sum")
        )
        .reset_index()
    )

    monthly["revenue_change_percent"] = (
        monthly["revenue"].pct_change() * 100
    )

    monthly["profit_change_percent"] = (
        monthly["profit"].pct_change() * 100
    )

    valid_revenue_changes = monthly.dropna(
        subset=["revenue_change_percent"]
    )

    valid_profit_changes = monthly.dropna(
        subset=["profit_change_percent"]
    )

    largest_revenue_increase = valid_revenue_changes.loc[
        valid_revenue_changes["revenue_change_percent"].idxmax()
    ]

    largest_revenue_decrease = valid_revenue_changes.loc[
        valid_revenue_changes["revenue_change_percent"].idxmin()
    ]

    largest_profit_increase = valid_profit_changes.loc[
        valid_profit_changes["profit_change_percent"].idxmax()
    ]

    largest_profit_decrease = valid_profit_changes.loc[
        valid_profit_changes["profit_change_percent"].idxmin()
    ]

    return {
        "monthly_changes": monthly,

        "largest_revenue_increase": {
            "month": str(largest_revenue_increase["month"]),
            "change_percent": largest_revenue_increase[
                "revenue_change_percent"
            ]
        },

        "largest_revenue_decrease": {
            "month": str(largest_revenue_decrease["month"]),
            "change_percent": largest_revenue_decrease[
                "revenue_change_percent"
            ]
        },

        "largest_profit_increase": {
            "month": str(largest_profit_increase["month"]),
            "change_percent": largest_profit_increase[
                "profit_change_percent"
            ]
        },

        "largest_profit_decrease": {
            "month": str(largest_profit_decrease["month"]),
            "change_percent": largest_profit_decrease[
                "profit_change_percent"
            ]
        }
    }


def analyze_segment_changes(df, dimension, start_month, end_month):

    df = df.copy()

    df["month"] = df["date"].dt.to_period("M")

    start_data = df[df["month"] == start_month]
    end_data = df[df["month"] == end_month]

    start_analysis = (
        start_data.groupby(dimension)["revenue"]
        .sum()
        .reset_index()
        .rename(columns={"revenue": "start_revenue"})
    )

    end_analysis = (
        end_data.groupby(dimension)["revenue"]
        .sum()
        .reset_index()
        .rename(columns={"revenue": "end_revenue"})
    )

    comparison = start_analysis.merge(
        end_analysis,
        on=dimension,
        how="outer"
    )

    comparison["start_revenue"] = comparison["start_revenue"].fillna(0)
    comparison["end_revenue"] = comparison["end_revenue"].fillna(0)

    comparison["revenue_change"] = (
        comparison["end_revenue"]
        - comparison["start_revenue"]
    )

    comparison["revenue_change_percent"] = (
        comparison["revenue_change"]
        / comparison["start_revenue"].replace(0, np.nan)
    ) * 100

    return comparison



def analyze_change_contribution(df, dimension, start_month, end_month):

    df = df.copy()

    df["month"] = df["date"].dt.to_period("M")

    start_data = df[df["month"] == start_month]
    end_data = df[df["month"] == end_month]

    start_analysis = (
        start_data.groupby(dimension)["revenue"]
        .sum()
        .reset_index()
        .rename(columns={"revenue": "start_revenue"})
    )

    end_analysis = (
        end_data.groupby(dimension)["revenue"]
        .sum()
        .reset_index()
        .rename(columns={"revenue": "end_revenue"})
    )

    comparison = start_analysis.merge(
        end_analysis,
        on=dimension,
        how="outer"
    )

    comparison["start_revenue"] = comparison["start_revenue"].fillna(0)
    comparison["end_revenue"] = comparison["end_revenue"].fillna(0)

    comparison["revenue_change"] = (
        comparison["end_revenue"]
        - comparison["start_revenue"]
    )

    total_change = (
        comparison["end_revenue"].sum()
        - comparison["start_revenue"].sum()
    )

    comparison["contribution_to_total_change_percent"] = (
        comparison["revenue_change"]
        / total_change
    ) * 100

    return comparison


def analyze_order_metrics(df):

    total_orders = df["order_id"].nunique()

    total_revenue = df["revenue"].sum()

    total_units = df["units"].sum()

    average_order_value = total_revenue / total_orders

    median_order_value = df.groupby("order_id")["revenue"].sum().median()

    average_units_per_order = total_units / total_orders

    revenue_per_unit = total_revenue / total_units

    return {
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "average_order_value": average_order_value,
        "median_order_value": median_order_value,
        "average_units_per_order": average_units_per_order,
        "revenue_per_unit": revenue_per_unit
    }


def analyze_marketing_performance(df):

    total_marketing_spend = df["marketing_spend"].sum()

    total_revenue = df["revenue"].sum()

    total_profit = df["profit"].sum()

    marketing_spend_percent = (
        total_marketing_spend / total_revenue
    ) * 100

    revenue_per_marketing = (
        total_revenue / total_marketing_spend
    )

    profit_per_marketing = (
        total_profit / total_marketing_spend
    )

    return {
        "total_marketing_spend": total_marketing_spend,
        "total_revenue": total_revenue,
        "total_profit": total_profit,
        "marketing_spend_percent_of_revenue": marketing_spend_percent,
        "revenue_per_marketing_spend": revenue_per_marketing,
        "profit_per_marketing_spend": profit_per_marketing
    }


def analyze_customer_retention(df):

    customer_orders = (
        df.groupby("customer_id")
        .agg(
            total_orders=("order_id", "nunique"),
            total_revenue=("revenue", "sum"),
            total_profit=("profit", "sum")
        )
        .reset_index()
    )

    total_customers = len(customer_orders)

    repeat_customers = (
        customer_orders["total_orders"] > 1
    ).sum()

    one_time_customers = (
        customer_orders["total_orders"] == 1
    ).sum()

    repeat_customer_share = (
        repeat_customers / total_customers
    ) * 100

    repeat_customer_revenue = customer_orders.loc[
        customer_orders["total_orders"] > 1,
        "total_revenue"
    ].sum()

    total_revenue = customer_orders["total_revenue"].sum()

    repeat_revenue_share = (
        repeat_customer_revenue / total_revenue
    ) * 100

    return {
        "total_customers": total_customers,
        "repeat_customers": repeat_customers,
        "one_time_customers": one_time_customers,
        "repeat_customer_share_percent": repeat_customer_share,
        "repeat_customer_revenue": repeat_customer_revenue,
        "repeat_revenue_share_percent": repeat_revenue_share,
        "customer_analysis": customer_orders
    }


def analyze_distribution_statistics(df):

    numerical_columns = [
        "units",
        "unit_price",
        "revenue",
        "cost",
        "marketing_spend",
        "profit",
        "profit_margin_percent"
    ]

    statistics = (
        df[numerical_columns]
        .agg([
            "mean",
            "median",
            "std",
            "min",
            "max"
        ])
        .T
    )

    statistics["q25"] = df[numerical_columns].quantile(0.25)

    statistics["q75"] = df[numerical_columns].quantile(0.75)

    return {
        "distribution_statistics": statistics
    }



def analyze_outliers(df):

    numerical_columns = [
        "units",
        "unit_price",
        "revenue",
        "cost",
        "marketing_spend",
        "profit",
        "profit_margin_percent"
    ]

    outlier_summary = {}

    for column in numerical_columns:

        q1 = df[column].quantile(0.25)

        q3 = df[column].quantile(0.75)

        iqr = q3 - q1

        lower_bound = q1 - (1.5 * iqr)

        upper_bound = q3 + (1.5 * iqr)

        outliers = df[
            (df[column] < lower_bound)
            | (df[column] > upper_bound)
        ]

        outlier_summary[column] = {
            "outlier_count": len(outliers),
            "lower_bound": lower_bound,
            "upper_bound": upper_bound
        }

    return {
        "outlier_summary": outlier_summary
    }








if __name__ == "__main__":

    file_path = r"N:\BizScopeAI\dataset\sales_dataset.csv"

    df = pd.read_csv(file_path)

    df["date"] = pd.to_datetime(df["date"])

    print("\n" + "=" * 70)
    print("BIZSCOPEAI ANALYTICS TEST")
    print("=" * 70)

    print("\nDataset shape:", df.shape)

    # ============================================================
    # 1. REVENUE TREND
    # ============================================================

    print("\n" + "=" * 70)
    print("1. REVENUE TREND")
    print("=" * 70)

    result = analyze_revenue_trend(df)
    print(result)


    # ============================================================
    # 2. PRODUCT PERFORMANCE
    # ============================================================

    print("\n" + "=" * 70)
    print("2. PRODUCT PERFORMANCE")
    print("=" * 70)

    result = analyze_product_performance(df)
    print(result)


    # ============================================================
    # 3. REGIONAL PERFORMANCE
    # ============================================================

    print("\n" + "=" * 70)
    print("3. REGIONAL PERFORMANCE")
    print("=" * 70)

    result = analyze_regional_performance(df)
    print(result)


    # ============================================================
    # 4. PROFITABILITY
    # ============================================================

    print("\n" + "=" * 70)
    print("4. PROFITABILITY")
    print("=" * 70)

    result = analyze_profitability(df)
    print(result)


    # ============================================================
    # 5. CUSTOMER PERFORMANCE
    # ============================================================

    print("\n" + "=" * 70)
    print("5. CUSTOMER PERFORMANCE")
    print("=" * 70)

    result = analyze_customer_performance(df)
    print(result)


    # ============================================================
    # 6. CUSTOMER TYPE
    # ============================================================

    print("\n" + "=" * 70)
    print("6. CUSTOMER TYPE")
    print("=" * 70)

    result = analyze_customer_type(df)
    print(result)


    # ============================================================
    # 7. CATEGORY PERFORMANCE
    # ============================================================

    print("\n" + "=" * 70)
    print("7. CATEGORY PERFORMANCE")
    print("=" * 70)

    result = analyze_category_performance(df)
    print(result)


    # ============================================================
    # 8. MONTHLY PERFORMANCE
    # ============================================================

    print("\n" + "=" * 70)
    print("8. MONTHLY PERFORMANCE")
    print("=" * 70)

    result = analyze_monthly_performance(df)
    print(result)


    # ============================================================
    # 9. CORRELATIONS
    # ============================================================

    print("\n" + "=" * 70)
    print("9. CORRELATIONS")
    print("=" * 70)

    result = analyze_correlations(df)
    print(result)


    # ============================================================
    # 10. BUSINESS COMPARISONS
    # ============================================================

    print("\n" + "=" * 70)
    print("10. BUSINESS COMPARISONS")
    print("=" * 70)

    result = analyze_business_comparisons(df)
    print(result)


    # ============================================================
    # 11. SIGNIFICANT CHANGES
    # ============================================================

    print("\n" + "=" * 70)
    print("11. SIGNIFICANT CHANGES")
    print("=" * 70)

    result = analyze_significant_changes(df)
    print(result)


    # ============================================================
    # 12. SEGMENT CHANGES
    # ============================================================

    print("\n" + "=" * 70)
    print("12. SEGMENT CHANGES")
    print("=" * 70)

    result = analyze_segment_changes(
        df,
        dimension="product",
        start_month="2025-01",
        end_month="2025-02"
    )

    print(result)


    # ============================================================
    # 13. CHANGE CONTRIBUTION
    # ============================================================

    print("\n" + "=" * 70)
    print("13. CHANGE CONTRIBUTION")
    print("=" * 70)

    result = analyze_change_contribution(
        df,
        dimension="product",
        start_month="2025-01",
        end_month="2025-02"
    )

    print(result)


    # ============================================================
    # 14. ORDER METRICS
    # ============================================================

    print("\n" + "=" * 70)
    print("14. ORDER METRICS")
    print("=" * 70)

    result = analyze_order_metrics(df)
    print(result)


    # ============================================================
    # 15. MARKETING PERFORMANCE
    # ============================================================

    print("\n" + "=" * 70)
    print("15. MARKETING PERFORMANCE")
    print("=" * 70)

    result = analyze_marketing_performance(df)
    print(result)


    # ============================================================
    # 16. CUSTOMER RETENTION
    # ============================================================

    print("\n" + "=" * 70)
    print("16. CUSTOMER RETENTION")
    print("=" * 70)

    result = analyze_customer_retention(df)
    print(result)


    # ============================================================
    # 17. DISTRIBUTION STATISTICS
    # ============================================================

    print("\n" + "=" * 70)
    print("17. DISTRIBUTION STATISTICS")
    print("=" * 70)

    result = analyze_distribution_statistics(df)
    print(result)


    # ============================================================
    # 18. OUTLIERS
    # ============================================================

    print("\n" + "=" * 70)
    print("18. OUTLIERS")
    print("=" * 70)

    result = analyze_outliers(df)
    print(result)


    # ============================================================
    # COMPLETE
    # ============================================================

    print("\n" + "=" * 70)
    print("ALL 18 ANALYTICS FUNCTIONS EXECUTED")
    print("=" * 70)
