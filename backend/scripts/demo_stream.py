"""
Call POST /api/agent/stream and print each SSE event.

Terminal 1 (from backend/):
    .venv\\Scripts\\python.exe -m uvicorn app.main:app --reload --port 8000

Terminal 2 (from backend/):
    .venv\\Scripts\\python.exe scripts\\demo_stream.py
"""

import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SAMPLE_REPO = ROOT / "data" / "sample_repo"

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

TEST = """\
from solution import login

def test_username_is_not_pasted_into_the_query():
    result = login("alice")
    query = result[0] if isinstance(result, tuple) else result
    assert isinstance(query, str)
    assert "alice" not in query
    assert "?" in query
"""


def main() -> None:
    url = "http://127.0.0.1:8000/api/agent/stream"
    body = {
        "thread_id": "demo-1",
        "diff_text": DIFF,
        "repo_path": str(SAMPLE_REPO),
        "test_code": TEST,
    }
    print(f"POST {url}\n")
    with httpx.stream("POST", url, json=body, timeout=120.0) as response:
        response.raise_for_status()
        event_name = "message"
        data_lines: list[str] = []
        for line in response.iter_lines():
            if line.startswith("event:"):
                event_name = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                data_lines.append(line.removeprefix("data:").strip())
            elif line == "" and data_lines:
                raw = "\n".join(data_lines)
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    payload = raw
                print(f"[{event_name}]")
                print(json.dumps(payload, indent=2) if isinstance(payload, dict) else payload)
                print()
                event_name = "message"
                data_lines = []


if __name__ == "__main__":
    main()
