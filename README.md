# Agentic PR Review Studio

**Status:** Work in progress.

## Idea

Building a full-stack AI system that reviews pull-request diffs like a senior engineer: pull surrounding code and security-policy context (dual-layer RAG), run a LangGraph agent through security audit → refactor → sandbox test loops, stream live progress to a React UI, and pause for human approval before creating a PR.

## Why this is different from similar AI agents

Most “AI code review” demos are a single chat prompt over a pasted diff. This project is different because it is an **orchestrated state machine**, not a one-shot completion: dual-layer RAG grounds answers in real code and OWASP/policy rules, a cyclic test-and-fix loop can retry until tests pass (or hit a limit), Server-Sent Events expose each agent node live, and a human-in-the-loop checkpoint blocks PR creation until you approve.
