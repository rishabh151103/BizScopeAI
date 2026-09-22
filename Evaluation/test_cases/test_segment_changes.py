from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from Backend.analytics import analyze_segment_changes


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "dataset" / "sales_dataset.csv"


@pytest.fixture
def business_data():
    df = pd.read_csv(DATASET_PATH)
    df["date"] = pd.to_datetime(df["date"])
    return df


def test_product_segment_count(business_data):
    result = analyze_segment_changes(
        business_data,
        "product",
        "2025-01",
        "2025-02"
    )

    assert len(result) == 6


def test_product_segment_columns(business_data):
    result = analyze_segment_changes(
        business_data,
        "product",
        "2025-01",
        "2025-02"
    )

    expected_columns = [
        "product",
        "start_revenue",
        "end_revenue",
        "revenue_change",
        "revenue_change_percent"
    ]

    assert list(result.columns) == expected_columns


def test_product_revenue_changes(business_data):
    result = analyze_segment_changes(
        business_data,
        "product",
        "2025-01",
        "2025-02"
    )

    laptop = result.loc[
        result["product"] == "Laptop Pro"
    ].iloc[0]

    assert laptop["revenue_change_percent"] == pytest.approx(
        -50.767917,
        abs=1e-5
    )


def test_product_positive_change(business_data):
    result = analyze_segment_changes(
        business_data,
        "product",
        "2025-01",
        "2025-02"
    )

    mouse = result.loc[
        result["product"] == "Mouse M"
    ].iloc[0]

    assert mouse["revenue_change_percent"] == pytest.approx(
        1.819774,
        abs=1e-5
    )


def test_revenue_change_calculation(business_data):
    result = analyze_segment_changes(
        business_data,
        "product",
        "2025-01",
        "2025-02"
    )

    calculated_change = (
        result["end_revenue"]
        - result["start_revenue"]
    )

    assert np.allclose(
        result["revenue_change"],
        calculated_change
    )


def test_revenue_change_percent_calculation(business_data):
    result = analyze_segment_changes(
        business_data,
        "product",
        "2025-01",
        "2025-02"
    )

    valid = result["start_revenue"] != 0

    expected = (
        result.loc[valid, "revenue_change"]
        / result.loc[valid, "start_revenue"]
    ) * 100

    assert np.allclose(
        result.loc[valid, "revenue_change_percent"],
        expected
    )


def test_missing_dimension():
    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2025-01-01",
            "2025-02-01"
        ]),
        "product": ["Laptop Pro", "Laptop Pro"],
        "revenue": [1000, 800]
    })

    with pytest.raises(KeyError):
        analyze_segment_changes(
            df,
            "region",
            "2025-01",
            "2025-02"
        )


def test_segment_existing_only_in_end_month():
    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2025-01-01",
            "2025-02-01"
        ]),
        "product": [
            "Laptop Pro",
            "New Product"
        ],
        "revenue": [
            1000,
            500
        ]
    })

    result = analyze_segment_changes(
        df,
        "product",
        "2025-01",
        "2025-02"
    )

    new_product = result.loc[
        result["product"] == "New Product"
    ].iloc[0]

    assert new_product["start_revenue"] == 0
    assert new_product["end_revenue"] == 500
    assert new_product["revenue_change"] == 500
    assert np.isnan(new_product["revenue_change_percent"])