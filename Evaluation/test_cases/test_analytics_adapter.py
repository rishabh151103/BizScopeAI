import io

import pandas as pd
import pytest

from Backend.analytics_adapter import adapt_dataset
from Backend.data_loader import (
    clean_column_names,
    load_uploaded_dataset,
    preprocess_dataset,
)
from Backend.schema_mapper import map_business_columns


def create_sales_dataset():
    csv_data = """Order Date,Sales,Profit,Quantity,Product Name
2025-01-01,1000,200,5,Laptop
2025-02-01,1500,300,7,Monitor
2025-03-01,1200,250,6,Keyboard
"""

    uploaded_file = io.BytesIO(csv_data.encode("utf-8"))
    uploaded_file.name = "superstore.csv"

    df = load_uploaded_dataset(uploaded_file)
    df = clean_column_names(df)

    preprocessing_result = preprocess_dataset(df)

    return preprocessing_result["data"]


def test_adapt_dataset_renames_mapped_columns():

    df = create_sales_dataset()

    mapping = map_business_columns(df)

    adapted = adapt_dataset(df, mapping)

    assert "date" in adapted.columns
    assert "revenue" in adapted.columns
    assert "profit" in adapted.columns
    assert "units" in adapted.columns
    assert "product" in adapted.columns


def test_adapt_dataset_preserves_original_dataframe():

    df = create_sales_dataset()

    original_columns = df.columns.tolist()

    mapping = map_business_columns(df)

    adapted = adapt_dataset(df, mapping)

    assert df.columns.tolist() == original_columns

    assert "order_date" in df.columns
    assert "sales" in df.columns
    assert "quantity" in df.columns
    assert "product_name" in df.columns


def test_adapt_dataset_preserves_values():

    df = create_sales_dataset()

    mapping = map_business_columns(df)

    adapted = adapt_dataset(df, mapping)

    assert adapted["revenue"].tolist() == [1000, 1500, 1200]
    assert adapted["profit"].tolist() == [200, 300, 250]
    assert adapted["units"].tolist() == [5, 7, 6]


def test_adapt_dataset_does_not_modify_row_count():

    df = create_sales_dataset()

    mapping = map_business_columns(df)

    adapted = adapt_dataset(df, mapping)

    assert len(adapted) == len(df)


def test_adapt_dataset_invalid_dataframe():

    mapping = map_business_columns(
        pd.DataFrame({
            "date": ["2025-01-01"],
            "revenue": [100]
        })
    )

    with pytest.raises(TypeError):

        adapt_dataset(
            "not a dataframe",
            mapping
        )


def test_adapt_dataset_invalid_mapping():

    df = create_sales_dataset()

    with pytest.raises(TypeError):

        adapt_dataset(
            df,
            {"date": "order_date"}
        )


def test_adapt_dataset_missing_mapped_column():

    df = pd.DataFrame({
        "order_date": ["2025-01-01"],
        "sales": [1000]
    })

    mapping = map_business_columns(df)

    # Deliberately create an invalid mapping.
    mapping.date = "does_not_exist"

    with pytest.raises(ValueError):

        adapt_dataset(
            df,
            mapping
        )


def test_adapt_dataset_derives_cost():

    df = pd.DataFrame({
        "sales": [1000, 1500],
        "profit": [200, 300]
    })

    mapping = map_business_columns(df)

    adapted = adapt_dataset(
        df,
        mapping
    )

    assert "cost" in adapted.columns

    assert adapted["cost"].tolist() == [
        800,
        1200
    ]


def test_adapt_dataset_derives_profit_margin():

    df = pd.DataFrame({
        "sales": [1000, 2000],
        "profit": [200, 500]
    })

    mapping = map_business_columns(df)

    adapted = adapt_dataset(
        df,
        mapping
    )

    assert "profit_margin_percent" in adapted.columns

    assert adapted["profit_margin_percent"].tolist() == [
        20.0,
        25.0
    ]

def test_adapt_dataset_handles_zero_revenue():

    df = pd.DataFrame({
        "sales": [0],
        "profit": [0]
    })

    mapping = map_business_columns(df)

    adapted = adapt_dataset(
        df,
        mapping
    )

    assert "profit_margin_percent" in adapted.columns

    assert pd.isna(
        adapted["profit_margin_percent"].iloc[0]
    )            