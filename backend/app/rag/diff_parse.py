"""Parse unified diffs for nearby-code search and multi-file PR apply."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_DIFF_PATH = re.compile(r"^(?:---|\+\+\+)\s+(?:a/|b/)?(.+)$", re.MULTILINE)
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
_GIT_HEADER = re.compile(r"^diff --git a/(.+?) b/(.+)$")
_PLUS_PLUS = re.compile(r"^\+\+\+\s+(?:b/)?(.+)$")
_MINUS_MINUS = re.compile(r"^---\s+(?:a/)?(.+)$")


@dataclass
class FilePatch:
    """One file section from a unified diff."""

    path: str
    old_path: str | None = None
    is_new: bool = False
    is_deleted: bool = False
    lines: list[str] = field(default_factory=list)

    def new_content(self) -> str | None:
        """Rebuild the post-change file from context and + lines."""
        if self.is_deleted:
            return None
        body: list[str] = []
        for line in self.lines:
            if line.startswith("@@") or line.startswith("diff --git") or line.startswith("index "):
                continue
            if line.startswith("---") or line.startswith("+++"):
                continue
            if line.startswith("\\"):  # "\ No newline at end of file"
                continue
            if line.startswith("+") or line.startswith(" "):
                body.append(line[1:])
            elif line.startswith("-"):
                continue
        text = "\n".join(body)
        if body:
            text += "\n"
        return text


def changed_paths(diff: str) -> list[str]:
    """Return unique paths mentioned on --- / +++ lines, skipping /dev/null."""
    paths: list[str] = []
    seen: set[str] = set()
    for match in _DIFF_PATH.finditer(diff or ""):
        path = match.group(1).strip()
        if path == "/dev/null" or path in seen:
            continue
        seen.add(path)
        paths.append(path)
    return paths


def search_terms(diff: str) -> set[str]:
    """Words from the diff that are useful for matching nearby source files."""
    skip = {
        "diff",
        "git",
        "def",
        "class",
        "return",
        "import",
        "from",
        "None",
        "True",
        "False",
        "self",
        "with",
        "for",
        "while",
        "elif",
        "else",
        "pass",
        "print",
    }
    terms = {word for word in _WORD.findall(diff or "") if word not in skip}
    for path in changed_paths(diff):
        stem = path.rsplit("/", 1)[-1]
        if stem.endswith(".py"):
            terms.add(stem[:-3])
        terms.add(stem)
    return terms


def parse_unified_diff(diff: str) -> list[FilePatch]:
    """Split a unified diff into per-file patches (supports multi-file)."""
    text = diff or ""
    if not text.strip():
        return []

    # Prefer git-style file headers when present.
    if "diff --git " in text:
        return _parse_git_diff(text)
    return _parse_simple_diff(text)


def _parse_git_diff(text: str) -> list[FilePatch]:
    patches: list[FilePatch] = []
    current: FilePatch | None = None

    for raw in text.splitlines():
        header = _GIT_HEADER.match(raw)
        if header:
            if current is not None:
                patches.append(current)
            old_p, new_p = header.group(1), header.group(2)
            current = FilePatch(path=new_p, old_path=old_p, lines=[raw])
            continue
        if current is None:
            continue
        current.lines.append(raw)
        if raw.startswith("new file mode"):
            current.is_new = True
        elif raw.startswith("deleted file mode"):
            current.is_deleted = True
        plus = _PLUS_PLUS.match(raw)
        if plus:
            path = plus.group(1).strip()
            if path == "/dev/null":
                current.is_deleted = True
            else:
                current.path = path
        minus = _MINUS_MINUS.match(raw)
        if minus:
            path = minus.group(1).strip()
            if path == "/dev/null":
                current.is_new = True
            else:
                current.old_path = path

    if current is not None:
        patches.append(current)
    return patches


def _parse_simple_diff(text: str) -> list[FilePatch]:
    """Fallback when there is no `diff --git` header (pasted --- / +++ blocks)."""
    patches: list[FilePatch] = []
    current: FilePatch | None = None

    for raw in text.splitlines():
        minus = _MINUS_MINUS.match(raw)
        plus = _PLUS_PLUS.match(raw)
        if minus and current is None:
            path = minus.group(1).strip()
            current = FilePatch(
                path="" if path == "/dev/null" else path,
                old_path=None if path == "/dev/null" else path,
                is_new=path == "/dev/null",
                lines=[raw],
            )
            continue
        if plus and current is not None and not any(
            line.startswith("+++") for line in current.lines
        ):
            path = plus.group(1).strip()
            if path == "/dev/null":
                current.is_deleted = True
            else:
                current.path = path
            current.lines.append(raw)
            continue
        if plus and (current is None or any(line.startswith("+++") for line in current.lines)):
            if current is not None and current.path:
                patches.append(current)
            path = plus.group(1).strip()
            current = FilePatch(
                path="" if path == "/dev/null" else path,
                is_new=False,
                lines=[raw],
            )
            continue
        if current is None:
            continue
        # Next --- starts a new file block after a completed +++ section.
        if minus and any(line.startswith("+++") for line in current.lines):
            patches.append(current)
            path = minus.group(1).strip()
            current = FilePatch(
                path="" if path == "/dev/null" else path,
                old_path=None if path == "/dev/null" else path,
                is_new=path == "/dev/null",
                lines=[raw],
            )
            continue
        current.lines.append(raw)

    if current is not None and current.path:
        patches.append(current)
    return patches


def looks_like_unified_diff(text: str) -> bool:
    sample = (text or "").lstrip()
    return sample.startswith("diff --git ") or sample.startswith("--- ") or "\n@@ " in (
        "\n" + sample
    )


def files_from_diff(diff: str) -> dict[str, str]:
    """Map path → new file text for every non-deleted file in the diff."""
    out: dict[str, str] = {}
    for patch in parse_unified_diff(diff):
        if not patch.path or patch.is_deleted:
            continue
        content = patch.new_content()
        if content is None:
            continue
        out[patch.path] = content
    return out


def files_for_pull_request(
    diff_text: str,
    refactored_code: str,
    primary_path: str | None = None,
) -> dict[str, str]:
    """
    Build the file map to write into a GitHub PR.

    - Parses the original multi-file diff into per-file new contents.
    - Overlays `refactored_code` onto the primary path when it is plain code.
    - If `refactored_code` itself is a unified diff, those files win.
    """
    rewrite = (refactored_code or "").strip()
    files = files_from_diff(diff_text)

    if rewrite and looks_like_unified_diff(rewrite):
        rewritten_files = files_from_diff(rewrite)
        if rewritten_files:
            files.update(rewritten_files)
            return files

    paths = changed_paths(diff_text)
    primary = (primary_path or "").strip() or (paths[0] if paths else "app.py")

    if rewrite and not looks_like_unified_diff(rewrite):
        content = rewrite if rewrite.endswith("\n") else rewrite + "\n"
        files[primary] = content
    elif not files and rewrite:
        content = rewrite if rewrite.endswith("\n") else rewrite + "\n"
        files[primary] = content

    return files
