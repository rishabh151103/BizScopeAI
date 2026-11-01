from unittest.mock import MagicMock, patch

import pandas as pd

from Backend.main import execute_analysis_plan
from Backend.schemas import (
    AnalysisPlan,
    AnalysisRequirement,
    AnalysisSelection,
)


def test_v2_execution_uses_canonical_dataset(monkeypatch):
    from Backend import main
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
            "revenue": [
                100.0,
                150.0,
                200.0,
                250.0,
            ],
            "profit": [
                20.0,
                30.0,
                40.0,
                50.0,
            ],
        }
    )

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

    fake_analysis_run = MagicMock()
    fake_analysis_run.analysis_name = "revenue_trend"
    fake_analysis_run.result_data = {
        "monthly_revenue": {
            "2025-01": 250.0,
            "2025-02": 450.0,
        }
    }

    service = MagicMock()
    service.execute_analysis_selection.return_value = fake_analysis_run
    monkeypatch.setattr(main, "get_investigation_service", lambda: service)
    with patch.object(
        service,
        "execute_analysis_selection",
        return_value=fake_analysis_run,
    ) as mock_execute,patch(
        "Backend.main.run_visualization", return_value=None):

        result = execute_analysis_plan(
            investigation_id=1,
            df=df,
            analysis_plan=analysis_plan,
        )

    mock_execute.assert_called_once_with(
        investigation_id=1,
        df=df,
        selection=analysis_plan.analyses[0],
    )

    assert len(result) == 1
    assert (
    result[0]["analysis_run"].result_data["monthly_revenue"]["2025-01"]
    == 250.0
    )



def test_v2_pipeline_rolls_back_when_analysis_fails(monkeypatch):
    from Backend import main

    rollback_called = False

    def fake_rollback():
        nonlocal rollback_called
        rollback_called = True

    service = MagicMock()
    service.rollback = fake_rollback
    monkeypatch.setattr(main, "get_investigation_service", lambda: service)

    def fake_analysis_execution(**kwargs):
        raise RuntimeError("Simulated analysis failure")

    monkeypatch.setattr(
        main,
        "execute_analysis_plan",
        fake_analysis_execution,
    )

    monkeypatch.setattr(
        main,
        "build_evidence_requirement",
        lambda request: object(),
    )

    monkeypatch.setattr(
        main,
        "select_analyses_from_requirement",
        lambda requirement: object(),
    )
