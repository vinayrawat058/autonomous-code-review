"""Pull file paths and words out of a unified diff for nearby-code search."""

import re

_DIFF_PATH = re.compile(r"^(?:---|\+\+\+)\s+(?:a/|b/)?(.+)$", re.MULTILINE)
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")


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
