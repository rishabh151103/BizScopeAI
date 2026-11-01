import pandas as pd
from unittest.mock import Mock, patch

from Backend.investigation_service import InvestigationService


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


def test_execute_visualization_for_analysis_run():
    db = Mock()
    service = InvestigationService(db)

    analysis_run = type(
        "AnalysisRunStub",
        (),
        {
            "analysis_name": "revenue_trend",
            "result_data": {
                "monthly_revenue": [
                    {
                        "month": "2026-01",
                        "revenue": 1000,
                    },
                    {
                        "month": "2026-02",
                        "revenue": 1200,
                    },
                ]
            },
        },
    )()

    fake_figure = object()

    with patch(
        "Backend.investigation_service.run_visualization",
        create=True,
    ) as mock_run_visualization:

        mock_run_visualization.return_value = fake_figure

        result = service.execute_visualization_for_analysis_run(
            analysis_run
        )

    mock_run_visualization.assert_called_once_with(
        analysis_name="revenue_trend",
        analysis_result=analysis_run.result_data,
    )

    assert result is fake_figure