import logging

from django.conf import settings
from langchain_core.messages import AIMessage, HumanMessage

from ..graph import get_graph
from ..models import Lead
from .evolution_service import send_text

logger = logging.getLogger(__name__)


def send_message(session_id: str, message: str) -> dict:
    """Run one turn of the sales conversation for the given session."""
    graph = get_graph()
    config = {'configurable': {'thread_id': session_id}}

    result = graph.invoke(
        {'messages': [HumanMessage(content=message)]},
        config=config,
    )

    _sync_lead(session_id, result)

    replies: list[str] = []
    for m in reversed(result['messages']):
        if isinstance(m, AIMessage):
            replies.append(m.content)
        else:
            break
    replies.reverse()

    return {
        'session_id': session_id,
        'replies': replies,
    }


def _sync_lead(session_id: str, result: dict) -> None:
    """Espelha o lead do checkpoint num registro Django (visível no admin) e,
    quando o cliente pede atendimento humano, notifica o time UMA única vez.

    Qualquer falha aqui é logada e engolida: o espelhamento nunca pode impedir
    a resposta de chegar ao cliente."""
    graph_lead = result.get('lead')
    handoff = bool(result.get('handoff_requested'))

    try:
        row, _ = Lead.objects.update_or_create(
            session_id=session_id,
            defaults={
                'name': (graph_lead.name if graph_lead else '') or '',
                'area_type': (graph_lead.area_type if graph_lead else '') or '',
                'handoff_requested': handoff,
            },
        )
        if handoff and not row.handoff_notified and _notify_handoff(row):
            row.handoff_notified = True
            row.save(update_fields=['handoff_notified'])
    except Exception:
        logger.exception('falha ao sincronizar lead da sessão %s', session_id)


def _notify_handoff(row: Lead) -> bool:
    """Avisa o time (via WhatsApp) que um lead pediu atendimento humano.

    Retorna True só quando o aviso foi de fato entregue, para o chamador marcar
    ``handoff_notified`` — assim uma falha tenta de novo no próximo turno."""
    number = settings.HANDOFF_NOTIFY_NUMBER
    if not number:
        logger.warning(
            'handoff solicitado (sessão %s) mas HANDOFF_NOTIFY_NUMBER não está '
            'configurado — nenhum humano foi avisado',
            row.session_id,
        )
        return False

    text = (
        'Novo lead pedindo atendimento humano:\n'
        f'WhatsApp: {row.session_id}\n'
        f'Nome: {row.name or "não informado"}\n'
        f'Área: {row.get_area_type_display() or "não identificada"}'
    )
    try:
        send_text(number, text)
        return True
    except Exception:
        logger.exception('falha ao notificar handoff da sessão %s', row.session_id)
        return False
