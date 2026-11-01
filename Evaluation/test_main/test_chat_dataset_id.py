from Backend import main


def test_chat_passes_dataset_id(monkeypatch):
    captured = {}

    def mock_process_message(
        message,
        **kwargs,
    ):
        captured["message"] = message
        captured.update(kwargs)

        return {
            "response": "test response",
            "visualizations": [],
        }

    monkeypatch.setattr(
        main,
        "process_message",
        mock_process_message,
    )

    request = main.ChatRequest(
        message="Why did revenue decline?",
        dataset_id=123,
    )

    response = main.chat(request, db=object())

    assert captured["message"] == "Why did revenue decline?"
    assert captured["dataset_id"] == 123
    assert captured["investigation_id"] is None
    assert captured["include_visualizations"] is True

    assert response == {
        "response": "test response",
        "visualizations": [],
    }


def test_chat_returns_visualizations(monkeypatch):
    fake_visualization = {
        "data": [
            {
                "type": "bar",
                "x": ["Jan", "Feb"],
                "y": [100, 90],
            }
        ],
        "layout": {},
    }

    def mock_process_message(
        message,
        **kwargs,
    ):
        return {
            "response": "Revenue declined.",
            "visualizations": [
                fake_visualization,
            ],
        }

    monkeypatch.setattr(
        main,
        "process_message",
        mock_process_message,
    )

    request = main.ChatRequest(
        message="Why did revenue decline?",
        dataset_id=123,
    )

    response = main.chat(request, db=object())

    assert response["response"] == "Revenue declined."
    assert len(response["visualizations"]) == 1

    visualization = response["visualizations"][0]

    assert visualization["data"][0]["type"] == "bar"
    assert visualization["data"][0]["x"] == ["Jan", "Feb"]
    assert visualization["data"][0]["y"] == [100, 90]
