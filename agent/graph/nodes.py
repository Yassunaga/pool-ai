from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from .llm import get_llm
from .models import ConversationState, Decision, Lead
from .prompts import (
    ASK_AREA_SCRIPT,
    ASK_NAME_SCRIPT,
    DECIDE_PROMPT,
    EXTRACTOR_PROMPT,
    GREET_SCRIPT,
    HANDOFF_MESSAGES,
    RURAL_SCRIPT,
    URBAN_SCRIPT,
)
from .subagents import faq_subagent

# Mapa action → mensagens canônicas (emitidas VERBATIM, sem passar pelo LLM).
SCRIPTS: dict[str, list[str]] = {
    'greeting': GREET_SCRIPT,
    'ask_area': [ASK_AREA_SCRIPT],
    'ask_name': [ASK_NAME_SCRIPT],
    'pitch_urban': URBAN_SCRIPT,
    'pitch_rural': RURAL_SCRIPT,
    'handoff': HANDOFF_MESSAGES,
}


# =============================================================================
# extract — preenche o Lead a partir da conversa (merge idempotente)
# =============================================================================
def extract(state: ConversationState) -> dict:
    """Extrai name/area_type. Só sobrescreve com valores não-null do LLM,
    pra não apagar dado já coletado."""
    llm = get_llm(temperature=0.0).with_structured_output(Lead)
    result = llm.invoke([SystemMessage(content=EXTRACTOR_PROMPT), *state.messages])

    merged = state.lead.model_dump()
    for key, value in result.model_dump().items():
        if value is not None:
            merged[key] = value

    return {'lead': Lead(**merged)}


# =============================================================================
# respond — o LLM decide a ação do turno; o código emite.
#   - script   → texto canônico VERBATIM (fidelidade às regras de preço/prazo)
#   - freeform → o LLM improvisa (ex.: saudar um cliente que já voltou)
#   - faq      → subagente em contexto isolado
# A decisão recebe `lead` e `skill_path` como contexto, pro LLM saber o que já
# fez sem reler/adivinhar pelo histórico cru.
# =============================================================================
def respond(state: ConversationState) -> dict:
    llm = get_llm(temperature=0.3).with_structured_output(Decision)
    decision = llm.invoke(
        [
            SystemMessage(content=DECIDE_PROMPT.format(
                name=state.lead.name or 'desconhecido',
                area_type=state.lead.area_type or 'não identificado',
                skill_path=', '.join(state.skill_path) or 'nada ainda',
            )),
            *state.messages,
        ]
    )

    # Safety net: nunca re-disparar handoff (evento terminal).
    if decision.action == 'handoff' and 'handoff' in state.skill_path:
        decision.action = 'freeform'

    if decision.action == 'faq':
        result = faq_subagent.invoke(
            {'messages': [HumanMessage(content=_last_user_text(state))]}
        )
        return {
            'messages': [AIMessage(content=result['messages'][-1].content)],
            'skill_path': ['faq'],
        }

    if decision.action == 'freeform':
        return {
            'messages': [AIMessage(content=decision.text or '')],
            'skill_path': ['freeform'],
        }

    # Script: emite as mensagens canônicas verbatim.
    messages = [AIMessage(content=m) for m in SCRIPTS[decision.action]]
    return {
        'messages': messages,
        'skill_path': [decision.action],
    }


def _last_user_text(state: ConversationState) -> str:
    return state.messages[-1].content if state.messages else ''
