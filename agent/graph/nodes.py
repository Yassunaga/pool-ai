from django.conf import settings
from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .prompts import (
    EXTRACTOR_SYSTEM_PROMPT,
    FAQ_PROMPT,
    GREET_PROMPT,
    SELLER_PROMPT,
    SUPERVISOR_PROMPT,
)
from .models import (
    REQUIRED_FIELDS,
    ConversationState,
    ExtractedData,
    FaqResponse,
    GreetResponse,
    SupervisorRoute,
)
from .utils import _format_collected_context, _format_summaries


def _llm(temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=temperature,
    )


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


def supervisor(state: ConversationState) -> dict:
    """Classifica a intenção do cliente e escolhe a próxima skill.

    Não emite mensagem ao cliente — apenas grava `intent` e
    `confidence_last_route` no state. O roteamento real acontece nas
    `conditional_edges` do grafo, lendo `state['intent']`.
    """
    collected = state.get('collected_data') or {}
    collected_summary, missing_summary = _format_summaries(collected)

    llm = _llm(temperature=0.0).with_structured_output(SupervisorRoute)
    decision = llm.invoke(
        [
            SystemMessage(content=SUPERVISOR_PROMPT.format(
                is_greeted='sim' if state.get('is_greeted') else 'não',
                collected_summary=collected_summary,
                missing_summary=missing_summary,
                lead_stage=state.get('lead_stage') or 'novo',
            )),
            *state['messages'],
        ]
    )

    return {
        'intent': decision.skill,
        'confidence_last_route': decision.confidence,
    }


def greet(state: ConversationState) -> dict:
    """Saudação inicial — abre o terreno, NÃO qualifica ainda.

    Gera 2-3 mensagens curtas via LLM (structured output) e marca o
    lead como `qualificando` para o próximo turn.
    """
    llm = _llm(temperature=0.7).with_structured_output(GreetResponse)
    result = llm.invoke([SystemMessage(content=GREET_PROMPT)])

    return {
        'messages': [AIMessage(content=chunk) for chunk in result.chunks],
        'is_greeted': True,
        'lead_stage': 'qualificando',
        'skill_path': ['greet'],
    }


def faq(state: ConversationState) -> dict:
    """Responde dúvidas técnicas/conceituais do cliente.

    Sem RAG nesta versão — o conhecimento base está embutido no prompt.
    Responde APENAS o que o cliente perguntou; não emenda qualificação.
    """
    collected = state.get('collected_data') or {}
    collected_context = _format_collected_context(collected)

    llm = _llm(temperature=0.3).with_structured_output(FaqResponse)
    result = llm.invoke(
        [
            SystemMessage(content=FAQ_PROMPT.format(
                collected_context=collected_context,
            )),
            *state['messages'],
        ]
    )

    return {
        'messages': [AIMessage(content=chunk) for chunk in result.chunks],
        'skill_path': ['faq'],
    }
