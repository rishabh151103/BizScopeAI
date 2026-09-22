from pathlib import Path

import pandas as pd
import pytest

from Backend.analytics import analyze_business_comparisons


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "dataset" / "sales_dataset.csv"


@pytest.fixture
def business_data():
    return pd.read_csv(DATASET_PATH)


def test_all_comparison_types_present(business_data):
    result = analyze_business_comparisons(business_data)

    assert set(result.keys()) == {
        "customer_type",
        "region",
        "product",
        "category"
    }


def test_customer_type_comparison(business_data):
    result = analyze_business_comparisons(business_data)

    customer_type = result["customer_type"]

    assert set(customer_type["customer_type"]) == {
        "New",
        "Returning"
    }

    assert customer_type["revenue"].sum() == pytest.approx(
        business_data["revenue"].sum()
    )

    assert customer_type["profit"].sum() == pytest.approx(
        business_data["profit"].sum()
    )


def test_region_comparison(business_data):
    result = analyze_business_comparisons(business_data)

    region = result["region"]

    assert len(region) == 4

    assert region["revenue"].sum() == pytest.approx(
        business_data["revenue"].sum()
    )

    assert region["profit"].sum() == pytest.approx(
        business_data["profit"].sum()
    )


def test_product_comparison(business_data):
    result = analyze_business_comparisons(business_data)

    product = result["product"]

    assert len(product) == 6

    assert product["revenue"].sum() == pytest.approx(
        business_data["revenue"].sum()
    )

    assert product["profit"].sum() == pytest.approx(
        business_data["profit"].sum()
    )


def test_category_comparison(business_data):
    result = analyze_business_comparisons(business_data)

    category = result["category"]

    assert len(category) == 5

    assert category["revenue"].sum() == pytest.approx(
        business_data["revenue"].sum()
    )

    assert category["profit"].sum() == pytest.approx(
        business_data["profit"].sum()
    )


def test_customer_type_order_and_units(business_data):
    result = analyze_business_comparisons(business_data)

    customer_type = result["customer_type"]

    assert customer_type["orders"].sum() == len(business_data)
    assert customer_type["units"].sum() == pytest.approx(
        business_data["units"].sum()
    )


def test_region_order_and_units(business_data):
    result = analyze_business_comparisons(business_data)

    region = result["region"]

    assert region["orders"].sum() == len(business_data)
    assert region["units"].sum() == pytest.approx(
        business_data["units"].sum()
    )


def test_optional_comparison_sections():
    df = pd.DataFrame({
        "customer_type": ["New", "Returning"],
        "revenue": [100, 200],
        "profit": [40, 80],
        "order_id": [1, 2],
        "units": [2, 4]
    })

    result = analyze_business_comparisons(df)

    assert "customer_type" in result
    assert "region" not in result
    assert "product" not in result
    assert "category" not in result


def test_empty_dataframe():
    df = pd.DataFrame()

    result = analyze_business_comparisons(df)

    assert result == {}