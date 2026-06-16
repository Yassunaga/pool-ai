import logging

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, SystemMessage

from .guardrail import MAX_CHUNK_LEN, Violations, detect, sanitize
from .llm import get_llm
from .models import ChunkedReply, ConversationState, Lead

from .prompts import AGENT_PROMPT, EXTRACTOR_PROMPT, REGEN_PROMPT, GREETING_INSTRUCTION

from .tools import (
    make_build_budget,
    make_retrieve_lead_information,
)

logger = logging.getLogger(__name__)


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
    chamar tools (ex.: `build_budget` para o valor médio do orçamento). Recebe o
    `lead` já extraído como contexto para não repetir perguntas e adequar a fala
    ao caso (urbano x rural). No primeiro contato a saudação de abertura é
    injetada direto no system prompt (não depende de tool call).

    Roda um loop ReAct interno (create_agent); só a resposta final volta ao
    estado — as mensagens intermediárias de tool ficam no contexto isolado.

    Via `response_format=ChunkedReply`, a resposta final já sai dividida em
    mensagens curtas (chunks), enviadas separadamente no WhatsApp como na
    primeira versão da IA.

    A resposta NÃO é anexada às mensagens aqui: vai para `pending_chunks` e quem
    valida (guardrail determinístico) e anexa ao cliente é o nó `validate`.
    """
    system = AGENT_PROMPT.format(
        name=state.lead.name or 'desconhecido',
        area_type=state.lead.area_type or 'não identificado',
        handoff_status='já solicitado' if state.handoff_requested else 'ainda não solicitado',
        budget_status='já informado' if state.budget_given else 'ainda não informado',
    )

    # Primeiro contato (conversa nova): injeta a saudação de abertura no prompt em
    # vez de depender de uma tool call que o modelo pode esquecer de chamar.
    if len(state.messages) == 1:
        system = f'{system}\n\n{GREETING_INSTRUCTION}'

    runnable = create_agent(
        model=get_llm(temperature=0.3),
        tools=[
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
    budget_called = _build_budget_called(result['messages'])
    budget_delivered_now = budget_called and not state.budget_given

    return {
        'pending_chunks': chunks,
        'handoff_requested': state.handoff_requested or reply.request_handoff,
        'budget_given': state.budget_given or budget_called,
        'budget_delivered_now': budget_delivered_now,
    }


def validate(state: ConversationState) -> dict:
    """Guardrail determinístico pós-agent (nó entre `agent` e `END`).

    Regra de prompt nunca garante; aqui é onde de fato se impede que valor não
    autorizado, hífen ou chunk longo demais cheguem ao cliente. Lê os
    `pending_chunks` produzidos pelo `agent` e:

    * detecta violações (regex de `guardrail.py`, reaproveitado dos evals);
    * em violação, tenta UMA regeneração via LLM apontando o problema;
    * sanitiza deterministicamente o resultado (garantia final, mesmo que a
      regeneração falhe ou continue violando);
    * só então anexa as mensagens finais ao estado (`messages`).

    `budget_delivered_now` diz se UMA menção monetária é permitida neste turno
    (a tool `build_budget` entregou o valor agora) — qualquer outra é bloqueada.
    """
    chunks = list(state.pending_chunks)
    money_allowed = state.budget_delivered_now

    violations = detect(chunks, money_allowed)
    if violations.any:
        logger.warning('guardrail acionado (%s): %s', violations, chunks)
        regenerated = _regenerate(chunks, violations, money_allowed)
        if regenerated:
            chunks = regenerated
        # Sanitização determinística é a garantia final: vale mesmo após a regen.
        chunks = sanitize(chunks, money_allowed)

    return {
        'messages': [AIMessage(content=chunk) for chunk in chunks],
        'pending_chunks': [],
    }


def _regenerate(
    chunks: list[str], violations: Violations, money_allowed: bool
) -> list[str] | None:
    """Reescreve os chunks via LLM apontando as violações. Best-effort: se falhar,
    devolve None e o chamador cai na sanitização determinística."""
    money_clause = (
        'O valor médio do orçamento pode aparecer UMA única vez, não mais que isso.'
        if money_allowed
        else 'NUNCA cite qualquer valor monetário (R$, preço, faixa).'
    )
    prompt = REGEN_PROMPT.format(
        violations='\n'.join(f'- {d}' for d in violations.describe()),
        money_clause=f' {money_clause}',
        max_len=MAX_CHUNK_LEN,
        original='\n'.join(chunks),
    )
    try:
        llm = get_llm(temperature=0.0).with_structured_output(ChunkedReply)
        reply: ChunkedReply = llm.invoke(prompt)
        return [c.strip() for c in reply.chunks if c and c.strip()]
    except Exception:  # noqa: BLE001 — regen é best-effort; sanitização garante o invariante
        logger.exception('falha ao regenerar resposta no guardrail')
        return None


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
