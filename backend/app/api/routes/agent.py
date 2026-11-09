"""
Agent HTTP routes.

POST /api/agent/stream — SSE stream of LangGraph node updates
POST /api/agent/approve — Phase 4: resume after human approval (not built yet)
"""

import json
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.agent.graph import workflow
from app.models.schemas import PRPayload

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

    yield {
        "event": "done",
        "data": json.dumps(
            {
                "thread_id": payload.thread_id,
                "findings": final.get("findings") or [],
                "refactored_code": final.get("refactored_code") or "",
                "test_errors": final.get("test_errors") or [],
                "iteration": final.get("iteration") or 0,
            }
        ),
    }


@router.post("/stream")
async def stream_agent(payload: PRPayload):
    """Run the review graph and push each node update over Server-Sent Events."""
    return EventSourceResponse(_run_review(payload))


@router.post("/approve")
async def approve_agent(thread_id: str):
    """Placeholder — Phase 4 resumes the graph after human approval."""
    return {
        "status": "not_implemented",
        "thread_id": thread_id,
    }
