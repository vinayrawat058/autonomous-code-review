"""
HTTP request/response shapes.

These are what the React frontend will send/receive — separate from
the LangGraph internal GraphState (see app/agent/state.py).
"""

from pydantic import BaseModel, Field


class PRPayload(BaseModel):
    """Body for POST /api/agent/stream."""

    thread_id: str = Field(..., description="Unique id for this review run (for resume/checkpoints).")
    diff_text: str = Field(..., description="Unified git diff or pasted code change.")
    repo_path: str | None = Field(
        default=None,
        description="Optional local path to the full repo (for Codebase RAG).",
    )
    test_code: str | None = Field(
        default=None,
        description="Optional pytest source run against the rewrite in the sandbox.",
    )


class AgentEvent(BaseModel):
    """Shape of one SSE event pushed to the UI (node updates, tokens, etc.)."""

    event: str
    data: dict
