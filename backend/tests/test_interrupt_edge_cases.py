"""Edge cases around interrupt_before: reject, force, double-approve, restream."""

import json

from fastapi.testclient import TestClient

from app.main import app
from app.services.review_store import review_store

client = TestClient(app)

DIFF = """\
diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,2 +1,2 @@
 def login(user):
-    return user
+    return "SELECT ?", (user,)
"""


def setup_function() -> None:
    review_store.clear()


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


def _stream(thread_id: str, diff_text: str = DIFF, test_code: str = "") -> list[tuple[str, dict]]:
    with client.stream(
        "POST",
        "/api/agent/stream",
        json={"thread_id": thread_id, "diff_text": diff_text, "test_code": test_code},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    return _parse_sse(body)


def test_reject_clears_paused_thread():
    _stream("edge-reject")
    rejected = client.post("/api/agent/reject", json={"thread_id": "edge-reject"})
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    approve = client.post(
        "/api/agent/approve",
        json={
            "thread_id": "edge-reject",
            "owner": "vinayrawat058",
            "repo": "autonomous-code-review",
        },
    )
    assert approve.status_code == 404


def test_double_approve_returns_existing_pr(monkeypatch):
    monkeypatch.setattr("app.services.github_pr.settings.github_token", "")
    _stream("edge-double")
    first = client.post(
        "/api/agent/approve",
        json={
            "thread_id": "edge-double",
            "owner": "vinayrawat058",
            "repo": "autonomous-code-review",
            "file_path": "app.py",
        },
    )
    assert first.status_code == 200
    second = client.post(
        "/api/agent/approve",
        json={
            "thread_id": "edge-double",
            "owner": "vinayrawat058",
            "repo": "autonomous-code-review",
            "file_path": "app.py",
        },
    )
    assert second.status_code == 200
    body = second.json()
    assert body["pr_url"] == first.json()["pr_url"]
    assert "already created" in body["message"].lower()


def test_approve_blocked_when_tests_fail_unless_forced(monkeypatch):
    monkeypatch.setattr("app.services.github_pr.settings.github_token", "")
    from app.agent.graph import workflow

    _stream("edge-force")
    config = {"configurable": {"thread_id": "edge-force"}}
    # as_node=sandbox recomputes the branch; high iteration keeps await_approval → create_pr.
    workflow.update_state(
        config,
        {"test_errors": ["assert False"], "iteration": 99},
        as_node="sandbox",
    )

    blocked = client.post(
        "/api/agent/approve",
        json={
            "thread_id": "edge-force",
            "owner": "vinayrawat058",
            "repo": "autonomous-code-review",
            "force": False,
        },
    )
    assert blocked.status_code == 409

    forced = client.post(
        "/api/agent/approve",
        json={
            "thread_id": "edge-force",
            "owner": "vinayrawat058",
            "repo": "autonomous-code-review",
            "force": True,
        },
    )
    assert forced.status_code == 200


def test_restream_same_thread_id_resets_checkpoint(monkeypatch):
    monkeypatch.setattr("app.services.github_pr.settings.github_token", "")
    first = _stream("edge-restream")
    assert any(name == "interrupt" for name, _ in first)

    second = _stream("edge-restream")
    assert any(name == "interrupt" for name, _ in second)

    # Fresh pause should still be approvable once.
    ok = client.post(
        "/api/agent/approve",
        json={
            "thread_id": "edge-restream",
            "owner": "vinayrawat058",
            "repo": "autonomous-code-review",
            "file_path": "app.py",
        },
    )
    assert ok.status_code == 200
