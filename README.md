# Agentic PR Review Studio

**Status:** Work in progress. Backend agent + SSE API + React studio run end to end, including Approve → GitHub PR (dry-run without a token).

## Done so far

The agent walks five steps: ingest the diff, load context, security audit, refactor, then sandbox tests.

- **Security audit** sends the diff and the OWASP rulebook to Groq and returns a cited finding.
- **Refactor** rewrites that diff from the finding. On the sample login change, the pasted username becomes a `?` placeholder.
- **Sandbox** runs pytest on the rewrite in a temporary folder. A failure goes back to refactor, up to three tries.
- **Ingest** validates and normalizes the paste (BOM/CRLF stripped, size/file limits, null bytes rejected). Plain Python is wrapped as a synthetic unified diff; real `diff --git` hunks are cleaned and path-counted.
- **Retrieve (vector RAG)** embeds the local `repo_path` and `data/policies` into **Qdrant** (on-disk by default, no Docker) with **FastEmbed**, then pulls the nearest code chunks and OWASP sections for the diff.
- **FastAPI SSE** — `POST /api/agent/stream` runs the graph and pushes `started` / `node` / live `token` (plus `llm_start` / `llm_end`) / `done` events to the client.
- **React studio** — paste a diff, watch the graph sidebar update from SSE, see original vs rewrite in Monaco, then Approve / Reject.
- **Approve → PR** — LangGraph pauses with `interrupt_before=["create_pr"]` after sandbox. `POST /api/agent/approve` resumes the graph so the `create_pr` node opens the GitHub PR (dry-run without `GITHUB_TOKEN`). `POST /api/agent/reject` clears the paused thread. Checkpoints persist in Sqlite (survive API restart). Re-using a `thread_id` resets the checkpoint; empty diffs are rejected; failed sandbox blocks approve unless `force=true`; paused reviews expire after `APPROVE_TTL_SECONDS`; a second approve returns the existing PR.

Secrets stay in `backend/.env` and are not committed. Add a GitHub PAT with `repo` scope as `GITHUB_TOKEN` for a real PR.

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
- **Server-Sent Events** push each agent step and **Groq tokens live** (security + refactor) to the UI as they happen.
- **Human-in-the-loop** uses LangGraph `interrupt_before` so the graph itself pauses before `create_pr` until you approve.

## Plan

Build in this order so each piece can be tested before the next one is added.

1. **Core agent (Python / LangGraph)** — done for the local loop (security, refactor, sandbox retry, dual-layer Qdrant RAG). Approve parses full multi-file diffs and writes every touched file into the PR.
2. **FastAPI + SSE** — done for node updates. `POST /api/agent/stream` streams each step.
3. **React UI** — done (form, SSE hook, Monaco diff, sidebar).
4. **Approve → GitHub PR** — done (dry-run without token; real PR with `GITHUB_TOKEN`).

Stack: Python, FastAPI, LangGraph (Sqlite checkpointer + interrupt_before), Qdrant + FastEmbed for the two RAG layers, React with Tailwind and the Monaco diff editor. v1 reviews Python changes and streams LLM tokens over SSE. Optional next: Docker sandbox.
