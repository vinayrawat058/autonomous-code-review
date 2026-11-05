"""
Shared embedding / vector-store helpers.

One place to build the embedding model and connect to Qdrant
so codebase.py and policy.py don't duplicate setup.
"""


def get_embeddings():
    """Placeholder — Phase 1 returns an OpenAI (or local) embeddings client."""
    raise NotImplementedError("Wire embeddings in Phase 1.")


def get_qdrant_client():
    """Placeholder — Phase 1 returns a Qdrant client from settings."""
    raise NotImplementedError("Wire Qdrant in Phase 1.")
