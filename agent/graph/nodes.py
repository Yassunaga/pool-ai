import json
from typing import Literal

from django.conf import settings
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .prompts import CLOSER_SYSTEM_PROMPT, EXTRACTOR_SYSTEM_PROMPT, SELLER_SYSTEM_PROMPT
from .state import REQUIRED_FIELDS, CollectedData, ConversationState


def _llm(temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=temperature,
    )


def _missing_fields(collected: CollectedData) -> list[str]:
    return [field for field in REQUIRED_FIELDS if not collected.get(field)]


def _format_collected(collected: CollectedData) -> str:
    if not collected:
        return '(nothing yet)'
    return '\n'.join(f'- {key}: {value}' for key, value in collected.items() if value)


def _format_missing(missing: list[str]) -> str:
    if not missing:
        return '(none)'
    return '\n'.join(f'- {field}' for field in missing)


def extract_info(state: ConversationState) -> dict:
    """Pull any newly-revealed lead fields out of the latest user message."""
    last_user_message = next(
        (m for m in reversed(state['messages']) if isinstance(m, HumanMessage)),
        None,
    )
    if last_user_message is None:
        return {}

    response = _llm(temperature=0.0).invoke([
        SystemMessage(content=EXTRACTOR_SYSTEM_PROMPT),
        HumanMessage(content=last_user_message.content),
    ])

    try:
        parsed = json.loads(response.content)
    except (json.JSONDecodeError, TypeError):
        return {}

    if not isinstance(parsed, dict):
        return {}

    current = dict(state.get('collected_data') or {})
    for key in REQUIRED_FIELDS:
        value = parsed.get(key)
        if isinstance(value, str) and value.strip():
            current[key] = value.strip()

    return {'collected_data': current}


def route_after_extract(state: ConversationState) -> Literal['ask_question', 'close_deal']:
    return 'close_deal' if not _missing_fields(state.get('collected_data') or {}) else 'ask_question'


def ask_question(state: ConversationState) -> dict:
    collected = state.get('collected_data') or {}
    missing = _missing_fields(collected)

    system = SELLER_SYSTEM_PROMPT.format(
        collected_summary=_format_collected(collected),
        missing_summary=_format_missing(missing),
    )

    response = _llm(temperature=0.5).invoke(
        [SystemMessage(content=system), *state['messages']],
    )
    return {'messages': [AIMessage(content=response.content)], 'is_complete': False}


def close_deal(state: ConversationState) -> dict:
    collected = state.get('collected_data') or {}
    system = CLOSER_SYSTEM_PROMPT.format(collected_summary=_format_collected(collected))

    response = _llm(temperature=0.4).invoke(
        [SystemMessage(content=system), *state['messages']],
    )
    return {'messages': [AIMessage(content=response.content)], 'is_complete': True}
