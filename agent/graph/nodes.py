from django.conf import settings
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END

from .prompts import EXTRACTOR_SYSTEM_PROMPT, SELLER_PROMPT, WORKFLOW_CLASSIFIER_PROMPT
from .models import (
    FIELD_LABELS, REQUIRED_FIELDS, CollectedData, ConversationState, ExtractedData,
    WorkflowClassification,
)
from .workflow import FREE_FORM_STEP_ID, INITIAL_STEP_ID, WORKFLOW


def _llm(temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=temperature,
    )

def router(state: ConversationState) -> str:
    if state.get('is_greeted', False):
        return 'chatbot'

    return 'greetings'

def greetings(state: ConversationState) -> dict:
    GREETING_MESSAGES: tuple[str, ...] = (
        'Oi! Bem Vindo à Natural Engenharia! Empresa referência no segmento de perfuração de poços artesianos!',
        'Vi que está interessado em ter seu próprio poço artesiano e não ter mais problemas para ter água! Esse é o caminho certo!',
        'Para começar a te ajudar a não ter mais falta de água em nenhum momento, preciso saber: você vai querer um poço artesiano na cidade ou na área rural?',
    )

    return {
        'messages': [AIMessage(content=message) for message in GREETING_MESSAGES],
        'is_greeted': True,
    }


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


def _format_summaries(collected: CollectedData) -> tuple[str, str]:
    collected_lines = []
    missing_lines = []
    for field in REQUIRED_FIELDS:
        label = FIELD_LABELS[field]
        value = collected.get(field)
        if value:
            collected_lines.append(f'- {label}: {value}')
        else:
            missing_lines.append(f'- {label}')

    collected_summary = '\n'.join(collected_lines) or '- (nenhuma ainda)'
    missing_summary = '\n'.join(missing_lines) or '- (todas coletadas)'
    return collected_summary, missing_summary


def chatbot(state: ConversationState) -> dict:
    collected = state.get('collected_data') or {}
    collected_summary, missing_summary = _format_summaries(collected)
    prompt = SELLER_PROMPT.format(
        collected_summary=collected_summary,
        missing_summary=missing_summary,
    )

    response = _llm(temperature=0.0).invoke(
        [
            SystemMessage(content=prompt),
            *state['messages'],
        ]
    )

    return {
        'messages': [AIMessage(content=response.content)],
    }
