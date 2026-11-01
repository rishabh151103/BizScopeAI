from unittest.mock import MagicMock

from Backend import main


def test_build_evidence_context_formats_persisted_evidence(monkeypatch):
    evidence = MagicMock()
    evidence.analysis_run_id = 42
    evidence.content = (
        "Analysis 'revenue_trend' produced "
        "the following result: "
        "{'monthly_revenue': {'2025-01': 250.0}}"
    )
    evidence.structured_data = {
        "monthly_revenue": {
            "2025-01": 250.0
        }
    }

    service = MagicMock()
    service.get_evidence.return_value = [evidence]
    monkeypatch.setattr(main, "get_investigation_service", lambda: service)

    context = main.build_evidence_context(investigation_id=7)

    assert "revenue_trend" in context
    assert "2025-01" in context
    assert "250.0" in context
