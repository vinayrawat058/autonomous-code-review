"""
LangGraph graph builder.

Wires nodes + edges into the state machine from the PDF:

    IngestDiff → RetrieveRAGContext → SecurityAudit → RefactorCode
         → ExecuteSandboxTests ──(fail, iteration < 3)──► RefactorCode
                              └──(pass)──► interrupt_before → CreatePullRequest

A MemorySaver checkpointer keeps state so /approve can resume after the pause.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.agent.nodes import create_pr, execute_sandbox, ingest, refactor, retrieve, security
from app.agent.state import GraphState
from app.core.config import settings

# Shared across stream + approve in this process.
_checkpointer = MemorySaver()


def _should_retry(state: GraphState) -> str:
    """Conditional edge after sandbox: retry refactor or wait for human approval."""
    errors = state.get("test_errors") or []
    iteration = state.get("iteration") or 0
    if errors and iteration < settings.max_refactor_iterations:
        return "refactor"
    return "await_approval"


def build_graph(*, checkpointer=None, interrupt: bool = True):
    """Create and compile the agent graph. Call this once at startup."""
    graph = StateGraph(GraphState)

    graph.add_node("ingest", ingest.ingest_diff)
    graph.add_node("retrieve", retrieve.retrieve_rag_context)
    graph.add_node("security", security.security_audit)
    graph.add_node("refactor", refactor.refactor_code)
    graph.add_node("sandbox", execute_sandbox.execute_sandbox_tests)
    graph.add_node("create_pr", create_pr.create_pull_request_node)

    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "retrieve")
    graph.add_edge("retrieve", "security")
    graph.add_edge("security", "refactor")
    graph.add_edge("refactor", "sandbox")
    graph.add_conditional_edges(
        "sandbox",
        _should_retry,
        {"refactor": "refactor", "await_approval": "create_pr"},
    )
    graph.add_edge("create_pr", END)

    memory = checkpointer if checkpointer is not None else _checkpointer
    compile_kwargs: dict = {"checkpointer": memory}
    if interrupt:
        compile_kwargs["interrupt_before"] = ["create_pr"]
    return graph.compile(**compile_kwargs)


# Compiled once for the FastAPI streaming + approve resume routes.
workflow = build_graph()
