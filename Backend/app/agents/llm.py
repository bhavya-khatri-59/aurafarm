import groq
from langchain_core.runnables import Runnable
from langchain_groq import ChatGroq

from app.config import get_settings


def make_llm(model: str, temperature: float = 0.3) -> ChatGroq:
    settings = get_settings()
    # No client-side retries: Groq's 429 retry-after can be ~20 s, which is worse for a live user
    # than a quick "busy, try again". retry_on_groq_error still retries a malformed tool call once.
    return ChatGroq(
        model=model,
        api_key=settings.groq_api_key,
        temperature=temperature,
        max_retries=0,
        timeout=45,
        max_tokens=settings.max_reply_tokens,
    )


def retry_on_groq_error(runnable: Runnable) -> Runnable:
    """Retries once on Groq API errors. Groq validates tool calls server-side and fails the whole
    request when a model emits a malformed one (e.g. missing arguments); a second sample usually
    succeeds."""
    return runnable.with_retry(retry_if_exception_type=(groq.BadRequestError, groq.APIError), stop_after_attempt=2)
