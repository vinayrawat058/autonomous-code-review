"""
GitHub App webhook endpoint.

POST /api/github/webhook
  - Verifies X-Hub-Signature-256
  - Handles ping + pull_request (opened / synchronize / reopened / ready_for_review)
  - Fetches the PR diff, runs the agent, posts findings back on the PR
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.services.github_pr_review import review_pull_request_event
from app.services.github_webhook import (
    WebhookVerificationError,
    parse_pull_request_event,
    should_review_pull_request,
    verify_signature,
)

router = APIRouter()


def _process_pull_request(payload: dict[str, Any]) -> dict[str, Any]:
    event = parse_pull_request_event(payload)
    if not should_review_pull_request(
        event.action,
        event.draft,
        settings.github_webhook_review_drafts,
    ):
        return {
            "status": "ignored",
            "reason": f"action={event.action!r} draft={event.draft}",
        }

    result = review_pull_request_event(event)
    return {
        "status": result.status,
        "thread_id": result.thread_id,
        "message": result.message,
        "comment_url": result.comment_url,
        "findings_count": result.findings_count,
        "pull_request": event.html_url,
    }


@router.post("/webhook")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str | None = Header(default=None, alias="X-GitHub-Event"),
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
    x_github_delivery: str | None = Header(default=None, alias="X-GitHub-Delivery"),
):
    """Receive GitHub App / webhook deliveries for pull request reviews."""
    body = await request.body()
    secret = (settings.github_webhook_secret or "").strip()

    if settings.github_webhook_require_secret or secret:
        try:
            verify_signature(body=body, signature_header=x_hub_signature_256, secret=secret)
        except WebhookVerificationError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
    elif settings.app_env != "development":
        raise HTTPException(
            status_code=500,
            detail="GITHUB_WEBHOOK_SECRET must be set outside development.",
        )

    try:
        payload: dict[str, Any] = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body.") from exc

    event_name = (x_github_event or "").strip()
    if event_name == "ping":
        return {
            "status": "ok",
            "message": "pong",
            "zen": payload.get("zen"),
            "delivery": x_github_delivery,
        }

    if event_name != "pull_request":
        return JSONResponse(
            status_code=202,
            content={
                "status": "ignored",
                "reason": f"unsupported event {event_name!r}",
                "delivery": x_github_delivery,
            },
        )

    if settings.github_webhook_async:
        background_tasks.add_task(_process_pull_request, payload)
        return JSONResponse(
            status_code=202,
            content={
                "status": "accepted",
                "message": "Pull request review queued.",
                "delivery": x_github_delivery,
            },
        )

    result = _process_pull_request(payload)
    status_code = 200 if result.get("status") in {"ok", "ignored"} else 502
    result["delivery"] = x_github_delivery
    return JSONResponse(status_code=status_code, content=result)
