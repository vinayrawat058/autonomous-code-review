"""Qdrant collection helpers shared by codebase + policy RAG."""

from __future__ import annotations

import hashlib
import uuid
from typing import Iterable

from langchain_core.documents import Document
from qdrant_client.http import models as qmodels

from app.rag.embeddings import get_embedding_dim, get_embeddings, get_qdrant_client


def _stable_id(text: str) -> str:
    return str(uuid.UUID(hashlib.md5(text.encode("utf-8")).hexdigest()))


def ensure_collection(name: str) -> None:
    """Create the collection if missing (cosine, embedding-sized vectors)."""
    client = get_qdrant_client()
    if client.collection_exists(name):
        return
    client.create_collection(
        collection_name=name,
        vectors_config=qmodels.VectorParams(
            size=get_embedding_dim(),
            distance=qmodels.Distance.COSINE,
        ),
    )


def collection_count(name: str) -> int:
    client = get_qdrant_client()
    if not client.collection_exists(name):
        return 0
    return int(client.count(collection_name=name, exact=True).count)


def wipe_collection(name: str) -> None:
    client = get_qdrant_client()
    if client.collection_exists(name):
        client.delete_collection(name)


def upsert_documents(collection: str, documents: Iterable[Document]) -> int:
    """Embed and upsert documents. Returns how many were written."""
    docs = list(documents)
    if not docs:
        return 0

    ensure_collection(collection)
    embeddings = get_embeddings()
    client = get_qdrant_client()

    texts = [doc.page_content for doc in docs]
    vectors = embeddings.embed_documents(texts)
    points = []
    for doc, vector in zip(docs, vectors, strict=True):
        key = f"{doc.metadata.get('source', '')}::{doc.metadata.get('chunk', '')}::{doc.page_content[:80]}"
        points.append(
            qmodels.PointStruct(
                id=_stable_id(key),
                vector=vector,
                payload={
                    "page_content": doc.page_content,
                    "metadata": doc.metadata,
                },
            )
        )
    client.upsert(collection_name=collection, points=points)
    return len(points)


def similarity_search(collection: str, query: str, k: int) -> list[Document]:
    """Return top-k documents for the query text."""
    if collection_count(collection) == 0:
        return []

    client = get_qdrant_client()
    vector = get_embeddings().embed_query(query)
    hits = client.query_points(
        collection_name=collection,
        query=vector,
        limit=k,
        with_payload=True,
    ).points

    docs: list[Document] = []
    for hit in hits:
        payload = hit.payload or {}
        content = payload.get("page_content") or ""
        metadata = payload.get("metadata") or {}
        if content:
            docs.append(Document(page_content=content, metadata=metadata))
    return docs


def source_fingerprint(paths_and_mtime: Iterable[tuple[str, float]]) -> str:
    """Hash of path+mtime pairs so we can reindex when files change."""
    blob = "|".join(f"{path}:{mtime}" for path, mtime in sorted(paths_and_mtime))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
