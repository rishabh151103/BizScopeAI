from Backend.analysis_planner import (
    select_analyses_from_requirement,
)
from Backend.schemas import EvidenceRequirement


def test_evidence_requirement_can_be_converted_to_analysis_plan():
    evidence_requirement = EvidenceRequirement(
        question="Analyze monthly revenue trend.",
        metric="revenue",
        dimension="month",
        operation="trend",
    )

    plan = select_analyses_from_requirement(
        evidence_requirement
    )

    assert plan.question_summary == (
        "Analyze monthly revenue trend."
    )

    assert len(plan.analyses) == 1

    assert (
        plan.analyses[0].analysis_name
        == "revenue_trend"
    )

    assert "monthly revenue trend" in (
        plan.analyses[0].requirement.requirement.casefold()
    )

    assert (
        plan.analyses[0].requirement.metric
        == "revenue"
    )

    assert (
        plan.analyses[0].requirement.dimension
        == "month"
    )

    assert (
        plan.analyses[0].requirement.operation
        == "trend"
    )
