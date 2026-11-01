from Backend.analysis_planner import select_analyses_from_requirement
from Backend.answer_grounding import answer_category_comparison
from Backend import main
from Backend.schemas import EvidenceRequirement, Hypotheses, InvestigationState


def test_average_profit_margin_by_region_resolves_to_regional_tool():
    requirement = EvidenceRequirement(
        question=(
            "Compare total revenue, total profit, and average profit margin "
            "by region; rank by profit and calculate the top-two gap."
        ),
        metric="average_profit_margin",
        dimension="region",
        operation="average",
    )

    plan = select_analyses_from_requirement(requirement)

    assert plan is not None
    assert [selection.analysis_name for selection in plan.analyses] == [
        "regional_performance"
    ]
    assert plan.analyses[0].requirement.dimension == "region"
    assert plan.analyses[0].requirement.operation == "performance"


def test_regional_ranking_and_gap_come_from_saved_result_values():
    result = [{
        "analysis_name": "regional_performance",
        "result": {
            "regional_analysis": [
                {"region": "North", "total_revenue": 1_250_000, "total_profit": 375_000, "average_profit_margin": 30.0},
                {"region": "South", "total_revenue": 900_000, "total_profit": 315_000, "average_profit_margin": 35.0},
                {"region": "East", "total_revenue": 700_000, "total_profit": 245_000, "average_profit_margin": 35.0},
                {"region": "West", "total_revenue": 600_000, "total_profit": 210_000, "average_profit_margin": 35.0},
            ]
        },
    }]

    answer = answer_category_comparison(
        "Rank the regions by total profit and calculate the gap between the top two.",
        result,
    )

    assert answer is not None
    assert "Region ranking by profit" in answer
    assert "North" in answer and "375,000.00" in answer
    assert "South" in answer and "315,000.00" in answer
    assert "**Gap between the top two:** 60,000.00" in answer


def test_regional_multi_metric_request_ranks_by_the_explicit_ranking_metric():
    result = [{
        "analysis_name": "regional_performance",
        "result": {
            "regional_analysis": [
                {"region": "North", "total_revenue": 1_250_000, "total_profit": 375_000, "average_profit_margin": 30.0},
                {"region": "South", "total_revenue": 900_000, "total_profit": 315_000, "average_profit_margin": 35.0},
            ]
        },
    }]

    answer = answer_category_comparison(
        "Compare total revenue, total profit, and average profit margin by region. "
        "Rank the regions by total profit and calculate the top-two gap.",
        result,
    )

    assert answer is not None
    assert "1. **North** — profit: 375,000.00" in answer
    assert "2. **South** — profit: 315,000.00" in answer
    assert "**Gap between the top two:** 60,000.00" in answer


def _regional_hypothesis_state():
    return InvestigationState(
        problem="Regional sales may not translate into profit.",
        business_context="Multi-region business.",
        confirmed_facts=[],
        hypotheses=[
            Hypotheses(
                id=1,
                statement="Regional sales are driven by low-margin products.",
                basis="Product mix may differ across regions.",
                evidence_needed=["Compare products within each region."],
                status="active",
                priority="high",
            ),
            Hypotheses(
                id=2,
                statement="Regional differences in operating costs affect profitability.",
                basis="Operating expenses may differ by region.",
                evidence_needed=["Compare costs by region."],
                status="active",
                priority="medium",
            ),
            Hypotheses(
                id=3,
                statement="Pricing strategies differ across regions.",
                basis="Pricing may affect regional margins.",
                evidence_needed=["Compare prices or discounts by region."],
                status="active",
                priority="medium",
            ),
        ],
        evidence_needed=[],
        current_focus="Regional profitability",
        investigation_history=[],
    )


def _regional_results():
    return [{
        "analysis_name": "regional_performance",
        "result": {
            "regional_analysis": [
                {"region": "Central", "total_revenue": 503170.67, "total_profit": 39865.31, "average_profit_margin": -10.4745},
                {"region": "East", "total_revenue": 691828.17, "total_profit": 94883.26, "average_profit_margin": 17.0532},
                {"region": "South", "total_revenue": 391721.91, "total_profit": 46749.43, "average_profit_margin": 16.3519},
                {"region": "West", "total_revenue": 739813.61, "total_profit": 110798.82, "average_profit_margin": 22.0214},
            ]
        },
    }]


def test_regional_hypothesis_review_does_not_upgrade_untested_causes():
    response = main.format_regional_hypothesis_review(
        _regional_hypothesis_state(),
        _regional_results(),
    )

    assert "West leads total profit at $110,798.82" in response
    assert "total-profit gap of $15,915.56" in response
    assert "**Hypothesis 1 · Unresolved · High priority:**" in response
    assert "**Hypothesis 2 · Unresolved · Medium priority:**" in response
    assert "**Hypothesis 3 · Unresolved · Medium priority:**" in response
    assert "not by product within each region" in response
    assert "no regional cost or expense measure" in response
    assert "no regional price or discount breakdown" in response
    assert "Supported" not in response


def test_regional_takeaway_labels_the_gap_as_total_profit():
    response = main.format_regional_business_takeaway(_regional_results())

    assert response is not None
    assert "total-profit gap of $15,915.56" in response
    assert "22.02%" in response
    assert "-10.47%" in response
    assert "statistical significance" in response


def test_regional_deferred_recommendation_stays_with_registered_metrics():
    response = main.format_regional_analysis_recommendation(
        "Recommend the most useful first analysis by region, but don't run it yet.",
        {"region", "revenue", "profit", "units"},
    )

    assert response is not None
    assert "average row-level profit margin by region" in response
    assert "cannot establish whether costs, product mix, or pricing caused" in response
    assert "does not calculate statistical significance" in response
    assert "by region and product" not in response


def test_hypothesis_update_and_takeaway_followups_are_conversational_routes():
    question = (
        "Update the investigation hypotheses using the regional results. For "
        "each one, say whether it is supported, weakened, or unresolved, cite "
        "the relevant measured evidence, and explain what the analysis cannot "
        "tell us. Don't infer causes the dataset hasn't tested."
    )
    assert main.is_conversational_evidence_followup(question)
    assert main.is_hypothesis_update_request(
        question
    )
    assert main.is_takeaway_followup(
        "What should I take away as the business owner?"
    )
