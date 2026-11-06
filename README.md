# Agentic PR Review Studio

**Status:** Work in progress. Backend skeleton is in place; agent logic, streaming, and the UI are not built yet.

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

1. **Core agent (Python / LangGraph)** — shared review state, then the node sequence: ingest the diff, retrieve RAG context, security audit, refactor, run sandbox tests. If tests fail and retries remain, loop back to refactor.
2. **FastAPI + SSE** — `POST /api/agent/stream` runs that graph and streams node and token events to the browser. Approval is a separate REST call, not GraphQL.
3. **React UI** — split-screen Monaco diff (original vs refactored) and a client that consumes the event stream.
4. **Graph view and approval** — sidebar of node states (idle, running, passed) and a modal that resumes the graph only after you approve PR creation.

Stack: Python, FastAPI, LangGraph, Qdrant (or pgvector) for the two RAG layers, React with Tailwind and the Monaco diff editor. v1 reviews Python changes and runs tests in a temp folder; GitHub PR creation and stricter sandbox isolation come after the loop works locally.
