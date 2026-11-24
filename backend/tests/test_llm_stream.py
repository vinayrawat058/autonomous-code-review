"""stream_complete yields chunks and returns the joined reply."""

from types import SimpleNamespace

from app.agent import llm


def test_stream_complete_joins_chunks(monkeypatch):
    class FakeModel:
        def stream(self, _messages):
            yield SimpleNamespace(content="hel")
            yield SimpleNamespace(content="lo")

    monkeypatch.setattr(llm, "get_chat_model", lambda streaming=False: FakeModel())
    assert llm.stream_complete("hi", node="security") == "hello"
