import pandas as pd

from .schemas import BusinessColumnMapping


COLUMN_ALIASES = {
    "date": [
        "date",
        "order_date",
        "transaction_date",
        "sale_date",
        "sales_date",
        "invoice_date",
        "purchase_date",
    ],
    "revenue": [
        "revenue",
        "sales",
        "total_sales",
        "net_sales",
        "sales_amount",
        "revenue_amount",
    ],
    "profit": [
        "profit",
        "net_profit",
        "profit_amount",
    ],
    "cost": [
        "cost",
        "total_cost",
        "cost_amount",
    ],
    "units": [
        "units",
        "quantity",
        "qty",
        "units_sold",
        "quantity_sold",
    ],
    "unit_price": [
        "unit_price",
        "price",
        "selling_price",
        "sale_price",
    ],
    "marketing_spend": [
        "marketing_spend",
        "marketing_cost",
        "advertising_spend",
        "ad_spend",
        "marketing_expense",
    ],
    "customer_id": [
        "customer_id",
        "customer",
        "client_id",
        "customer_number",
        "customer_no",
    ],
    "order_id": [
        "order_id",
        "order_number",
        "order_no",
        "transaction_id",
        "transaction_number",
    ],
    "product": [
        "product",
        "product_name",
        "item",
        "item_name",
    ],
    "category": [
        "category",
        "product_category",
        "item_category",
    ],
    "region": [
        "region",
        "territory",
        "sales_region",
        "area",
    ],
    "customer_type": [
        "customer_type",
        "customer_segment",
        "customer_category",
        "client_type",
    ],
    "discount": [
        "discount",
        "discount_rate",
        "discount_percent",
        "discount_percentage",
    ],
}


def map_business_columns(df):
    """
    Map dataset columns to BizScopeAI business concepts.

    The DataFrame itself is not modified.

    Returns:
        BusinessColumnMapping
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            "df must be a pandas DataFrame."
        )

    normalized_columns = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    mapping = {}

    for concept, aliases in COLUMN_ALIASES.items():

        matched_column = None

        for alias in aliases:

            if alias in normalized_columns:

                matched_column = (
                    normalized_columns[alias]
                )

                break

        mapping[concept] = matched_column

    return BusinessColumnMapping(
        **mapping
    )
