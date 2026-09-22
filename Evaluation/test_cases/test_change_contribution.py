from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from Backend.analytics import analyze_change_contribution


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "dataset" / "sales_dataset.csv"


@pytest.fixture
def business_data():
    df = pd.read_csv(DATASET_PATH)
    df["date"] = pd.to_datetime(df["date"])
    return df


def test_product_segment_count(business_data):
    result = analyze_change_contribution(
        business_data,
        "product",
        "2025-01",
        "2025-02"
    )

    assert len(result) == 6


def test_expected_columns(business_data):
    result = analyze_change_contribution(
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
        "contribution_to_total_change_percent"
    ]

    assert list(result.columns) == expected_columns


def test_laptop_contribution(business_data):
    result = analyze_change_contribution(
        business_data,
        "product",
        "2025-01",
        "2025-02"
    )

    laptop = result.loc[
        result["product"] == "Laptop Pro"
    ].iloc[0]

    assert laptop["contribution_to_total_change_percent"] == pytest.approx(
        87.316588,
        abs=1e-5
    )


def test_headset_contribution(business_data):
    result = analyze_change_contribution(
        business_data,
        "product",
        "2025-01",
        "2025-02"
    )

    headset = result.loc[
        result["product"] == "Headset H"
    ].iloc[0]

    assert headset["contribution_to_total_change_percent"] == pytest.approx(
        9.222161,
        abs=1e-5
    )


def test_webcam_negative_contribution(business_data):
    result = analyze_change_contribution(
        business_data,
        "product",
        "2025-01",
        "2025-02"
    )

    webcam = result.loc[
        result["product"] == "Webcam W"
    ].iloc[0]

    assert webcam["contribution_to_total_change_percent"] == pytest.approx(
        -4.614864,
        abs=1e-5
    )


def test_contributions_sum_to_100(business_data):
    result = analyze_change_contribution(
        business_data,
        "product",
        "2025-01",
        "2025-02"
    )

    total_contribution = (
        result["contribution_to_total_change_percent"].sum()
    )

    assert total_contribution == pytest.approx(100.0)


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
        analyze_change_contribution(
            df,
            "region",
            "2025-01",
            "2025-02"
        )


def test_zero_total_change():
    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2025-01-01",
            "2025-02-01"
        ]),
        "product": [
            "Laptop Pro",
            "Laptop Pro"
        ],
        "revenue": [
            1000,
            1000
        ]
    })

    result = analyze_change_contribution(
        df,
        "product",
        "2025-01",
        "2025-02"
    )

    assert result["revenue_change"].iloc[0] == 0
    assert np.isnan(
        result["contribution_to_total_change_percent"].iloc[0]
    )