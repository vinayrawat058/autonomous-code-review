"""The review graph walks every placeholder node once when tests pass."""

from app.agent.graph import build_graph


def test_stub_graph_visits_each_node_once():
    graph = build_graph()
    seen: list[str] = []
    for update in graph.stream({"diff": "def add(a, b):\n    return a + b\n", "iteration": 0}):
        seen.extend(update.keys())

    assert seen == ["ingest", "retrieve", "security", "refactor", "sandbox"]
