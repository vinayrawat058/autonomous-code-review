"""
Walk the review graph. The security step calls Groq when GROQ_API_KEY is set.

From the backend folder:

    .venv\\Scripts\\python.exe scripts\\run_stub_review.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.graph import build_graph

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


def main() -> None:
    graph = build_graph()
    print("Review path:\n")
    step = 0
    final_state: dict = {"diff": SAMPLE_DIFF, "iteration": 0}
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
