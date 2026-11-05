"""
FastAPI application entrypoint.

Run (later):
    uvicorn app.main:app --reload --app-dir backend
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import agent
from app.core.config import settings

app = FastAPI(
    title="Agentic PR Review Studio",
    version="0.1.0",
    description="Backend API for agentic PR review, security audit, and refactoring.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent.router, prefix="/api/agent", tags=["agent"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
