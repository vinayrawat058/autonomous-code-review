"""
Run the LangGraph review until interrupt_before create_pr (no SSE).

Used by the GitHub webhook path and other non-UI callers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.agent.diff_ingest import IngestError
from app.agent.graph import workflow
from app.services.review_store import StoredReview, review_store


@dataclass
class ReviewRunResult:
    thread_id: str
    findings: list[str] = field(default_factory=list)
    refactored_code: str = ""
    test_errors: list[str] = field(default_factory=list)
    iteration: int = 0
    changed_files: list[str] = field(default_factory=list)
    diff_kind: str = ""
    ingest_warnings: list[str] = field(default_factory=list)
    awaiting_approval: bool = False
    error: str = ""


def _clear_thread(thread_id: str) -> None:
    if workflow.checkpointer is not None:
        workflow.checkpointer.delete_thread(thread_id)
    review_store.delete(thread_id)


def run_review_until_interrupt(
    *,
    thread_id: str,
    diff_text: str,
    repo_path: str | None = None,
    test_code: str = "",
) -> ReviewRunResult:
    """
    Execute ingest → … → sandbox, pause before create_pr, and persist the review.
    """
    _clear_thread(thread_id)
    inputs: dict[str, Any] = {
        "diff": diff_text,
        "iteration": 0,
        "repo_path": repo_path,
        "test_code": test_code or "",
        "thread_id": thread_id,
        "approved": False,
    }
    config = {"configurable": {"thread_id": thread_id}}
    final: dict[str, Any] = dict(inputs)

    try:
        for mode, chunk in workflow.stream(
            inputs,
            config=config,
            stream_mode=["updates", "custom"],
        ):
            if mode != "updates" or not isinstance(chunk, dict):
                continue
            for node_name, node_update in chunk.items():
                if node_name == "__interrupt__":
                    continue
                if isinstance(node_update, dict):
                    final.update(node_update)
    except IngestError as exc:
        return ReviewRunResult(thread_id=thread_id, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        return ReviewRunResult(thread_id=thread_id, error=str(exc))

    snapshot = workflow.get_state(config)
    awaiting = "create_pr" in tuple(snapshot.next or ())
    if awaiting:
        workflow.update_state(
            config,
            {"paused_at": datetime.now(timezone.utc).isoformat()},
        )

    review_store.save(
        StoredReview(
            thread_id=thread_id,
            diff_text=str(final.get("diff") or diff_text),
            refactored_code=str(final.get("refactored_code") or ""),
            findings=list(final.get("findings") or []),
            test_errors=list(final.get("test_errors") or []),
            iteration=int(final.get("iteration") or 0),
            repo_path=repo_path,
        )
    )

    return ReviewRunResult(
        thread_id=thread_id,
        findings=list(final.get("findings") or []),
        refactored_code=str(final.get("refactored_code") or ""),
        test_errors=list(final.get("test_errors") or []),
        iteration=int(final.get("iteration") or 0),
        changed_files=list(final.get("changed_files") or []),
        diff_kind=str(final.get("diff_kind") or ""),
        ingest_warnings=list(final.get("ingest_warnings") or []),
        awaiting_approval=awaiting,
    )
