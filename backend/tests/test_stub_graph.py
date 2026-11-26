"""The review graph walks each node and pauses before create_pr until resumed."""

from app.agent.graph import build_graph
from langgraph.checkpoint.memory import MemorySaver


def test_stub_graph_pauses_before_create_pr_then_resumes():
    memory = MemorySaver()
    graph = build_graph(checkpointer=memory, interrupt=True)
    config = {"configurable": {"thread_id": "stub-1"}}
    seen: list[str] = []

    for update in graph.stream(
        {
            "diff": "def add(a, b):\n    return a + b\n",
            "iteration": 0,
            "thread_id": "stub-1",
            "approved": False,
        },
        config=config,
    ):
        seen.extend(key for key in update.keys() if key != "__interrupt__")

    assert seen == ["ingest", "retrieve", "security", "refactor", "sandbox"]
    assert "create_pr" not in seen
    assert graph.get_state(config).next == ("create_pr",)

    graph.update_state(
        config,
        {
            "approved": True,
            "pr_owner": "vinayrawat058",
            "pr_repo": "autonomous-code-review",
            "pr_base_branch": "main",
        },
    )

    for update in graph.stream(None, config=config):
        seen.extend(key for key in update.keys() if key != "__interrupt__")

    assert seen[-1] == "create_pr"
    assert graph.get_state(config).next == ()
