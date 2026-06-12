from langchain.agents import create_agent
from langchain_core.messages import AIMessage, SystemMessage

from .llm import get_llm
from .models import ChunkedReply, ConversationState, Lead
from .prompts import AGENT_PROMPT, EXTRACTOR_PROMPT
from .tools import (
    greeting_instructions,
    make_build_budget,
    make_retrieve_lead_information,
)


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


def agent(state: ConversationState) -> dict:
    """Atendente flexível: lê o histórico + lead e responde naturalmente.

    Sem scripts; o LLM conduz a conversa guiado por persona/regras/fluxo e pode
    chamar tools (ex.: `greeting_instructions` para saber como abrir a conversa).
    Recebe o `lead` já extraído como contexto para não repetir perguntas e
    adequar a fala ao caso (urbano x rural).

    Roda um loop ReAct interno (create_agent); só a resposta final volta ao
    estado — as mensagens intermediárias de tool ficam no contexto isolado.

    Via `response_format=ChunkedReply`, a resposta final já sai dividida em
    mensagens curtas (chunks), enviadas separadamente no WhatsApp como na
    primeira versão da IA.
    """
    system = AGENT_PROMPT.format(
        name=state.lead.name or 'desconhecido',
        area_type=state.lead.area_type or 'não identificado',
        handoff_status='já solicitado' if state.handoff_requested else 'ainda não solicitado',
        budget_status='já informado' if state.budget_given else 'ainda não informado',
    )
    runnable = create_agent(
        model=get_llm(temperature=0.3),
        tools=[
            greeting_instructions,
            make_retrieve_lead_information(state.lead),
            make_build_budget(state.lead, state.budget_given),
        ],
        system_prompt=system,
        response_format=ChunkedReply,
    )
    result = runnable.invoke({'messages': list(state.messages)})

    reply: ChunkedReply = result['structured_response']
    chunks = [c.strip() for c in reply.chunks if c and c.strip()]

    # O valor passa a ser considerado "informado" assim que a tool `build_budget`
    # roda num turno em que o flag ainda era False (ou seja, ela entregou o número).
    budget_given = state.budget_given or (
        not state.budget_given and _build_budget_called(result['messages'])
    )

    return {
        'messages': [AIMessage(content=chunk) for chunk in chunks],
        'handoff_requested': state.handoff_requested or reply.request_handoff,
        'budget_given': budget_given,
    }


def _build_budget_called(messages: list) -> bool:
    """Detecta se a tool `build_budget` foi invocada no loop ReAct deste turno.

    O loop interno do `create_agent` não volta ao estado externo, mas suas
    mensagens (incluindo as tool calls e ToolMessages) ficam em
    ``result['messages']``. As mensagens de turnos anteriores que entram aqui são
    só Human/AI (os chunks), sem tool calls — então não geram falso positivo."""
    for m in messages:
        for tc in getattr(m, 'tool_calls', None) or []:
            name = tc.get('name') if isinstance(tc, dict) else getattr(tc, 'name', None)
            if name == 'build_budget':
                return True
        if getattr(m, 'name', None) == 'build_budget':
            return True
    return False
