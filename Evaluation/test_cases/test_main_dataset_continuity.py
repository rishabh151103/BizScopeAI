from unittest.mock import Mock

from Backend import main


def test_resolve_analysis_dataset_id_uses_persisted_investigation_dataset(monkeypatch):
    service = Mock()
    service.load_state.return_value.dataset_id = 42
    monkeypatch.setattr(main, "get_investigation_service", lambda: service)
    result = main.resolve_analysis_dataset_id(investigation_id=7, dataset_id=None)

    assert result == 42


def test_resolve_analysis_dataset_id_prefers_explicit_dataset_id(monkeypatch):
    service = Mock()
    monkeypatch.setattr(main, "get_investigation_service", lambda: service)
    result = main.resolve_analysis_dataset_id(
        investigation_id=7,
        dataset_id=99,
    )

    assert result == 99
