import numpy as np
import pandas as pd

from Backend.result_serializer import serialize_result


def test_serialize_dataframe():
    df = pd.DataFrame(
        {
            "Product": ["A", "B"],
            "Revenue": [100, 200],
        }
    )

    result = serialize_result(df)

    assert result == [
        {
            "Product": "A",
            "Revenue": 100,
        },
        {
            "Product": "B",
            "Revenue": 200,
        },
    ]


def test_serialize_nested_numpy_values():
    result = serialize_result(
        {
            "count": np.int64(10),
            "average": np.float64(25.5),
            "active": np.bool_(True),
        }
    )

    assert result == {
        "count": 10,
        "average": 25.5,
        "active": True,
    }


def test_serialize_nested_dataframe():
    result = serialize_result(
        {
            "summary": pd.DataFrame(
                {
                    "Region": ["North", "South"],
                    "Revenue": [100, 200],
                }
            ),
            "total": np.int64(300),
        }
    )

    assert result == {
        "summary": [
            {
                "Region": "North",
                "Revenue": 100,
            },
            {
                "Region": "South",
                "Revenue": 200,
            },
        ],
        "total": 300,
    }


def test_serialize_dataframe_with_pandas_period():
    df = pd.DataFrame(
        {
            "month": pd.period_range(
                "2025-01",
                periods=2,
                freq="M",
            ),
            "revenue": [1000, 1500],
        }
    )

    result = serialize_result(df)

    assert result == [
        {
            "month": "2025-01",
            "revenue": 1000,
        },
        {
            "month": "2025-02",
            "revenue": 1500,
        },
    ]


def test_serialize_nan_and_infinite_values():
    result = serialize_result(
        {
            "nan": np.nan,
            "positive_infinity": np.inf,
            "negative_infinity": -np.inf,
            "valid": 25.5,
        }
    )

    assert result == {
        "nan": None,
        "positive_infinity": None,
        "negative_infinity": None,
        "valid": 25.5,
    }

def test_serialize_dataframe_with_nan():
    df = pd.DataFrame(
        {
            "month": pd.period_range(
                "2025-01",
                periods=2,
                freq="M",
            ),
            "revenue": [250, 450],
            "percentage_change": [np.nan, 80.0],
        }
    )

    result = serialize_result(df)

    assert result == [
        {
            "month": "2025-01",
            "revenue": 250,
            "percentage_change": None,
        },
        {
            "month": "2025-02",
            "revenue": 450,
            "percentage_change": 80.0,
        },
    ]            