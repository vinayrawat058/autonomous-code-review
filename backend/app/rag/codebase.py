"""
RAG Layer 1 — Codebase.

Walk a local repo, chunk Python files, embed into Qdrant, and retrieve
snippets that are nearest to the pasted diff.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document

from app.core.config import settings
from app.rag import store
from app.rag.diff_parse import changed_paths

_SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache", ".qdrant"}
_CHUNK_CHARS = 800
_CHUNK_OVERLAP = 100

# Track which repo fingerprint is already in the code collection.
_indexed_fingerprint: str | None = None


def _iter_python_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        files.append(path)
    return files


def _chunk_text(text: str, size: int = _CHUNK_CHARS, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []
    if len(cleaned) <= size:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + size)
        chunks.append(cleaned[start:end].strip())
        if end >= len(cleaned):
            break
        start = max(0, end - overlap)
    return [chunk for chunk in chunks if chunk]


def _docs_from_repo(root: Path) -> list[Document]:
    docs: list[Document] = []
    for path in _iter_python_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for index, chunk in enumerate(_chunk_text(text)):
            docs.append(
                Document(
                    page_content=chunk,
                    metadata={"source": rel, "chunk": index, "repo": str(root)},
                )
            )
    return docs


def _fingerprint(root: Path) -> str:
    pairs: list[tuple[str, float]] = []
    for path in _iter_python_files(root):
        try:
            pairs.append((path.relative_to(root).as_posix(), path.stat().st_mtime))
        except OSError:
            continue
    return store.source_fingerprint(pairs)


def index_repository(repo_path: str, *, force: bool = False) -> int:
    """Crawl + chunk + upsert a local repo into the codebase collection."""
    global _indexed_fingerprint
    root = Path(repo_path)
    if not root.is_dir():
        raise FileNotFoundError(f"repo_path not found: {repo_path}")

    fingerprint = _fingerprint(root)
    collection = settings.qdrant_collection_code
    already = (
        not force
        and _indexed_fingerprint == fingerprint
        and store.collection_count(collection) > 0
    )
    if already:
        return 0

    docs = _docs_from_repo(root)
    store.wipe_collection(collection)
    written = store.upsert_documents(collection, docs)
    _indexed_fingerprint = fingerprint
    return written


def retrieve_code_context(query: str, repo_path: str | None = None) -> str:
    """Return nearby source snippets for the diff via vector search."""
    if not repo_path:
        return ""
    root = Path(repo_path)
    if not root.is_dir():
        return f"(repo_path not found: {repo_path})"

    try:
        index_repository(str(root))
    except Exception as exc:  # keep the agent alive if indexing fails
        return f"(code index failed: {exc})"

    # Bias the query with changed paths so edited files rank higher.
    paths = " ".join(changed_paths(query))
    search_query = f"{paths}\n{query}".strip()
    docs = store.similarity_search(
        settings.qdrant_collection_code,
        search_query,
        k=settings.rag_top_k_code,
    )
    if not docs:
        return "(no nearby Python files matched this change)"

    parts: list[str] = []
    used = 0
    seen: set[str] = set()
    for doc in docs:
        source = doc.metadata.get("source") or "snippet"
        key = f"{source}:{doc.metadata.get('chunk')}"
        if key in seen:
            continue
        seen.add(key)
        chunk = f"# {source}\n{doc.page_content.strip()}"
        if used + len(chunk) > settings.rag_max_chars and parts:
            break
        parts.append(chunk)
        used += len(chunk)
    return "\n\n".join(parts)


def reset_code_index_state() -> None:
    global _indexed_fingerprint
    _indexed_fingerprint = None
