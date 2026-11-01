import pandas as pd
import pytest

from Backend.analysis_executor import execute_analysis
from Backend.schemas import AnalysisSelection, AnalysisRequirement


def test_execute_analysis_calls_registered_function(monkeypatch):

    df = pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2025-01-01", "2025-02-01"]
            ),
            "revenue": [100, 200],
        }
    )

    expected_result = {
        "trend": "increasing"
    }

    def fake_analysis(dataframe):
        assert dataframe is df
        return expected_result

    monkeypatch.setitem(
        __import__(
            "Backend.analysis_executor",
            fromlist=["ANALYTICS_REGISTRY"]
        ).ANALYTICS_REGISTRY,
        "revenue_trend",
        {
            "function": fake_analysis,
            "description": "test",
            "answers": [],
        },
    )

    selection = AnalysisSelection(
        analysis_name="revenue_trend",
        requirement=AnalysisRequirement(
            requirement="Determine revenue trend",
            metric="revenue",
            dimension="time",
            operation="trend",
        ),
    )

    result = execute_analysis(
        df,
        selection,
    )

    assert result == expected_result


def test_execute_analysis_passes_resolved_parameters(monkeypatch):

    df = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2025-01-01",
                    "2025-02-01",
                ]
            ),
            "product": [
                "A",
                "A",
            ],
            "revenue": [
                100,
                150,
            ],
        }
    )

    captured = {}

    def fake_analysis(
        dataframe,
        dimension,
        start_month,
        end_month,
    ):
        captured["dimension"] = dimension
        captured["start_month"] = start_month
        captured["end_month"] = end_month

        return {"ok": True}

    monkeypatch.setitem(
        __import__(
            "Backend.analysis_executor",
            fromlist=["ANALYTICS_REGISTRY"]
        ).ANALYTICS_REGISTRY,
        "segment_changes",
        {
            "function": fake_analysis,
            "description": "test",
            "answers": [],
        },
    )

    selection = AnalysisSelection(
        analysis_name="segment_changes",
        requirement=AnalysisRequirement(
            requirement="Compare product revenue",
            metric="revenue",
            dimension="product",
            operation="change",
            start_month="2025-01",
            end_month="2025-02",
        ),
    )

    result = execute_analysis(
        df,
        selection,
    )

    assert result == {"ok": True}

    assert captured == {
        "dimension": "product",
        "start_month": "2025-01",
        "end_month": "2025-02",
    }


def test_execute_analysis_rejects_unknown_analysis(monkeypatch):

    df = pd.DataFrame(
        {
            "revenue": [100]
        }
    )

    selection = AnalysisSelection(
        analysis_name="revenue_trend",
        requirement=AnalysisRequirement(
            requirement="Test",
            metric="revenue",
            dimension="business",
            operation="overall",
        ),
    )

    monkeypatch.delitem(
        __import__(
            "Backend.analysis_executor",
            fromlist=["ANALYTICS_REGISTRY"]
        ).ANALYTICS_REGISTRY,
        "revenue_trend",
    )

    with pytest.raises(
        ValueError,
        match="Unknown analysis",
    ):
        execute_analysis(
            df,
            selection,
        )