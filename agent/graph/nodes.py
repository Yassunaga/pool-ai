from django.conf import settings
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from .prompts import EXTRACTOR_SYSTEM_PROMPT, SELLER_PROMPT
from .state import REQUIRED_FIELDS, ConversationState


class ExtractedData(BaseModel):
    location: str | None = Field(None, description='cidade ou localização do poço')
    depth: str | None = Field(None, description='profundidade estimada do poço')
    purpose: str | None = Field(None, description='finalidade do poço')
    flow_rate: str | None = Field(None, description='vazão desejada')
    terrain: str | None = Field(None, description='tipo de terreno')


def _llm(temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=temperature,
    )


def get_last_user_message(state: ConversationState):
    last_user_message = next(
        (m for m in reversed(state['messages']) if isinstance(m, HumanMessage)),
        None,
    )

    return last_user_message or {}

def extract_info(state: ConversationState) -> dict:
    llm = _llm(temperature=0.0).with_structured_output(ExtractedData)
    result = llm.invoke(
        [
            SystemMessage(content=EXTRACTOR_SYSTEM_PROMPT),
            *state['messages'],
        ]
    )

    collected = dict(state.get('collected_data') or {})
    for key, value in result.model_dump().items():
        if value:
            collected[key] = value

    is_complete = all(collected.get(field) for field in REQUIRED_FIELDS)

    return {
        'collected_data': collected,
        'is_complete': is_complete,
    }


def chatbot(state: ConversationState) -> dict:
    response = _llm(temperature=0.0).invoke(
        [
            SystemMessage(content=SELLER_PROMPT),
            *state['messages']
        ]
    )

    return {
        'messages': [AIMessage(content=response.content)],
    }
