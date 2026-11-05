"""
RAG Layer 1 — Codebase.

Index repo files (later: AST-aware chunks) into a vector DB.
At review time, retrieve surrounding code beyond the PR diff.
"""


def index_repository(repo_path: str) -> None:
    """Placeholder — crawl + chunk + upsert into Qdrant collection_code."""
    raise NotImplementedError(f"Index repo at {repo_path} in Phase 1.")


def retrieve_code_context(query: str, repo_path: str | None = None) -> str:
    """Placeholder — similarity search over indexed code."""
    _ = (query, repo_path)
    return ""
