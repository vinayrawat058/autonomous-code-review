"""
LangGraph graph builder.

Wires nodes + edges into the state machine from the PDF:

    IngestDiff → RetrieveRAGContext → SecurityAudit → RefactorCode
         → ExecuteSandboxTests ──(fail, iteration < 3)──► RefactorCode
                              └──(pass)──► (interrupt) → CreatePullRequest

Phase 1 implements the compile() path; Phase 4 adds interrupt_before.
"""

from langgraph.graph import END, StateGraph

from app.agent.nodes import execute_sandbox, ingest, refactor, retrieve, security
from app.agent.state import GraphState
from app.core.config import settings


def _should_retry(state: GraphState) -> str:
    """Conditional edge after sandbox: retry refactor or finish."""
    errors = state.get("test_errors") or []
    iteration = state.get("iteration") or 0
    if errors and iteration < settings.max_refactor_iterations:
        return "refactor"
    return "done"


def build_graph():
    """Create and compile the agent graph. Call this once at startup."""
    graph = StateGraph(GraphState)

    graph.add_node("ingest", ingest.ingest_diff)
    graph.add_node("retrieve", retrieve.retrieve_rag_context)
    graph.add_node("security", security.security_audit)
    graph.add_node("refactor", refactor.refactor_code)
    graph.add_node("sandbox", execute_sandbox.execute_sandbox_tests)

    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "retrieve")
    graph.add_edge("retrieve", "security")
    graph.add_edge("security", "refactor")
    graph.add_edge("refactor", "sandbox")
    graph.add_conditional_edges(
        "sandbox",
        _should_retry,
        {"refactor": "refactor", "done": END},
    )

    # Phase 4: add checkpointer + interrupt_before=["create_pr"]
    return graph.compile()


# Compiled once; imported by the API layer in Phase 2.
# workflow = build_graph()  # enable after nodes are real
