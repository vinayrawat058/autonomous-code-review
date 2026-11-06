"""
Node: RefactorCode

Rewrites the change so the security findings are fixed.
On a later retry, the same step also sees the test errors.
"""

from collections.abc import Callable

from app.agent.llm import complete
from app.agent.state import GraphState
from app.core.config import settings

_CLEAR = "No rule from the rulebook matched this change."


def strip_code_fences(text: str) -> str:
    """Drop a markdown code fence if the model wrapped the rewrite in one."""
    cleaned = text.strip()
    if not cleaned.startswith("```"):
        return cleaned
    lines = cleaned.splitlines()[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _ask_model(diff: str, findings: list[str], test_errors: list[str]) -> str:
    finding_text = "\n".join(findings) or "(none)"
    error_text = "\n".join(test_errors) or "(none)"
    prompt = f"""Rewrite the code so every problem below is gone.
The change may be a unified diff. Lines that start with + are the new code. Ignore lines that start with - or @@.
Return only the fixed function. Do not return a diff. Do not repeat string concatenation.
If a value is pasted into SQL, use a ? placeholder instead.

Problems:
{finding_text}

Previous test failures:
{error_text}

Change to fix:
{diff}
"""
    return complete(prompt)


def refactor_code(
    state: GraphState,
    complete_fn: Callable[[str, list[str], list[str]], str] | None = None,
) -> dict:
    """Rewrite the diff from the findings. Uses Groq unless a test passes complete_fn."""
    iteration = (state.get("iteration") or 0) + 1
    diff = state.get("diff") or ""
    findings = list(state.get("findings") or [])
    test_errors = list(state.get("test_errors") or [])

    nothing_to_fix = not findings or findings == [_CLEAR]
    if nothing_to_fix or (complete_fn is None and not settings.groq_api_key):
        return {"refactored_code": diff, "iteration": iteration}

    ask = complete_fn or _ask_model
    rewritten = strip_code_fences(ask(diff, findings, test_errors))
    return {"refactored_code": rewritten or diff, "iteration": iteration}
