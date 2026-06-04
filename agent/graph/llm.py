from django.conf import settings
from langchain_openrouter import ChatOpenRouter


def get_llm(temperature: float = 0.3) -> ChatOpenRouter:
    """Factory do chat model (OpenRouter).

    Centralizado aqui pra ser compartilhado por `nodes` e `subagents`
    sem import circular.
    """
    return ChatOpenRouter(
        model=settings.OPENROUTER_MODEL,
        openrouter_api_key=settings.OPENROUTER_API_KEY,
        temperature=temperature,
    )
