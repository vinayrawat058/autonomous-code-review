"""GitHub webhook signature verification and pull_request handling."""

import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from app.main import app
from app.services.github_webhook import (
    WebhookVerificationError,
    parse_pull_request_event,
    should_review_pull_request,
    verify_signature,
)
from app.services.review_store import review_store

client = TestClient(app)


def setup_function() -> None:
    review_store.clear()


def _sign(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_verify_signature_accepts_valid_hmac():
    body = b'{"zen":"test"}'
    secret = "whsec_test"
    verify_signature(body=body, signature_header=_sign(body, secret), secret=secret)


def test_verify_signature_rejects_bad_hmac():
    body = b'{"zen":"test"}'
    try:
        verify_signature(body=body, signature_header="sha256=deadbeef", secret="whsec_test")
        assert False, "expected WebhookVerificationError"
    except WebhookVerificationError:
        pass


def test_should_review_actions():
    assert should_review_pull_request("opened", draft=False, review_drafts=False)
    assert should_review_pull_request("synchronize", draft=False, review_drafts=False)
    assert not should_review_pull_request("closed", draft=False, review_drafts=False)
    assert not should_review_pull_request("opened", draft=True, review_drafts=False)
    assert should_review_pull_request("opened", draft=True, review_drafts=True)


def test_parse_pull_request_event():
    payload = {
        "action": "opened",
        "installation": {"id": 42},
        "repository": {"name": "autonomous-code-review", "owner": {"login": "vinayrawat058"}},
        "pull_request": {
            "number": 7,
            "title": "Fix SQL",
            "draft": False,
            "html_url": "https://github.com/vinayrawat058/autonomous-code-review/pull/7",
            "head": {"sha": "abc123deadbeef"},
            "base": {"ref": "main"},
        },
    }
    event = parse_pull_request_event(payload)
    assert event.owner == "vinayrawat058"
    assert event.repo == "autonomous-code-review"
    assert event.number == 7
    assert event.installation_id == 42
    assert event.head_sha.startswith("abc123")


def test_webhook_ping(monkeypatch):
    monkeypatch.setattr("app.api.routes.github_webhook.settings.github_webhook_secret", "s3cret")
    monkeypatch.setattr("app.api.routes.github_webhook.settings.github_webhook_require_secret", True)
    body = json.dumps({"zen": "design for failure"}).encode("utf-8")
    response = client.post(
        "/api/github/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "ping",
            "X-Hub-Signature-256": _sign(body, "s3cret"),
            "X-GitHub-Delivery": "delivery-1",
        },
    )
    assert response.status_code == 200
    assert response.json()["message"] == "pong"


def test_webhook_rejects_bad_signature(monkeypatch):
    monkeypatch.setattr("app.api.routes.github_webhook.settings.github_webhook_secret", "s3cret")
    body = b'{"action":"opened"}'
    response = client.post(
        "/api/github/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=00",
        },
    )
    assert response.status_code == 401


def test_webhook_pull_request_queues_async_review(monkeypatch):
    monkeypatch.setattr("app.api.routes.github_webhook.settings.github_webhook_secret", "s3cret")
    monkeypatch.setattr("app.api.routes.github_webhook.settings.github_webhook_async", True)

    called: dict = {}

    def fake_process(payload: dict) -> dict:
        called["payload"] = payload
        return {"status": "ok"}

    monkeypatch.setattr("app.api.routes.github_webhook._process_pull_request", fake_process)

    payload = {
        "action": "opened",
        "installation": {"id": 1},
        "repository": {"name": "autonomous-code-review", "owner": {"login": "vinayrawat058"}},
        "pull_request": {
            "number": 1,
            "title": "t",
            "draft": False,
            "html_url": "https://example.com/pr/1",
            "head": {"sha": "sha1"},
            "base": {"ref": "main"},
        },
    }
    body = json.dumps(payload).encode("utf-8")
    response = client.post(
        "/api/github/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": _sign(body, "s3cret"),
        },
    )
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"


def test_webhook_pull_request_sync_posts_review(monkeypatch):
    monkeypatch.setattr("app.api.routes.github_webhook.settings.github_webhook_secret", "s3cret")
    monkeypatch.setattr("app.api.routes.github_webhook.settings.github_webhook_async", False)
    monkeypatch.setattr("app.services.github_app_auth.settings.github_token", "tok")
    monkeypatch.setattr("app.services.github_app_auth.settings.github_app_id", "")
    monkeypatch.setattr("app.services.github_app_auth.settings.github_app_private_key", "")
    monkeypatch.setattr("app.services.github_app_auth.settings.github_app_private_key_path", "")
    monkeypatch.setattr(
        "app.services.github_pr_review.fetch_pull_request_diff",
        lambda **kwargs: (
            "diff --git a/app.py b/app.py\n"
            "--- a/app.py\n+++ b/app.py\n"
            "@@ -1 +1 @@\n-return user\n+return '?'\n"
        ),
    )
    monkeypatch.setattr(
        "app.services.github_pr_review.run_review_until_interrupt",
        lambda **kwargs: __import__(
            "app.services.review_runner", fromlist=["ReviewRunResult"]
        ).ReviewRunResult(
            thread_id=kwargs["thread_id"],
            findings=["A03 | injection"],
            refactored_code="def login(user):\n    return '?', (user,)\n",
            iteration=1,
            awaiting_approval=True,
        ),
    )
    monkeypatch.setattr(
        "app.services.github_pr_review.post_pull_request_review",
        lambda **kwargs: "https://github.com/example/comment/1",
    )

    payload = {
        "action": "opened",
        "installation": {"id": 99},
        "repository": {"name": "autonomous-code-review", "owner": {"login": "vinayrawat058"}},
        "pull_request": {
            "number": 9,
            "title": "fix",
            "draft": False,
            "html_url": "https://github.com/vinayrawat058/autonomous-code-review/pull/9",
            "head": {"sha": "abcdef123456"},
            "base": {"ref": "main"},
        },
    }
    body = json.dumps(payload).encode("utf-8")
    response = client.post(
        "/api/github/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": _sign(body, "s3cret"),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["thread_id"].startswith("gh-vinayrawat058-autonomous-code-review-9-")
    assert data["comment_url"]
