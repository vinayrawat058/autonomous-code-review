"""Build the LangGraph checkpointer (Sqlite on disk by default, memory for tests)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver

from app.core.config import settings


def make_checkpointer():
    """
    Return a checkpointer instance.

    - memory  — in-process only (pytest / ephemeral)
    - sqlite  — durable file so paused reviews survive API restart
    """
    backend = (settings.checkpoint_backend or "sqlite").strip().lower()
    if backend == "memory":
        return MemorySaver()

    path = Path(settings.checkpoint_sqlite_path or ".checkpoints/langgraph.sqlite")
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    from langgraph.checkpoint.sqlite import SqliteSaver

    saver = SqliteSaver(conn)
    saver.setup()
    return saver
