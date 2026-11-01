import pytest

from Backend import analysis_planner
from Backend.analytics_registry import ANALYTICS_REGISTRY
from Backend.schemas import AnalysisPlan, AnalysisRequirement, RequirementPlan


def get_selected_names(plan):
    return {selection.analysis_name for selection in plan.analyses}


@pytest.fixture
def offline_requirement_extraction(monkeypatch):
    """Keep planner tests deterministic and independent of a local Qwen server."""

    def extract(question):
        text = question.casefold()
        requirements = []

        if "revenue" in text and ("declined" in text or "decline" in text):
            requirements.append(
                AnalysisRequirement(
                    requirement="Analyze the revenue trend over time.",
                    metric="revenue",
                    dimension="month",
                    operation="trend",
                )
            )

        if "product" in text:
            if "between january and february 2025" in text:
                requirements.append(
                    AnalysisRequirement(
                        requirement="Compare product revenue from January to February 2025.",
                        metric="revenue",
                        dimension="product",
                        operation="change",
                        start_month="2025-01",
                        end_month="2025-02",
                    )
                )
            else:
                requirements.append(
                    AnalysisRequirement(
                        requirement="Compare product performance.",
                        metric="revenue",
                        dimension="product",
                        operation="maximum",
                    )
                )

        if not requirements:
            requirements.append(
                AnalysisRequirement(
                    requirement="Analyze the business question.",
                    metric="revenue",
                    dimension="month",
                    operation="trend",
                )
            )

        return RequirementPlan(
            question_summary=question,
            requirements=requirements,
        )

    monkeypatch.setattr(analysis_planner, "extract_requirements", extract)
    return extract


def test_analysis_planner_returns_valid_plan(offline_requirement_extraction):
    question = "Why has our revenue declined and which product is still performing nicely?"

    plan = analysis_planner.select_analyses(question)

    assert isinstance(plan, AnalysisPlan)
    assert plan.question_summary == question
    assert 1 <= len(plan.analyses) <= 5
    for selection in plan.analyses:
        assert selection.analysis_name in ANALYTICS_REGISTRY
        assert selection.requirement.requirement.strip()


def test_analysis_selection_preserves_requirement(offline_requirement_extraction):
    plan = analysis_planner.select_analyses("Why has our revenue declined?")

    assert len(plan.analyses) == 1
    assert plan.analyses[0].requirement.metric == "revenue"
    assert plan.analyses[0].requirement.dimension == "month"
    assert plan.analyses[0].requirement.operation == "trend"


def test_revenue_question_selects_revenue_analysis(offline_requirement_extraction):
    plan = analysis_planner.select_analyses("Why has our revenue declined?")
    assert "revenue_trend" in get_selected_names(plan)


def test_product_question_selects_product_analysis(offline_requirement_extraction):
    plan = analysis_planner.select_analyses("Which product is performing best?")
    assert "product_performance" in get_selected_names(plan)


def test_multi_intent_question_selects_multiple_analyses(offline_requirement_extraction):
    plan = analysis_planner.select_analyses(
        "Why has revenue declined and which product is still performing nicely?"
    )
    assert {"revenue_trend", "product_performance"}.issubset(
        get_selected_names(plan)
    )


def test_empty_question_is_rejected():
    with pytest.raises(ValueError):
        analysis_planner.select_analyses("")


def test_analysis_planner_extracts_comparison_period(offline_requirement_extraction):
    plan = analysis_planner.select_analyses(
        "How did product revenue change between January and February 2025?"
    )

    requirement = plan.analyses[0].requirement
    assert plan.analyses[0].analysis_name == "segment_changes"
    assert requirement.metric == "revenue"
    assert requirement.dimension == "product"
    assert requirement.operation == "change"
    assert requirement.start_month == "2025-01"
    assert requirement.end_month == "2025-02"
