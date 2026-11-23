"""
Shared embedding / vector-store helpers.

Default stack is free and local:
  - embeddings: FastEmbed (or a hash backend for offline tests)
  - vectors: embedded Qdrant on disk, remote URL if set, or :memory: for tests
"""

from __future__ import annotations

import math
import re
from functools import lru_cache

from langchain_core.embeddings import Embeddings
from qdrant_client import QdrantClient

from app.core.config import settings

_TOKEN = re.compile(r"[a-z0-9_]+", re.IGNORECASE)

_client: QdrantClient | None = None
_embeddings: Embeddings | None = None


class TokenHashEmbeddings(Embeddings):
    """Deterministic bag-of-tokens vectors for offline tests (no model download)."""

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in _TOKEN.findall(text.lower()):
            vec[hash(token) % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def reset_rag_clients() -> None:
    """Drop cached client/embeddings (tests call this between cases)."""
    global _client, _embeddings
    if _client is not None:
        try:
            _client.close()
        except Exception:
            pass
    _client = None
    _embeddings = None
    get_embedding_dim.cache_clear()
    # Avoid circular imports at module load — only when resetting.
    from app.rag import codebase, policy

    codebase.reset_code_index_state()
    policy.reset_policy_index_state()


def get_embeddings() -> Embeddings:
    """Return the shared embedding model."""
    global _embeddings
    if _embeddings is not None:
        return _embeddings

    backend = (settings.embedding_backend or "fastembed").strip().lower()
    if backend == "hash":
        _embeddings = TokenHashEmbeddings(dim=settings.embedding_dim)
        return _embeddings

    from langchain_community.embeddings import FastEmbedEmbeddings

    _embeddings = FastEmbedEmbeddings(model_name=settings.embedding_model)
    return _embeddings


@lru_cache(maxsize=1)
def get_embedding_dim() -> int:
    """Probe embedding size once (needed when creating Qdrant collections)."""
    sample = get_embeddings().embed_query("dimension probe")
    return len(sample)


def get_qdrant_client() -> QdrantClient:
    """
    Shared Qdrant client.

    Priority:
      1. QDRANT_PATH=:memory: → in-memory (tests)
      2. QDRANT_URL set → remote server
      3. else embedded store at QDRANT_PATH (default .qdrant)
    """
    global _client
    if _client is not None:
        return _client

    path = (settings.qdrant_path or "").strip()
    url = (settings.qdrant_url or "").strip()

    if path in {":memory:", ":memory"}:
        _client = QdrantClient(location=":memory:")
    elif url:
        _client = QdrantClient(url=url)
    else:
        _client = QdrantClient(path=path or ".qdrant")
    return _client
