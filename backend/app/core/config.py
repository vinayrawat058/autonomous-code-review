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

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_code: str = "codebase"
    qdrant_collection_policy: str = "policies"

    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | list[str]) -> list[str] | str:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    # LangGraph retry loop max (PDF: 3)
    max_refactor_iterations: int = 3


settings = Settings()
