"""
Validate and normalize pasted diffs / code before the LangGraph walk.

Turns messy clipboard input into a consistent LF unified diff (or a
synthetic one when the user pasted plain Python).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.config import settings
from app.rag.diff_parse import changed_paths, looks_like_unified_diff, parse_unified_diff

_BOM = "\ufeff"
_NULL = "\x00"
_PATH_HINT = re.compile(
    r"^(?:#\s*)?(?:file|path)\s*[:=]\s*(?P<path>[\w./\\-]+\.py)\s*$",
    re.IGNORECASE,
)


class IngestError(ValueError):
    """Raised when the pasted change cannot be accepted."""


@dataclass
class IngestResult:
    diff: str
    diff_kind: str  # unified | plain | synthetic
    changed_files: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    byte_length: int = 0
    line_count: int = 0


def _max_chars() -> int:
    value = getattr(settings, "max_diff_chars", 200_000)
    return max(1, int(value if value is not None else 200_000))


def _max_files() -> int:
    value = getattr(settings, "max_diff_files", 40)
    return max(1, int(value if value is not None else 40))


def normalize_text(raw: str) -> str:
    """Strip BOM, reject NULs, normalize newlines to LF, trim outer blank lines."""
    if raw is None:
        return ""
    text = str(raw)
    if _NULL in text:
        raise IngestError("Diff contains null bytes — binary patches are not supported.")
    if text.startswith(_BOM):
        text = text.lstrip(_BOM)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Drop trailing spaces on each line; keep intentional content.
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def _ensure_trailing_newline(text: str) -> str:
    if not text:
        return text
    return text if text.endswith("\n") else text + "\n"


def _plain_path_hint(text: str) -> str | None:
    first = text.split("\n", 1)[0].strip()
    match = _PATH_HINT.match(first)
    if match:
        path = match.group("path").replace("\\", "/")
        return path.lstrip("./")
    return None


def _wrap_plain_as_diff(text: str, path: str) -> str:
    """Turn pasted source into a new-file unified diff so downstream steps stay consistent."""
    body_lines = text.split("\n")
    # Drop a leading path hint comment line from the file body.
    if _PATH_HINT.match(body_lines[0].strip() if body_lines else ""):
        body_lines = body_lines[1:]
        while body_lines and not body_lines[0].strip():
            body_lines.pop(0)
    if not body_lines:
        raise IngestError("Plain paste had a path hint but no code body.")

    n = len(body_lines)
    plus = "\n".join(f"+{line}" for line in body_lines)
    return (
        f"diff --git a/{path} b/{path}\n"
        f"new file mode 100644\n"
        f"--- /dev/null\n"
        f"+++ b/{path}\n"
        f"@@ -0,0 +1,{n} @@\n"
        f"{plus}\n"
    )


def _normalize_unified_diff(text: str) -> tuple[str, list[str]]:
    """Light cleanup for real unified diffs; return text + warnings."""
    warnings: list[str] = []
    lines = text.split("\n")
    cleaned: list[str] = []
    for line in lines:
        # Keep diff structure lines intact; only normalize odd spacing on headers.
        if line.startswith("diff --git"):
            cleaned.append(" ".join(line.split()))
            continue
        if line.startswith("--- ") or line.startswith("+++ "):
            cleaned.append(line.rstrip())
            continue
        cleaned.append(line)

    normalized = _ensure_trailing_newline("\n".join(cleaned))
    patches = parse_unified_diff(normalized)
    if not patches and not looks_like_unified_diff(normalized):
        raise IngestError("Input looked like a diff but no file hunks could be parsed.")

    paths = changed_paths(normalized)
    if not paths and patches:
        paths = [p.path for p in patches if p.path]

    max_files = _max_files()
    if len(paths) > max_files:
        raise IngestError(
            f"Diff touches {len(paths)} files; max allowed is {max_files}."
        )

    # Warn on delete-only patches (supported for parse, not applied as PR files).
    if any(p.is_deleted for p in patches):
        warnings.append("Diff includes deleted files — create_pr skips deletions.")

    return normalized, warnings


def ingest_and_normalize(raw: str) -> IngestResult:
    """
    Validate + normalize clipboard input.

    - Unified diffs are cleaned and path-counted.
    - Plain Python (or any text) is wrapped as a synthetic new-file diff.
    """
    text = normalize_text(raw)
    if not text.strip():
        raise IngestError("Diff is empty after normalization.")

    encoded = text.encode("utf-8")
    max_chars = _max_chars()
    if len(text) > max_chars:
        raise IngestError(
            f"Diff is {len(text)} characters; max allowed is {max_chars}."
        )

    warnings: list[str] = []
    if looks_like_unified_diff(text):
        normalized, diff_warnings = _normalize_unified_diff(text)
        warnings.extend(diff_warnings)
        kind = "unified"
        paths = changed_paths(normalized)
        if not paths:
            # Hunk without standard ---/+++ paths — still keep the text.
            warnings.append("Unified diff had no clear file paths.")
    else:
        path = _plain_path_hint(text) or "pasted_change.py"
        normalized = _wrap_plain_as_diff(text, path)
        kind = "synthetic"
        paths = [path]
        warnings.append(
            f"Plain paste normalized into a synthetic new-file diff for `{path}`."
        )

    normalized = _ensure_trailing_newline(normalized)
    return IngestResult(
        diff=normalized,
        diff_kind=kind,
        changed_files=paths,
        warnings=warnings,
        byte_length=len(encoded),
        line_count=normalized.count("\n") + (0 if normalized.endswith("\n") else 1),
    )
