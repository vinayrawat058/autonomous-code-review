"""
GraphState — the shared memory bag passed between LangGraph nodes.

Every node reads from / writes fields on this state.
"""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class GraphState(TypedDict, total=False):
    """Fields accumulate as the agent walks the graph."""

    # Input / identity
    diff: str
    repo_path: str | None
    test_code: str
    thread_id: str

    # RAG context
    code_context: str
    policy_context: str

    # Working artifacts
    findings: list[str]
    refactored_code: str
    test_errors: list[str]

    # Loop control (PDF: max 3)
    iteration: int

    # Human gate + PR (filled on approve, consumed by create_pr)
    approved: bool
    pr_owner: str
    pr_repo: str
    pr_base_branch: str
    pr_file_path: str
    pr_title: str
    pr_body: str
    pr_url: str
    pr_branch: str
    pr_number: int | None
    pr_dry_run: bool
    pr_error: str
    files_written: list[str]

    # Optional chat-style messages if we stream LLM reasoning
    messages: Annotated[list, add_messages]
