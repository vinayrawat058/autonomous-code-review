"""
Agent HTTP routes.

POST /api/agent/stream  — SSE: run graph until interrupt_before create_pr
POST /api/agent/approve — resume the paused graph so create_pr runs
"""

import json
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.agent.graph import workflow
from app.models.schemas import ApprovePayload, ApproveResponse, PRPayload
from app.rag.diff_parse import changed_paths
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


def _default_file_path(diff_text: str, fallback: str) -> str:
    paths = changed_paths(diff_text)
    return paths[0] if paths else fallback


def _sse_from_custom(chunk: Any) -> dict[str, str] | None:
    """Map LangGraph custom writer payloads to SSE event dicts."""
    if not isinstance(chunk, dict):
        return None
    kind = str(chunk.get("type") or "")
    if kind == "token":
        return {
            "event": "token",
            "data": json.dumps(
                {
                    "node": chunk.get("node") or "llm",
                    "token": chunk.get("token") or "",
                }
            ),
        }
    if kind == "llm_start":
        return {
            "event": "llm_start",
            "data": json.dumps({"node": chunk.get("node") or "llm"}),
        }
    if kind == "llm_end":
        return {
            "event": "llm_end",
            "data": json.dumps(
                {
                    "node": chunk.get("node") or "llm",
                    "text": chunk.get("text") or "",
                }
            ),
        }
    return {
        "event": "custom",
        "data": json.dumps(chunk),
    }


def _consume_stream(
    inputs: dict[str, Any] | None,
    config: dict[str, Any],
    final: dict[str, Any],
) -> Iterator[dict[str, str]]:
    """Yield SSE chunks from one graph.stream call (start or resume)."""
    for mode, chunk in workflow.stream(
        inputs,
        config=config,
        stream_mode=["updates", "custom"],
    ):
        if mode == "custom":
            event = _sse_from_custom(chunk)
            if event is not None:
                yield event
            continue

        if mode != "updates" or not isinstance(chunk, dict):
            continue

        for node_name, node_update in chunk.items():
            if isinstance(node_update, dict):
                final.update(node_update)
                yield {
                    "event": "node",
                    "data": json.dumps(_public_update(node_name, node_update)),
                }


def _awaiting_create_pr(config: dict[str, Any]) -> bool:
    snapshot = workflow.get_state(config)
    next_nodes = tuple(snapshot.next or ())
    return "create_pr" in next_nodes


def _run_review(payload: PRPayload) -> Iterator[dict[str, str]]:
    """Yield SSE events until the graph pauses before create_pr."""
    inputs: dict[str, Any] = {
        "diff": payload.diff_text,
        "iteration": 0,
        "repo_path": payload.repo_path,
        "test_code": payload.test_code or "",
        "thread_id": payload.thread_id,
        "approved": False,
    }
    config = {"configurable": {"thread_id": payload.thread_id}}
    final: dict[str, Any] = dict(inputs)

    yield {
        "event": "started",
        "data": json.dumps({"thread_id": payload.thread_id}),
    }

    try:
        yield from _consume_stream(inputs, config, final)
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

    paused = _awaiting_create_pr(config)
    done_payload = {
        "thread_id": payload.thread_id,
        "findings": final.get("findings") or [],
        "refactored_code": final.get("refactored_code") or "",
        "test_errors": final.get("test_errors") or [],
        "iteration": final.get("iteration") or 0,
        "suggested_file_path": _default_file_path(payload.diff_text, "app.py"),
        "suggested_file_paths": changed_paths(payload.diff_text)
        or [_default_file_path(payload.diff_text, "app.py")],
        "awaiting_approval": paused,
        "next_node": "create_pr" if paused else None,
    }

    if paused:
        yield {
            "event": "interrupt",
            "data": json.dumps(
                {
                    "thread_id": payload.thread_id,
                    "next_node": "create_pr",
                    "message": "Paused before create_pr — approve to resume the graph.",
                }
            ),
        }

    yield {
        "event": "done",
        "data": json.dumps(done_payload),
    }


@router.post("/stream")
async def stream_agent(payload: PRPayload):
    """Run the review graph until interrupt_before=['create_pr']."""
    return EventSourceResponse(_run_review(payload))


@router.post("/approve", response_model=ApproveResponse)
async def approve_agent(payload: ApprovePayload):
    """Resume the paused graph so the create_pr node can open the GitHub PR."""
    config = {"configurable": {"thread_id": payload.thread_id}}

    if not _awaiting_create_pr(config):
        # Fallback: older path / tests that only seeded review_store.
        stored = review_store.get(payload.thread_id)
        if stored is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    "No paused review for this thread_id. "
                    "Run /stream first and approve while the graph is interrupted."
                ),
            )
        raise HTTPException(
            status_code=409,
            detail=(
                "Graph is not paused before create_pr. "
                "Re-run /stream so LangGraph can interrupt_before the PR node."
            ),
        )

    snapshot = workflow.get_state(config)
    values = dict(snapshot.values or {})
    if not (values.get("refactored_code") or "").strip() and not (values.get("diff") or "").strip():
        raise HTTPException(status_code=400, detail="Review has no rewritten code to commit.")

    workflow.update_state(
        config,
        {
            "approved": True,
            "pr_owner": payload.owner,
            "pr_repo": payload.repo,
            "pr_base_branch": payload.base_branch,
            "pr_file_path": payload.file_path or "",
            "pr_title": payload.title or "",
            "pr_body": payload.body or "",
            "thread_id": payload.thread_id,
        },
    )

    final: dict[str, Any] = {}
    try:
        # Resume from the interrupt — create_pr runs now.
        for _ in _consume_stream(None, config, final):
            pass
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"GitHub PR failed: {exc}") from exc

    # Prefer values written by the create_pr node; fall back to latest checkpoint.
    state_after = workflow.get_state(config).values or {}
    pr_error = final.get("pr_error") or state_after.get("pr_error") or ""
    if pr_error:
        raise HTTPException(status_code=502, detail=str(pr_error))

    pr_url = str(final.get("pr_url") or state_after.get("pr_url") or "")
    branch = str(final.get("pr_branch") or state_after.get("pr_branch") or "")
    number = final.get("pr_number")
    if number is None:
        number = state_after.get("pr_number")
    dry_run = bool(final.get("pr_dry_run", state_after.get("pr_dry_run", False)))
    written = list(final.get("files_written") or state_after.get("files_written") or [])

    message = (
        "Dry run — set GITHUB_TOKEN in backend/.env to open a real pull request."
        if dry_run
        else f"Pull request created with {len(written)} file(s)."
    )
    return ApproveResponse(
        status="ok",
        thread_id=payload.thread_id,
        pr_url=pr_url,
        branch=branch,
        number=number,
        dry_run=dry_run,
        message=message,
        files_written=written,
    )
