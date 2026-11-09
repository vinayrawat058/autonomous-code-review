"""SSE route emits started → node → done without needing a live Groq call for the shell."""

import json

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
    assert names[-1] == "done"
    nodes = [payload["active_node"] for name, payload in events if name == "node"]
    assert nodes[:5] == ["ingest", "retrieve", "security", "refactor", "sandbox"]
