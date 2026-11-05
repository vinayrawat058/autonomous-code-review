"""
Node: RefactorCode

Produces improved code from diff + findings + code_context.
On retry loops, also considers previous test_errors.
"""

from app.agent.state import GraphState


def refactor_code(state: GraphState) -> dict:
    """Placeholder — Phase 1 will call the LLM to rewrite the change."""
    iteration = (state.get("iteration") or 0) + 1
    return {
        "refactored_code": state.get("diff") or "",
        "iteration": iteration,
    }
