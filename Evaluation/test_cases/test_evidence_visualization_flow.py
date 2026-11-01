from unittest.mock import MagicMock, Mock, patch

import pandas as pd

from Backend import main


def test_evidence_execution_collects_visualization():
    fake_analysis_run = Mock()
    fake_analysis_run.analysis_name = "revenue_trend"
    fake_analysis_run.result_data = {
        "monthly_revenue": [
            {
                "month": "Jan",
                "revenue": 100,
            },
            {
                "month": "Feb",
                "revenue": 90,
            },
        ]
    }

    fake_visualization = Mock()

    analysis_plan = Mock()
    analysis_plan.analyses = [Mock()]

    service = MagicMock()
    service.execute_analysis_selection.return_value = fake_analysis_run
    with patch("Backend.main.get_investigation_service", return_value=service), patch.object(
        service,
        "execute_analysis_selection",
        return_value=fake_analysis_run,
    ) as mock_execute, patch(
        "Backend.main.run_visualization",
        return_value=fake_visualization,
    ) as mock_visualization:

        results = main.execute_analysis_plan(
            investigation_id=1,
            df=pd.DataFrame(
                {
                    "month": ["Jan", "Feb"],
                    "revenue": [100, 90],
                }
            ),
            analysis_plan=analysis_plan,
        )

    assert mock_execute.call_count == 1

    mock_visualization.assert_called_once_with(
        analysis_name="revenue_trend",
        analysis_result=fake_analysis_run.result_data,
    )

    assert len(results) == 1

    assert results[0]["analysis_run"] is fake_analysis_run
    assert results[0]["visualization"] is fake_visualization
