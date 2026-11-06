"""
Node: ExecuteSandboxTests

Runs pytest against the rewritten code in a temporary folder.
Failures are written to test_errors so the graph can loop back to RefactorCode.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

from app.agent.state import GraphState


def execute_sandbox_tests(state: GraphState) -> dict:
    """Run state['test_code'] against the rewrite. No tests means nothing failed."""
    code = (state.get("refactored_code") or "").strip()
    tests = (state.get("test_code") or "").strip()
    if not tests:
        return {"test_errors": []}
    if not code:
        return {"test_errors": ["No rewritten code to test."]}

    with tempfile.TemporaryDirectory(prefix="review-sandbox-") as folder:
        root = Path(folder)
        (root / "solution.py").write_text(code + "\n", encoding="utf-8")
        (root / "test_solution.py").write_text(tests + "\n", encoding="utf-8")
        try:
            completed = subprocess.run(
                [sys.executable, "-m", "pytest", "test_solution.py", "-q", "--tb=line"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            return {"test_errors": ["Tests timed out after 30 seconds."]}

    if completed.returncode == 0:
        return {"test_errors": []}

    output = f"{completed.stdout}\n{completed.stderr}".strip()
    lines = [line for line in output.splitlines() if line.strip()]
    return {"test_errors": lines[-20:] or ["Tests failed with no output."]}
