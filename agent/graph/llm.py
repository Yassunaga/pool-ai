from django.conf import settings
from langchain_openrouter import ChatOpenRouter


def get_llm(temperature: float = 0.3, model: str | None = None) -> ChatOpenRouter:
    """Factory do chat model (OpenRouter).

    Centralizado aqui pra ser compartilhado pelos nós sem import circular.
    ``model`` permite sobrescrever o modelo padrão (ex.: transcrição de áudio ou
    visão de imagem usam modelos multimodais dedicados — ver media_service).
    """
    return ChatOpenRouter(
        model=model or settings.OPENROUTER_MODEL,
        openrouter_api_key=settings.OPENROUTER_API_KEY,
        temperature=temperature,
    )
