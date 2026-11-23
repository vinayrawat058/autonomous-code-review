"""Approve stores a finished review and can dry-run a GitHub PR without a token."""

from fastapi.testclient import TestClient

from app.main import app
from app.services.review_store import StoredReview, review_store

client = TestClient(app)


def setup_function() -> None:
    review_store.clear()


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


def test_approve_dry_run_returns_compare_url(monkeypatch):
    monkeypatch.setattr("app.services.github_pr.settings.github_token", "")
    review_store.save(
        StoredReview(
            thread_id="t-1",
            diff_text="diff --git a/app.py b/app.py\n",
            refactored_code='def login(user):\n    return "SELECT ?", (user,)\n',
            findings=["A03 | injection"],
            iteration=1,
        )
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
    assert body["files_written"] == ["app.py"]


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
    review_store.save(
        StoredReview(
            thread_id="t-multi",
            diff_text=multi,
            refactored_code="def login(user):\n    return run_query('SELECT 1', ())\n",
            findings=["A03 | injection"],
            iteration=1,
        )
    )
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
