"""Sync review runner persists a paused review without SSE."""

from app.services.review_runner import run_review_until_interrupt
from app.services.review_store import review_store


def setup_function() -> None:
    review_store.clear()


def test_run_review_until_interrupt_saves_store():
    result = run_review_until_interrupt(
        thread_id="runner-1",
        diff_text="def add(a, b):\n    return a + b\n",
    )
    assert result.error == ""
    assert result.awaiting_approval is True
    stored = review_store.get("runner-1")
    assert stored is not None
    assert stored.diff_text.startswith("diff --git") or "add" in stored.diff_text
