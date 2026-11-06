"""
GraphState — the shared memory bag passed between LangGraph nodes.

Every node reads from / writes fields on this state. Phase 1 fills this in
with TypedDict or a Pydantic model (diff, context, errors, code, etc.).
"""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class GraphState(TypedDict, total=False):
    """Fields accumulate as the agent walks the graph."""

    # Input
    diff: str
    repo_path: str | None
    test_code: str

    # RAG context
    code_context: str
    policy_context: str

    # Working artifacts
    findings: list[str]
    refactored_code: str
    test_errors: list[str]

    # Loop control (PDF: max 3)
    iteration: int

    # Optional chat-style messages if we stream LLM reasoning
    messages: Annotated[list, add_messages]
