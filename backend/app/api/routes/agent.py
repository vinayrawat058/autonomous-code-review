"""
Agent HTTP routes.

Phase 2 will implement:
    POST /api/agent/stream  — SSE stream of LangGraph node/token events
    POST /api/agent/approve — resume graph after human-in-the-loop interrupt
"""

from fastapi import APIRouter

from app.models.schemas import PRPayload

router = APIRouter()


@router.post("/stream")
async def stream_agent(payload: PRPayload):
    """Placeholder — Phase 2 wires this to workflow.astream_events()."""
    return {
        "status": "not_implemented",
        "message": "SSE streaming lands in Phase 2. Payload accepted.",
        "thread_id": payload.thread_id,
    }


@router.post("/approve")
async def approve_agent(thread_id: str):
    """Placeholder — Phase 4 resumes the graph after human approval."""
    return {
        "status": "not_implemented",
        "thread_id": thread_id,
    }
