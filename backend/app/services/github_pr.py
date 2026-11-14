"""
Create a GitHub branch + file commit + pull request for an approved rewrite.

Uses the GitHub REST API (no local git clone). Requires GITHUB_TOKEN with repo scope.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass

import httpx

from app.core.config import settings

API = "https://api.github.com"


@dataclass
class PullRequestResult:
    url: str
    branch: str
    number: int | None
    dry_run: bool = False


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def create_pull_request(
    *,
    owner: str,
    repo: str,
    base_branch: str,
    branch_name: str,
    file_path: str,
    file_content: str,
    title: str,
    body: str,
) -> PullRequestResult:
    """Open a PR that adds/updates file_path with file_content on a new branch."""
    if not settings.github_token:
        # Local demo without a token — still returns a clear result for the UI.
        return PullRequestResult(
            url=f"https://github.com/{owner}/{repo}/compare/{base_branch}...{branch_name}?expand=1",
            branch=branch_name,
            number=None,
            dry_run=True,
        )

    headers = _headers()
    with httpx.Client(timeout=60.0, headers=headers) as client:
        ref = client.get(f"{API}/repos/{owner}/{repo}/git/ref/heads/{base_branch}")
        if ref.status_code == 404:
            raise ValueError(f"Base branch '{base_branch}' not found on {owner}/{repo}.")
        ref.raise_for_status()
        base_sha = ref.json()["object"]["sha"]

        create_ref = client.post(
            f"{API}/repos/{owner}/{repo}/git/refs",
            json={"ref": f"refs/heads/{branch_name}", "sha": base_sha},
        )
        if create_ref.status_code == 422:
            # Branch may already exist from a prior approve — reuse it.
            pass
        else:
            create_ref.raise_for_status()

        existing_sha: str | None = None
        existing = client.get(
            f"{API}/repos/{owner}/{repo}/contents/{file_path}",
            params={"ref": branch_name},
        )
        if existing.status_code == 200:
            existing_sha = existing.json().get("sha")
        elif existing.status_code != 404:
            existing.raise_for_status()

        encoded = base64.b64encode(file_content.encode("utf-8")).decode("ascii")
        put_body: dict = {
            "message": title,
            "content": encoded,
            "branch": branch_name,
        }
        if existing_sha:
            put_body["sha"] = existing_sha

        put = client.put(
            f"{API}/repos/{owner}/{repo}/contents/{file_path}",
            json=put_body,
        )
        put.raise_for_status()

        pr = client.post(
            f"{API}/repos/{owner}/{repo}/pulls",
            json={
                "title": title,
                "head": branch_name,
                "base": base_branch,
                "body": body,
            },
        )
        if pr.status_code == 422:
            # PR may already exist for this head — return the compare URL.
            return PullRequestResult(
                url=f"https://github.com/{owner}/{repo}/compare/{base_branch}...{branch_name}?expand=1",
                branch=branch_name,
                number=None,
                dry_run=False,
            )
        pr.raise_for_status()
        data = pr.json()
        return PullRequestResult(
            url=data["html_url"],
            branch=branch_name,
            number=data.get("number"),
            dry_run=False,
        )
