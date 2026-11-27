"""
GitHub webhook helpers: signature verification and pull_request event parsing.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any


class WebhookVerificationError(ValueError):
    """Invalid or missing X-Hub-Signature-256."""


@dataclass
class PullRequestEvent:
    action: str
    owner: str
    repo: str
    number: int
    title: str
    head_sha: str
    base_ref: str
    html_url: str
    installation_id: int | None
    draft: bool = False


def verify_signature(*, body: bytes, signature_header: str | None, secret: str) -> None:
    """
    Validate X-Hub-Signature-256 (sha256=<hex>).

    If secret is empty, verification is skipped only when explicitly allowed by caller.
    """
    if not secret:
        raise WebhookVerificationError("GITHUB_WEBHOOK_SECRET is not configured.")
    if not signature_header or not signature_header.startswith("sha256="):
        raise WebhookVerificationError("Missing or malformed X-Hub-Signature-256 header.")

    expected = signature_header.removeprefix("sha256=").strip()
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(digest, expected):
        raise WebhookVerificationError("Webhook signature mismatch.")


def should_review_pull_request(action: str, draft: bool, review_drafts: bool) -> bool:
    if action not in {"opened", "synchronize", "reopened", "ready_for_review"}:
        return False
    if draft and not review_drafts:
        return False
    return True


def parse_pull_request_event(payload: dict[str, Any]) -> PullRequestEvent:
    pr = payload.get("pull_request") or {}
    repo = payload.get("repository") or {}
    owner_obj = repo.get("owner") or {}
    installation = payload.get("installation") or {}

    owner = str(owner_obj.get("login") or "")
    name = str(repo.get("name") or "")
    number = int(pr.get("number") or 0)
    if not owner or not name or number <= 0:
        raise ValueError("pull_request payload missing owner/repo/number.")

    installation_id = installation.get("id")
    return PullRequestEvent(
        action=str(payload.get("action") or ""),
        owner=owner,
        repo=name,
        number=number,
        title=str(pr.get("title") or ""),
        head_sha=str((pr.get("head") or {}).get("sha") or ""),
        base_ref=str((pr.get("base") or {}).get("ref") or "main"),
        html_url=str(pr.get("html_url") or ""),
        installation_id=int(installation_id) if installation_id is not None else None,
        draft=bool(pr.get("draft")),
    )
