# Agentic PR Review Studio

**Status:** Work in progress. The core review path runs locally. Streaming and the UI are not built yet.

## Done so far

The agent walks five steps: ingest the diff, load context, security audit, refactor, then sandbox tests.

- **Security audit** sends the diff and the OWASP rulebook to Groq and returns a cited finding.
- **Refactor** rewrites that diff from the finding. On the sample login change, the pasted username becomes a `?` placeholder.
- **Sandbox** runs pytest on the rewrite in a temporary folder. A failure goes back to refactor, up to three tries.
- **Ingest** stores the pasted diff. **Retrieve** loads the whole rulebook file. Nearby-code search and a vector database are not built yet.

The API key stays in `backend/.env` and is not committed. Run the path from `backend` with `.venv\Scripts\python.exe scripts\run_stub_review.py`.

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

1. **Core agent (Python / LangGraph)** — in progress. Security, refactor, and the sandbox retry loop run. Still to do: parse real diffs, search nearby code, and index the rulebook in a vector database.
2. **FastAPI + SSE** — `POST /api/agent/stream` runs that graph and streams node and token events to the browser. Approval is a separate REST call, not GraphQL.
3. **React UI** — split-screen Monaco diff (original vs refactored) and a client that consumes the event stream.
4. **Graph view and approval** — sidebar of node states (idle, running, passed) and a modal that resumes the graph only after you approve PR creation.

Stack: Python, FastAPI, LangGraph, Qdrant (or pgvector) for the two RAG layers, React with Tailwind and the Monaco diff editor. v1 reviews Python changes and runs tests in a temp folder; GitHub PR creation and stricter sandbox isolation come after the loop works locally.
