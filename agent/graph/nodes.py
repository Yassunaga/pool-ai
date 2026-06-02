from django.conf import settings
from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .prompts import (
    ASK_AREA_PROMPT,
    EXTRACTOR_SYSTEM_PROMPT,
    FAQ_PROMPT,
    GREET_PROMPT,
    HANDOFF_MESSAGES,
    RURAL_FLOW_SCRIPT,
    SELLER_PROMPT,
    SUPERVISOR_PROMPT,
    URBAN_FLOW_PROMPT,
)
from .models import (
    AskAreaResponse,
    CollectedData,
    ConversationState,
    FaqResponse,
    GreetResponse,
    SupervisorRoute,
    UrbanFlowResponse,
)
from .utils import _format_collected_context, _format_summaries


def _llm(temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=temperature,
    )


def extract(state: ConversationState) -> dict:
    """Extrai `area_type` da conversa, se presente.

    Rodando antes do supervisor (e só quando `area_type` ainda é None,
    conforme conditional edge do START). Merge idempotente: só sobrescreve
    se vier valor não-null do LLM.

    Não recebe `collected_data` no prompt para evitar viés de "preservar
    valor antigo" — assim o cliente pode mudar de ideia ("ah, é urbano").
    """
    llm = _llm(temperature=0.0).with_structured_output(CollectedData)
    result = llm.invoke(
        [
            SystemMessage(content=EXTRACTOR_SYSTEM_PROMPT),
            *state.messages,
        ]
    )

    collected = state.collected_data.model_dump()
    for key, value in result.model_dump().items():
        if value is not None:
            collected[key] = value

    return {
        'collected_data': CollectedData(**collected),
    }


def supervisor(state: ConversationState) -> dict:
    """Classifica a intenção do cliente e escolhe a próxima skill.

    Short-circuit determinístico: se o cliente ainda não foi cumprimentado,
    roteia direto pra `greet` sem chamar LLM (economiza 1 turn por sessão).

    Caso contrário, chama LLM com structured output. O LLM enxerga
    `is_greeted`, `area_type` e `lead_stage` no prompt.
    """
    # Short-circuit: primeira interação sempre é greet.
    if not state.is_greeted:
        return {
            'intent': 'greet',
            'confidence_last_route': 1.0,
        }

    llm = _llm(temperature=0.0).with_structured_output(SupervisorRoute)
    decision = llm.invoke(
        [
            SystemMessage(content=SUPERVISOR_PROMPT.format(
                is_greeted='sim',
                area_type=state.collected_data.area_type or 'ainda não identificado',
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
    """Saudação inicial — abre o terreno, NÃO qualifica ainda."""
    llm = _llm(temperature=0.7).with_structured_output(GreetResponse)
    result = llm.invoke([SystemMessage(content=GREET_PROMPT)])

    return {
        'messages': [AIMessage(content=chunk) for chunk in result.chunks],
        'is_greeted': True,
        'lead_stage': 'qualificando',
        'skill_path': ['greet'],
    }


def ask_area(state: ConversationState) -> dict:
    """Pergunta diretamente se o poço será em área urbana ou rural."""
    llm = _llm(temperature=0.5).with_structured_output(AskAreaResponse)
    result = llm.invoke(
        [
            SystemMessage(content=ASK_AREA_PROMPT),
            *state.messages,
        ]
    )

    return {
        'messages': [AIMessage(content=chunk) for chunk in result.chunks],
        'skill_path': ['ask_area'],
    }


def urban_flow(state: ConversationState) -> dict:
    """Continuação da conversa no caminho URBANO.

    Confirma área no primeiro turn pós-extract (mitiga hallucination do
    extractor) e segue com perguntas/considerações relevantes ao contexto.
    """
    llm = _llm(temperature=0.5).with_structured_output(UrbanFlowResponse)
    result = llm.invoke(
        [
            SystemMessage(content=URBAN_FLOW_PROMPT),
            *state.messages,
        ]
    )

    return {
        'messages': [AIMessage(content=chunk) for chunk in result.chunks],
        'skill_path': ['urban_flow'],
    }


def rural_flow(state: ConversationState) -> dict:
    """Caminho RURAL — script em um único turno.

    Primeira chamada: emite todas as mensagens do `RURAL_FLOW_SCRIPT`
    de uma vez (posicionamento, geofísica, valores, convite a agendar).
    Chamadas subsequentes: emite apenas a última mensagem (convite a
    agendar) — evita repetir todo o script caso o supervisor volte aqui
    sem o cliente ter avançado.

    Não chama LLM: o conteúdo é roteirizado pela equipe de vendas.
    """
    already_ran = 'rural_flow' in state.skill_path
    if already_ran:
        messages = [AIMessage(content=RURAL_FLOW_SCRIPT[-1])]
    else:
        messages = [AIMessage(content=msg) for msg in RURAL_FLOW_SCRIPT]

    return {
        'messages': messages,
        'skill_path': ['rural_flow'],
    }


def handoff(state: ConversationState) -> dict:
    """Passa o atendimento pra um humano — mensagens fixas.

    Determinístico de propósito: handoff é o sinal mais crítico da conversa
    (cliente pediu humano explicitamente ou supervisor identificou
    frustração). Qualquer variação criativa do LLM aqui vira risco — ex.
    prometer prazo de resposta que não vamos cumprir, ou puxar o cliente
    de volta pra qualificação. Marca `lead_stage='qualificado'` pra equipe
    externa identificar a fila.
    """
    return {
        'messages': [AIMessage(content=msg) for msg in HANDOFF_MESSAGES],
        'skill_path': ['handoff'],
        'lead_stage': 'qualificado',
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

    Atende intents que ainda não tem skill própria
    (pricing, schedule, handoff, close). Usa o SELLER_PROMPT como base.
    TODO: substituir por skills dedicadas, um intent por vez.
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
