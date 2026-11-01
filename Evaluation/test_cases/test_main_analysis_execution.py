from unittest.mock import MagicMock, patch

from Backend import main
from Backend.schemas import (
    AnalysisPlan,
    AnalysisRequirement,
    AnalysisSelection,
)


def test_direct_regional_analysis_request_is_never_routed_as_conversation():
    question = "Run the regional analysis and compare revenue with profit."

    assert main.is_explicit_analysis_request(question)
    assert not main.is_conversational_evidence_followup(question)


def test_execute_analysis_plan_runs_all_planned_analyses():
    analysis_plan = AnalysisPlan(
        question_summary="Analyze monthly revenue trend.",
        analyses=[
            AnalysisSelection(
                analysis_name="revenue_trend",
                requirement=AnalysisRequirement(
                    requirement="Analyze monthly revenue trend.",
                    metric="revenue",
                    dimension="month",
                    operation="trend",
                ),
            )
        ],
    )

    expected_run = type(
        "AnalysisRunStub",
        (),
        {
            "analysis_name": "revenue_trend",
            "result_data": {
                "monthly_revenue": [
                    {
                        "month": "2025-01",
                        "revenue": 250.0,
                    },
                    {
                        "month": "2025-02",
                        "revenue": 450.0,
                    },
                ]
            },
            "status": "completed",
        },
    )()

    fake_visualization = "FIGURE"

    service = MagicMock()
    service.execute_analysis_selection.return_value = expected_run
    with patch("Backend.main.get_investigation_service", return_value=service), patch.object(
        service,
        "execute_analysis_selection",
        return_value=expected_run,
    ) as mock_execute, patch(
        "Backend.main.run_visualization",
        return_value=fake_visualization,
    ) as mock_visualization:

        result = main.execute_analysis_plan(
            investigation_id=1,
            df="TEST_DF",
            analysis_plan=analysis_plan,
        )

    mock_execute.assert_called_once_with(
        investigation_id=1,
        df="TEST_DF",
        selection=analysis_plan.analyses[0],
    )

    mock_visualization.assert_called_once_with(
        analysis_name="revenue_trend",
        analysis_result=expected_run.result_data,
    )

    assert len(result) == 1

    assert result[0]["analysis_run"] is expected_run
    assert result[0]["visualization"] == fake_visualization
