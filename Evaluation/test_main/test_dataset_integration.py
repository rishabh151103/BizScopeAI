from Backend import main


def test_chat_forwards_dataset_and_investigation_ids(monkeypatch):
    captured = {}

    def fake_process_message(message, **kwargs):
        captured["message"] = message
        captured.update(kwargs)
        return {"response": "Investigation continued.", "visualizations": []}

    monkeypatch.setattr(main, "process_message", fake_process_message)

    request = main.ChatRequest(
        message="Analyze the latest revenue trend.",
        dataset_id=123,
        investigation_id=456,
    )
    result = main.chat(request, db=object())

    assert captured == {
        "message": "Analyze the latest revenue trend.",
        "investigation_id": 456,
        "dataset_id": 123,
        "branch_context": [],
        "include_visualizations": True,
    }
    assert result["response"] == "Investigation continued."
    assert main._investigation_service_context.get() is None
    assert main._dataset_service_context.get() is None
