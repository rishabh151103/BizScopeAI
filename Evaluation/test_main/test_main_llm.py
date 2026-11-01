"""Deterministic tests for conversational and evidence routing."""

from Backend import main
from Backend.schemas import EvidenceRequirement


def test_existing_evidence_routes_interpretation_to_conversation():
    evidence = [{"analysis_name": "category_performance"}]

    assert main.existing_evidence_can_support_followup(
        "What does this result mean for the business?", evidence
    )


def test_new_calculation_is_not_mistaken_for_conversation():
    evidence = [{"analysis_name": "category_performance"}]

    assert not main.existing_evidence_can_support_followup(
        "Calculate average profit margin by region.", evidence
    )


def test_interpretation_without_results_does_not_skip_evidence_decision():
    assert not main.existing_evidence_can_support_followup(
        "What does this result mean?", []
    )


def test_visualization_intent_is_explicit():
    assert main.requests_visualization("Plot monthly revenue as a chart.")
    assert not main.requests_visualization("What does the revenue trend mean?")


def test_evidence_request_uses_qwen_and_returns_schema(monkeypatch):
    captured = {}
    requirement = EvidenceRequirement(
        question="Calculate average profit margin by category.",
        metric="average_profit_margin",
        dimension="category",
        operation="average",
    )

    def fake_call(data, model, schema, **kwargs):
        captured.update(model=model, schema=schema, data=data)
        return requirement

    monkeypatch.setattr(main, "call_structured_ollama", fake_call)

    result = main.build_evidence_requirement(requirement.question)

    assert result == requirement
    assert captured["model"] == "qwen3:4b"
    assert captured["schema"] is EvidenceRequirement


def test_visualization_request_does_not_count_as_evidence_by_itself():
    assert main.requests_visualization("Show me a chart of existing results.")
    assert not main.is_explicit_analysis_request("Show me a chart of existing results.")
