"""
RAG Layer 1 — Codebase.

v1: walk a local repo folder and return the Python files that best match the
diff (same paths first, then shared names). A vector database comes later.
"""

from pathlib import Path

from app.rag.diff_parse import changed_paths, search_terms

_SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache"}
_MAX_FILES = 4
_MAX_CHARS = 4000


def index_repository(repo_path: str) -> None:
    """Placeholder — crawl + chunk + upsert into Qdrant collection_code."""
    raise NotImplementedError(f"Index repo at {repo_path} in Phase 1.")


def _iter_python_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        files.append(path)
    return files


def _score_file(path: Path, root: Path, terms: set[str], preferred: set[str]) -> int:
    rel = path.relative_to(root).as_posix()
    score = 0
    if rel in preferred or path.name in preferred:
        score += 100
    name_terms = {path.stem, path.name, *path.stem.split("_")}
    score += 5 * len(terms & name_terms)
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return score
    score += sum(1 for term in terms if term in text)
    return score


def retrieve_code_context(query: str, repo_path: str | None = None) -> str:
    """Return nearby source snippets for the diff. Empty if no repo_path."""
    if not repo_path:
        return ""
    root = Path(repo_path)
    if not root.is_dir():
        return f"(repo_path not found: {repo_path})"

    terms = search_terms(query)
    preferred = set(changed_paths(query))
    preferred.update(Path(path).name for path in preferred)

    ranked = sorted(
        (
            (_score_file(path, root, terms, preferred), path)
            for path in _iter_python_files(root)
        ),
        key=lambda item: item[0],
        reverse=True,
    )
    chosen = [path for score, path in ranked if score > 0][:_MAX_FILES]
    if not chosen:
        return "(no nearby Python files matched this change)"

    parts: list[str] = []
    used = 0
    for path in chosen:
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        chunk = f"# {rel}\n{text}"
        if used + len(chunk) > _MAX_CHARS and parts:
            break
        parts.append(chunk)
        used += len(chunk)
    return "\n\n".join(parts)
