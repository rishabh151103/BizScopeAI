from pathlib import Path

from Backend.analytics_adapter import adapt_dataset
from Backend.analytics import (
    analyze_product_performance,
    analyze_regional_performance,
    analyze_profitability,
)
from Backend.data_loader import (
    clean_column_names,
    load_dataset,
    preprocess_dataset,
)
from Backend.schema_mapper import map_business_columns


DATASET_PATH = Path(
    r"N:\BizScopeAI\dataset\samplesuperstore_dirty.csv"
)


def prepare_dirty_superstore():

    df = load_dataset(DATASET_PATH)

    df = clean_column_names(df)

    preprocessing_result = preprocess_dataset(df)

    cleaned_df = preprocessing_result["data"]

    mapping = map_business_columns(cleaned_df)

    adapted_df = adapt_dataset(
        cleaned_df,
        mapping
    )

    return (
        cleaned_df,
        mapping,
        adapted_df,
        preprocessing_result,
    )


def test_dirty_superstore_loads_and_preprocesses():

    cleaned_df, _, _, preprocessing_result = (
        prepare_dirty_superstore()
    )

    assert not cleaned_df.empty

    assert "warnings" in preprocessing_result
    assert "changes" in preprocessing_result


def test_dirty_superstore_mapping():

    _, mapping, _, _ = prepare_dirty_superstore()

    assert mapping.date == "order_date"
    assert mapping.revenue == "sales"
    assert mapping.profit == "profit"
    assert mapping.units == "quantity"
    assert mapping.product == "product_name"
    assert mapping.category == "category"
    assert mapping.region == "region"


def test_dirty_superstore_adapter():

    _, _, adapted_df, _ = prepare_dirty_superstore()

    assert "date" in adapted_df.columns
    assert "revenue" in adapted_df.columns
    assert "profit" in adapted_df.columns
    assert "units" in adapted_df.columns
    assert "product" in adapted_df.columns


def test_dirty_superstore_preserves_negative_profit():

    _, _, adapted_df, _ = prepare_dirty_superstore()

    assert (adapted_df["profit"] < 0).any()


def test_dirty_superstore_product_analysis():

    _, _, adapted_df, _ = prepare_dirty_superstore()

    result = analyze_product_performance(
        adapted_df
    )

    assert "product_analysis" in result
    assert not result["product_analysis"].empty


def test_dirty_superstore_regional_analysis():

    _, _, adapted_df, _ = prepare_dirty_superstore()

    result = analyze_regional_performance(
        adapted_df
    )

    assert "regional_analysis" in result
    assert not result["regional_analysis"].empty


def test_dirty_superstore_profitability():

    _, _, adapted_df, _ = prepare_dirty_superstore()

    result = analyze_profitability(
        adapted_df
    )

    assert "total_revenue" in result
    assert "total_profit" in result