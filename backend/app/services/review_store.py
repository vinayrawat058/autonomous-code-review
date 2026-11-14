"""In-memory store for finished reviews, keyed by thread_id."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock


@dataclass
class StoredReview:
    thread_id: str
    diff_text: str
    refactored_code: str
    findings: list[str] = field(default_factory=list)
    test_errors: list[str] = field(default_factory=list)
    iteration: int = 0
    repo_path: str | None = None


class ReviewStore:
    def __init__(self) -> None:
        self._items: dict[str, StoredReview] = {}
        self._lock = Lock()

    def save(self, review: StoredReview) -> None:
        with self._lock:
            self._items[review.thread_id] = review

    def get(self, thread_id: str) -> StoredReview | None:
        with self._lock:
            return self._items.get(thread_id)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


review_store = ReviewStore()
