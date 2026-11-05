"""
Node: RetrieveRAGContext

Pulls Dual-Layer RAG context into state:
  Layer 1 — nearby code from the repo (codebase vector store)
  Layer 2 — OWASP / policy snippets (policy vector store)
"""

from app.agent.state import GraphState
from app.rag import codebase, policy


def retrieve_rag_context(state: GraphState) -> dict:
    """Placeholder — Phase 1 wires real retrievers."""
    query = state.get("diff") or ""
    code_context = codebase.retrieve_code_context(query, state.get("repo_path"))
    policy_context = policy.retrieve_policy_context(query)
    return {
        "code_context": code_context,
        "policy_context": policy_context,
    }
