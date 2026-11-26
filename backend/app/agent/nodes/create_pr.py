"""
Node: CreatePullRequest

Runs only after the human approves. Builds the multi-file map from the
review and opens a GitHub PR (or dry-run without a token).
"""

from __future__ import annotations

import re

from app.agent.state import GraphState
from app.rag.diff_parse import changed_paths, files_for_pull_request
from app.services.github_pr import create_pull_request


def _branch_name(thread_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", thread_id or "").strip("-")[:40] or "review"
    return f"agent-review/{safe}"


def _primary_path(state: GraphState) -> str:
    override = (state.get("pr_file_path") or "").strip()
    if override:
        return override
    paths = changed_paths(state.get("diff") or "")
    return paths[0] if paths else "app.py"


def create_pull_request_node(state: GraphState) -> dict:
    """Write approved files into a GitHub PR. Requires pr_* fields on state."""
    if not state.get("approved"):
        return {
            "pr_error": "Graph resumed without approval.",
            "pr_url": "",
            "files_written": [],
        }

    diff_text = (state.get("diff") or "").strip()
    refactored = (state.get("refactored_code") or "").strip()
    if not diff_text and not refactored:
        return {
            "pr_error": "Empty review — no diff or rewritten code to commit.",
            "pr_url": "",
            "files_written": [],
        }

    file_map = files_for_pull_request(
        diff_text,
        refactored,
        primary_path=_primary_path(state),
    )
    if not file_map:
        return {
            "pr_error": (
                "Could not build any files from the review "
                "(unparseable diff and no plain rewrite to fall back on)."
            ),
            "pr_url": "",
            "files_written": [],
        }

    owner = (state.get("pr_owner") or "").strip()
    repo = (state.get("pr_repo") or "").strip()
    if not owner or not repo:
        return {
            "pr_error": "Missing GitHub owner/repo on approval.",
            "pr_url": "",
            "files_written": [],
        }

    title = state.get("pr_title") or "Agentic PR Review Studio: security fix"
    findings = list(state.get("findings") or [])
    findings_block = "\n".join(f"- {item}" for item in findings) or "- (none)"
    files_block = "\n".join(f"- `{path}`" for path in sorted(file_map))
    body = state.get("pr_body") or (
        "## Summary\n"
        "Approved rewrite from Agentic PR Review Studio.\n\n"
        f"## Findings\n{findings_block}\n\n"
        f"## Files\n{files_block}\n\n"
        f"Iterations: {state.get('iteration') or 0}\n"
    )
    thread_id = state.get("thread_id") or "review"
    branch = _branch_name(thread_id)

    try:
        result = create_pull_request(
            owner=owner,
            repo=repo,
            base_branch=state.get("pr_base_branch") or "main",
            branch_name=branch,
            files=file_map,
            title=title,
            body=body,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "pr_error": f"GitHub PR failed: {exc}",
            "pr_url": "",
            "files_written": [],
        }

    written = result.files or sorted(file_map.keys())
    return {
        "pr_url": result.url,
        "pr_branch": result.branch,
        "pr_number": result.number,
        "pr_dry_run": result.dry_run,
        "files_written": written,
        "pr_error": "",
    }
