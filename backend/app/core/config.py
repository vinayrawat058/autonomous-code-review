"""
Application settings loaded from environment variables / .env.

Keeps secrets and tunable knobs out of hard-coded values.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_code: str = "codebase"
    qdrant_collection_policy: str = "policies"

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # LangGraph retry loop max (PDF: 3)
    max_refactor_iterations: int = 3


settings = Settings()
