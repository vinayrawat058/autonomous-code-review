"""
Agent HTTP routes.

POST /api/agent/stream  — SSE stream of LangGraph node updates
POST /api/agent/approve — human gate: create a GitHub PR from the rewrite
"""

import json
import re
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.agent.graph import workflow
from app.models.schemas import ApprovePayload, ApproveResponse, PRPayload
from app.rag.diff_parse import changed_paths
from app.services.github_pr import create_pull_request
from app.services.review_store import StoredReview, review_store

router = APIRouter()

_LONG_FIELDS = {"code_context", "policy_context", "diff", "refactored_code", "test_code"}
_PREVIEW = 400


def _preview(value: Any) -> Any:
    """Keep SSE payloads readable; long text is truncated for the wire."""
    if isinstance(value, str) and len(value) > _PREVIEW:
        return value[:_PREVIEW] + "..."
    if isinstance(value, list):
        return [_preview(item) for item in value]
    if isinstance(value, dict):
        return {key: _preview(item) for key, item in value.items()}
    return value


def _public_update(node_name: str, update: dict[str, Any]) -> dict[str, Any]:
    public: dict[str, Any] = {}
    for key, value in update.items():
        if key in _LONG_FIELDS and isinstance(value, str):
            public[key] = _preview(value)
        else:
            public[key] = value
    return {"active_node": node_name, "update": public}


def _branch_name(thread_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", thread_id).strip("-")[:40] or "review"
    return f"agent-review/{safe}"


def _default_file_path(diff_text: str, fallback: str) -> str:
    paths = changed_paths(diff_text)
    return paths[0] if paths else fallback


def _run_review(payload: PRPayload) -> Iterator[dict[str, str]]:
    """Yield SSE event dicts while the LangGraph review runs."""
    inputs: dict[str, Any] = {
        "diff": payload.diff_text,
        "iteration": 0,
        "repo_path": payload.repo_path,
        "test_code": payload.test_code or "",
    }
    config = {"configurable": {"thread_id": payload.thread_id}}
    final: dict[str, Any] = dict(inputs)

    yield {
        "event": "started",
        "data": json.dumps({"thread_id": payload.thread_id}),
    }

    try:
        for update in workflow.stream(inputs, config=config, stream_mode="updates"):
            for node_name, node_update in update.items():
                final.update(node_update)
                yield {
                    "event": "node",
                    "data": json.dumps(_public_update(node_name, node_update)),
                }
    except Exception as exc:  # noqa: BLE001 — surface the failure as an SSE event
        yield {
            "event": "error",
            "data": json.dumps({"message": str(exc)}),
        }
        return

    review_store.save(
        StoredReview(
            thread_id=payload.thread_id,
            diff_text=payload.diff_text,
            refactored_code=str(final.get("refactored_code") or ""),
            findings=list(final.get("findings") or []),
            test_errors=list(final.get("test_errors") or []),
            iteration=int(final.get("iteration") or 0),
            repo_path=payload.repo_path,
        )
    )

    yield {
        "event": "done",
        "data": json.dumps(
            {
                "thread_id": payload.thread_id,
                "findings": final.get("findings") or [],
                "refactored_code": final.get("refactored_code") or "",
                "test_errors": final.get("test_errors") or [],
                "iteration": final.get("iteration") or 0,
                "suggested_file_path": _default_file_path(payload.diff_text, "app.py"),
            }
        ),
    }


@router.post("/stream")
async def stream_agent(payload: PRPayload):
    """Run the review graph and push each node update over Server-Sent Events."""
    return EventSourceResponse(_run_review(payload))


@router.post("/approve", response_model=ApproveResponse)
async def approve_agent(payload: ApprovePayload):
    """After human approval, open a GitHub PR with the rewritten code."""
    stored = review_store.get(payload.thread_id)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="No finished review for this thread_id. Run /stream first.",
        )
    if not (stored.refactored_code or "").strip():
        raise HTTPException(status_code=400, detail="Review has no rewritten code to commit.")

    file_path = payload.file_path or _default_file_path(stored.diff_text, "app.py")
    title = payload.title or "Agentic PR Review Studio: security fix"
    findings_block = "\n".join(f"- {item}" for item in stored.findings) or "- (none)"
    body = payload.body or (
        "## Summary\n"
        "Approved rewrite from Agentic PR Review Studio.\n\n"
        f"## Findings\n{findings_block}\n\n"
        f"Iterations: {stored.iteration}\n"
    )
    branch = _branch_name(payload.thread_id)

    try:
        result = create_pull_request(
            owner=payload.owner,
            repo=payload.repo,
            base_branch=payload.base_branch,
            branch_name=branch,
            file_path=file_path,
            file_content=stored.refactored_code,
            title=title,
            body=body,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"GitHub PR failed: {exc}") from exc

    message = (
        "Dry run — set GITHUB_TOKEN in backend/.env to open a real pull request."
        if result.dry_run
        else "Pull request created."
    )
    return ApproveResponse(
        status="ok",
        thread_id=payload.thread_id,
        pr_url=result.url,
        branch=result.branch,
        number=result.number,
        dry_run=result.dry_run,
        message=message,
    )
