"""
RAG Layer 2 — Policy / security rules.

Indexes OWASP Top 10 notes and internal guidelines from data/policies/
so the SecurityAudit node cites real rules instead of hallucinating.
"""


def index_policies(policies_dir: str = "data/policies") -> None:
    """Placeholder — load markdown/text policies into Qdrant collection_policy."""
    raise NotImplementedError(f"Index policies from {policies_dir} in Phase 1.")


def retrieve_policy_context(query: str) -> str:
    """Placeholder — similarity search over security policies."""
    _ = query
    return ""
