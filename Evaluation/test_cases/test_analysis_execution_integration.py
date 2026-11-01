import pandas as pd

from Backend.analysis_executor import execute_analysis
from Backend.analysis_planner import AnalysisSelection
from Backend.result_serializer import serialize_result


def test_revenue_trend_real_execution_is_json_safe():

    df = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2025-01-01",
                    "2025-01-15",
                    "2025-02-01",
                    "2025-02-15",
                ]
            ),
            "revenue": [100, 150, 200, 250],
            "profit": [20, 30, 40, 50],
        }
    )

    selection = AnalysisSelection(
        analysis_name="revenue_trend",
        requirement={
            "requirement": "Determine revenue trend",
            "metric": "revenue",
            "dimension": "time",
            "operation": "trend",
            "start_month": None,
            "end_month": None,
        },
    )

    result = execute_analysis(
        df,
        selection,
    )

    serialized = serialize_result(result)

    assert isinstance(serialized, dict)

    assert serialized["trend"] is not None