from langchain_groq import ChatGroq

from app.config import get_settings


def make_llm(model: str, temperature: float = 0.3) -> ChatGroq:
    settings = get_settings()
    return ChatGroq(model=model, api_key=settings.groq_api_key, temperature=temperature, max_retries=2)
