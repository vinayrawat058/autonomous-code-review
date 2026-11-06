"""
RAG Layer 2 — Policy / security rules.

The rulebook is short, so the security step currently receives the whole file.
A vector search over these notes comes later.
"""

from pathlib import Path

_POLICIES_DIR = Path(__file__).resolve().parents[2] / "data" / "policies"


def index_policies(policies_dir: str = "data/policies") -> None:
    """Placeholder — load markdown/text policies into Qdrant collection_policy."""
    raise NotImplementedError(f"Index policies from {policies_dir} in Phase 1.")


def retrieve_policy_context(query: str) -> str:
    """Return the security rulebook text. `query` is unused until vector search."""
    _ = query
    if not _POLICIES_DIR.is_dir():
        return ""
    parts = [
        path.read_text(encoding="utf-8")
        for path in sorted(_POLICIES_DIR.glob("*.md"))
    ]
    return "\n\n".join(parts).strip()
