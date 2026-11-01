from unittest.mock import patch

from Backend.main import build_evidence_requirement
from Backend.schemas import (
    AnalysisPlan,
    AnalysisRequirement,
    AnalysisSelection,
    EvidenceRequirement,
)


def test_main_planning_path_uses_structured_evidence_requirement():
    evidence_request = "Analyze monthly revenue trend."

    evidence_requirement = EvidenceRequirement(
        question=evidence_request,
        metric="revenue",
        dimension="month",
        operation="trend",
    )

    expected_plan = AnalysisPlan(
        question_summary=evidence_request,
        analyses=[
            AnalysisSelection(
                analysis_name="revenue_trend",
                requirement=AnalysisRequirement(
                    requirement=evidence_request,
                    metric="revenue",
                    dimension="month",
                    operation="trend",
                    start_month=None,
                    end_month=None,
                ),
            )
        ],
    )

    with patch(
        "Backend.main.build_evidence_requirement",
        return_value=evidence_requirement,
    ), patch(
        "Backend.main.select_analyses_from_requirement",
        return_value=expected_plan,
    ) as mock_planner:

        plan = mock_planner(
            evidence_requirement
        )

        mock_planner.assert_called_once_with(
            evidence_requirement
        )

        assert plan == expected_plan