"""SSE route emits started → node / token → done without needing a live Groq call for the shell."""

import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    event_name = "message"
    data_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("event:"):
            event_name = line.removeprefix("event:").strip()
        elif line.startswith("data:"):
            data_lines.append(line.removeprefix("data:").strip())
        elif line == "" and data_lines:
            events.append((event_name, json.loads("\n".join(data_lines))))
            event_name = "message"
            data_lines = []
    if data_lines:
        events.append((event_name, json.loads("\n".join(data_lines))))
    return events


def test_stream_emits_started_nodes_and_done():
    with client.stream(
        "POST",
        "/api/agent/stream",
        json={
            "thread_id": "test-1",
            "diff_text": "def add(a, b):\n    return a + b\n",
            "test_code": "",
        },
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    events = _parse_sse(body)
    names = [name for name, _ in events]
    assert names[0] == "started"
    assert "node" in names
    assert "interrupt" in names
    assert names[-1] == "done"
    nodes = [payload["active_node"] for name, payload in events if name == "node"]
    assert nodes[:5] == ["ingest", "retrieve", "security", "refactor", "sandbox"]
    assert "create_pr" not in nodes
    done = next(payload for name, payload in events if name == "done")
    assert done["awaiting_approval"] is True
    assert done["next_node"] == "create_pr"


def test_stream_emits_live_tokens(monkeypatch):
    """Force Groq streaming path and assert token SSE events leave the graph."""

    class FakeModel:
        def stream(self, _messages):
            yield SimpleNamespace(content="A03")
            yield SimpleNamespace(content=" | injection")

    monkeypatch.setattr("app.agent.llm.settings.groq_api_key", "test-key")
    monkeypatch.setattr("app.agent.nodes.security.settings.groq_api_key", "test-key")
    monkeypatch.setattr("app.agent.nodes.refactor.settings.groq_api_key", "test-key")
    monkeypatch.setattr("app.agent.llm.get_chat_model", lambda streaming=False: FakeModel())

    # Refactor should also stream something short.
    call_count = {"n": 0}

    class FakeModelBoth:
        def stream(self, _messages):
            call_count["n"] += 1
            if call_count["n"] == 1:
                yield SimpleNamespace(content="A03 | bad SQL")
            else:
                yield SimpleNamespace(content="def login(user):\n")
                yield SimpleNamespace(content="    return user\n")

    monkeypatch.setattr("app.agent.llm.get_chat_model", lambda streaming=False: FakeModelBoth())

    with client.stream(
        "POST",
        "/api/agent/stream",
        json={
            "thread_id": "test-tokens",
            "diff_text": "diff --git a/app.py b/app.py\n+query = user\n",
            "test_code": "",
        },
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    events = _parse_sse(body)
    names = [name for name, _ in events]
    assert "llm_start" in names
    assert "token" in names
    assert "llm_end" in names

    token_nodes = {payload["node"] for name, payload in events if name == "token"}
    assert "security" in token_nodes
    assert "refactor" in token_nodes

    security_bits = "".join(
        payload["token"]
        for name, payload in events
        if name == "token" and payload["node"] == "security"
    )
    assert "A03" in security_bits
