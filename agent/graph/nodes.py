from django.conf import settings
from langchain_core.messages import AIMessage, SystemMessage
from langchain_openrouter import ChatOpenRouter

from .models import ConversationState
from .prompts import SELLER_PROMPT


def _llm(temperature: float = 0.3) -> ChatOpenRouter:
    return ChatOpenRouter(
        model=settings.OPENROUTER_MODEL,
        openrouter_api_key=settings.OPENROUTER_API_KEY,
        temperature=temperature,
    )


def agent(state: ConversationState) -> dict:
    response = _llm().invoke(
        [SystemMessage(content=SELLER_PROMPT), *state.messages]
    )
    return {'messages': [AIMessage(content=response.content)]}
