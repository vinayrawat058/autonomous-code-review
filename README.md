# Agentic PR Review Studio

**Status:** Work in progress. Backend agent + SSE API run; the React studio can start a review, show live node status, and display a Monaco diff.

## Done so far

The agent walks five steps: ingest the diff, load context, security audit, refactor, then sandbox tests.

- **Security audit** sends the diff and the OWASP rulebook to Groq and returns a cited finding.
- **Refactor** rewrites that diff from the finding. On the sample login change, the pasted username becomes a `?` placeholder.
- **Sandbox** runs pytest on the rewrite in a temporary folder. A failure goes back to refactor, up to three tries.
- **Ingest** stores the pasted diff.
- **Retrieve** now fills both shelves: nearby Python files from a local `repo_path` (sample repo under `backend/data/sample_repo`), plus the whole OWASP rulebook. A vector database is still later.
- **FastAPI SSE** — `POST /api/agent/stream` runs the graph and pushes `started` / `node` / `done` events to the client.
- **React studio** — paste a diff, watch the graph sidebar update from SSE, see original vs rewrite in Monaco, then Approve / Reject (PR creation still later).

The API key stays in `backend/.env` and is not committed.

```powershell
# API
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# Studio (other terminal)
cd frontend
npm install
npm run dev
# open http://127.0.0.1:5173
```

## Idea

Build a full-stack AI system that reviews pull-request diffs the way a senior engineer would. You paste a diff (and optionally point at the repo). The system loads surrounding code and security-policy context, runs a multi-step agent through security audit, refactor, and a sandbox test loop, streams each step live to a React UI, and pauses for human approval before creating a pull request.

## Why this is different from similar AI agents

Most “AI code review” demos are a single chat prompt over a pasted diff. This project is an **orchestrated state machine**, not a one-shot completion:

- **Dual-layer RAG** grounds the review in real nearby code (beyond the diff) and in OWASP / policy rules, so findings cite actual lines and rules instead of generic advice.
- **A test-and-fix loop** retries the refactor when sandbox tests fail, up to a fixed limit, instead of returning one unchecked suggestion.
- **Server-Sent Events** push each agent step (and model tokens) to the UI as they happen.
- **Human-in-the-loop** stops the graph before a pull request is created until you approve it.

## Plan

Build in this order so each piece can be tested before the next one is added.

1. **Core agent (Python / LangGraph)** — in progress. Security, refactor, sandbox retry, and local nearby-code search run. Still to do: vector-database RAG and richer diff parsing.
2. **FastAPI + SSE** — done for node updates. `POST /api/agent/stream` streams each step; token-level streaming and `/approve` come later.
3. **React UI** — done for the first studio pass (form, SSE hook, Monaco diff, sidebar).
4. **Graph view and approval** — sidebar + modal are in the UI; wiring Approve to create a real GitHub PR is still ahead.

Stack: Python, FastAPI, LangGraph, Qdrant (or pgvector) for the two RAG layers, React with Tailwind and the Monaco diff editor. v1 reviews Python changes and runs tests in a temp folder; GitHub PR creation and stricter sandbox isolation come after the loop works locally.
