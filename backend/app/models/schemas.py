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


class ApprovePayload(BaseModel):
    """Body for POST /api/agent/approve — human gate before opening a PR."""

    thread_id: str = Field(..., description="Same id used when the review was streamed.")
    owner: str = Field(..., description="GitHub repo owner, e.g. vinayrawat058.")
    repo: str = Field(..., description="GitHub repo name, e.g. autonomous-code-review.")
    base_branch: str = Field(default="main", description="Branch to open the PR against.")
    file_path: str = Field(
        default="app.py",
        description="Path in the repo to write the rewritten code to.",
    )
    title: str | None = Field(
        default=None,
        description="Optional PR title. Defaults to an agent-generated title.",
    )
    body: str | None = Field(
        default=None,
        description="Optional PR body. Defaults to findings from the review.",
    )


class ApproveResponse(BaseModel):
    status: str
    thread_id: str
    pr_url: str
    branch: str
    number: int | None = None
    dry_run: bool = False
    message: str = ""
