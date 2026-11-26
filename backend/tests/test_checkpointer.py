"""Durable Sqlite checkpointer can round-trip a paused thread."""

from pathlib import Path

from app.agent.checkpointer import make_checkpointer
from app.agent.graph import build_graph
from app.core.config import settings


def test_sqlite_checkpointer_survives_new_graph_instance(tmp_path, monkeypatch):
    db = tmp_path / "langgraph.sqlite"
    monkeypatch.setattr(settings, "checkpoint_backend", "sqlite")
    monkeypatch.setattr(settings, "checkpoint_sqlite_path", str(db))

    saver = make_checkpointer()
    graph = build_graph(checkpointer=saver, interrupt=True)
    config = {"configurable": {"thread_id": "persist-1"}}

    list(
        graph.stream(
            {
                "diff": "def add(a, b):\n    return a + b\n",
                "iteration": 0,
                "thread_id": "persist-1",
                "approved": False,
            },
            config=config,
        )
    )
    assert graph.get_state(config).next == ("create_pr",)
    assert Path(db).exists()

    # New graph instance, same sqlite file → still paused.
    saver2 = make_checkpointer()
    graph2 = build_graph(checkpointer=saver2, interrupt=True)
    assert graph2.get_state(config).next == ("create_pr",)
