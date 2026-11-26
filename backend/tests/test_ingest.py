"""Ingest validates and normalizes pasted diffs / plain code."""

import pytest

from app.agent.diff_ingest import IngestError, ingest_and_normalize
from app.agent.nodes.ingest import ingest_diff


UNIFIED = """\
diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,2 +1,2 @@
 def login(user):
-    return user
+    return "SELECT ?", (user,)
"""


def test_normalize_crlf_and_bom():
    raw = "\ufeff" + UNIFIED.replace("\n", "\r\n")
    result = ingest_and_normalize(raw)
    assert "\r" not in result.diff
    assert result.diff_kind == "unified"
    assert result.changed_files == ["app.py"]
    assert result.diff.endswith("\n")


def test_reject_empty_and_null_bytes():
    with pytest.raises(IngestError, match="empty"):
        ingest_and_normalize("   \n\n")
    with pytest.raises(IngestError, match="null"):
        ingest_and_normalize("hello\x00world")


def test_reject_oversized(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "max_diff_chars", 20)
    with pytest.raises(IngestError, match="characters"):
        ingest_and_normalize("x" * 50)


def test_plain_python_becomes_synthetic_diff():
    plain = "def add(a, b):\n    return a + b\n"
    result = ingest_and_normalize(plain)
    assert result.diff_kind == "synthetic"
    assert result.changed_files == ["pasted_change.py"]
    assert result.diff.startswith("diff --git a/pasted_change.py")
    assert "+def add(a, b):" in result.diff
    assert result.warnings


def test_plain_path_hint():
    plain = "# file: helpers/auth.py\ndef ok():\n    return True\n"
    result = ingest_and_normalize(plain)
    assert result.changed_files == ["helpers/auth.py"]
    assert "helpers/auth.py" in result.diff


def test_ingest_node_writes_state_fields():
    out = ingest_diff({"diff": UNIFIED, "iteration": 2})
    assert out["diff_kind"] == "unified"
    assert out["changed_files"] == ["app.py"]
    assert out["iteration"] == 2
    assert out["findings"] == []
    assert out["test_errors"] == []


def test_ingest_node_raises_on_bad_input():
    with pytest.raises(IngestError):
        ingest_diff({"diff": ""})
