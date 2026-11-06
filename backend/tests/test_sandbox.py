"""Sandbox runs pytest and the graph retries the fixer when tests fail."""

from langgraph.graph import END, StateGraph

from app.agent.graph import _should_retry
from app.agent.nodes.execute_sandbox import execute_sandbox_tests
from app.agent.state import GraphState

TEST_CODE = """\
from solution import login

def test_username_is_not_pasted_into_the_query():
    result = login("alice")
    query = result[0] if isinstance(result, tuple) else result
    assert "alice" not in query
    assert "?" in query
"""


def test_concatenated_sql_fails():
    result = execute_sandbox_tests(
        {
            "refactored_code": 'def login(user):\n    return "SELECT " + user\n',
            "test_code": TEST_CODE,
        }
    )
    assert result["test_errors"]


def test_placeholder_query_passes():
    result = execute_sandbox_tests(
        {
            "refactored_code": 'def login(user):\n    return "SELECT ?", (user,)\n',
            "test_code": TEST_CODE,
        }
    )
    assert result["test_errors"] == []


def test_graph_retries_until_the_rewrite_passes():
    attempts = {"n": 0}

    def fake_refactor(state: GraphState) -> dict:
        attempts["n"] += 1
        iteration = (state.get("iteration") or 0) + 1
        if attempts["n"] == 1:
            code = 'def login(user):\n    return "SELECT " + user\n'
        else:
            code = 'def login(user):\n    return "SELECT ?", (user,)\n'
        return {"refactored_code": code, "iteration": iteration}

    graph = StateGraph(GraphState)
    graph.add_node("refactor", fake_refactor)
    graph.add_node("sandbox", execute_sandbox_tests)
    graph.set_entry_point("refactor")
    graph.add_edge("refactor", "sandbox")
    graph.add_conditional_edges(
        "sandbox",
        _should_retry,
        {"refactor": "refactor", "done": END},
    )
    seen: list[str] = []
    for update in graph.compile().stream(
        {"test_code": TEST_CODE, "iteration": 0, "test_errors": []}
    ):
        seen.extend(update.keys())

    assert attempts["n"] == 2
    assert seen == ["refactor", "sandbox", "refactor", "sandbox"]
