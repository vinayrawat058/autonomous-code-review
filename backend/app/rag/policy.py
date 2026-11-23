"""
RAG Layer 2 — Policy / security rules.

Chunk OWASP / policy markdown into Qdrant and retrieve only the sections
that match the pasted diff (instead of dumping the whole rulebook).
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document

from app.core.config import settings
from app.rag import store

_POLICIES_DIR = Path(__file__).resolve().parents[2] / "data" / "policies"
_indexed_fingerprint: str | None = None


def _policy_files(policies_dir: Path) -> list[Path]:
    if not policies_dir.is_dir():
        return []
    return sorted(policies_dir.glob("*.md"))


def _split_markdown_sections(text: str, source: str) -> list[Document]:
    """Split on ## headings so each OWASP item is its own vector."""
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_title = source
    current_body: list[str] = []

    for line in lines:
        if line.startswith("## "):
            if current_body and any(part.strip() for part in current_body):
                sections.append((current_title, current_body))
            current_title = line[3:].strip() or source
            current_body = [line]
        else:
            current_body.append(line)

    if current_body and any(part.strip() for part in current_body):
        sections.append((current_title, current_body))

    docs: list[Document] = []
    for index, (title, body) in enumerate(sections):
        content = "\n".join(body).strip()
        if len(content) < 40 and not title.startswith("A"):
            # Skip tiny intro blurb without a real rule.
            continue
        docs.append(
            Document(
                page_content=content,
                metadata={"source": source, "section": title, "chunk": index},
            )
        )
    return docs


def _docs_from_dir(policies_dir: Path) -> list[Document]:
    docs: list[Document] = []
    for path in _policy_files(policies_dir):
        text = path.read_text(encoding="utf-8")
        docs.extend(_split_markdown_sections(text, path.name))
    return docs


def _fingerprint(policies_dir: Path) -> str:
    pairs: list[tuple[str, float]] = []
    for path in _policy_files(policies_dir):
        pairs.append((path.name, path.stat().st_mtime))
    return store.source_fingerprint(pairs)


def index_policies(policies_dir: str | None = None, *, force: bool = False) -> int:
    """Load markdown policies into the policy Qdrant collection."""
    global _indexed_fingerprint
    root = Path(policies_dir) if policies_dir else _POLICIES_DIR
    if not root.is_dir():
        raise FileNotFoundError(f"policies dir not found: {root}")

    fingerprint = _fingerprint(root)
    collection = settings.qdrant_collection_policy
    already = (
        not force
        and _indexed_fingerprint == fingerprint
        and store.collection_count(collection) > 0
    )
    if already:
        return 0

    docs = _docs_from_dir(root)
    store.wipe_collection(collection)
    written = store.upsert_documents(collection, docs)
    _indexed_fingerprint = fingerprint
    return written


def _enrich_query(query: str) -> str:
    """Add light security hints so short diffs still hit the right OWASP section."""
    lower = (query or "").lower()
    hints: list[str] = []
    if any(
        token in lower
        for token in ("select ", "insert ", "update ", "delete ", "sql", "'+", '"+', "execute(")
    ):
        hints.append("A03 Injection SQL parameterized queries concatenate")
    if any(token in lower for token in ("password", "secret", "api_key", "token")):
        hints.append("A02 Cryptographic Failures secrets hashing")
    if any(token in lower for token in ("http://", "https://", "requests.get", "urlopen")):
        hints.append("A10 SSRF outbound URLs allowlist")
    return f"{query}\n{' '.join(hints)}".strip() or "security injection access control"


def retrieve_policy_context(query: str, policies_dir: str | None = None) -> str:
    """Return the policy sections nearest to the diff query."""
    root = Path(policies_dir) if policies_dir else _POLICIES_DIR
    if not root.is_dir():
        return ""

    try:
        index_policies(str(root))
    except Exception as exc:
        return f"(policy index failed: {exc})"

    docs = store.similarity_search(
        settings.qdrant_collection_policy,
        _enrich_query(query),
        k=settings.rag_top_k_policy,
    )
    if not docs:
        return ""

    parts: list[str] = []
    used = 0
    for doc in docs:
        chunk = doc.page_content.strip()
        if used + len(chunk) > settings.rag_max_chars and parts:
            break
        parts.append(chunk)
        used += len(chunk)
    return "\n\n".join(parts).strip()


def reset_policy_index_state() -> None:
    global _indexed_fingerprint
    _indexed_fingerprint = None
