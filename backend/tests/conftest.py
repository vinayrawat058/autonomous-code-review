"""Shared fixtures — isolate vector RAG + use in-memory checkpoints in tests."""

import os

# Must run before app.agent.graph imports make_checkpointer().
os.environ.setdefault("CHECKPOINT_BACKEND", "memory")

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
    monkeypatch.setattr(settings, "checkpoint_backend", "memory")
    monkeypatch.setattr(settings, "approve_ttl_seconds", 3600)
    reset_rag_clients()
    yield
    reset_rag_clients()
