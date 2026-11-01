from unittest.mock import MagicMock, patch

from Backend.main import process_evidence_update
from Backend.schemas import StateUpdate


def test_process_evidence_update_updates_investigation_state():
    evidence_context = (
        "Analysis 'revenue_trend' produced "
        "the following result: "
        "{'monthly_revenue': {'2025-01': 250.0, '2025-02': 450.0}}"
    )

    state_update = StateUpdate(
        new_facts=[
            "Revenue increased from January to February."
        ],
        hypotheses_updates=[],
        new_evidence_needed=[],
        current_focus="Determine the cause of the revenue increase.",
        history_entry="Revenue trend evidence was incorporated.",
    )

    with patch(
        "Backend.main.update_state_from_evidence",
        return_value=state_update,
    ) as mock_update, patch(
        "Backend.main.apply_evidence_state_update",
        return_value=state_update,
    ) as mock_apply:

        result = process_evidence_update(
            investigation_id=7,
            evidence_context=evidence_context,
        )

    mock_update.assert_called_once_with(
        investigation_id=7,
        evidence_context=evidence_context,
    )

    mock_apply.assert_called_once_with(
        investigation_id=7,
        state_update=state_update,
    )

    assert result == state_update


def test_process_evidence_update_stops_when_state_generation_fails():
    evidence_context = "Analysis produced invalid evidence."
    service = MagicMock()

    with patch(
        "Backend.main.update_state_from_evidence",
        side_effect=RuntimeError("Evidence update failed."),
    ), patch("Backend.main.get_investigation_service", return_value=service):

        result = process_evidence_update(
            investigation_id=7,
            evidence_context=evidence_context,
        )

    assert result is None
    service.rollback.assert_not_called()
