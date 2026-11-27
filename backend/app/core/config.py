"""
Application settings loaded from environment variables / .env.

Keeps secrets and tunable knobs out of hard-coded values.
"""

from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    # Free Groq key from https://console.groq.com — no credit card on the free plan.
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "openai/gpt-oss-20b"

    # Vector RAG — default is embedded Qdrant on disk (no Docker).
    # Set QDRANT_URL to use a remote server instead; QDRANT_PATH=:memory: for tests.
    qdrant_url: str = ""
    qdrant_path: str = ".qdrant"
    qdrant_collection_code: str = "codebase"
    qdrant_collection_policy: str = "policies"
    embedding_backend: str = "fastembed"  # fastembed | hash
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384  # used by hash backend; fastembed probes real size
    rag_top_k_code: int = 4
    rag_top_k_policy: int = 4
    rag_max_chars: int = 4000

    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | list[str]) -> list[str] | str:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    # LangGraph retry loop max (PDF: 3)
    max_refactor_iterations: int = 3

    # Checkpoint persistence for interrupt_before resume (sqlite survives API restart)
    checkpoint_backend: str = "sqlite"  # sqlite | memory
    checkpoint_sqlite_path: str = ".checkpoints/langgraph.sqlite"

    # How long a paused review may wait for Approve/Reject (seconds)
    approve_ttl_seconds: int = 3600

    # Ingest limits for pasted diffs / plain code
    max_diff_chars: int = 200_000
    max_diff_files: int = 40

    # GitHub PR creation on approve (optional — without a token, approve is a dry run)
    github_token: str = ""
    github_default_owner: str = ""
    github_default_repo: str = ""
    github_default_base: str = "main"

    # GitHub App + webhook (review real PRs instead of paste-only)
    github_app_id: str = ""
    github_app_private_key: str = ""  # PEM with \n escapes, or use path below
    github_app_private_key_path: str = ""
    github_app_installation_id: str = ""  # fallback if payload has no installation
    github_webhook_secret: str = ""
    github_webhook_require_secret: bool = True
    github_webhook_review_drafts: bool = False
    github_webhook_async: bool = True  # return 202 and review in background
    github_webhook_post_review: bool = True  # True=PR review, False=issue comment


settings = Settings()
