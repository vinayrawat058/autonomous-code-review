"""Shared fixtures — isolate vector RAG between tests (in-memory + hash embeddings)."""

import pytest

from app.core.config import settings
from app.rag.embeddings import reset_rag_clients


@pytest.fixture(autouse=True)
def _isolate_rag(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "embedding_backend", "hash")
    monkeypatch.setattr(settings, "qdrant_url", "")
    monkeypatch.setattr(settings, "qdrant_path", ":memory:")
    monkeypatch.setattr(settings, "qdrant_collection_code", "codebase_test")
    monkeypatch.setattr(settings, "qdrant_collection_policy", "policies_test")
    reset_rag_clients()
    yield
    reset_rag_clients()
