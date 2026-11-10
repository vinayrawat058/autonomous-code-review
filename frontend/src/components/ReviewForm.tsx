/**
 * Paste the diff (and optional repo path / tests), then start a review.
 */

import { useState, type FormEvent } from "react";

const SAMPLE_DIFF = `diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,3 +1,4 @@
 def login(user):
-    return user
+    query = "SELECT * FROM users WHERE name = '" + user + "'"
+    return query
`;

const SAMPLE_TEST = `from solution import login

def test_username_is_not_pasted_into_the_query():
    result = login("alice")
    query = result[0] if isinstance(result, tuple) else result
    assert isinstance(query, str)
    assert "alice" not in query
    assert "?" in query
`;

type Props = {
  running: boolean;
  onSubmit: (input: {
    diff_text: string;
    repo_path: string;
    test_code: string;
  }) => void;
};

export function ReviewForm({ running, onSubmit }: Props) {
  const [diffText, setDiffText] = useState(SAMPLE_DIFF);
  const [repoPath, setRepoPath] = useState("");
  const [testCode, setTestCode] = useState(SAMPLE_TEST);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!diffText.trim() || running) return;
    onSubmit({
      diff_text: diffText,
      repo_path: repoPath.trim(),
      test_code: testCode,
    });
  }

  return (
    <section className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-4">
      <h2 className="text-sm font-medium text-zinc-200">Review input</h2>
      <form className="mt-3 grid gap-3" onSubmit={handleSubmit}>
        <label className="grid gap-1 text-sm">
          <span className="text-zinc-400">Diff</span>
          <textarea
            className="min-h-[140px] rounded border border-zinc-700 bg-zinc-950 px-3 py-2 font-mono text-xs text-zinc-100 outline-none focus:border-zinc-500"
            value={diffText}
            onChange={(e) => setDiffText(e.target.value)}
            spellCheck={false}
          />
        </label>
        <label className="grid gap-1 text-sm">
          <span className="text-zinc-400">
            Local repo path (optional — for nearby-code search)
          </span>
          <input
            className="rounded border border-zinc-700 bg-zinc-950 px-3 py-2 font-mono text-xs text-zinc-100 outline-none focus:border-zinc-500"
            value={repoPath}
            onChange={(e) => setRepoPath(e.target.value)}
            placeholder="C:\path\to\backend\data\sample_repo"
          />
        </label>
        <label className="grid gap-1 text-sm">
          <span className="text-zinc-400">Sandbox pytest (optional)</span>
          <textarea
            className="min-h-[100px] rounded border border-zinc-700 bg-zinc-950 px-3 py-2 font-mono text-xs text-zinc-100 outline-none focus:border-zinc-500"
            value={testCode}
            onChange={(e) => setTestCode(e.target.value)}
            spellCheck={false}
          />
        </label>
        <button
          type="submit"
          disabled={running || !diffText.trim()}
          className="justify-self-start rounded bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-zinc-700"
        >
          {running ? "Reviewing…" : "Start review"}
        </button>
      </form>
    </section>
  );
}
