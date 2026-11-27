"""
Orchestrate: webhook PR event → fetch diff → run agent → comment on the PR.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings
from app.services.github_app_auth import GitHubAppAuthError, get_installation_token
from app.services.github_pr_content import (
    GitHubContentError,
    fetch_pull_request_diff,
    format_review_comment,
    post_pull_request_comment,
    post_pull_request_review,
)
from app.services.github_webhook import PullRequestEvent
from app.services.review_runner import ReviewRunResult, run_review_until_interrupt


@dataclass
class WebhookReviewResult:
    thread_id: str
    status: str
    message: str
    comment_url: str = ""
    findings_count: int = 0


def thread_id_for_pr(event: PullRequestEvent) -> str:
    sha = (event.head_sha or "head")[:12]
    return f"gh-{event.owner}-{event.repo}-{event.number}-{sha}"


def review_pull_request_event(event: PullRequestEvent) -> WebhookReviewResult:
    """Fetch the PR diff, run the agent until interrupt, post findings to GitHub."""
    installation_id = event.installation_id or settings.github_app_installation_id
    if not installation_id and not (settings.github_token or "").strip():
        return WebhookReviewResult(
            thread_id="",
            status="error",
            message="No installation id on the webhook and GITHUB_TOKEN is empty.",
        )

    try:
        token = get_installation_token(installation_id if installation_id else 0)
        diff = fetch_pull_request_diff(
            owner=event.owner,
            repo=event.repo,
            number=event.number,
            token=token,
        )
    except (GitHubAppAuthError, GitHubContentError) as exc:
        return WebhookReviewResult(
            thread_id="",
            status="error",
            message=str(exc),
        )

    thread_id = thread_id_for_pr(event)
    result: ReviewRunResult = run_review_until_interrupt(
        thread_id=thread_id,
        diff_text=diff,
        repo_path=None,
        test_code="",
    )
    if result.error:
        return WebhookReviewResult(
            thread_id=thread_id,
            status="error",
            message=result.error,
        )

    body = format_review_comment(
        findings=result.findings,
        test_errors=result.test_errors,
        iteration=result.iteration,
        thread_id=thread_id,
        refactored_preview=result.refactored_code,
    )

    comment_url = ""
    try:
        if settings.github_webhook_post_review:
            comment_url = post_pull_request_review(
                owner=event.owner,
                repo=event.repo,
                number=event.number,
                token=token,
                body=body,
                event="COMMENT",
            )
        else:
            comment_url = post_pull_request_comment(
                owner=event.owner,
                repo=event.repo,
                number=event.number,
                token=token,
                body=body,
            )
    except GitHubContentError as exc:
        return WebhookReviewResult(
            thread_id=thread_id,
            status="reviewed_but_comment_failed",
            message=str(exc),
            findings_count=len(result.findings),
        )

    return WebhookReviewResult(
        thread_id=thread_id,
        status="ok",
        message="Review completed and posted to the pull request.",
        comment_url=comment_url,
        findings_count=len(result.findings),
    )
