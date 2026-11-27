"""
Node: ExecuteSandboxTests

Runs pytest against the rewritten code in Docker (preferred) or a local temp folder.
Failures are written to test_errors so the graph can loop back to RefactorCode.
"""

from app.agent.state import GraphState
from app.services.sandbox_runner import run_sandbox_tests


def execute_sandbox_tests(state: GraphState) -> dict:
    """Run state['test_code'] against the rewrite. No tests means nothing failed."""
    code = (state.get("refactored_code") or "").strip()
    tests = (state.get("test_code") or "").strip()
    if not tests:
        return {"test_errors": []}
    if not code:
        return {"test_errors": ["No rewritten code to test."]}

    return {"test_errors": run_sandbox_tests(code=code, tests=tests)}
