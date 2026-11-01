from Backend.reasoning import resolve_deterministically
from Backend.schemas import AnalysisRequirement


def test_supported_requirement_resolves_category_performance():
    requirement = AnalysisRequirement(
        requirement="Compare profit margins across product categories.",
        metric="profit_margin",
        dimension="category",
        operation="comparison",
    )

    result = resolve_deterministically(requirement)

    assert result["supported"] is True
    assert result["tool"] == "category_performance"
    assert "category_performance" in result["candidates"]


def test_unsupported_requirement_returns_no_tool():
    requirement = AnalysisRequirement(
        requirement="Calculate changes in profit margin by category.",
        metric="profit_margin",
        dimension="category",
        operation="change",
    )

    result = resolve_deterministically(requirement)

    assert result["supported"] is False
    assert result["tool"] is None
    assert result["candidates"] == []
    assert result["reason"] is not None