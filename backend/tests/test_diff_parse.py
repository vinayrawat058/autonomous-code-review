"""Multi-file unified diff parsing and PR file-map building."""

from app.rag.diff_parse import files_for_pull_request, files_from_diff, parse_unified_diff

MULTI = """\
diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,3 +1,4 @@
 def login(user):
-    return user
+    query = "SELECT * FROM users WHERE name = ?"
+    return query, (user,)
diff --git a/db.py b/db.py
--- a/db.py
+++ b/db.py
@@ -1,2 +1,3 @@
 def run_query(sql, params=None):
+    # always use params
     return {"sql": sql, "params": params or ()}
"""


def test_parse_multi_file_paths():
    patches = parse_unified_diff(MULTI)
    assert [p.path for p in patches] == ["app.py", "db.py"]


def test_files_from_diff_rebuilds_both():
    files = files_from_diff(MULTI)
    assert set(files) == {"app.py", "db.py"}
    assert "SELECT * FROM users WHERE name = ?" in files["app.py"]
    assert "always use params" in files["db.py"]
    assert "return user" not in files["app.py"]


def test_files_for_pr_overlays_refactor_on_primary():
    rewrite = "def login(user):\n    return run_query('SELECT * FROM users WHERE name = ?', (user,))\n"
    files = files_for_pull_request(MULTI, rewrite, primary_path="app.py")
    assert set(files) == {"app.py", "db.py"}
    assert "run_query" in files["app.py"]
    assert "always use params" in files["db.py"]


def test_files_for_pr_accepts_refactored_multi_diff():
    rewrite = """\
diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,2 +1,2 @@
 def login(user):
-    return user
+    return safe(user)
diff --git a/helpers.py b/helpers.py
new file mode 100644
--- /dev/null
+++ b/helpers.py
@@ -0,0 +1,2 @@
+def safe(user):
+    return user
"""
    files = files_for_pull_request("diff --git a/app.py b/app.py\n", rewrite)
    assert "app.py" in files
    assert "helpers.py" in files
    assert "def safe" in files["helpers.py"]
