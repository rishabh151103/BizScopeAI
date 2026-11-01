from pydantic import BaseModel

from Backend import llm_client


def test_ollama_uses_configured_request_timeout(monkeypatch):
    captured = {}

    class Response:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": "ok"}}

    def fake_post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return Response()

    monkeypatch.setattr(llm_client, "OLLAMA_TIMEOUT_SECONDS", 17)
    monkeypatch.setattr(llm_client.requests, "post", fake_post)

    result = llm_client.call_ollama({"messages": []}, "test-model")

    assert result["message"]["content"] == "ok"
    assert captured["timeout"] == (
        llm_client.OLLAMA_CONNECT_TIMEOUT_SECONDS,
        17,
    )


def test_structured_model_output_is_not_written_to_logs(monkeypatch, caplog):
    class Answer(BaseModel):
        answer: str

    monkeypatch.setattr(
        llm_client,
        "call_ollama",
        lambda *args, **kwargs: {
            "message": {"content": '{"answer":"confidential business detail"}'},
            "done_reason": "stop",
            "eval_count": 5,
        },
    )

    with caplog.at_level("DEBUG", logger="Backend.llm_client"):
        result = llm_client.call_structured_ollama(
            {"messages": []}, "test-model", Answer
        )

    assert result.answer == "confidential business detail"
    assert "confidential business detail" not in caplog.text
    assert "content_length" in caplog.text
