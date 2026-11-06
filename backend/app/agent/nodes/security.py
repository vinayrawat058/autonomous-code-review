"""
Node: SecurityAudit

Reads the diff and the rulebook, then asks Groq which rules the change breaks.
"""

from collections.abc import Callable

from app.agent.llm import complete
from app.agent.state import GraphState
from app.core.config import settings

_MISSING_KEY = (
    "No GROQ_API_KEY set. Copy backend/.env.example to backend/.env and paste a free key "
    "from https://console.groq.com"
)


def findings_from_reply(reply: str) -> list[str]:
    """Turn the model reply into a list of findings. NONE means the change looks clear."""
    lines = [line.strip() for line in reply.splitlines() if line.strip()]
    findings = [line for line in lines if line.upper() != "NONE"]
    if not findings:
        return ["No rule from the rulebook matched this change."]
    return findings


def _ask_model(diff: str, policy_context: str, code_context: str) -> str:
    prompt = f"""You are a security reviewer. Use only the rulebook below. Do not invent rules.

Rulebook:
{policy_context or "(empty)"}

Nearby code:
{code_context or "(none)"}

Code change:
{diff}

If the change breaks a rule, reply with one finding per line in this form:
RULE | short quote from the rulebook | what is wrong in the change
If nothing in the rulebook applies, reply with exactly: NONE
"""
    return complete(prompt)


def security_audit(
    state: GraphState,
    complete_fn: Callable[[str, str, str], str] | None = None,
) -> dict:
    """Write findings for this diff. Uses Groq unless a test passes complete_fn."""
    if complete_fn is None and not settings.groq_api_key:
        return {"findings": [_MISSING_KEY]}

    ask = complete_fn or _ask_model
    reply = ask(
        state.get("diff") or "",
        state.get("policy_context") or "",
        state.get("code_context") or "",
    )
    return {"findings": findings_from_reply(reply)}
