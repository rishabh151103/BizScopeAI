from unittest.mock import MagicMock, patch

from Backend import main
from Backend.schemas import StateUpdate


def test_update_state_from_evidence_returns_structured_state_update(monkeypatch):
    evidence_context = (
        "Analysis 'revenue_trend' produced "
        "the following result: "
        "{'monthly_revenue': {'2025-01': 250.0, '2025-02': 450.0}}"
    )

    expected_update = StateUpdate(
        new_facts=[
            "Revenue increased from 250.0 in January to 450.0 in February."
        ],
        hypotheses_updates=[],
        new_evidence_needed=[],
        current_focus="Determine what caused the increase in revenue.",
        history_entry="Revenue trend evidence was analyzed.",
    )

    service = MagicMock()
    service.load_state.return_value = MagicMock(model_dump_json=lambda **kwargs: "{}")
    monkeypatch.setattr(main, "get_investigation_service", lambda: service)
    with patch(
        "Backend.main.call_structured_ollama",
        return_value=expected_update,
    ) as mock_llm:

        result = main.update_state_from_evidence(
            investigation_id=7,
            evidence_context=evidence_context,
        )

    assert result == expected_update

    mock_llm.assert_called_once()
