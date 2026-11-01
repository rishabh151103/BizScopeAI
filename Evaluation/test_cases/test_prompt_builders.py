from Backend.prompts import (
    SYSTEM_MESSAGE,
    build_evidence_requirement_prompt,
    build_evidence_state_update_prompt,
    build_hypothesis_generation_prompt,
    build_scope_check_prompt,
    build_problem_clarity_prompt,
    build_new_information_state_prompt,
)
from Backend.schemas import Hypotheses, InvestigationState
from Backend.answer_grounding import select_relevant_analysis_results
from Backend.response_prompt import (
    build_response_messages,
    normalize_assistant_response,
    strip_visualization_placeholder,
)


def test_evidence_requirement_prompt_limits_qwen_to_structuring():
    prompt = build_evidence_requirement_prompt("Average profit by region")
    assert "ONLY to structure" in prompt
    assert "Do NOT:" in prompt
    assert "average_profit_margin" in prompt


def test_evidence_state_prompt_uses_current_state_and_new_evidence():
    state = InvestigationState(
        problem="Profit is declining",
        business_context="Retail business",
        current_focus="Discount impact",
        confirmed_facts=[],
        evidence_needed=[],
        hypotheses=[Hypotheses(
            id=1,
            statement="Discounts reduce profit",
            basis="Discount evidence is pending",
            evidence_needed=["Compare profit by discount"],
        )],
        investigation_history=[],
    )
    prompt = build_evidence_state_update_prompt(state, '[{"profit": -12}]')
    assert "Profit is declining" in prompt
    assert '"profit": -12' in prompt
    assert "Preserve\nstatus for hypotheses this analysis did not test" in prompt


def test_hypothesis_generation_prompt_requires_testable_unresolved_explanations():
    prompt = build_hypothesis_generation_prompt("{}", '{"profit": 10}', "Why?")
    assert "DIAGNOSTIC QUESTION:\nWhy?" in prompt
    assert "Keep status active until that test has actually run" in prompt


def test_scope_and_clarity_prompts_include_latest_user_message():
    scope = build_scope_check_prompt("Sales issue", "prior turns", "We changed price")
    clarity = build_problem_clarity_prompt("Revenue fell last month")
    assert "We changed price" in scope
    assert "Revenue fell last month" in clarity
    assert "Do not generate hypotheses" in clarity


def test_shared_system_prompt_preserves_evidence_and_uncertainty_rules():
    text = SYSTEM_MESSAGE["content"]
    assert "Do not infer or invent facts" in text
    assert "Generate hypotheses only for unresolved" in text


def test_category_revenue_chart_selection_excludes_overall_revenue_chart():
    results = [
        {"analysis_name": "revenue_trend", "result": {}},
        {"analysis_name": "category_revenue_trend", "result": {}},
    ]
    selected = select_relevant_analysis_results(
        results,
        "Show monthly revenue by category as a chart.",
    )
    assert [item["analysis_name"] for item in selected] == [
        "category_revenue_trend"
    ]


def test_followup_response_rules_limit_claims_from_discount_group_results():
    messages = build_response_messages(
        latest_question="What do these discount results tell us?",
        state={},
        recent_messages=[],
        evidence_context="",
        structured_results=(
            '{"selected_analysis_names":["discount_performance"],'
            '"analysis_results":[]}'
        ),
    )
    prompt = messages[1]["content"]

    assert "grouped table alone shows observed" in messages[0]["content"].casefold()
    assert "does not calculate a correlation coefficient" in prompt
    assert "transaction_count" in prompt
    assert "No selected correlation analysis is available" in prompt


def test_correlation_response_rule_is_not_added_when_correlation_result_is_selected():
    messages = build_response_messages(
        latest_question="Interpret this result",
        state={},
        recent_messages=[],
        evidence_context="",
        structured_results='{"selected_analysis_names":["correlations"]}',
    )

    assert "No selected correlation analysis is available" not in messages[1]["content"]


def test_regional_followup_rules_compare_stored_values_and_limit_causal_claims():
    messages = build_response_messages(
        latest_question="What do the regional results change?",
        state={},
        recent_messages=[],
        evidence_context="",
        structured_results=(
            '{"selected_analysis_names":["regional_performance"]}'
        ),
    )
    prompt = messages[1]["content"]

    assert "do not say the regional margin differs when the reported values are equal" in prompt
    assert "do not measure regional cost structures, product mix, or pricing strategy" in prompt


def test_response_prompt_forbids_written_visualization_placeholders():
    messages = build_response_messages(
        latest_question="Show a chart of regional profit.",
        state={},
        recent_messages=[],
        evidence_context="",
        structured_results='{"selected_analysis_names":[]}',
    )

    assert "Never write visual placeholders" in messages[0]["content"]


def test_visualization_placeholder_is_removed_from_response_text():
    response = (
        "The regions differ in total revenue.\n\n"
        "Visualization:\n[Visualization of the data above — a bar chart.]"
    )

    cleaned = strip_visualization_placeholder(response)

    assert "The regions differ in total revenue." in cleaned
    assert "Visualization" not in cleaned
    assert "bar chart" not in cleaned


def test_json_answer_envelope_is_normalized_to_plain_markdown():
    response = '''```json
{"regional_performance_analysis":{"summary":"## Regional results\\n\\n| Region | Profit |\\n|---|---:|\\n| North | 100 |"}}
```'''

    normalized = normalize_assistant_response(response)

    assert normalized.startswith("## Regional results")
    assert "regional_performance_analysis" not in normalized
    assert "\\n" not in normalized
