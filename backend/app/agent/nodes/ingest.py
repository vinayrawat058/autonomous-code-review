"""
Node: IngestDiff

Normalize the incoming PR diff / pasted change into GraphState.
Later: parse unified diffs, extract changed file paths, validate size.
"""

from app.agent.state import GraphState


def ingest_diff(state: GraphState) -> dict:
    """Placeholder — Phase 1 will parse and validate the diff."""
    diff = (state.get("diff") or "").strip()
    return {
        "diff": diff,
        "iteration": state.get("iteration") or 0,
        "findings": [],
        "test_errors": [],
    }
