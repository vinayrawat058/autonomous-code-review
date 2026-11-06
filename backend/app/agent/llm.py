"""Chat model pointed at Groq's free, OpenAI-style API."""

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings


def get_chat_model() -> ChatOpenAI:
    return ChatOpenAI(
        model_name=settings.llm_model,
        openai_api_key=settings.groq_api_key,
        openai_api_base=settings.groq_base_url,
        temperature=0,
        max_tokens=500,
        use_responses_api=False,
    )


def complete(prompt: str) -> str:
    """Send one prompt and return the model's text."""
    message = get_chat_model().invoke([HumanMessage(content=prompt)])
    content = message.content
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(str(block.get("text") or ""))
        return "\n".join(part for part in parts if part).strip()
    return str(content).strip()
