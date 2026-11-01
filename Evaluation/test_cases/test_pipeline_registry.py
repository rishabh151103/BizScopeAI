import pandas as pd
import pytest

from Backend.pipeline import run_analysis
from Backend.schema_mapper import map_business_columns


def create_test_dataframe():
    return pd.DataFrame({
        "date": pd.to_datetime([
            "2025-01-01",
            "2025-01-15",
            "2025-02-01",
            "2025-02-15",
        ]),
        "product": [
            "Laptop",
            "Monitor",
            "Laptop",
            "Monitor",
        ],
        "revenue": [
            1000,
            1500,
            1200,
            1800,
        ],
        "profit": [
            200,
            300,
            240,
            360,
        ],
        "units": [
            10,
            15,
            12,
            18,
        ],
        "profit_margin_percent": [
            20.0,
            20.0,
            20.0,
            20.0,
        ],
    })

def test_run_registered_analysis():

    df = create_test_dataframe()

    mapping = map_business_columns(df)

    result = run_analysis(
        df,
        mapping,
        "revenue_trend"
    )

    assert isinstance(result, dict)

    assert "monthly_revenue" in result
    assert "overall_change_percent" in result
    assert "trend" in result


def test_run_analysis_uses_registry():

    df = create_test_dataframe()

    mapping = map_business_columns(df)

    result = run_analysis(
        df,
        mapping,
        "profitability"
    )

    assert isinstance(result, dict)

    assert "total_revenue" in result
    assert "total_profit" in result


def test_unknown_analysis_raises_error():

    df = create_test_dataframe()

    mapping = map_business_columns(df)

    with pytest.raises(ValueError, match="Unknown analysis"):

        run_analysis(
            df,
            mapping,
            "does_not_exist"
        )