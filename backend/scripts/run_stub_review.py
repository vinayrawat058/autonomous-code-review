"""
Walk the review graph. The security step calls Groq when GROQ_API_KEY is set.

From the backend folder:

    .venv\\Scripts\\python.exe scripts\\run_stub_review.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agent.graph import build_graph

SAMPLE_REPO = ROOT / "data" / "sample_repo"

SAMPLE_DIFF = """\
diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,3 +1,4 @@
 def login(user):
-    return user
+    query = "SELECT * FROM users WHERE name = '" + user + "'"
+    return query
"""

SAMPLE_TEST = """\
from solution import login

def test_username_is_not_pasted_into_the_query():
    result = login("alice")
    query = result[0] if isinstance(result, tuple) else result
    assert isinstance(query, str)
    assert "alice" not in query
    assert "?" in query
"""


def main() -> None:
    graph = build_graph()
    print("Review path:\n")
    step = 0
    final_state: dict = {
        "diff": SAMPLE_DIFF,
        "iteration": 0,
        "test_code": SAMPLE_TEST,
        "repo_path": str(SAMPLE_REPO),
    }
    for update in graph.stream(final_state):
        for node_name, node_update in update.items():
            step += 1
            print(f"{step}. {node_name}")
            for key, value in node_update.items():
                text = value if isinstance(value, str) else repr(value)
                print(f"   {key}: {text}")
            print()
            final_state.update(node_update)
    print("Finished.")
    print(f"findings: {final_state.get('findings')}")
    print(f"iteration: {final_state.get('iteration')}")
    print(f"test_errors: {final_state.get('test_errors')}")


if __name__ == "__main__":
    main()
