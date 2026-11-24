"""Chat model pointed at Groq's free, OpenAI-style API — with live token streaming."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings


def get_chat_model(*, streaming: bool = False) -> ChatOpenAI:
    return ChatOpenAI(
        model_name=settings.llm_model,
        openai_api_key=settings.groq_api_key,
        openai_api_base=settings.groq_base_url,
        temperature=0,
        max_tokens=2000,
        streaming=streaming,
        use_responses_api=False,
    )


def _content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(str(block.get("text") or ""))
            else:
                text = getattr(block, "text", None)
                if text:
                    parts.append(str(text))
        return "".join(parts)
    return str(content)


def _try_stream_writer():
    """Return LangGraph's custom stream writer when running inside a graph."""
    try:
        from langgraph.config import get_stream_writer

        return get_stream_writer()
    except Exception:
        return None


def iter_token_chunks(prompt: str) -> Iterator[str]:
    """Yield text chunks from Groq as they arrive."""
    model = get_chat_model(streaming=True)
    for chunk in model.stream([HumanMessage(content=prompt)]):
        piece = _content_to_text(getattr(chunk, "content", None))
        if piece:
            yield piece


def stream_complete(prompt: str, *, node: str = "llm") -> str:
    """
    Stream one prompt through Groq.

    While the LangGraph review is running, each chunk is pushed as a custom
    stream event (`llm_start` / `token` / `llm_end`) so FastAPI can forward
    them over SSE.
    """
    writer = _try_stream_writer()
    if writer is not None:
        writer({"type": "llm_start", "node": node})

    parts: list[str] = []
    for piece in iter_token_chunks(prompt):
        parts.append(piece)
        if writer is not None:
            writer({"type": "token", "node": node, "token": piece})

    full = "".join(parts).strip()
    if writer is not None:
        writer({"type": "llm_end", "node": node, "text": full})
    return full


def complete(prompt: str, *, node: str = "llm") -> str:
    """Send one prompt and return the model's text (streams tokens when in-graph)."""
    return stream_complete(prompt, node=node)
