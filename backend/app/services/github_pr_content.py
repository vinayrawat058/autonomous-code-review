"""
Fetch a pull request unified diff and post review comments via GitHub API.
"""

from __future__ import annotations

import httpx

from app.services.github_app_auth import api_headers

API = "https://api.github.com"


class GitHubContentError(RuntimeError):
    """Raised when PR diff fetch or comment posting fails."""


def fetch_pull_request_diff(*, owner: str, repo: str, number: int, token: str) -> str:
    """Return the unified diff for a pull request."""
    url = f"{API}/repos/{owner}/{repo}/pulls/{number}"
    with httpx.Client(timeout=60.0) as client:
        response = client.get(
            url,
            headers={
                **api_headers(token),
                "Accept": "application/vnd.github.v3.diff",
            },
        )
        if response.status_code >= 400:
            raise GitHubContentError(
                f"Failed to fetch PR diff ({response.status_code}): {response.text[:500]}"
            )
        text = response.text or ""
        if not text.strip():
            raise GitHubContentError("Pull request diff is empty.")
        return text


def post_pull_request_comment(
    *,
    owner: str,
    repo: str,
    number: int,
    token: str,
    body: str,
) -> str:
    """Post an issue comment on the PR; returns the comment html_url."""
    url = f"{API}/repos/{owner}/{repo}/issues/{number}/comments"
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            url,
            headers=api_headers(token),
            json={"body": body},
        )
        if response.status_code >= 400:
            raise GitHubContentError(
                f"Failed to post PR comment ({response.status_code}): {response.text[:500]}"
            )
        return str(response.json().get("html_url") or "")


def post_pull_request_review(
    *,
    owner: str,
    repo: str,
    number: int,
    token: str,
    body: str,
    event: str = "COMMENT",
) -> str:
    """Create a PR review (COMMENT / REQUEST_CHANGES / APPROVE). Returns html_url."""
    url = f"{API}/repos/{owner}/{repo}/pulls/{number}/reviews"
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            url,
            headers=api_headers(token),
            json={"body": body, "event": event},
        )
        if response.status_code >= 400:
            raise GitHubContentError(
                f"Failed to post PR review ({response.status_code}): {response.text[:500]}"
            )
        return str(response.json().get("html_url") or "")


def format_review_comment(
    *,
    findings: list[str],
    test_errors: list[str],
    iteration: int,
    thread_id: str,
    refactored_preview: str = "",
) -> str:
    """Markdown body posted back onto the GitHub pull request."""
    finding_lines = "\n".join(f"- {item}" for item in findings) or "- (none)"
    error_lines = "\n".join(f"- `{item}`" for item in test_errors[:10]) or "- (none)"
    preview = (refactored_preview or "").strip()
    if len(preview) > 1200:
        preview = preview[:1200] + "\n…"

    parts = [
        "## Agentic PR Review Studio",
        "",
        f"Automated security review finished (iteration **{iteration}**).",
        "",
        "### Findings",
        finding_lines,
        "",
        "### Sandbox",
        error_lines,
        "",
        f"**thread_id:** `{thread_id}`",
        "",
        "Approve or reject the rewrite in the Studio UI (graph is paused before `create_pr`).",
    ]
    if preview:
        parts.extend(["", "### Rewrite preview", "```python", preview, "```"])
    return "\n".join(parts)
