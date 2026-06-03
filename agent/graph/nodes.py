from django.conf import settings
from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .models import ConversationState
from .prompts import SELLER_PROMPT


def _llm(temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=temperature,
    )


def agent(state: ConversationState) -> dict:
    response = _llm().invoke(
        [SystemMessage(content=SELLER_PROMPT), *state.messages]
    )
    return {'messages': [AIMessage(content=response.content)]}
