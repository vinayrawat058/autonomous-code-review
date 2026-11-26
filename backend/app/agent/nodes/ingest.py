"""
Node: IngestDiff

Validate and normalize the incoming PR diff / pasted change into GraphState.
Rejects empty, binary, or oversized input; wraps plain pastes as synthetic diffs.
"""

from app.agent.diff_ingest import IngestError, ingest_and_normalize
from app.agent.state import GraphState


def ingest_diff(state: GraphState) -> dict:
    """Normalize the diff and seed loop fields for the rest of the graph."""
    try:
        result = ingest_and_normalize(state.get("diff") or "")
    except IngestError:
        # Let FastAPI SSE surface this as an error event.
        raise

    return {
        "diff": result.diff,
        "diff_kind": result.diff_kind,
        "changed_files": result.changed_files,
        "ingest_warnings": result.warnings,
        "iteration": state.get("iteration") or 0,
        "findings": [],
        "test_errors": [],
    }
