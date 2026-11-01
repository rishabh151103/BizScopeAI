from unittest.mock import MagicMock

from Backend import main


def test_persist_analysis_evidence_creates_evidence_from_analysis_run(monkeypatch):
    analysis_run = MagicMock()
    analysis_run.id = 42
    analysis_run.analysis_name = "revenue_trend"
    analysis_run.result_data = {
        "monthly_revenue": {
            "2025-01": 250.0,
            "2025-02": 450.0,
        }
    }

    service = MagicMock()
    monkeypatch.setattr(main, "get_investigation_service", lambda: service)
    main.persist_analysis_evidence(investigation_id=7, analysis_run=analysis_run)

    service.add_evidence.assert_called_once_with(
        investigation_id=7,
        content=(
            "Analysis 'revenue_trend' produced "
            "the following result: "
            "{'monthly_revenue': {'2025-01': 250.0, "
            "'2025-02': 450.0}}"
        ),
        structured_data=analysis_run.result_data,
        analysis_run_id=42,
    )
