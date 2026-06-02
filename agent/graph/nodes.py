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
    CollectedData,
    ConversationState,
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
    llm = _llm(temperature=0.0).with_structured_output(CollectedData)
    result = llm.invoke(
        [
            SystemMessage(content=EXTRACTOR_SYSTEM_PROMPT),
            *state.messages,
        ]
    )

    collected = state.collected_data.model_dump()
    for key, value in result.model_dump().items():
        if value:
            collected[key] = value

    return {
        'collected_data': CollectedData(**collected),
    }


def supervisor(state: ConversationState) -> dict:
    """Classifica a intenção do cliente e escolhe a próxima skill.

    Não emite mensagem ao cliente — apenas grava `intent` e
    `confidence_last_route` no state. O roteamento real acontece nas
    `conditional_edges` do grafo, lendo `state.intent`.
    """
    collected_summary, missing_summary = _format_summaries(state.collected_data)

    llm = _llm(temperature=0.0).with_structured_output(SupervisorRoute)
    decision = llm.invoke(
        [
            SystemMessage(content=SUPERVISOR_PROMPT.format(
                is_greeted='sim' if state.is_greeted else 'não',
                collected_summary=collected_summary,
                missing_summary=missing_summary,
                lead_stage=state.lead_stage,
            )),
            *state.messages,
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
    collected_context = _format_collected_context(state.collected_data)

    llm = _llm(temperature=0.3).with_structured_output(FaqResponse)
    result = llm.invoke(
        [
            SystemMessage(content=FAQ_PROMPT.format(
                collected_context=collected_context,
            )),
            *state.messages,
        ]
    )

    return {
        'messages': [AIMessage(content=chunk) for chunk in result.chunks],
        'skill_path': ['faq'],
    }


def fallback(state: ConversationState) -> dict:
    """Catch-all temporário enquanto skills específicas não existem.

    Atende qualquer intent que ainda não tem skill própria
    (qualify, pricing, schedule, handoff, close). Usa o SELLER_PROMPT
    como base. TODO: substituir por skills dedicadas, um intent por vez.
    """
    collected_summary, missing_summary = _format_summaries(state.collected_data)
    prompt = SELLER_PROMPT.format(
        collected_summary=collected_summary,
        missing_summary=missing_summary,
    )

    response = _llm(temperature=0.3).invoke(
        [
            SystemMessage(content=prompt),
            *state.messages,
        ]
    )

    return {
        'messages': [AIMessage(content=response.content)],
        'skill_path': ['fallback'],
    }
