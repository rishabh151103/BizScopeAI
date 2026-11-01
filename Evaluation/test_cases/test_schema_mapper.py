import sys
from pathlib import Path

import pandas as pd
import pytest


sys.path.append(
    str(Path(__file__).resolve().parents[2])
)

from Backend.schema_mapper import (
    map_business_columns,
)


def test_map_sales_dataset_columns():

    df = pd.DataFrame({
        "date": [],
        "revenue": [],
        "profit": [],
        "cost": [],
        "units": [],
        "unit_price": [],
        "marketing_spend": [],
        "customer_id": [],
        "order_id": [],
        "product": [],
        "category": [],
        "region": [],
        "customer_type": [],
    })

    mapping = map_business_columns(df)

    assert mapping.date == "date"
    assert mapping.revenue == "revenue"
    assert mapping.profit == "profit"
    assert mapping.cost == "cost"
    assert mapping.units == "units"
    assert mapping.unit_price == "unit_price"
    assert mapping.marketing_spend == "marketing_spend"
    assert mapping.customer_id == "customer_id"
    assert mapping.order_id == "order_id"
    assert mapping.product == "product"
    assert mapping.category == "category"
    assert mapping.region == "region"
    assert mapping.customer_type == "customer_type"


def test_map_superstore_columns():

    df = pd.DataFrame({
        "row_id": [],
        "order_id": [],
        "order_date": [],
        "ship_date": [],
        "ship_mode": [],
        "customer_id": [],
        "customer_name": [],
        "segment": [],
        "country_region": [],
        "city": [],
        "state_province": [],
        "postal_code": [],
        "region": [],
        "product_id": [],
        "category": [],
        "sub_category": [],
        "product_name": [],
        "sales": [],
        "quantity": [],
        "discount": [],
        "profit": [],
    })

    mapping = map_business_columns(df)

    assert mapping.date == "order_date"
    assert mapping.revenue == "sales"
    assert mapping.profit == "profit"
    assert mapping.units == "quantity"
    assert mapping.customer_id == "customer_id"
    assert mapping.order_id == "order_id"
    assert mapping.product == "product_name"
    assert mapping.category == "category"
    assert mapping.region == "region"


def test_missing_optional_columns_return_none():

    df = pd.DataFrame({
        "date": [],
        "revenue": [],
    })

    mapping = map_business_columns(df)

    assert mapping.date == "date"
    assert mapping.revenue == "revenue"

    assert mapping.profit is None
    assert mapping.customer_id is None
    assert mapping.product is None


def test_unknown_columns_are_ignored():

    df = pd.DataFrame({
        "foo": [],
        "bar": [],
        "random_column": [],
    })

    mapping = map_business_columns(df)

    assert mapping.date is None
    assert mapping.revenue is None
    assert mapping.profit is None


def test_invalid_input():

    with pytest.raises(TypeError):

        map_business_columns(
            "not a dataframe"
        )

def test_map_actual_sales_dataset():

    dataset_path = (
        r"N:\BizScopeAI\dataset\sales_dataset.csv"
    )

    df = pd.read_csv(dataset_path)

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )

    mapping = map_business_columns(df)

    assert mapping.date == "date"
    assert mapping.revenue == "revenue"
    assert mapping.profit == "profit"
    assert mapping.cost == "cost"
    assert mapping.units == "units"
    assert mapping.unit_price == "unit_price"
    assert mapping.marketing_spend == "marketing_spend"
    assert mapping.customer_id == "customer_id"
    assert mapping.order_id == "order_id"
    assert mapping.product == "product"
    assert mapping.category == "category"
    assert mapping.region == "region"
    assert mapping.customer_type == "customer_type"


def test_map_actual_superstore_dataset():

    dataset_path = (
        r"N:\BizScopeAI\dataset\samplesuperstore.csv"
    )

    df = pd.read_csv(dataset_path)

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )

    mapping = map_business_columns(df)

    assert mapping.date == "order_date"
    assert mapping.revenue == "sales"
    assert mapping.profit == "profit"
    assert mapping.units == "quantity"
    assert mapping.customer_id == "customer_id"
    assert mapping.order_id == "order_id"
    assert mapping.product == "product_name"
    assert mapping.category == "category"
    assert mapping.region == "region"


def test_map_actual_dirty_superstore_dataset():

    dataset_path = (
        r"N:\BizScopeAI\dataset\samplesuperstore_dirty.csv"
    )

    df = pd.read_csv(dataset_path)

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )

    mapping = map_business_columns(df)

    assert mapping.date == "order_date"
    assert mapping.revenue == "sales"
    assert mapping.profit == "profit"
    assert mapping.units == "quantity"
    assert mapping.customer_id == "customer_id"
    assert mapping.order_id == "order_id"
    assert mapping.product == "product_name"
    assert mapping.category == "category"
    assert mapping.region == "region"        