"""
Create a GitHub branch + commit + pull request for an approved rewrite.

Supports one or many files in a single commit (Git Data API).
Requires GITHUB_TOKEN with repo scope for a real PR.
"""

from __future__ import annotations

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
    files: list[str] | None = None


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
    files: dict[str, str] | None = None,
    file_path: str | None = None,
    file_content: str | None = None,
    title: str,
    body: str,
) -> PullRequestResult:
    """
    Open a PR that writes one or more files on a new branch.

    Prefer `files={path: content, ...}`. The older file_path/file_content
    pair still works for a single-file PR.
    """
    file_map = dict(files or {})
    if not file_map and file_path and file_content is not None:
        file_map = {file_path: file_content}
    if not file_map:
        raise ValueError("No files to commit into the pull request.")

    paths = sorted(file_map.keys())

    if not settings.github_token:
        return PullRequestResult(
            url=f"https://github.com/{owner}/{repo}/compare/{base_branch}...{branch_name}?expand=1",
            branch=branch_name,
            number=None,
            dry_run=True,
            files=paths,
        )

    headers = _headers()
    with httpx.Client(timeout=60.0, headers=headers) as client:
        ref = client.get(f"{API}/repos/{owner}/{repo}/git/ref/heads/{base_branch}")
        if ref.status_code == 404:
            raise ValueError(f"Base branch '{base_branch}' not found on {owner}/{repo}.")
        ref.raise_for_status()
        base_sha = ref.json()["object"]["sha"]

        base_commit = client.get(f"{API}/repos/{owner}/{repo}/git/commits/{base_sha}")
        base_commit.raise_for_status()
        base_tree_sha = base_commit.json()["tree"]["sha"]

        create_ref = client.post(
            f"{API}/repos/{owner}/{repo}/git/refs",
            json={"ref": f"refs/heads/{branch_name}", "sha": base_sha},
        )
        if create_ref.status_code == 422:
            # Branch may already exist from a prior approve — point a new commit at it.
            pass
        else:
            create_ref.raise_for_status()

        tree_items: list[dict] = []
        for path, content in file_map.items():
            blob = client.post(
                f"{API}/repos/{owner}/{repo}/git/blobs",
                json={"content": content, "encoding": "utf-8"},
            )
            blob.raise_for_status()
            tree_items.append(
                {
                    "path": path,
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob.json()["sha"],
                }
            )

        tree = client.post(
            f"{API}/repos/{owner}/{repo}/git/trees",
            json={"base_tree": base_tree_sha, "tree": tree_items},
        )
        tree.raise_for_status()

        commit = client.post(
            f"{API}/repos/{owner}/{repo}/git/commits",
            json={
                "message": title,
                "tree": tree.json()["sha"],
                "parents": [base_sha],
            },
        )
        commit.raise_for_status()
        commit_sha = commit.json()["sha"]

        update_ref = client.patch(
            f"{API}/repos/{owner}/{repo}/git/refs/heads/{branch_name}",
            json={"sha": commit_sha, "force": True},
        )
        update_ref.raise_for_status()

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
            return PullRequestResult(
                url=f"https://github.com/{owner}/{repo}/compare/{base_branch}...{branch_name}?expand=1",
                branch=branch_name,
                number=None,
                dry_run=False,
                files=paths,
            )
        pr.raise_for_status()
        data = pr.json()
        return PullRequestResult(
            url=data["html_url"],
            branch=branch_name,
            number=data.get("number"),
            dry_run=False,
            files=paths,
        )
