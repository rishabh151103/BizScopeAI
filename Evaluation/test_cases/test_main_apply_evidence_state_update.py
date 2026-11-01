from unittest.mock import MagicMock

from Backend import main
from Backend.schemas import StateUpdate


def test_apply_evidence_state_update_persists_new_state(monkeypatch):
    state_update = StateUpdate(
        new_facts=[
            "Revenue increased significantly over the analyzed period."
        ],
        hypotheses_updates=[],
        new_evidence_needed=[],
        current_focus="Determine the cause of the revenue increase.",
        history_entry="Revenue trend evidence was incorporated.",
    )

    service = MagicMock()
    monkeypatch.setattr(main, "get_investigation_service", lambda: service)
    result = main.apply_evidence_state_update(investigation_id=7, state_update=state_update)

    service.apply_state_update.assert_called_once_with(
        7,
        state_update,
    )

    assert result == state_update
