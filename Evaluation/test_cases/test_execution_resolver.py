from Backend.execution_resolver import resolve_execution_parameters
from Backend.schemas import AnalysisRequirement, AnalysisSelection


def test_segment_changes_execution_parameters():

    requirement = AnalysisRequirement(
        requirement="Compare product revenue between January and February 2025",
        metric="revenue",
        dimension="product",
        operation="change",
        start_month="2025-01",
        end_month="2025-02",
    )

    selection = AnalysisSelection(
        analysis_name="segment_changes",
        requirement=requirement,
    )

    params = resolve_execution_parameters(selection)

    assert params == {
        "dimension": "product",
        "start_month": "2025-01",
        "end_month": "2025-02",
    }


def test_non_parameterized_analysis_returns_empty_parameters():

    requirement = AnalysisRequirement(
        requirement="Analyze revenue trend",
        metric="revenue",
        dimension="time",
        operation="trend",
    )

    selection = AnalysisSelection(
        analysis_name="revenue_trend",
        requirement=requirement,
    )

    params = resolve_execution_parameters(selection)

    assert params == {}