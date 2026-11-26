"""Approve resumes a graph paused by interrupt_before=['create_pr']."""

from fastapi.testclient import TestClient

from app.main import app
from app.services.review_store import review_store

client = TestClient(app)


def setup_function() -> None:
    review_store.clear()


def _run_stream(thread_id: str, diff_text: str) -> None:
    with client.stream(
        "POST",
        "/api/agent/stream",
        json={
            "thread_id": thread_id,
            "diff_text": diff_text,
            "test_code": "",
        },
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    assert "interrupt" in body
    assert "awaiting_approval" in body


def test_approve_without_review_returns_404():
    response = client.post(
        "/api/agent/approve",
        json={
            "thread_id": "missing",
            "owner": "vinayrawat058",
            "repo": "autonomous-code-review",
            "file_path": "app.py",
        },
    )
    assert response.status_code == 404


def test_approve_resumes_interrupt_and_dry_runs_pr(monkeypatch):
    monkeypatch.setattr("app.services.github_pr.settings.github_token", "")
    _run_stream(
        "t-1",
        'diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-return user\n+return "SELECT ?", (user,)\n',
    )
    response = client.post(
        "/api/agent/approve",
        json={
            "thread_id": "t-1",
            "owner": "vinayrawat058",
            "repo": "autonomous-code-review",
            "base_branch": "main",
            "file_path": "app.py",
            "title": "Test PR",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["dry_run"] is True
    assert body["branch"].startswith("agent-review/")
    assert "github.com/vinayrawat058/autonomous-code-review" in body["pr_url"]
    assert "app.py" in body["files_written"]


def test_approve_dry_run_writes_multiple_files(monkeypatch):
    monkeypatch.setattr("app.services.github_pr.settings.github_token", "")
    multi = """\
diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,2 +1,2 @@
 def login(user):
-    return user
+    return query
diff --git a/db.py b/db.py
--- a/db.py
+++ b/db.py
@@ -1,1 +1,2 @@
 def run_query(sql, params=None):
+    return {"sql": sql, "params": params}
"""
    _run_stream("t-multi", multi)
    response = client.post(
        "/api/agent/approve",
        json={
            "thread_id": "t-multi",
            "owner": "vinayrawat058",
            "repo": "autonomous-code-review",
            "base_branch": "main",
            "title": "Multi file PR",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["dry_run"] is True
    assert set(body["files_written"]) == {"app.py", "db.py"}
