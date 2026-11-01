from Backend import main
from Backend.schemas import EvidenceRequirement


def test_build_evidence_requirement_returns_typed_requirement(monkeypatch):
    expected = EvidenceRequirement(
        question="Analyze monthly revenue trend.",
        metric="revenue",
        dimension="month",
        operation="trend",
    )

    monkeypatch.setattr(
        main,
        "call_structured_ollama",
        lambda *args, **kwargs: expected,
    )

    result = main.build_evidence_requirement(expected.question)

    assert result == expected
    assert result.metric == "revenue"
    assert result.dimension == "month"
    assert result.operation == "trend"


def test_build_evidence_requirement_uses_qwen(monkeypatch):
    captured = {}
    expected = EvidenceRequirement(
        question="Analyze customer retention.",
        metric="customer_retention",
        dimension="month",
        operation="trend",
    )

    def fake_call(data, model, schema, **kwargs):
        captured.update(model=model, schema=schema)
        return expected

    monkeypatch.setattr(main, "call_structured_ollama", fake_call)

    result = main.build_evidence_requirement(expected.question)

    assert result == expected
    assert captured["model"] == "qwen3:4b"
    assert captured["schema"] is EvidenceRequirement
