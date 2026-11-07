"""Nearby-code search returns matching files from a local repo folder."""

from pathlib import Path

from app.rag.codebase import retrieve_code_context
from app.rag.diff_parse import changed_paths, search_terms

SAMPLE_REPO = Path(__file__).resolve().parents[1] / "data" / "sample_repo"

DIFF = """\
diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,3 +1,4 @@
 def login(user):
-    return user
+    query = "SELECT * FROM users WHERE name = '" + user + "'"
+    return query
"""


def test_changed_paths_and_terms():
    assert "app.py" in changed_paths(DIFF)
    terms = search_terms(DIFF)
    assert "login" in terms
    assert "query" in terms


def test_retrieve_finds_app_and_db_helpers():
    context = retrieve_code_context(DIFF, str(SAMPLE_REPO))
    assert "# app.py" in context
    assert "# db.py" in context
    assert "run_query" in context
    assert "params" in context


def test_missing_repo_returns_empty():
    assert retrieve_code_context(DIFF, None) == ""
