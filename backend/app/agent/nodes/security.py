"""
Node: SecurityAudit

Uses LLM + Policy RAG to flag vulnerabilities with line-level citations.
Writes a list of findings into GraphState.
"""

from app.agent.state import GraphState


def security_audit(state: GraphState) -> dict:
    """Placeholder — Phase 1 will call the LLM with policy_context."""
    _ = state  # unused until implemented
    return {
        "findings": [
            "TODO: replace with real security findings from the LLM",
        ],
    }
