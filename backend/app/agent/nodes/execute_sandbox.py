"""
Node: ExecuteSandboxTests

Runs tests against refactored code (v1: local pytest in a temp dir).
On failure, sets test_errors so the graph can loop back to RefactorCode.
"""

from app.agent.state import GraphState


def execute_sandbox_tests(state: GraphState) -> dict:
    """Placeholder — Phase 1 stub always 'passes' (empty errors)."""
    _ = state
    return {"test_errors": []}
